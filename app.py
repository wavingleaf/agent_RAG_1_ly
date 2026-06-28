"""
app.py —— RAG Agent 聊天端（Chainlit 界面）

启动方式：
    chainlit run app.py

所有业务逻辑在 src/ 包中，本文件只负责 Chainlit UI 装配。
"""

import re

import chainlit as cl
from dotenv import load_dotenv

from src.config import load_config, PROJECT_DIR
from src.embedding import create_embedding
from src.llm import create_model
from src.knowledge.store import create_vectorstore
from src.agent.prompt import build_system_prompt
from src.agent.tools import build_tools
from src.agent.factory import create_agent, run_agent_stream

# ── 0. 环境初始化 ──────────────────────────────────────────────────

load_dotenv(PROJECT_DIR / ".env")


# ── 0b. 本地辅助 ───────────────────────────────────────────────────


def _format_tool_output(raw: str) -> str:
    """将 search_knowledge_base 的原始输出转为人类可读的 markdown。

    LLM 收到的格式是 "[来源N：Mod/文件]\\n内容\\n\\n---\\n\\n"。
    这里解析后加上：片段总数、不同文件数、每条来源+代码块。
    如果所有结果来自同一文件，顶部告警。
    """
    if not raw:
        return raw

    # 检查并提取顶部提示（如"注意：以下结果均来自同一文件"）
    same_file_warning = ""
    content_without_prefix = raw
    if raw.startswith("(注意："):
        prefix_end = raw.find(")\n\n")
        if prefix_end != -1:
            same_file_warning = raw[:prefix_end + 1]
            content_without_prefix = raw[prefix_end + 3:]

    # 按 --- 分隔线切分各检索结果
    blocks = content_without_prefix.split("\n\n---\n\n")

    # 解析每条，收集统计信息
    parsed = []  # [(source, content), ...]
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        m = re.match(r"^\[来源\d+：(.+?)\]\n(.+)", block, re.DOTALL)
        if m:
            source = m.group(1)
            content = m.group(2).strip()
            if len(content) > 500:
                content = content[:500] + "\n...（截断）"
            parsed.append((source, content))
        else:
            parsed.append(("未知来源", block))

    # 构建 markdown
    sources = [s for s, _ in parsed]
    unique_files = len(set(sources))
    total = len(parsed)

    # 头部摘要
    parts = [f"📋 **{total}** 个相关片段，来自 **{unique_files}** 个不同文件"]

    if same_file_warning:
        parts.append(f"\n⚠️ {same_file_warning}")

    # 各条来源
    for i, (source, content) in enumerate(parsed, 1):
        # 提取文件名（source := "Mod名/scripts/xxx/file.lua"）
        file_name = source.rsplit("/", 1)[-1] if "/" in source else source
        mod_name = source.split("/", 1)[0] if "/" in source else ""
        if mod_name:
            source_label = f"{mod_name} → {file_name}"
        else:
            source_label = file_name

        parts.append(
            f"\n\n**{i}. {source_label}**\n```lua\n{content}\n```"
        )

    return "\n".join(parts)


# ── 1. Chainlit 生命周期 ──────────────────────────────────────────


@cl.on_chat_start
async def on_chat_start():
    """每次打开/刷新聊天窗口时触发"""
    cfg = load_config()

    embedding = create_embedding(cfg)
    vectorstore = create_vectorstore(cfg, embedding)
    retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
    model = create_model(cfg)
    system_prompt = build_system_prompt(cfg)
    tools = build_tools(cfg, retriever)

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
    """用户发送消息时触发——流式 token + 工具调用可视化 + 思考路径透传

    时间序控制（问题 1 修复）：
      - msg 不提前 send()，工具 Step 先出现在时间线上
      - 工具调用前 LLM 吐出的前置 token（如"我来搜索..."）丢弃
      - 所有工具执行完毕后，才 send(msg) 并开始流式写入最终回答

    Phase 1 §1: 流式逐 token 展示
    Phase 1 §2: 每次工具调用 → cl.Step（含 markdown 格式化输出）
    Phase 1 §4: 事件序列 = 思考路径
    """
    agent = cl.user_session.get("agent")

    # 多 msg 方案：工具调用前后各自成段，工具调用本身也是一个消息。
    # 不用 cl.Step——Chainlit 中 Step 不与 Message 混合排序，
    # 改用纯 Message 保证时间线上的正确位置。
    current_msg = cl.Message(content="")   # 当前文本段
    tool_msgs = {}                         # run_id → cl.Message（工具调用占位）

    async for event in run_agent_stream(agent, message.content):
        if event["type"] == "token":
            if not current_msg.content:
                await current_msg.send()
            await current_msg.stream_token(event["content"])

        elif event["type"] == "tool_start":
            # 关闭上一段文字
            if current_msg.content:
                await current_msg.update()
            # 工具调用开始：先发一个消息显示"正在搜索..."
            tool_msg = cl.Message(
                content=f"🔍 **{event['name']}**\n\n_{event['input']}_",
            )
            await tool_msg.send()
            tool_msgs[event["run_id"]] = tool_msg
            current_msg = cl.Message(content="")

        elif event["type"] == "tool_end":
            tool_msg = tool_msgs.pop(event["run_id"], None)
            if tool_msg:
                formatted = _format_tool_output(event["output"])
                # <details> 默认折叠，summary 显示工具名+检索词
                tool_msg.content = (
                    f"<details>\n"
                    f"<summary>🔍 **{event['name']}**</summary>\n\n"
                    f"{formatted}\n"
                    f"</details>"
                )
                await tool_msg.update()

    # 关闭最后一段文字
    if current_msg.content:
        await current_msg.update()
