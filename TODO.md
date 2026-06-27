# TODO.md — agent_RAG_1_ly 待办清单

> **代码结构**：见 [`src架构设计_ly.md`](src架构设计_ly.md)。后续改动归属 `src/config.py / llm.py / embedding.py / knowledge/ / agent/`。
> **已完成优化**：见 [`项目优化记录_ly.md`](项目优化记录_ly.md)。PoC 发现、Docker 容器化、代码分包等均记录在那边。

---

## 👉 当前阶段——RAG 过程可视化

> **背景**：当前聊天端使用 `agent.invoke()`（阻塞式），用户提交问题后只能看到一个静态的"思考中…"动画，直到回答一次性返回。Agent 内部在做什么（检索？分析？重试？）完全不可见。
>
> **目标**：让用户实时看到 Agent 的每一步动作——工具调用、检索进度、回答生成——全部在 Chainlit UI 中可视化展示。
>
> **参考来源**：参考项目「SuperMew」的 SSE 流式架构 + 前端思考状态机（见 `参考项目对比分析_ly.md` 第 2.7 节和第 3.1 节）。设计思路借鉴，具体实现用 Chainlit 原生 API 重写。
>
> **可行性**：✅ 所有依赖已具备——Chainlit 2.11.1 的 `cl.Step` / `@cl.step` / `cl.Message.stream_token()` 均为内置 API，不需要安装任何新依赖。

### 1. 切换到流式 Agent 模式

将 `agent.invoke()` 改为 `agent.astream(stream_mode="messages")`，逐 token 产出后用 `cl.Message.stream_token()` 发送。

- **依赖**：无
- **影响文件**：`agent/factory.py`（新增 `run_agent_stream()` 生成器）、`app.py`（消费流式产出）
- **工作量**：小（~40 行改动）
- **收益**：回答从"卡住等待"变成打字机效果

### 2. 工具调用过程可视化

用 `@cl.step` 装饰器包裹工具调用，让每次检索在 UI 中显示为独立的折叠步骤。

```
用户看到的效果：
┌─────────────────────────────┐
│ 🔍 正在检索知识库...        │ ← cl.Step（可展开看检索结果摘要）
│ ✅ 找到 3 个相关片段        │
├─────────────────────────────┤
│ 🤖 正在生成回答...          │ ← 自动过渡到流式回答
│ 根据知识库中的信息，便携...  │ ← 逐 token 出现
└─────────────────────────────┘
```

- **依赖**：任务 1
- **影响文件**：`agent/tools.py`（工具内部加 `@cl.step`）
- **工作量**：中（理解 Chainlit Step 生命周期和 LangChain tool 的交互方式）

### 3. 检索详情展示（检索到了什么、来自哪里）

在 `cl.Step` 的输出中展示检索结果的关键信息：每个片段的文件来源 + Mod 名称、片段数量、同文件提示。

- **依赖**：任务 2
- **影响文件**：`agent/tools.py`（结构化格式化检索结果放入 Step.output）
- **工作量**：小（数据已有，换展示方式）

### 4. Agent 思考路径透传

解析 `astream` 返回的消息类型（AIMessage / ToolMessage / AIMessageChunk），在消息级别用 Chainlit Step 展示推理过程。

- **依赖**：任务 1
- **影响文件**：`app.py`（解析消息类型并分阶段创建 Step）、`agent/factory.py`（消息类型标注）
- **工作量**：中（需要解析 `astream` 的消息类型并分阶段创建 Step）

---

## 𐄂 次优先级——迁移到 LangGraph（架构打底）

> **背景**：当前用 LangChain 1.0 `create_agent`，Agent 自行判断"是否检索、检索几次"——靠 system prompt 约束模型的概率性行为，不可靠。后续每加一层复杂度，system prompt 就更臃肿一圈。
>
> **方案**：迁移到 LangGraph StateGraph，把 RAG 流程从"让 LLM 决定"变为"开发者定义节点+边"的确定性图编排。
>
> **为什么放这里**：在加新功能之前把架构底子铺好。做完可视化后立刻做——可视化 Layer 已经写好了，迁移到 LangGraph 后每个节点的状态变化能直接复用已有的 `cl.Step` 来展示。
>
> **参考来源**：参考项目的 `backend/rag/pipeline.py`（680 行）是完整可参照的实现。
>
> **代码结构影响**：`agent/factory.py` 升级为子包 `agent/graph/`（含 `pipeline.py` + `nodes.py`）。详见 [`src架构设计_ly.md` §Phase 2](src架构设计_ly.md#phase-2-迁移到-langgraph)。

### 1. 搭建最小 LangGraph 骨架

```
入口(retrieve) → 检索 → END
```

- State 定义：`question / query / context / docs / response`
- 节点：`retrieve_initial`（调用 ChromaDB 检索）
- **依赖**：RAG 可视化全部完成
- **影响文件**：`agent/factory.py` → `agent/graph/pipeline.py` + `agent/graph/nodes.py`
- **工作量**：中

### 2. 添加评分门控节点

在检索后插入 `grade_documents` 节点：LLM 判断检索结果是否相关 → yes 进回答 / no 进重写。

- **依赖**：任务 1
- **影响文件**：`agent/graph/nodes.py` + `pipeline.py`
- **工作量**：小

### 3. 添加查询重写 + 重检索链路

`rewrite_question` → `retrieve_expanded` → 回答。

- **依赖**：任务 2
- **影响文件**：`agent/graph/nodes.py` + `pipeline.py`
- **工作量**：中

### 4. 工具调用硬限制（迁移后自然获得）

图的边本身就是硬限制——搜索节点只在指定位置出现。不再需要 prompt 约束。

- **依赖**：任务 1（自动附带）
- **影响文件**：无

---

## 𐄂 再下一轮——检索质量提升

> 说明：LangGraph 迁移完成后，每个改动可以独立验证（输 State 看 State 出）。
>
> **代码结构影响**：`knowledge/store.py` 随 rerank/expand 的加入升级为子包。详见 [`src架构设计_ly.md` §Phase 3](src架构设计_ly.md#phase-3-检索质量提升)。

### 1. 升级 Embedding 模型（优先）
- 候选：`bge-large-zh-v1.5` / `multilingual-e5-large` / `BAAI/bge-m3`（参考项目同款，1024维）
- 需评估：RTX 4060 8GB 显存占用、推理速度、ChromaDB 兼容性
- **影响文件**：`embedding.py`（改一行模型名）、`config.json`

### 2. 工具调用硬限制（参考项目方案）
- 参考项目 `tools/knowledge.py` 用 `_try_acquire_knowledge_tool_call()` 硬限制每轮最多 1 次检索
- **影响文件**：`agent/tools.py`

### 3. Query Expansion（查询扩展）
- Step-Back Prompting + HyDE
- **影响文件**：`knowledge/expand.py`（新建）、`agent/tools.py`

### 4. Rerank 精排
- 候选：Jina Rerank API / 本地 Cross-Encoder 模型
- **影响文件**：`knowledge/rerank.py`（新建）、`knowledge/store.py`

---

## 𐄂 再下一轮——四分库架构改造

> **代码结构影响**：`knowledge/` 新增 `router.py`；`agent/tools.py` 拆为多工具。详见 [`src架构设计_ly.md` §Phase 4](src架构设计_ly.md#phase-4-四分库架构)。

### 1. config.json 结构调整
- `knowledge_base` 从单对象改为四个独立知识源配置，各有独立 collection、持久化路径、分块参数
- `tools` 拆为四个：`glossary_lookup` / `search_game_scripts` / `search_reference_mods` / `search_local_docs`
- **影响文件**：`config.json`、`agent/tools.py`、`knowledge/store.py`、`管理面板.py`、`批量导入mod代码.py`

### 2. 管理面板适配四库
- 文档上传增加「目标知识源」下拉框，已索引文档按知识源分组
- **影响文件**：`管理面板.py`

### 3. glossary-lookup 工具实现
- 加载 chinese_s.po → 中文名→英文 ID；prefablist.lua → 有效 Prefab ID；tuning.lua → 参数名→值
- **影响文件**：`agent/tools.py`、`knowledge/store.py`

### 4. Query Expansion 管道
- System prompt 注入两阶段检索规则：先 glossary-lookup → 拼 ID 重写 query → 并行检索三个知识源
- **影响文件**：`agent/prompt.py`、`knowledge/router.py`

### 5. 词典缺失降级策略
- glossary 返回空 → 自动并行全源 + 标注「词典未命中」→ 全局无果 → 提示手动指定
- **影响文件**：`knowledge/router.py`

### 6. 大规模文档导入
- 本体代码：DST scripts/ ~4000 .lua 文件；词典数据：prefablist.lua + tuning.lua + chinese_s.po；本地文档 ~30 .md
- **影响文件**：仅入库操作

---

## 𐄂 远期——多跳与交叉验证

- Query Decomposition：Planner 拆解复杂问题为子问题链（参考来源：参考项目 `rag/pipeline.py` 的 `decompose_question` + LangGraph `Send` API 并行子 Agent）
- 跨源交叉验证：同一概念在本体 vs Mod vs 文档中的差异比对

---

## 维护类

- 踩坑记录：[`踩坑记录/`](踩坑记录/) — 9 项，已按「已避免/使用方式依赖/仍可能触发」分类
- `.env` 编码 / HuggingFace 镜像 / Streamlit 文件监视器 / `RecursiveCharacterTextSplitter` 路径 — 已修复
- ChromaDB 持久化目录：Docker 内 `/app/chroma_data/v1`，宿主机由 volume 管理
