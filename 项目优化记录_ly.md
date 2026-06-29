# 项目优化记录

> 记录本项目已完成的工程改进、解决的问题与踩过的坑。
> 领域创新与改进点的全面清单见 [创新点清单_ly.md](创新点清单_ly.md)。

---

## 一、工程优化（已完成）

### 1. Docker 容器化（环境锁定）

- **完成日期**：2026-06-27
- **问题**：Python 3.7 + PyTorch CUDA + ChromaDB Rust 后端的组合，`pip install` 一个新包可能导致 torch 版本被覆盖、HNSW 索引格式不兼容
- **方案**：Dockerfile 锁死所有依赖版本，一行 `docker compose up -d` 复现环境
- **效果**：宿主机环境问题不再影响项目，GPU Embedding 直通可用
- **文件**：`Dockerfile` / `docker-compose.yml` / `.dockerignore` / `Docker操作速查_ly.md`

### 2. 代码分包（src/ 包架构）

- **完成日期**：2026-06-27
- **问题**：`app.py`、`管理面板.py`、`批量导入mod代码.py` 各自实现了重复的 `load_config`、`get_embedding`、ChromaDB 初始化函数
- **方案**：抽取公共逻辑到 `src/` 包，按耦合分 `agent/` + `knowledge/` 两个子包，三入口改为导入消费
- **效果**：app.py 208→62 行，重复代码清零，后续所有功能改动只需改对应子包
- **文件**：10 个新建文件（见 `src架构设计_ly.md`）
- **踩坑**：
  - `factory.py` 中本地 `def create_agent` shadow 了 `from langchain.agents import create_agent`，导致递归。解决：`import ... as _create_langchain_agent`
  - Windows 上 `docker exec` 直接传 Unix 路径被 mangling。解决：用 `sh -c "..."` 包裹

### 3. LangGraph 确定性编排（Phase 2）

- **完成日期**：2026-06-29
- **问题**：LangChain `create_agent` 由 LLM 自行决定何时检索、检索几次——概率性行为，靠 system prompt 软约束（"最多 3 次"）不可靠。后续每加一层复杂度，prompt 就臃肿一圈
- **方案**：迁移到 LangGraph StateGraph，把 RAG 流程从"LLM 决定"变为"开发者定义节点+边"的确定性图编排
- **图结构**：`retrieve_initial → grade_documents → [yes] generate_answer / [no] rewrite_question → retrieve_expanded → generate_answer`
- **效果**：
  - 检索次数由图的边固化（最多 2 次），物理硬限制替代 prompt 软约束
  - `app.py` 事件格式不变（`{type: "token" | "tool_start" | "tool_end"}`），UI 零改动
  - `recursion_limit=25` 不再需要，图的最大深度固定（5 个节点）
- **文件**：
  - 🆕 `src/agent/graph/__init__.py` / `nodes.py` / `pipeline.py`（3 个新文件）
  - ✏️ `src/agent/factory.py` — 委托给 graph；`run_agent_stream` 适配 astream_events 事件映射
  - ✏️ `src/agent/prompt.py` — 移除"最多调 3 次工具"等过时软约束
  - ✏️ `src/llm.py` — 添加 `streaming=True`（LangGraph astream_events 捕获节点内 LLM 流式）
  - ✏️ `app.py` — `create_agent` 调用新增 `retriever=` 参数（一行改动）
  - ⚠️ **集成测试暴露检索质量问题**：LangGraph 图跑通后发现回答质量反而比 Phase 1 差——不是因为图不对，而是底层 `all-MiniLM-L6-v2` 纯英文模型对中文"失明"。此发现直接触发了 Embedding 升级（见下方 §4）。

### 4. Embedding 模型升级——修复中文"语义失明"（Phase 2 中途 → Phase 3）

- **完成日期**：2026-06-29
- **触发原因**：Phase 2 LangGraph 迁移完成后做集成测试时，发现检索结果**系统性错误**——
  - 查询"棱镜mod有哪些装备"：Top-10 全部返回小穹 mod 的文件，0% 命中棱镜
  - 查询"DST中食物腐败速度怎么修改"：5 条中 4 条是小穹，与问题模组无关
  - 根因定位：`all-MiniLM-L6-v2`（384 维）是纯英文预训练模型。对中国文字做 embedding 时，所有中文都被映射到同一个拥挤的低质量区域，模型无法区分"棱镜"和"小穹"、"装备"和"食物"之间的语义差异。哪个 mod 的 chunk 里中文多一点（小穹中文字符占比 4.1% vs 棱镜 1.1%），向量就近邻落在哪。
- **方案**：升级到 `BAAI/bge-m3`（1024 维，多语言 100+ 种，BAAI 2024）。查询时添加 bge 系列模型训练时使用的指令前缀（`"Represent this sentence for searching relevant passages:"`），入库时不加前缀，保持查询端和文档端在同一个语义空间。
- **代价**：旧模型 384 维向量与新模型 1024 维不兼容，必须清空 ChromaDB collection 后重新入库全部 35,039 个片段（GPU 满载 ~15 分钟）
- **效果**：
  - "棱镜mod装备"：0% → 100% 命中棱镜
  - "DST食物腐败"：80% 小穹 → 棱镜+能力勋章正确混合
  - 5 条基准测试中 4 条检索准确性明显提升
  - 纯英文 Mod 名（如"Beneath the World Below"）匹配仍有盲区——这是专有名词冷启动问题：Mod 名和缩写（BWB）在通用 Embedding 训练语料中几乎不存在，模型无法建立映射。需词典术语解析层补齐（"深埋之下" ↔ "Beneath the World Below" ↔ "BWB"）
- **踩坑**：
  - `HuggingFaceEmbeddings` 不接受 `query_instruction` 入参 → 改为在 `nodes.py` 检索节点手动调用 `add_query_prefix()`（见 [踩坑记录/11](踩坑记录/11_HuggingFaceEmbeddings不支持query_instruction.md)）
  - 节点闭包依赖注入链（app.py → factory.py → pipeline.py → nodes.py）需四层同步更新 `model_name` 参数（见 [踩坑记录/10](踩坑记录/10_LangGraph节点闭包依赖注入.md)）
- **文件**：
  - ✏️ `config.json` / `src/config.py` — `model_name`: `all-MiniLM-L6-v2` → `BAAI/bge-m3`
  - ✏️ `src/embedding.py` — 新增 `add_query_prefix()` + `normalize_embeddings=True`
  - ✏️ `src/agent/graph/nodes.py` — 检索节点调用 `add_query_prefix()`
  - ✏️ `src/agent/graph/pipeline.py` / `factory.py` / `app.py` — 四层链路透传 `model_name`

---

## 二、工程优化（进行中 / 计划中）

| # | 优化点 | 说明 | Phase |
|---|--------|------|-------|
| 8 | 流式输出（打字机效果） | `agent.invoke()` → `agent.astream()` + `stream_token()` | 🟢 Phase 1 |
| 9 | 工具调用可视化 | `@cl.step` 包裹检索，UI 中展示搜索进度 | 🟢 Phase 1 |
| 10 | Agent 思考路径透传 | 解析 astream 消息类型，展示推理链路（2026-06-29 新增 grade/rewrite 节点可视化） | 🟢 Phase 1-2 |
| 11 | 检索详情结构化展示 | 文件来源/Mod 名称/片段数 放入 Step.output | 🟢 Phase 1 |
| 12 | LangGraph 确定性编排 | `create_agent` 概率性行为 → StateGraph 节点+边的硬约束 | 🟢 Phase 2（2026-06-29） |
| 13 | 评分门控 | LLM 判断检索结果相关性，不相关则重写查询 | 🟢 Phase 2（2026-06-29） |
| 14 | Embedding 模型升级 | `all-MiniLM-L6-v2` 384d → `BAAI/bge-m3` 1024d 多语言 100+ 种 | 🟢 Phase 3（2026-06-29） |
| 15 | Rerank 精排 | 粗检后再过精排模型，提升 Top-K 精度 | Phase 3 |
| 16 | 工具调用硬限制 | 代码级限制检索次数（替代 prompt 软约束）— 随 LangGraph 迁移自动获得 | 🟢 Phase 2（2026-06-29） |
| 17 | 图节点过程可视化 | grade_documents / rewrite_question 节点在 UI 中以 📊✏️ 折叠卡片展示，用户可见 LLM 的 yes/no 判断和查询改写结果 | 🟢 Phase 2（2026-06-29） |

---

## 三、实测发现（供后续参考）

- **Phase 2 集成测试暴露检索灾难**（2026-06-29）：
  - 查询"棱镜mod有哪些装备"→ Top-10 **全部是小穹**，0% 命中目标 Mod
  - 查询"DST中食物腐败速度怎么修改"→ 5 条中 4 条小穹，与问题无关
  - 根因：`all-MiniLM-L6-v2` 是纯英文模型，无法区分任何中文语义。谁的中文 chunk 多（小穹 4.1% vs 棱镜 1.1%），谁就被"撞上"。
  - 此发现触发了 **Phase 3 首项提前执行**——bge-m3 升级。升级后命中率飞跃：棱镜 0%→100%，DST 食物 80%小穹→正确混合。
- **专有名词冷启动**：bge-m3 升级后中文语义匹配大幅改善，但 Mod 名/缩写（如"Beneath the World Below"、"BWB"）在通用 Embedding 训练语料中几乎不存在，用户说"深埋之下 mod"时向量无法关联到该 Mod 的代码 chunk。这不是模型的"盲区"，而是所有通用 Embedding 都无法处理的专有名词问题。解决方案：词典术语解析层——将用户俗称映射为 Mod 内文件路径/标识符，检索前用精确 ID 过滤。
- **Agent 容易反复搜索**：~~已加 `recursion_limit=25` + system prompt 约束（最多 3 次），但属软控制。~~ **Phase 2 已解决**：LangGraph 图的边固化检索次数（最多 2 次），物理上不可能有第三次搜索
- **单库够用但不够好**：四分库 + 词典扩展是提升精度的关键路径
- **影响**：检索质量问题不解决，后续增强（Step-Back/HyDE/多跳）效果会打折扣
