# 项目优化记录

> 记录本项目相对于通用 RAG Agent 方案的差异化设计与已完成的工程改进。
> 「领域创新」指 DST Mod 开发场景特有的优化，通用 RAG 项目不需要或不会想到做这些。

---

## 一、领域创新（DST Mod 特有问题驱动）

这些改进源自「用户语言 ≠ 文档语言」的领域鸿沟——用户说中文俗称，文档是英文代码标识符。

| # | 创新点 | 关键词 | 状态 |
|---|--------|--------|------|
| 1 | 检索前插入**词典术语解析层**，将用户的中文俗称映射为英文代码标识符，跨越语言鸿沟 | `术语解析` `中英映射` | ⚪ 待实现（Phase 4） |
| 2 | 知识源按**认知类型四分**（本体/范例/文档/词典），而非按数据来源切分，每个源有独立检索语义 | `认知分类` `独立 collection` | ⚪ 待实现（Phase 4） |
| 3 | 领域最优检索路径固化——**先词典后知识源**，减少 Agent 在无关分支上的试错 | `检索顺序` `路径固化` | ⚪ 待实现（Phase 4） |
| 4 | 词典命中后驱动 **Query Expansion**——用精确标识符重写查询再检索，提升代码库命中率 | `查询重写` `标识符拼接` | ⚪ 待实现（Phase 3-4） |
| 5 | **两阈值三路径降级**：词典命中→精确检索 / 词典缺失→自动并行全源 / 知识库全空→手动指定，每级降级告知用户 | `降级透明度` `兜底策略` | ⚪ 待实现（Phase 4） |
| 6 | 四种查询增强技术（Step-Back / HyDE / Query Decomposition / Expansion）各有**领域触发条件**，非全开全关 | `条件触发` `token 节省` | ⚪ 待实现（Phase 3/5） |
| 7 | 检索结果全程携带**来源标签**（game-scripts / reference-mods / local-docs），可跨源对比"本体实现 A，棱镜实现 B" | `来源溯源` `跨源对比` | 🟢 已实现 |

---

## 二、工程优化（已完成）

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

---

## 三、工程优化（进行中 / 计划中）

| # | 优化点 | 说明 | Phase |
|---|--------|------|-------|
| 8 | 流式输出（打字机效果） | `agent.invoke()` → `agent.astream()` + `stream_token()` | Phase 1 |
| 9 | 工具调用可视化 | `@cl.step` 包裹检索，UI 中展示搜索进度 | Phase 1 |
| 10 | Agent 思考路径透传 | 解析 astream 消息类型，展示推理链路 | Phase 1 |
| 11 | 检索详情结构化展示 | 文件来源/Mod 名称/片段数 放入 Step.output | Phase 1 |
| 12 | LangGraph 确定性编排 | `create_agent` 概率性行为 → StateGraph 节点+边的硬约束 | Phase 2 |
| 13 | 评分门控 | LLM 判断检索结果相关性，不相关则重写查询 | Phase 2 |
| 14 | Embedding 模型升级 | `all-MiniLM-L6-v2` → `bge-m3` 或 `multilingual-e5`，提升中英混排语义 | Phase 3 |
| 15 | Rerank 精排 | 粗检后再过精排模型，提升 Top-K 精度 | Phase 3 |
| 16 | 工具调用硬限制 | 代码级限制检索次数（替代 prompt 软约束） | Phase 3 |

---

## 四、PoC 实测发现（供后续参考）

- **检索质量是当前瓶颈**：`all-MiniLM-L6-v2` 对中英混排 Lua 代码语义不准，检索结果常不相关。Embedding 升级是 Phase 3 首项
- **Agent 容易反复搜索**：已加 `recursion_limit=25` + system prompt 约束（最多 3 次），但属软控制。Phase 2 LangGraph 迁移后用图的边做硬限制
- **单库够用但不够好**：四分库 + 词典扩展是提升精度的关键路径
- **影响**：检索质量问题不解决，后续增强（Step-Back/HyDE/多跳）效果会打折扣
