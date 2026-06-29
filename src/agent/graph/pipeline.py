"""
src/agent/graph/pipeline.py —— StateGraph 构建 + 编译 + 对外接口

LangGraph 图结构（Phase 2 完整版）：

  retrieve_initial → grade_documents → [yes] → generate_answer → END
                                     → [no]  → rewrite_question
                                                   ↓
                                              retrieve_expanded
                                                   ↓
                                              generate_answer → END

图的边本身就是硬限制——检索节点各只出现一次，不可能有第三次搜索。
替代 Phase 1 的 prompt 软约束（"最多调 3 次工具"）。
"""

from langgraph.graph import StateGraph, END

from src.agent.graph.nodes import (
    RAGState,
    retrieve_initial,
    grade_documents,
    rewrite_question,
    retrieve_expanded,
    generate_answer,
)


def create_agent(model, tools, system_prompt, retriever=None, model_name=""):
    """构建并编译 LangGraph StateGraph，替代 LangChain create_agent。

    参数：
        model         — ChatOpenAI 实例（需启用 streaming）
        tools         — 工具列表（Phase 2 保留参数但暂不使用；供未来 Phase 在图中集成工具）
        system_prompt — 拼装好的系统提示词字符串
        retriever     — ChromaDB retriever 实例
        model_name    — Embedding 模型名，用于 bge 系列模型自动加查询前缀

    返回：
        编译后的 LangGraph 图（Runnable），可直接 .invoke() 或 .astream_events()
    """
    graph = StateGraph(RAGState)

    # ── 注册节点 ─────────────────────────────────────────────────
    # 用 lambda 闭包将外部依赖（retriever/model/system_prompt/model_name）
    # 注入节点函数，节点函数本身保持纯函数签名（不直接依赖外部状态），便于单测。

    graph.add_node(
        "retrieve_initial",
        lambda s: retrieve_initial(s, retriever, model_name),
    )
    graph.add_node(
        "grade_documents",
        lambda s: grade_documents(s, model),
    )
    graph.add_node(
        "rewrite_question",
        lambda s: rewrite_question(s, model),
    )
    graph.add_node(
        "retrieve_expanded",
        lambda s: retrieve_expanded(s, retriever, model_name),
    )
    graph.add_node(
        "generate_answer",
        lambda s: generate_answer(s, model, system_prompt),
    )

    # ── 连接边 ───────────────────────────────────────────────────

    # 入口
    graph.set_entry_point("retrieve_initial")

    # retrieve → grade（无条件）
    graph.add_edge("retrieve_initial", "grade_documents")

    # grade → 条件路由：
    #   "generate_answer" → 直接回答（检索结果相关）
    #   "rewrite_question" → 重写查询后重新检索（检索结果不相关）
    graph.add_conditional_edges(
        "grade_documents",
        lambda s: s.get("route", "rewrite_question"),
        {
            "generate_answer": "generate_answer",
            "rewrite_question": "rewrite_question",
        },
    )

    # 重写 → 扩展检索 → 回答
    graph.add_edge("rewrite_question", "retrieve_expanded")
    graph.add_edge("retrieve_expanded", "generate_answer")

    # 回答 → 结束
    # generate_answer 是两个分支的汇聚点：
    #   - 直接路径：retrieve_initial → grade(yes) → generate_answer
    #   - 重写路径：retrieve_initial → grade(no) → rewrite → retrieve_expanded → generate_answer
    graph.add_edge("generate_answer", END)

    return graph.compile()
