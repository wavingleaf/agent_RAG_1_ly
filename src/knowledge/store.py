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
