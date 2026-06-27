"""
管理面板.py —— RAG Agent 配置管理（Streamlit 界面）

启动方式：
    streamlit run 管理面板.py  --server.fileWatcherType none

功能：
  - 切换 LLM 模型 / Embedding 模型
  - 上传文档到知识库，切分入库
  - 开关工具、调整 Agent 行为
  - 修改保存到 config.json，重启聊天端后生效

注意：
  --server.fileWatcherType none 避免 Streamlit 文件监视器扫描
  transformers 包时触发 torchvision 缺失报错（不影响功能）
"""

import json
import os
from datetime import datetime
from pathlib import Path

# Streamlit 文件监视器会遍历所有已安装包的源码。
# transformers 内部有懒加载模块依赖 torchvision（本项目不需要），
# 触发时会报 ModuleNotFoundError。关掉文件监视器即可避免。
os.environ.setdefault("STREAMLIT_SERVER_FILE_WATCHER_TYPE", "none")

import streamlit as st
from dotenv import load_dotenv

# LangChain 1.0 把 RecursiveCharacterTextSplitter 移到了 langchain-classic 包
from langchain_classic.text_splitter import RecursiveCharacterTextSplitter

from src.config import load_config, PROJECT_DIR, CONFIG_PATH
from src.embedding import create_embedding
from src.knowledge.store import create_vectorstore, get_chroma_dir, get_doc_count

# ── 0. 项目路径 ────────────────────────────────────────────────────

load_dotenv(PROJECT_DIR / ".env")

# 页面基本设置
st.set_page_config(page_title="RAG 管理面板", page_icon="🛠️", layout="wide")
st.title("🛠️ RAG 助手 — 管理面板")
st.caption("修改配置后点「保存」，然后重启聊天端使其生效")


# ── 辅助函数 ──────────────────────────────────────────────────────


def save_config(cfg: dict) -> None:
    """保存配置到 config.json（管理面板独有逻辑）"""
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


# ── 加载当前配置 ──────────────────────────────────────────────────

cfg = load_config()
if not cfg:
    st.error("❌ 未找到 config.json，请先在项目目录运行一次 app.py 生成默认配置")
    st.stop()

# ── 侧边栏：状态摘要 ──────────────────────────────────────────────

with st.sidebar:
    st.header("📊 状态")
    doc_count = get_doc_count(cfg)
    if doc_count >= 0:
        st.metric("知识库片段数", doc_count)
    else:
        st.metric("知识库片段数", "N/A", help="数据库尚未初始化，上传第一篇文档后自动创建")

    enabled_tools = [k for k, v in cfg.get("tools", {}).items() if v.get("enabled")]
    st.metric("已启用工具", len(enabled_tools))

    st.divider()
    st.markdown(f"**LLM**: {cfg['llm']['model']}")
    st.markdown(f"**Embedding**: {cfg['embedding']['model_name']}")
    st.markdown(f"**温度**: {cfg['llm'].get('temperature', 0)}")

    st.divider()
    st.caption("💡 配置保存后需重启聊天端")
    st.caption("聊天端: `chainlit run app.py`")


# ── 主体：标签页 ──────────────────────────────────────────────────

tabs = st.tabs(["📡 LLM 模型", "🧠 Embedding", "📚 知识库", "🔧 工具集", "🤖 Agent 行为"])

# ──────────────────── Tab 1: LLM 模型 ─────────────────────────────
with tabs[0]:
    st.subheader("对话模型配置")

    col1, col2 = st.columns(2)
    with col1:
        cfg["llm"]["model"] = st.text_input(
            "模型名", value=cfg["llm"]["model"],
            help="传给 API 的 model 参数，DeepSeek 用 deepseek-chat"
        )
    with col2:
        cfg["llm"]["base_url"] = st.text_input(
            "API 地址", value=cfg["llm"]["base_url"],
            help="API 端点 URL"
        )

    col3, col4 = st.columns(2)
    with col3:
        cfg["llm"]["api_key_env"] = st.text_input(
            "API Key 环境变量名", value=cfg["llm"].get("api_key_env", "DEEPSEEK_API_KEY"),
            help="读取哪个环境变量的值作为 API Key"
        )
    with col4:
        api_val = os.getenv(cfg["llm"].get("api_key_env", "")) or ""
        masked = api_val[:8] + "..." + api_val[-4:] if len(api_val) > 12 else ("已设置" if api_val else "❌ 未设置")
        st.metric("当前 Key 状态", masked)

# ──────────────────── Tab 2: Embedding ─────────────────────────────
with tabs[1]:
    st.subheader("Embedding 模型配置")

    col1, col2 = st.columns(2)
    with col1:
        cfg["embedding"]["model_name"] = st.text_input(
            "模型名", value=cfg["embedding"]["model_name"],
            help="HuggingFace 模型 ID。中文推荐 BAAI/bge-small-zh-v1.5"
        )
    with col2:
        cfg["embedding"]["hf_endpoint"] = st.text_input(
            "HF 镜像站", value=cfg["embedding"].get("hf_endpoint", "https://hf-mirror.com"),
            help="国内用 https://hf-mirror.com，海外留空走官方站"
        )

    st.info(
        "⚠️ 更换 Embedding 模型后，需清空旧向量库（删除 chroma_db/ 目录）并重新索引文档。"
        "因为不同模型的向量维度不同，混用会导致检索失败。"
    )

# ──────────────────── Tab 3: 知识库 ────────────────────────────────
with tabs[2]:
    st.subheader("知识库文档管理")

    # — 分块参数 —
    col1, col2 = st.columns(2)
    with col1:
        cfg["knowledge_base"]["chunk_size"] = st.number_input(
            "分块大小（字符数）", value=cfg["knowledge_base"].get("chunk_size", 500),
            min_value=100, max_value=5000, step=100,
            help="每块最多多少字符。越小越精确但碎片化，越大越完整但检索模糊"
        )
    with col2:
        cfg["knowledge_base"]["chunk_overlap"] = st.number_input(
            "块间重叠（字符数）", value=cfg["knowledge_base"].get("chunk_overlap", 50),
            min_value=0, max_value=500, step=10,
            help="相邻两块之间重叠多少字符，防止关键信息刚好被切断"
        )

    # — 上传文档 —
    st.divider()
    st.markdown("### 📤 上传文档")

    uploaded_files = st.file_uploader(
        "支持 .txt / .md / .lua 文件，可多选",
        type=["txt", "md", "lua"],
        accept_multiple_files=True,
    )

    if uploaded_files:
        if st.button("📥 切分并入库", type="primary"):
            embedding = create_embedding(cfg)
            vs = create_vectorstore(cfg, embedding)
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=cfg["knowledge_base"]["chunk_size"],
                chunk_overlap=cfg["knowledge_base"]["chunk_overlap"],
                separators=["\n\n", "\n", "。", "；", "，", " ", ""],
            )

            added = 0
            for uf in uploaded_files:
                # 读文件内容
                try:
                    content = uf.read().decode("utf-8")
                except UnicodeDecodeError:
                    try:
                        uf.seek(0)
                        content = uf.read().decode("gbk")
                    except Exception:
                        st.warning(f"⚠️ 无法解码 {uf.name}，跳过")
                        continue

                chunks = splitter.split_text(content)
                # 给每个片段打上来源标记
                metadatas = [{"source": uf.name, "chunk": i} for i in range(len(chunks))]
                vs.add_texts(chunks, metadatas=metadatas)
                added += len(chunks)

                # 记录到 config
                cfg.setdefault("documents", []).append({
                    "filename": uf.name,
                    "chunks": len(chunks),
                    "indexed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                })

            save_config(cfg)
            st.success(f"✅ 入库完成，新增 {added} 个片段")
            st.rerun()

    # — 已索引文档列表 —
    st.divider()
    st.markdown("### 📋 已索引文档")

    docs = cfg.get("documents", [])
    if not docs:
        st.caption("暂无文档，上传文件并点击入库后出现在此")
    else:
        # 去重合并显示
        from collections import Counter
        doc_counter = Counter()
        for d in docs:
            doc_counter[d["filename"]] += d.get("chunks", 0)

        for fname, total_chunks in doc_counter.items():
            col_a, col_b = st.columns([3, 1])
            with col_a:
                st.markdown(f"📄 **{fname}**")
            with col_b:
                st.caption(f"{total_chunks} 片段")

    # — 危险操作 —
    st.divider()
    with st.expander("⚠️ 危险操作"):
        if st.button("🗑️ 清空知识库（删除所有已索引文档）", type="secondary"):
            import shutil
            chroma_dir = get_chroma_dir(cfg)
            if os.path.exists(chroma_dir):
                shutil.rmtree(chroma_dir)
            cfg["documents"] = []
            save_config(cfg)
            st.warning("知识库已清空")
            st.rerun()

# ──────────────────── Tab 4: 工具集 ────────────────────────────────
with tabs[3]:
    st.subheader("工具开关")
    st.caption("勾选后聊天端 Agent 即可调用该工具。新增工具需同时在 app.py 中注册函数。")

    tools_cfg = cfg.get("tools", {})
    for tool_name, tool_info in tools_cfg.items():
        col1, col2 = st.columns([1, 4])
        with col1:
            tool_info["enabled"] = st.checkbox(
                tool_name, value=tool_info.get("enabled", True),
                key=f"tool_{tool_name}"
            )
        with col2:
            st.caption(tool_info.get("description", ""))

    # 未来扩展提示
    st.divider()
    st.info(
        "💡 要新增工具：\n"
        "1. 在 `config.json` 的 `tools` 字段加一条记录\n"
        "2. 在 `app.py` 的 `_build_enabled_tools()` 中写对应的 `@langchain_tool` 函数\n"
        "3. 回到这个面板把开关打开"
    )

# ──────────────────── Tab 5: Agent 行为 ────────────────────────────
with tabs[4]:
    st.subheader("Agent 运行参数")

    # — 温度 —
    cfg["llm"]["temperature"] = st.slider(
        "温度 (Temperature)", min_value=0.0, max_value=2.0,
        value=float(cfg["llm"].get("temperature", 0.0)),
        step=0.1,
        help="0 = 最确定（适合事实性问答），越高越有创造性（适合头脑风暴）"
    )

    # — 检索策略 —
    st.divider()
    st.markdown("### 检索策略")
    cfg["agent"]["force_search_first"] = st.checkbox(
        "强制先检索再回答",
        value=cfg["agent"].get("force_search_first", True),
        help="开启：每次回答前必须先搜知识库。关闭：Agent 自己判断是否需要检索"
    )

    # — 外部知识 —
    cfg["agent"]["allow_external_knowledge"] = st.checkbox(
        "允许补充知识库外的知识",
        value=cfg["agent"].get("allow_external_knowledge", False),
        help="开启：知识库无结果时 Agent 可用自身训练知识补充，并标注来源。关闭：严格只回答知识库内容"
    )

    # — 额外规则 —
    st.divider()
    st.markdown("### 额外系统提示词")
    cfg["agent"]["system_prompt_extra"] = st.text_area(
        "追加规则（附加在自动生成的 prompt 末尾）",
        value=cfg["agent"].get("system_prompt_extra", ""),
        height=100,
        help="这里的内容会追加到自动生成的 system prompt 后面。留空则不追加。",
    )

    # — 预览 —
    st.divider()
    with st.expander("👁️ 预览当前生成的 System Prompt"):
        # 本地生成（与 app.py 中 _build_system_prompt 逻辑一致，避免跨进程 import）
        agent_preview = cfg.get("agent", {})
        preview_lines = ["你是一个基于知识库的问答助手。回答规则："]
        if agent_preview.get("force_search_first", True):
            preview_lines.append("1. 每次收到用户问题，**必须**先调用 search_knowledge_base 工具搜索知识库")
        if agent_preview.get("allow_external_knowledge", False):
            preview_lines.append("2. 如知识库信息不够，可基于自身知识补充，但需标注来源")
        else:
            preview_lines.append("2. 如工具返回「数据库中缺少相关信息」，告知用户无相关信息")
            preview_lines.append("3. **绝对禁止**编造知识库中没有的信息")
        extra = agent_preview.get("system_prompt_extra", "").strip()
        if extra:
            preview_lines.append(f"\n补充规则：{extra}")
        st.code("\n".join(preview_lines), language="text")


# ── 底部：保存按钮 ─────────────────────────────────────────────────

st.divider()
col_save, col_reset = st.columns([1, 5])
with col_save:
    if st.button("💾 保存配置", type="primary", use_container_width=True):
        save_config(cfg)
        st.success("✅ 配置已保存到 config.json，重启聊天端后生效")
        st.info("在终端执行 `chainlit run app.py` 或双击 启动rag助手.py")
with col_reset:
    st.caption("修改过的值在保存前不会生效。")
