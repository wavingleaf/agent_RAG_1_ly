"""
src/config.py —— 配置加载

从 config.json 读取所有配置，不存在时用默认值兜底。
所有入口（app.py、管理面板.py、批量导入mod代码.py）共用此模块。
"""

import json
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJECT_DIR / "config.json"


def load_config() -> dict:
    """加载 config.json，不存在时用默认值兜底"""
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {
        "llm": {
            "provider": "deepseek",
            "model": "deepseek-chat",
            "base_url": "https://api.deepseek.com",
            "api_key_env": "DEEPSEEK_API_KEY",
            "temperature": 0.0,
        },
        "embedding": {
            "provider": "huggingface",
            "model_name": "BAAI/bge-m3",
            "hf_endpoint": "https://hf-mirror.com",
        },
        "knowledge_base": {
            "persist_directory": "./chroma_db",
            "chunk_size": 500,
            "chunk_overlap": 50,
        },
        "tools": {
            "search_knowledge_base": {
                "enabled": True,
                "description": "在知识库中搜索与用户问题相关的文档。",
            }
        },
        "agent": {
            "force_search_first": True,
            "allow_external_knowledge": False,
            "system_prompt_extra": "",
        },
    }
