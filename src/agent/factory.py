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
    """调用 Agent（同步阻塞式，保留用于对比测试）。

    recursion_limit 防止 Agent 反复搜同一内容陷入死循环。
    日常使用请用 run_agent_stream()。"""
    result = agent.invoke(
        {"messages": [HumanMessage(content=user_message)]},
        config={"recursion_limit": 25},
    )
    return result


async def run_agent_stream(agent, user_message: str):
    """流式调用 Agent，产出结构化事件供 Chainlit UI 消费。

    astream_events（v2 API）按时间顺序触发所有 LangGraph 内部事件：
    - on_tool_start / on_tool_end → 工具调用可视化（Phase 1 §2）
    - on_chat_model_stream → 逐 token 流式展示（Phase 1 §1）
    - 事件序列本身 → Agent 思考路径透传（Phase 1 §4）

    产出格式：
        {"type": "token", "content": "..."}
        {"type": "tool_start", "run_id": "...", "name": "...", "input": "..."}
        {"type": "tool_end", "run_id": "...", "name": "...", "output": "..."}
    """
    async for event in agent.astream_events(
        {"messages": [HumanMessage(content=user_message)]},
        config={"recursion_limit": 25},
        version="v2",
    ):
        kind = event["event"]

        if kind == "on_chat_model_stream":
            content = event["data"]["chunk"].content
            if content:
                yield {"type": "token", "content": content}

        # on_tool_start: Agent 决定调用工具时触发。
        # 用 run_id 做 key——同名工具可能被多次调用，run_id 唯一。
        elif kind == "on_tool_start":
            raw_input = event["data"].get("input", "")
            # 工具输入可能是 {"query": "..."} 或纯字符串
            if isinstance(raw_input, dict):
                raw_input = raw_input.get("query", str(raw_input))
            yield {
                "type": "tool_start",
                "run_id": event["run_id"],
                "name": event["name"],
                "input": str(raw_input),
            }

        # on_tool_end: 工具执行完毕。
        # astream_events v2 中 output 是 ToolMessage 对象，需取 .content 才是
        # 工具函数的原始返回值（纯文本）。直接用 str() 会拿到 repr 格式：
        # "content='...' name='...' tool_call_id='...'"，导致解析错误。
        elif kind == "on_tool_end":
            raw_output = event["data"].get("output", "")
            # ToolMessage 对象 → 取 .content 字段（工具函数的原始返回文本）
            if hasattr(raw_output, "content"):
                raw_output = str(raw_output.content)
            else:
                raw_output = str(raw_output)
            yield {
                "type": "tool_end",
                "run_id": event["run_id"],
                "name": event["name"],
                "output": raw_output,
            }
