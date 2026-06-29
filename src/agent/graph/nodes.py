"""
src/agent/graph/nodes.py —— State 定义 + 图节点函数 + Pydantic 评分模型

每个节点是一个纯函数：接收 RAGState，返回部分状态更新（dict）。
节点不直接访问 retriever/model——通过闭包/偏函数注入（在 pipeline.py 中完成），
这样节点函数本身不依赖外部状态，便于测试。

State 字段说明（仅 Phase 2 实际需要的 6 个，不提前加未来字段）：
  question : str          — 用户原始问题（不变）
  query    : str          — 当前检索查询（可能被 rewrite_question 节点更新）
  context  : str          — 格式化后的检索结果文本（给 LLM 阅读，格式同原 search_knowledge_base 工具输出）
  docs     : List[dict]   — 检索到的原始文档列表
  route    : Optional[str]— 条件边路由标记："generate_answer" | "rewrite_question"
  response : str          — 最终回答文本
"""

from typing import List, Optional
from typing_extensions import TypedDict  # Python <3.12 兼容

from langchain_core.messages import SystemMessage, HumanMessage
from pydantic import BaseModel, Field

from src.embedding import add_query_prefix


# ── State 定义 ───────────────────────────────────────────────────────

class RAGState(TypedDict):
    """RAG 图的状态。所有节点共享此字典，每次节点返回部分更新。"""
    question: str
    query: str
    context: str
    docs: List[dict]
    route: Optional[str]
    response: str


# ── Pydantic 评分模型 ──────────────────────────────────────────────────

class GradeDocuments(BaseModel):
    """文档相关性评分——LLM 用 structured output 返回 yes/no。"""

    binary_score: str = Field(
        description="Relevance score: 'yes' if the document is relevant to the question, 'no' if not"
    )


# ── Prompt 常量 ───────────────────────────────────────────────────────

GRADE_PROMPT = (
    "你是一个评估检索文档与用户问题相关性的评分员。\n\n"
    "以下是检索到的文档：\n{context}\n\n"
    "以下是用户问题：{question}\n"
    "如果文档包含与用户问题相关的关键词或语义含义，则评为相关。\n"
    "给出二元评分 'yes' 或 'no' 表示文档是否与问题相关。"
)

REWRITE_PROMPT = (
    "你是一个查询优化器。请从不同角度重新表述以下问题，"
    "生成一个更利于语义检索的查询。\n\n"
    "原始问题：{question}\n\n"
    "重写后的查询（只输出查询文本，不要加任何前缀或解释）："
)

# ── 工具函数 ──────────────────────────────────────────────────────────

def _format_docs(docs: List[dict]) -> str:
    """将检索文档列表格式化为 LLM 可读的文本。

    输出格式与原 search_knowledge_base 工具一致——以 [来源N：Mod/文件] 开头、
    用 --- 分隔，确保 app.py 的 _format_tool_output() 能正确解析。
    """
    if not docs:
        return ""

    parts = []
    for i, doc in enumerate(docs):
        source = doc.metadata.get("source", "未知来源")
        mod = doc.metadata.get("mod_name", "未知")
        content = doc.page_content
        parts.append(f"[来源{i + 1}：{mod}/{source}]\n{content}")

    result = "\n\n---\n\n".join(parts)

    # 同 tools.py 逻辑：所有结果来自同一文件时加提示
    unique_sources = set(d.metadata.get("source", "") for d in docs)
    if len(unique_sources) <= 1 and len(docs) > 1:
        result = "(注意：以下结果均来自同一文件)\n\n" + result

    return result


# ── 图节点 ────────────────────────────────────────────────────────────

def retrieve_initial(state: RAGState, retriever, model_name: str = "") -> dict:
    """初次检索节点：用用户问题作为查询，从 ChromaDB 检索相关文档。

    bge 系列模型在训练时使用了查询指令前缀（"Represent this sentence
    for searching relevant passages:"），检索前自动添加以提升语义匹配精度。

    返回：
        query   — 固定为用户原始问题
        docs    — retriever 返回的 Document 列表
        context — 格式化后的文本（给后续节点 LLM 阅读）
    """
    question = state["question"]
    search_query = add_query_prefix(question, model_name)
    docs = retriever.invoke(search_query)
    context = _format_docs(docs)
    return {
        "query": question,
        "docs": docs,
        "context": context,
    }


def grade_documents(state: RAGState, model) -> dict:
    """评分门控节点：LLM 判断检索结果是否与问题相关。

    用 Pydantic structured output 强制 LLM 返回 yes/no，
    写入 state.route 供条件边路由。

    model 不可用时（如 API key 缺失），默认走 rewrite_question 路径。
    """
    question = state["question"]
    context = state.get("context", "")

    if not context:
        # 检索无结果 → 直接走重写路径
        return {"route": "rewrite_question"}

    try:
        prompt = GRADE_PROMPT.format(question=question, context=context)
        # with_structured_output 是 LangChain 的方法，将 Pydantic 模型
        # 作为工具的 schema 注入 LLM 调用，确保输出可解析
        response = model.with_structured_output(GradeDocuments).invoke(
            [{"role": "user", "content": prompt}]
        )
        score = (response.binary_score or "").strip().lower()
    except Exception:
        # structured output 失败时保守处理：视为不相关，走重写路径
        score = "no"

    route = "generate_answer" if score == "yes" else "rewrite_question"
    return {"route": route}


def rewrite_question(state: RAGState, model) -> dict:
    """查询重写节点：让 LLM 从不同角度重新表述问题。

    输出是一个新的查询字符串，写入 state.query 供 retrieve_expanded 使用。
    """
    question = state["question"]
    prompt = REWRITE_PROMPT.format(question=question)
    response = model.invoke([{"role": "user", "content": prompt}])
    rewritten = response.content.strip()
    # 防御：如果 LLM 返回空或太长（可能是解释而非查询），回退到原问题
    if not rewritten or len(rewritten) > len(question) * 3:
        rewritten = question
    return {"query": rewritten}


def retrieve_expanded(state: RAGState, retriever, model_name: str = "") -> dict:
    """扩展检索节点：用重写后的查询再次检索，合并去重后更新 docs + context。

    如果重写查询与原查询完全相同（退化），跳过检索以避免重复结果。
    """
    query = state.get("query", state["question"])
    question = state["question"]

    # 退化检测：重写查询与原问题完全相同时，跳过（节省 API 调用）
    if query == question:
        return {}

    search_query = add_query_prefix(query, model_name)
    new_docs = retriever.invoke(search_query)

    # 去重合并：按 page_content 去重，保留第一次出现的来源信息
    existing_contents = {doc.page_content for doc in state.get("docs", [])}
    unique_new = [d for d in new_docs if d.page_content not in existing_contents]

    if not unique_new:
        # 无新结果，保持原样
        return {}

    merged = list(state.get("docs", [])) + unique_new
    context = _format_docs(merged)
    return {
        "docs": merged,
        "context": context,
    }


def generate_answer(state: RAGState, model, system_prompt: str) -> dict:
    """答案生成节点：用 system_prompt + 检索上下文 + 用户问题调用 LLM。

    此节点的 model.invoke() 会在 LangGraph astream_events 中触发
    on_chat_model_stream 事件——这正是逐 token 流式展示所需的数据源。
    """
    question = state["question"]
    context = state.get("context", "")

    # 拼接 system prompt 与检索上下文
    system_content = system_prompt
    if context:
        system_content += f"\n\n## 知识库检索结果\n\n{context}"
    else:
        system_content += "\n\n注意：本次检索未找到相关结果，请如实告知用户。"

    messages = [
        SystemMessage(content=system_content),
        HumanMessage(content=question),
    ]

    response = model.invoke(messages)
    return {"response": response.content}
