# 02 — LangChain 1.0 `create_agent` 输入格式错误

## 症状

- 无论用户问什么问题，Agent 始终回复"好的，我将先搜索知识库来回答您的问题。请问您想了解什么内容？"
- 终端日志显示 DeepSeek API 返回 200，但 tool_calls 为空
- Agent 仿佛完全没看到用户的问题内容

## 根因

**LangChain 1.0 `create_agent()` 创建的 Agent 使用 LangGraph 作为运行时，其 `invoke()` 方法要求特定格式的输入。**

错误写法（当前代码用的）：
```python
result = agent.invoke({"role": "user", "content": "问题文本"})
```

正确写法：
```python
from langchain_core.messages import HumanMessage
result = agent.invoke({"messages": [HumanMessage(content="问题文本")]})
```

`{"role": "user", "content": ...}` 是旧版 `AgentExecutor` 的格式或直接调 LLM 时的格式。`create_agent` 内部用 LangGraph 的 `MessagesState`，它期望 `{"messages": [...]}` 键，消息对象必须是 `langchain_core.messages` 中的类型（`HumanMessage`、`AIMessage` 等）。

当传入 `{"role": "user", ...}` 时，LangGraph 的 state 中 `messages` 列表为空，Agent 只看到 system prompt，不知道用户问了什么，所以机械地回复"请问您想了解什么？"。

## 验证测试

```python
from langchain.agents import create_agent
from langchain_core.messages import HumanMessage

# ❌ 错误 — Agent 不调用工具
r1 = agent.invoke({"role": "user", "content": "北京天气?"})
# tool_calls = [] , content = "请问您想了解什么？"

# ✅ 正确 — Agent 调用工具并回答
r2 = agent.invoke({"messages": [HumanMessage(content="北京天气?")]})
# tool_calls = [get_weather(city="北京")] , content = "北京今天晴，25°C"
```

## 修复

[app.py](../app.py) `@cl.on_message` 中，将：
```python
agent.invoke({"role": "user", "content": message.content})
```
改为：
```python
agent.invoke({"messages": [HumanMessage(content=message.content)]})
```

同时需要 `from langchain_core.messages import HumanMessage`。

## 影响范围

- LangChain 1.0 所有使用 `create_agent` 的情况
- 网上大量教程使用旧版 `AgentExecutor` 的格式，直接复制会踩坑
- `create_agent` 返回的是编译后的 LangGraph graph，不是普通的 Runnable
