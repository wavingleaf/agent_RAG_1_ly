# src/ 源代码架构设计

> 决策日期: 2026-06-27
> 参考: `参考项目对比分析_ly.md`（SuperMew 项目结构分析）

---

## 设计原则

1. **单文件不拆分**：一个文件 < 200 行时不建子包，避免"每目录只一个文件"的过度设计
2. **按耦合分组**：会一起变化的文件放入同一子目录；独立变化的文件保持顶层
3. **`__init__.py` 重导出**：对外接口稳定，内部结构升级时 `app.py` 导入语句不变
4. **自然升级点**：当某文件膨胀到 ~200 行或出现 3+ 个内部辅助函数时，升级为子包（参考项目的 `schemas/`、`rag/` 模式）

---

## 当前结构（2 子目录 + 3 顶层文件）

```
src/
├── __init__.py            # 重导出：统一对外接口
├── config.py              # 配置加载（各阶段只加字段，不重构）
├── llm.py                 # ChatOpenAI 模型（稳定）
├── embedding.py           # HuggingFace Embedding（Phase 3 换模型名）
│
├── knowledge/             # 🔮 检索体系
│   ├── __init__.py        # 重导出
│   └── store.py           # ChromaDB 创建 + retriever
│   # Phase 3 计划加入：
│   #   rerank.py          # 结果重排序
│   #   expand.py          # Query Expansion
│   # Phase 4 计划加入：
│   #   router.py          # 四分库路由
│
└── agent/                 # 🧠 Agent 体系
    ├── __init__.py        # 重导出
    ├── prompt.py           # System Prompt 拼装
    ├── tools.py            # 工具注册表（Phase 1 加 @cl.step）
    └── factory.py          # Agent 创建 + 调用（Phase 1 加 astream，Phase 2 换 StateGraph）
```

---

## 为什么不更多子目录

| 候选子目录 | 为什么不建 |
|-----------|-----------|
| `config.py` 独立目录 | 当前 ~65 行，5 个阶段只加字段不重构，无拆分必要 |
| `llm.py` 独立目录 | 当前 ~15 行，只做 `ChatOpenAI()` 一行调用，永远不会膨胀 |
| `embedding.py` 独立目录 | 当前 ~8 行，Phase 3 换模型名只改一个字符串参数 |

参考项目也这么做：`db/` 子包只有 `models.py` 一个文件，`jobs/` 只有两个文件。它们不追求每个目录文件数平均。

---

## 为什么 knowledge/ 和 agent/ 是唯一的分组

```
耦合图：

config.py  ←── 被所有人导入（独立，放顶层）
embedding.py ←── 仅被 knowledge/store.py 和 app.py 使用
llm.py       ←── 仅被 agent/factory.py 消费
    │
    ├── 共同点：都是"外部模型提供商"的初始化器
    └── 结论：不合并——embedding 模型切换与 LLM 切换独立变化，无耦合
    │
knowledge/store.py ←── 被 agent/tools.py 消费（提供 retriever）
    │                    Phase 3-4 会膨胀出 rerank + expand + router
    │
agent/  ←── prompt.py + tools.py + factory.py 共同组成 Agent 的"大脑"
            prompt → factory ← tools → knowledge/store
```

knowledge/ 是"数据层"：向量库 → 检索 → 重排序 → 路由，全链路同生命周期。
agent/ 是"编排层"：创建 Agent → 提供工具 → 注入 prompt → 执行流式调用。

---

## 各阶段演进对结构的影响

### Phase 1: RAG 过程可视化

| 文件 | 变化 | 是否拆分 |
|------|------|---------|
| `agent/factory.py` | `invoke()` → `astream()`，新增 `run_agent_stream()` 生成器 | 否（~80 行） |
| `agent/tools.py` | 工具函数内加 `@cl.step` 装饰器，检索结果格式化 | 否（~100 行） |
| `app.py` | 流式消费，管理 `cl.Step` 生命周期 | 否（~60 行） |

**结构不变**。Phase 1 结束时只有 `agent/tools.py` 接近 ~100 行，仍不需要拆分。

### Phase 2: 迁移到 LangGraph

```
agent/                        # Phase 2 后
├── __init__.py               # 内部升级，重导出不变
├── prompt.py                 # 不变
├── tools.py                  # 不变（仍然用 LangChain @tool 装饰器）
├── factory.py                # create_agent 调用改为 StateGraph 编译
└── graph/                    # 🆕 升级：factory.py 拆成子包
    ├── __init__.py
    ├── pipeline.py           # StateGraph 定义 + 条件边 + 编译
    └── nodes.py              # 各图节点（retrieve, think, answer）
```

`app.py` 完全不受影响——它仍然从 `src.agent` 导入 `create_agent`。

### Phase 3: 检索质量提升

```
knowledge/                    # Phase 3 后
├── __init__.py
├── store.py                  # 不变
├── rerank.py                 # 🆕 结果重排序
└── expand.py                 # 🆕 Query Expansion
```

### Phase 4: 四分库架构

```
knowledge/                    # Phase 4 后
├── __init__.py
├── store.py                  # 单库 → 多 Collection 工厂
├── rerank.py
├── expand.py
└── router.py                 # 🆕 问题 → 目标库路由
```

### Phase 5: 多跳交叉验证

```
agent/graph/
├── __init__.py
├── pipeline.py               # 新增条件循环节点 + Send API
└── nodes.py                  # 新增 decompose / verify 节点
```

**不增加新子包**，只在 `graph/` 内部扩展。

---

## 与参考项目的对照

| 参考项目 | 本项目 | 备注 |
|---------|--------|------|
| `rag/`（管道 + 检索工具，2 文件） | `knowledge/`（当前 1 文件，Phase 3 增长） | 同模式 |
| `chat/`（编排 + 流式 + 存储，5 文件） | `agent/`（当前 3 文件，Phase 2 增长） | 精简版，无多用户持久化 |
| `indexing/`（文档摄取全链路，6 文件） | 无——由 Streamlit 管理面板处理 | 功能不同 |
| `infra/`（数据库 + 缓存 + 认证，3 文件） | 无——单用户不需要 | 功能不同 |
| `schemas/`（Pydantic 验证，3 文件） | 无——config.json 做类型约束 | 规模差异 |
| `api/`（HTTP 路由，5 文件） | 无——Chainlit/Streamlit 内置处理 | 框架差异 |
| `tools/`（LangChain @tool，2 文件） | `agent/tools.py` | 当前只有 1 个工具 |

参考项目隔离了 9 个子目录的复杂度，我们只有 2 个——因为项目规模小了约 10 倍。结构跟随规模，不提前建空中楼阁。

---

## 升级永不改 `app.py` 的导入

```python
# app.py —— 永远只要这两行
from src import load_config, create_embedding, create_llm
from src.knowledge import create_store
from src.agent import build_prompt, build_tools, create_agent, run_stream
```

内部升级时只改 `__init__.py` 的重导出：

```python
# 现在：agent/__init__.py
from src.agent.factory import create_agent, run_agent

# Phase 2：agent/__init__.py（对外不变）
from src.agent.graph.pipeline import create_agent, run_agent
```

---

## 文件命名规范

遵循项目根约定的三层命名：
- 文件在 Python 包内 → 用英文简名（`store.py`、`factory.py`），因为 Python import 不支持中文路径
- `__init__.py` 内的导出名 → 用英文函数名（`create_agent`、`build_prompt`）
- 代码注释、设计文档 → 中文
