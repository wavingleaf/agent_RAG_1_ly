"""
src/embedding.py —— Embedding 模型初始化

创建 HuggingFaceEmbeddings 实例，支持 HF 镜像站和离线模式。
"""

import os

from langchain_huggingface import HuggingFaceEmbeddings


def create_embedding(cfg: dict, model_kwargs: dict | None = None):
    """根据 config 的 embedding 节创建 HuggingFaceEmbeddings 实例

    model_kwargs: 传递给 HuggingFaceEmbeddings 的额外参数。
                  批量导入时用 {"local_files_only": True} 强制离线加速。
    """
    emb_cfg = cfg["embedding"]
    if emb_cfg.get("hf_endpoint") and not os.getenv("HF_ENDPOINT"):
        os.environ["HF_ENDPOINT"] = emb_cfg["hf_endpoint"]
    return HuggingFaceEmbeddings(
        model_name=emb_cfg["model_name"],
        model_kwargs=model_kwargs or {},
    )
