# 08 — RecursiveCharacterTextSplitter 在 LangChain 1.0 中位置变更

## 症状

- 导入 `RecursiveCharacterTextSplitter` 时报错
- `ImportError: cannot import name 'RecursiveCharacterTextSplitter' from 'langchain.text_splitter'`
- 按旧版写法 `from langchain.text_splitter import RecursiveCharacterTextSplitter` 无法工作

## 根因

**LangChain 1.0 将部分历史遗留组件移到了独立包 `langchain-classic`。**

`RecursiveCharacterTextSplitter`（以及其他 text splitter、旧的 chain 类型等）不属于 LangChain 1.0 的核心 API，被归类为"经典/兼容"组件。

LangChain 1.0 的核心包 `langchain` 只保留最新的高层 API（如 `create_agent`），旧版组件需要从 `langchain_classic` 导入。

## 修复

```python
# ❌ 旧写法（LangChain 0.x）
from langchain.text_splitter import RecursiveCharacterTextSplitter

# ✅ 新写法（LangChain 1.0+）
from langchain_classic.text_splitter import RecursiveCharacterTextSplitter
```

同时确保安装了对应的包：
```bash
pip install langchain-classic
```

## 影响范围

- LangChain 1.0 所有项目
- 其他被移至 `langchain-classic` 的组件包括：`LLMChain`、`ConversationChain`、`StuffDocumentsChain` 等（完整列表见 LangChain 官方迁移指南）
- 官方推荐新项目直接使用 LangGraph（`langgraph` 包）的底层 API，`langchain-classic` 仅作兼容过渡

## 获取完整迁移列表

参考官方文档：[LangChain 1.0 Migration Guide](https://docs.langchain.com/oss/python/migrate/langchain-v1)
