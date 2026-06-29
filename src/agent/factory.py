"""
src/agent/factory.py —— Agent 创建与调用

Phase 2: 委托给 src/agent/graph/pipeline.py 的 LangGraph StateGraph。
Phase 1 的 LangChain create_agent 已被替换，但对外接口（create_agent、
run_agent、run_agent_stream 的函数签名）保持不变——app.py 无需改动。

run_agent_stream 现在消费 LangGraph 的 astream_events（v2），
将图节点执行事件映射为 Phase 1 兼容的 {type, ...} 格式。
"""

from src.agent.graph.pipeline import create_agent as _create_graph_agent


def create_agent(model, tools, system_prompt, retriever=None, model_name=""):
    """创建 RAG Agent 实例（Phase 2：返回编译后的 LangGraph StateGraph）。

    retriever 是 Phase 2 新增参数——app.py 需传入 ChromaDB retriever 实例。
    model_name 是 Phase 3 新增参数——bge 系列模型需要查询前缀以提升检索精度。
    tools 参数保留用于未来 Phase 在图中集成工具调用（当前暂不使用）。"""
    return _create_graph_agent(
        model=model,
        tools=tools,
        system_prompt=system_prompt,
        retriever=retriever,
        model_name=model_name,
    )


def run_agent(agent, user_message: str) -> dict:
    """调用 Agent（同步阻塞式，保留用于对比测试）。

    Phase 2：传入 StateGraph 初始状态，用 graph.invoke() 执行全图。
    图的边固化了检索次数——不再需要 recursion_limit 防御无限循环。"""
    result = agent.invoke({
        "question": user_message,
        "query": "",
        "context": "",
        "docs": [],
        "route": None,
        "response": "",
    })
    return result


async def run_agent_stream(agent, user_message: str):
    """流式调用 Agent，产出结构化事件供 Chainlit UI 消费。

    Phase 2 改造：消费 LangGraph StateGraph 的 astream_events（v2），
    将图节点执行映射为 Phase 1 兼容的事件格式：

      - on_chat_model_stream → {"type": "token", ...}
      - retrieve_initial/retrieve_expanded 节点开始 → {"type": "tool_start", ...}
      - retrieve_initial/retrieve_expanded 节点结束 → {"type": "tool_end", ...}

    grade_documents 和 rewrite_question 节点不产生 UI 事件（内部流转）。
    图的边固化了检索次数上限——不再需要 recursion_limit=25 防御。
    """
    # LangGraph 节点通过闭包注入依赖，state 只用传数据字段
    initial_state = {
        "question": user_message,
        "query": "",
        "context": "",
        "docs": [],
        "route": None,
        "response": "",
    }

    async for event in agent.astream_events(initial_state, version="v2"):
        kind = event["event"]
        name = event.get("name", "")

        # ── LLM 逐 token 流式 ──────────────────────────────────
        # generate_answer 节点内的 ChatOpenAI 调用触发此事件，
        # 与 Phase 1 的 on_chat_model_stream 完全一致
        if kind == "on_chat_model_stream":
            content = event["data"]["chunk"].content
            if content:
                yield {"type": "token", "content": content}

        # ── 检索节点开始 → 映射为 tool_start ─────────────────
        # retrieve_initial 和 retrieve_expanded 都映射到同一工具名
        # "search_knowledge_base"，确保 app.py 能正确匹配 tool_start/tool_end
        elif kind == "on_chain_start" and name in ("retrieve_initial", "retrieve_expanded"):
            node_input = event["data"].get("input", {})
            # 从 state 中提取当前查询作为 tool input 展示
            query = node_input.get("query", "") or node_input.get("question", "")
            yield {
                "type": "tool_start",
                "run_id": event["run_id"],
                "name": "search_knowledge_base",
                "input": str(query),
            }

        # ── 检索节点结束 → 映射为 tool_end ─────────────────
        elif kind == "on_chain_end" and name in ("retrieve_initial", "retrieve_expanded"):
            node_output = event["data"].get("output", {})
            context = node_output.get("context", "")
            yield {
                "type": "tool_end",
                "run_id": event["run_id"],
                "name": "search_knowledge_base",
                "output": context,
            }

        # ── 评分门控节点 → 可视化 LLM 的 yes/no 判断 ────────
        # grade_documents 调用 LLM structured_output 判断检索结果是否相关，
        # 将判断结果暴露给 UI，用户可以看到系统为什么选择"直接回答"或"重写查询"
        elif kind == "on_chain_start" and name == "grade_documents":
            node_input = event["data"].get("input", {})
            doc_count = len(node_input.get("docs", []))
            yield {
                "type": "tool_start",
                "run_id": event["run_id"],
                "name": "相关性评估",
                "input": f"评估 {doc_count} 个检索结果是否与问题相关",
            }

        elif kind == "on_chain_end" and name == "grade_documents":
            node_output = event["data"].get("output", {})
            route = node_output.get("route", "rewrite_question")
            if route == "generate_answer":
                result = "✅ **相关** — 检索结果与问题匹配，直接生成回答"
            else:
                result = "⚠️ **不相关** — 检索结果与问题不匹配，将重写查询后重新检索"
            yield {
                "type": "tool_end",
                "run_id": event["run_id"],
                "name": "相关性评估",
                "output": result,
            }

        # ── 查询重写节点 → 可视化 LLM 如何改写用户问题 ──────
        elif kind == "on_chain_start" and name == "rewrite_question":
            node_input = event["data"].get("input", {})
            question = node_input.get("question", "")
            yield {
                "type": "tool_start",
                "run_id": event["run_id"],
                "name": "查询重写",
                "input": f"原问题：{question[:100]}{'…' if len(question) > 100 else ''}",
            }

        elif kind == "on_chain_end" and name == "rewrite_question":
            node_output = event["data"].get("output", {})
            rewritten = node_output.get("query", "")
            yield {
                "type": "tool_end",
                "run_id": event["run_id"],
                "name": "查询重写",
                "output": f"🔁 {rewritten}",
            }
