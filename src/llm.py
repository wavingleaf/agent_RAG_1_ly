"""
src/llm.py —— LLM 模型初始化

创建 ChatOpenAI 实例（兼容 DeepSeek 等 OpenAI 兼容 API）。
"""

import os

from langchain_openai import ChatOpenAI


def create_model(cfg: dict):
    """根据 config 的 llm 节创建 ChatOpenAI 实例"""
    llm_cfg = cfg["llm"]
    api_key = os.getenv(llm_cfg.get("api_key_env", "DEEPSEEK_API_KEY"))
    return ChatOpenAI(
        model=llm_cfg["model"],
        base_url=llm_cfg["base_url"],
        api_key=api_key,
        temperature=llm_cfg.get("temperature", 0.0),
    )
