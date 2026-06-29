"""
src/config.py —— 配置加载

从 config.json 读取所有配置，不存在时用默认值兜底。
所有入口（app.py、管理面板.py、批量导入mod代码.py）共用此模块。
"""

import json
import os
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJECT_DIR / "config.json"


def load_config() -> dict:
    """加载 config.json，不存在时用默认值兜底"""
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, encoding="utf-8") as f:
            cfg = json.load(f)
    else:
        cfg = {
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
                "query_prefix": "",
            },
            "knowledge_base": {
                "persist_directory": "./chroma_db",
                "chunk_size": 500,
                "chunk_overlap": 50,
            },
            "agent": {
                "force_search_first": True,
                "allow_external_knowledge": False,
                "system_prompt_extra": "",
            },
        }

    # ── Docker vs 宿主机路径一致性提醒 ──────────────────────────────
    # 如果 config.json 的 persist_directory 与运行环境不匹配，
    # 向量库会指向错误目录，表现为"库被清空"。
    _warn_env_mismatch(cfg)

    return cfg


def _warn_env_mismatch(cfg: dict) -> None:
    """检测运行环境与 persist_directory 是否匹配，不匹配时打印警告。

    场景：
    - 用户在宿主机跑 Python，但 persist_directory 指向 Docker 容器内路径（/app/...）
    - 用户在 Docker 内跑，但 persist_directory 是宿主机相对路径（./chroma_db）

    不阻止运行，仅提示——因为用户可能有意为之（如挂载了同一目录）。
    """
    persist_dir = cfg.get("knowledge_base", {}).get("persist_directory", "")
    in_docker = os.path.exists("/.dockerenv")

    if in_docker and persist_dir and not persist_dir.startswith("/"):
        # Docker 内但路径是相对路径（如 ./chroma_db）——
        # 如果 WORKDIR 正确则没问题，但挂载的 volume 位置是关键
        pass  # Docker 内相对路径是正常的（WORKDIR=/app，./chroma_db → /app/chroma_db）
    elif not in_docker and persist_dir.startswith("/app/"):
        print(
            f"⚠️  当前在宿主机运行，但 config.json 的 persist_directory 指向 "
            f"容器内路径「{persist_dir}」。\n"
            f"    向量库可能为空——请确认你是想在 Docker 内运行，或将 "
            f"persist_directory 改为本地路径（如 ./chroma_db）。"
        )
