"""
src/ —— agent_RAG_1_ly 共享源码包

目录结构设计见 `src架构设计_ly.md`。
后续所有功能改动在对应子包内完成，app.py 导入语句不变。
"""

from src.config import load_config, PROJECT_DIR, CONFIG_PATH
from src.embedding import create_embedding
from src.llm import create_model

__all__ = ["load_config", "create_embedding", "create_model", "PROJECT_DIR", "CONFIG_PATH"]
