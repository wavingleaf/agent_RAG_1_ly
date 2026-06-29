"""
src/knowledge/store.py —— ChromaDB 向量库

向量库创建、路径展开、文档计数。所有需要 ChromaDB 的地方统一走这里。
"""

from pathlib import Path

from langchain_chroma import Chroma

from src.config import PROJECT_DIR


def get_chroma_dir(cfg: dict) -> str:
    """解析配置中的 persist_directory，返回绝对路径。

    支持 `~` 展开（中文路径环境下 ChromaDB Rust 后端无法写入 .bin 文件，
    故允许将持久化目录放到 ASCII 路径）。
    """
    kb = cfg.get("knowledge_base", {})
    pd = kb.get("persist_directory", "./chroma_db")
    if pd.startswith("~"):
        return str(Path(pd).expanduser())
    return str(PROJECT_DIR / pd)


def create_vectorstore(cfg: dict, embedding):
    """根据 config 创建 Chroma 向量库实例"""
    persist_dir = get_chroma_dir(cfg)
    return Chroma(persist_directory=persist_dir, embedding_function=embedding)


def get_doc_count(cfg: dict) -> int:
    """读取 ChromaDB 中当前文档片段数。

    需要 cfg 因为要知道持久化路径和 embedding 模型。
    返回 -1 表示无法读取（数据库还不存在等）。
    """
    try:
        from src.embedding import create_embedding
        emb = create_embedding(cfg)
        vs = create_vectorstore(cfg, emb)
        return vs._collection.count() if vs._collection else 0
    except Exception:
        return -1


def format_retrieval_results(docs: list) -> str:
    """将检索文档列表格式化为 LLM 可读文本。

    输出格式：[来源N：Mod名/文件路径]\n内容，用 --- 分隔。
    当所有结果来自同一文件时，自动加「注意：以下结果均来自同一文件」提示。

    此函数是检索结果的标准格式化入口——图节点（nodes.py）和管理面板
    都通过它统一输出格式。原 tools.py 中的重复逻辑已合并至此。
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

    unique_sources = set(d.metadata.get("source", "") for d in docs)
    if len(unique_sources) <= 1 and len(docs) > 1:
        result = "(注意：以下结果均来自同一文件)\n\n" + result

    return result
