"""
src/agent/ —— Agent 体系

System Prompt 拼装、工具注册、Agent 创建与调用。
Phase 1 在此加 astream，Phase 2 在此迁移到 LangGraph。
"""

from src.agent.prompt import build_system_prompt
from src.agent.tools import build_tools
from src.agent.factory import create_agent, run_agent, run_agent_stream

__all__ = ["build_system_prompt", "build_tools", "create_agent", "run_agent", "run_agent_stream"]
