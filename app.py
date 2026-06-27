"""
app.py —— RAG Agent 聊天端（Chainlit 界面）

启动方式：
    chainlit run app.py

所有业务逻辑在 src/ 包中，本文件只负责 Chainlit UI 装配。
"""

import chainlit as cl
from dotenv import load_dotenv

from src.config import load_config, PROJECT_DIR
from src.embedding import create_embedding
from src.llm import create_model
from src.knowledge.store import create_vectorstore
from src.agent.prompt import build_system_prompt
from src.agent.tools import build_tools
from src.agent.factory import create_agent, run_agent

# ── 0. 环境初始化 ──────────────────────────────────────────────────

load_dotenv(PROJECT_DIR / ".env")


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
    """用户发送消息时触发"""
    agent = cl.user_session.get("agent")
    result = run_agent(agent, message.content)
    ai_messages = [m for m in result["messages"] if m.type == "ai"]
    if ai_messages:
        await cl.Message(content=ai_messages[-1].content).send()
    else:
        await cl.Message(content="（Agent 未生成回复，请检查终端日志）").send()
