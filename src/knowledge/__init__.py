"""
src/knowledge/ —— 检索体系

向量库创建、文档计数、路径展开。后续 Phase 3-4 会加入 rerank / expand / router。
"""

from src.knowledge.store import create_vectorstore, get_chroma_dir, get_doc_count

__all__ = ["create_vectorstore", "get_chroma_dir", "get_doc_count"]
