"""
src/agent/ —— Agent 体系

System Prompt 拼装、Agent 创建与调用。
Phase 2 已迁移到 LangGraph StateGraph。
原 tools.py 已在 Phase 2 后移除——图节点直接调 retriever，
格式化逻辑统一至 src/knowledge/store.py::format_retrieval_results()。
"""

from src.agent.prompt import build_system_prompt
from src.agent.factory import create_agent, run_agent, run_agent_stream

__all__ = ["build_system_prompt", "create_agent", "run_agent", "run_agent_stream"]
