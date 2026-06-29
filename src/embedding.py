"""
src/embedding.py —— Embedding 模型初始化

创建 HuggingFaceEmbeddings 实例，支持 HF 镜像站和离线模式。
Phase 3（2026-06-29）：升级模型从 all-MiniLM-L6-v2（384d，纯英文）
到 BAAI/bge-m3（1024d，多语言 100+ 种），解决中文查询"语义失明"问题。

bge-m3 要求：
  - normalize_embeddings=True —— 向量归一化到单位长度，余弦相似度 = 内积
  - query 前缀 —— "Represent this sentence for searching relevant passages:"
    HuggingFaceEmbeddings 不支持 query_instruction 入参（本版 LangChain 已移除该字段），
    改为在 nodes.py 中通过 add_query_prefix() 手动添加前缀
"""

import os

from langchain_huggingface import HuggingFaceEmbeddings


# bge-m3 的查询编码参数——模型在预训练时使用了此指令前缀，
# 查询时加上前缀可显著提升语义匹配精度。
# 文档端不使用前缀（文档数量大，前缀会引入噪声）。
_BGE_M3_ENCODE_KWARGS = {
    "normalize_embeddings": True,  # L2 归一化，使内积等价于余弦相似度
}

# bge-m3 查询指令前缀（模型训练时使用，不改变应在查询时也加上）
_BGE_M3_QUERY_INSTRUCTION = "Represent this sentence for searching relevant passages: "


def create_embedding(cfg: dict, model_kwargs: dict | None = None):
    """根据 config 的 embedding 节创建 HuggingFaceEmbeddings 实例

    model_kwargs: 传递给 HuggingFaceEmbeddings 的额外参数。
                  批量导入时用 {"local_files_only": True} 强制离线加速。
    """
    emb_cfg = cfg["embedding"]
    if emb_cfg.get("hf_endpoint") and not os.getenv("HF_ENDPOINT"):
        os.environ["HF_ENDPOINT"] = emb_cfg["hf_endpoint"]

    model_name = emb_cfg["model_name"]

    # HuggingFaceEmbeddings 构造参数
    # encode_kwargs 会传递给底层 sentence-transformers 的 model.encode() 调用
    hf_kwargs = {
        "model_name": model_name,
        "model_kwargs": model_kwargs or {},
        "encode_kwargs": _BGE_M3_ENCODE_KWARGS,
    }

    return HuggingFaceEmbeddings(**hf_kwargs)


# ── 公共工具函数 ──────────────────────────────────────────────────────


def add_query_prefix(query: str, model_name: str) -> str:
    """为 bge 系列模型的查询添加指令前缀。

    LangChain 的 HuggingFaceEmbeddings.embed_query() 不会自动加前缀，
    但 bge-m3 训练时使用了该前缀，加上的检索效果显著好于不加。
    在 nodes.py 的 retrieve 节点中调用此函数。

    其他模型（如 all-MiniLM-L6-v2、multilingual-e5）不需要前缀。
    """
    if "bge" in model_name.lower():
        return _BGE_M3_QUERY_INSTRUCTION + query
    return query
