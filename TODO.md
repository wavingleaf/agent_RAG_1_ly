# TODO.md — agent_RAG_1_ly 待办清单

> **代码结构**：见 [`src架构设计_ly.md`](src架构设计_ly.md)。后续改动归属 `src/config.py / llm.py / embedding.py / knowledge/ / agent/`。
> **已完成优化**：见 [`项目优化记录_ly.md`](项目优化记录_ly.md)。PoC 发现、Docker 容器化、代码分包等均记录在那边。

---

## ✅ 已完成——RAG 过程可视化（Phase 1）

> **完成日期**：2026-06-29
> **结果**：流式打字机 + 三色折叠卡片（🔍检索/📊评估/✏️重写）。详见 `项目优化记录_ly.md`。

### 1. 切换到流式 Agent 模式 ✅

### 2. 工具调用过程可视化 ✅

### 3. 检索详情展示 ✅

### 4. Agent 思考路径透传 ✅

---

## ✅ 已完成——迁移到 LangGraph（Phase 2）

> **完成日期**：2026-06-29
> **结果**：LangGraph StateGraph 替代 LangChain `create_agent`。图结构 `retrieve → grade → rewrite → re-retrieve → answer`，检索次数由图边固化（最多 2 次）。
> Phase 2 集成测试中暴露了 `all-MiniLM-L6-v2` 纯英文模型对中文"失明"的问题，直接触发了 Phase 3 Embedding 升级（见下方）。

### 1. 搭建最小 LangGraph 骨架 ✅

### 2. 添加评分门控节点 ✅

### 3. 添加查询重写 + 重检索链路 ✅

### 4. 工具调用硬限制（随图结构自动获得） ✅

---

## 👉 当前阶段——检索质量提升（Phase 3）

### 0. 🔴 统一 Streamlit 聊天+管理（第一优先级）

- **目标**：用 Streamlit 替换 Chainlit，聊天端与管理面板合并为一个应用
- **动机**：
  - 去除 Chainlit 依赖，减少框架数量
  - 聊天端与管理面板共享 `st.session_state`，不存在 ChromaDB 并发读写问题
  - 一个启动脚本、一个端口
- **代价**：工具调用不再有 Chainlit 独立时间线气泡，退化为回答中的内嵌 `<details>` 折叠卡片
- **代码量**：app.py ~80 行（从 ~196 行重写），管理面板.py 不动
- **影响文件**：`app.py`（重写）、`启动rag助手.py`（删除，合并入新启动脚本）、`requirements.txt`（移除 chainlit）

### 1. 升级 Embedding 模型 ✅（2026-06-29）

- `all-MiniLM-L6-v2` 384d → `BAAI/bge-m3` 1024d 多语言 100+ 种
- Phase 2 集成测试中发现：查询"棱镜mod装备" → Top-10 全返回小穹（0% 命中棱镜），根因是 MiniLM 纯英文模型无法区分钟文语义。升级后棱镜命中率 0%→100%。
- 详见 `项目优化记录_ly.md` §4。
- **影响文件**：`config.json`、`src/embedding.py`、`src/agent/graph/nodes.py`、`src/agent/graph/pipeline.py`、`src/agent/factory.py`、`app.py`

### 2. 工具调用硬限制 ✅（随 Phase 2 自动获得）

- LangGraph 图的边 = 物理硬约束，最多 2 次检索。不再需要 prompt 软约束或 `recursion_limit`。
- 已从 Phase 3 待办移除——Phase 2 迁移完成后自动获得。

### 3. Query Expansion（查询扩展）

- Step-Back Prompting + HyDE
- **影响文件**：`knowledge/expand.py`（新建）、`agent/graph/nodes.py`

### 4. Rerank 精排

- 候选：Jina Rerank API / 本地 Cross-Encoder 模型 / bge-reranker-v2-m3
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

- 踩坑记录：[`踩坑记录/`](踩坑记录/) — 11 项，已按「已避免/使用方式依赖」分类（🔴 仍可能触发，该类别数量为零）
- ChromaDB 持久化目录：Docker 内 `/app/chroma_data/bge-m3`，宿主机由 volume 管理
- Chat 容器用 CPU embedding、Admin 容器用 GPU embedding（入库时）。详见 `docker-compose.yml`
