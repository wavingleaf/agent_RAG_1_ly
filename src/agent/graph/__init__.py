"""
src/agent/graph/ —— LangGraph StateGraph 子包

Phase 2 迁移：将 RAG 流程从 LangChain create_agent 的"LLM 自主决定检索"
改为开发者定义的确定性图编排。

pipeline.py —— 图构建 + 编译 + create_agent 对外接口
nodes.py   —— State 定义 + 节点函数 + Pydantic 模型
"""

from src.agent.graph.pipeline import create_agent

__all__ = ["create_agent"]
