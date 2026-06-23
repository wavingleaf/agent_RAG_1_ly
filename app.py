"""
app.py —— RAG Agent 聊天端（Chainlit 界面）

启动方式：
    chainlit run app.py

所有配置从 config.json 读取，不再硬编码。
通过管理面板（Streamlit）修改配置，重启此端后生效。
"""

import json
import os
from pathlib import Path

import chainlit as cl
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.tools import tool as langchain_tool
from langchain_chroma import Chroma
from langchain_core.messages import HumanMessage
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_openai import ChatOpenAI

# ── 0. 项目路径与配置加载 ──────────────────────────────────────────

PROJECT_DIR = Path(__file__).resolve().parent
CONFIG_PATH = PROJECT_DIR / "config.json"

load_dotenv(PROJECT_DIR / ".env")


def load_config() -> dict:
    """加载 config.json，不存在时用默认值兜底"""
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {
        "llm": {
            "provider": "deepseek",
            "model": "deepseek-chat",
            "base_url": "https://api.deepseek.com",
            "api_key_env": "DEEPSEEK_API_KEY",
            "temperature": 0.0,
        },
        "embedding": {
            "provider": "huggingface",
            "model_name": "all-MiniLM-L6-v2",
            "hf_endpoint": "https://hf-mirror.com",
        },
        "knowledge_base": {
            "persist_directory": "./chroma_db",
            "chunk_size": 500,
            "chunk_overlap": 50,
        },
        "tools": {
            "search_knowledge_base": {
                "enabled": True,
                "description": "在知识库中搜索与用户问题相关的文档。",
            }
        },
        "agent": {
            "force_search_first": True,
            "allow_external_knowledge": False,
            "system_prompt_extra": "",
        },
    }


# ── 1. 初始化组件 ──────────────────────────────────────────────────

def _setup_embedding(cfg: dict):
    emb_cfg = cfg["embedding"]
    if emb_cfg.get("hf_endpoint") and not os.getenv("HF_ENDPOINT"):
        os.environ["HF_ENDPOINT"] = emb_cfg["hf_endpoint"]
    return HuggingFaceEmbeddings(model_name=emb_cfg["model_name"])


def _setup_vectorstore(cfg: dict, embedding):
    kb_cfg = cfg["knowledge_base"]
    pd = kb_cfg.get("persist_directory", "./chroma_db")
    # 支持 ~ 展开（中文路径环境下 ChromaDB Rust 后端无法写入 .bin 文件）
    persist_dir = str(Path(pd).expanduser()) if pd.startswith("~") else str(PROJECT_DIR / pd)
    return Chroma(persist_directory=persist_dir, embedding_function=embedding)


def _setup_model(cfg: dict):
    llm_cfg = cfg["llm"]
    api_key = os.getenv(llm_cfg.get("api_key_env", "DEEPSEEK_API_KEY"))
    return ChatOpenAI(
        model=llm_cfg["model"],
        base_url=llm_cfg["base_url"],
        api_key=api_key,
        temperature=llm_cfg.get("temperature", 0.0),
    )


def _build_system_prompt(cfg: dict) -> str:
    """根据 agent 配置动态拼装 system prompt"""
    agent_cfg = cfg["agent"]

    # 基础检索规则
    lines = [
        "你是 DST Mod 开发知识库助手。严格按以下规则工作：",
        "",
        "## 检索规则",
        "1. 收到用户问题后，必须先调用 search_knowledge_base 工具",
        "2. **最多调用 3 次工具**。超过后必须基于已有信息直接回答",
        "3. 连续 2 次检索返回相同内容 = 知识库已穷尽，立刻停止检索",
        "4. 工具返回的是知识库中实际存在的代码片段，请严格引用",
        "",
        "## 回答规则",
    ]

    if agent_cfg.get("allow_external_knowledge", False):
        lines += [
            "5. 知识库信息不足时，可用你自己的 DST Mod 知识补充",
            "6. 补充部分必须明确标注「（以下为补充知识）」并解释为什么知识库没有覆盖",
        ]
    else:
        lines += [
            "5. 知识库信息不足时，直接说「抱歉，当前知识库中没有足够的相关信息」",
            "6. 绝对禁止编造知识库中没有的信息",
        ]

    extra = agent_cfg.get("system_prompt_extra", "").strip()
    if extra:
        lines.append(f"\n补充规则：{extra}")

    return "\n".join(lines)


# ── 2. 工具注册表 ──────────────────────────────────────────────────

def _build_enabled_tools(cfg: dict, retriever):
    """根据 config 的 tools 开关，返回仅启用的工具列表"""
    tools_cfg = cfg.get("tools", {})
    all_tools = []

    if tools_cfg.get("search_knowledge_base", {}).get("enabled", True):
        _retriever = retriever

        @langchain_tool
        def search_knowledge_base(query: str) -> str:
            """在知识库中搜索 DST Mod 开发相关的文档。返回每个片段时附带文件来源和所属 Mod 名称。"""
            docs = _retriever.invoke(query)
            if not docs:
                return "数据库中缺少相关信息。"
            parts = []
            for i, doc in enumerate(docs):
                source = doc.metadata.get("source", "未知来源")
                mod = doc.metadata.get("mod_name", "未知")
                parts.append(f"[来源{i + 1}：{mod}/{source}]\n{doc.page_content}")
            result = "\n\n---\n\n".join(parts)
            # 如果所有检索结果都来自同一个文件/同一段内容，加提示
            if len(set(d.metadata.get("source", "") for d in docs)) <= 1 and len(docs) > 1:
                result = "(注意：以下结果均来自同一文件)\n\n" + result
            return result

        all_tools.append(search_knowledge_base)

    return all_tools


# ── 3. Chainlit 生命周期 ──────────────────────────────────────────

@cl.on_chat_start
async def on_chat_start():
    """每次打开/刷新聊天窗口时触发"""
    cfg = load_config()

    embedding = _setup_embedding(cfg)
    vectorstore = _setup_vectorstore(cfg, embedding)
    retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
    model = _setup_model(cfg)
    system_prompt = _build_system_prompt(cfg)
    tools = _build_enabled_tools(cfg, retriever)

    doc_count = vectorstore._collection.count() if vectorstore._collection else 0
    agent = create_agent(model=model, tools=tools, system_prompt=system_prompt)

    cl.user_session.set("agent", agent)
    cl.user_session.set("config", cfg)

    status_lines = [
        f"Model: {cfg['llm']['model']}",
        f"Embedding: {cfg['embedding']['model_name']}",
        f"Documents: {doc_count}",
        f"Tools: {len(tools)}",
    ]
    await cl.Message(content="\n".join(status_lines)).send()


@cl.on_message
async def on_message(message: cl.Message):
    """用户发送消息时触发"""
    agent = cl.user_session.get("agent")
    # LangChain 1.0 create_agent 使用 {"messages": [...]} 格式
    # recursion_limit 防止 Agent 反复搜同一内容陷入死循环
    result = agent.invoke(
        {"messages": [HumanMessage(content=message.content)]},
        config={"recursion_limit": 10},
    )
    ai_messages = [m for m in result["messages"] if m.type == "ai"]
    if ai_messages:
        await cl.Message(content=ai_messages[-1].content).send()
    else:
        await cl.Message(content="（Agent 未生成回复，请检查终端日志）").send()
