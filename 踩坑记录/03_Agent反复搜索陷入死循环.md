# 03 — Agent 反复搜索陷入死循环

## 症状

- 用户提问后，网页端长时间无响应，最终显示未生成回复
- 终端日志显示 DeepSeek API 被连续调用了 20+ 次
- 每次工具调用返回的检索结果几乎相同（同一文件的同一几个片段）
- Agent 不断重新搜索相同的 query，试图"找到更多信息"

## 根因

**Agent 没有递归上限，且 system prompt 未约束工具调用次数。**

当检索结果质量不够（例如 embedding 模型对中英文混合 Lua 代码的语义理解不准确，返回了无关片段），Agent 的反应不是"知识库中没有更多信息，我应该基于已有内容回答"，而是"检索结果不够好，我换个说法再搜一次"。

每次返回的结果稍有不同（至少排序不同），Agent 就认为"有新信息"，继续搜索。陷入 `搜 → 不满意 → 换说法搜 → 还是不满意 → ...` 的循环。

## 修复

### 1. System prompt 加约束

```python
lines = [
    ...
    "## 检索规则",
    "1. 收到用户问题后，必须先调用 search_knowledge_base 工具",
    "2. **最多调用 3 次工具**。超过后必须基于已有信息直接回答",
    "3. 连续 2 次检索返回相同内容 = 知识库已穷尽，立刻停止检索并回答",
    ...
]
```

### 2. invoke 时设置 recursion_limit

```python
result = agent.invoke(
    {"messages": [HumanMessage(content=message.content)]},
    config={"recursion_limit": 10},  # LangGraph 递归上限，防止无限循环
)
```

### 3. 工具返回值加"重复检测"提示

当检索结果全部来自同一文件时，在返回值前加提示：
```python
if len(set(d.metadata.get("source", "") for d in docs)) <= 1 and len(docs) > 1:
    result = "(注意：以下结果均来自同一文件)\n\n" + result
```

这帮助 LLM 更快意识到"这些是一样的内容"。

## 影响范围

- 所有 RAG Agent，尤其当 embedding 检索质量不高时更容易触发
- LangGraph 默认 `recursion_limit=25`，不加限制最多可调用 25 轮
- DeepSeek 等模型的"帮你多搜搜"倾向

## 深层原因

这个问题也暴露了当前 embedding 模型的局限性——`all-MiniLM-L6-v2` 对中英文混合的 Lua 代码语义理解不够精准，Agent 得到的结果不够好才反复搜索。换更强的 embedding 模型（如 `bge-large-zh-v1.5` 或 `multilingual-e5-large`）可以从根本上减少这种情况。
