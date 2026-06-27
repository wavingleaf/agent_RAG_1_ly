"""
src/agent/tools.py —— 工具注册表

根据 config 的 tools 节开关，构建启用的 LangChain @tool 列表。
目前只有一个工具：search_knowledge_base（知识库检索）。
"""

from langchain.tools import tool as langchain_tool


def build_tools(cfg: dict, retriever):
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
