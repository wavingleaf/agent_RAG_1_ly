"""
src/agent/factory.py —— Agent 创建与调用

封装 LangChain create_agent 的创建和调用，
为 Phase 1（astream 流式）和 Phase 2（LangGraph StateGraph）留替换点。
"""

# 用别名导入，避免与本地 create_agent 函数名冲突（Python 函数名会 shadow 模块级导入）
from langchain.agents import create_agent as _create_langchain_agent
from langchain_core.messages import HumanMessage


def create_agent(model, tools, system_prompt):
    """创建 LangChain Agent 实例。

    Phase 2 时此处替换为 StateGraph 编译。"""
    return _create_langchain_agent(model=model, tools=tools, system_prompt=system_prompt)


def run_agent(agent, user_message: str) -> dict:
    """调用 Agent（同步阻塞式）。

    recursion_limit 防止 Agent 反复搜同一内容陷入死循环。
    Phase 1 时新增 run_agent_stream() 替代此函数。
    """
    # LangChain 1.0 create_agent 使用 {"messages": [...]} 格式
    # recursion_limit: LangGraph 内部每步工具调用+LLM响应算 2+ 步；
    # 25 步给足余量。真正的死循环防护靠 Phase 2 的硬限制。
    result = agent.invoke(
        {"messages": [HumanMessage(content=user_message)]},
        config={"recursion_limit": 25},
    )
    return result
