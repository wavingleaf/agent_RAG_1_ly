# TODO.md — agent_RAG_1_ly 待办清单

> **代码结构**：见 [`src架构设计_ly.md`](src架构设计_ly.md)。后续改动归属 `src/config.py / llm.py / embedding.py / knowledge/ / agent/`。
> **已完成工作**：Phase 1（流式输出、工具可视化）、Phase 2（LangGraph 确定性编排、评分门控、查询重写）、Embedding 升级（bge-m3）均记录在 [`项目优化记录_ly.md`](项目优化记录_ly.md)，此处不再重复。
> **设计讨论与待决策项**：见 [`设计讨论临时记录_ly.md`](设计讨论临时记录_ly.md)。2026-06-29 grill-with-docs 审查的 17 条发现及决策结论均记录在那边。

---

## 维护类

- 踩坑记录：[`踩坑记录/`](踩坑记录/) — 11 项，已按「已避免/使用方式依赖」分类（🔴 仍可能触发，该类别数量为零）
- ChromaDB 持久化目录：Docker 内 `/app/chroma_data/bge-m3`，宿主机由 volume 管理
- Chat 容器用 CPU embedding、Admin 容器用 GPU embedding（入库时）。详见 `docker-compose.yml`

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

### 1. LLM 自主查询重写（Step-Back + HyDE）

- 参考项目 `rewrite_question_node` 的三策略路由：step_back / hyde / complex
- **这是查询重写的一种变体**，信息源是 LLM 内部知识或生成能力（非词典）。与 Phase 4 §5 的词典增强查询重写最终共用同一个 `rewrite_question` 节点，区别仅在 LLM 调用时输入是否包含词典候选。
- **这是上层策略**：条件触发，各需一次 LLM 调用。挂在基础链路（词典增强查询重写）之上，基础链路产出不够时启动。非"始终开启"。
- **实现顺序**：先 Step-Back（改动最小），再 HyDE，Decomposition 放远期
- **影响文件**：`knowledge/expand.py`（新建）、`agent/graph/nodes.py`

### 2. Rerank 精排

- 候选：Jina Rerank API / 本地 Cross-Encoder 模型 / bge-reranker-v2-m3
- **影响文件**：`knowledge/rerank.py`（新建）、`knowledge/store.py`

### 3. 🔬 分块质量测试与调优

> **类型**：依赖实验的决策——代码改动小，但需要先跑对比测试才能确定最优参数。

- **背景**：当前 chunk_size=500 / chunk_overlap=50，分隔符为默认值。Lua 代码可能被截断在不自然位置（如 `function` 和 `end` 分离），影响检索质量。此外 bge-m3 训练语料中 Lua 代码占比极低，代码语义在自然语言 embedding 空间中理解弱。两项均未入 TODO/创新点清单。
- **实验目标**：a) 找到 Lua 代码的最佳分块参数（chunk_size / overlap / 分隔符）；b) 确认当前分割策略是否对检索质量有明显损害
- **实验方法**：准备 ~10 条已知答案的代码查询，在不同分块参数下对比检索命中率
- **决策标准**：若调整参数后命中率提升 >10pp → 更新 config.json 默认值并重建向量库；否则保持现状
- **影响文件**：`config.json`（chunk 参数）、`批量导入mod代码.py`（可能需 Lua 感知的 splitter）
- 详见 `设计讨论临时记录_ly.md` #12

### 4. 🔬 MMR 多样性检索实验

> **类型**：依赖实验的决策——代码改动 ~10 行，但 k=3 的小候选集上 MMR 是否有意义需实测。

- **背景**：当前 `similarity_search` 不做多样性控制，Top-3 可能来自同一文件的不同行号偏移，chunk 内容高度重叠。踩坑记录 #03 的事后"同文件提示"只是标注而非预防。
- **实验目标**：在 k=3 的小候选集上，MMR 能否显著提升检索结果的来源多样性
- **实验方法**：用 `max_marginal_relevance_search`（LangChain 内置）替换 `similarity_search`，准备 ~20 条查询对比两组的来源文件分布
- **决策标准**：若 MMR 显著提升了来源多样性（Top-3 覆盖 ≥2 个不同文件的查询比例提升 >20pp）→ 替换默认检索函数；否则保持现状
- **影响文件**：`src/agent/graph/nodes.py`（检索调用）、`src/knowledge/store.py`
- 详见 `设计讨论临时记录_ly.md` #10

### 5. 🔬 评分门控可靠性评估与优化

> **类型**：依赖实验的决策——必须先收集样本数据，才能判断当前 yes/no 门控是否够用、该不该改阈值或粒度。

- **背景**：当前 `grade_documents` 和 `generate_answer` 使用同一个 DeepSeek 模型做 self-grade——"no"→重写查询（但重写也可能跑偏），"yes"→直接回答（但可能只是关键词匹配，未真正理解文档）。当前退化检测已从精确字符串比较改为 LLM 语义等价判断（#16），远期与本项一并优化。
- **实验目标**：收集 grade 节点的 yes/no 输出样本（目标 ~50 条不同问题），标注实际相关度，统计误判率
- **实验方法**：运行聊天端，记录 grade 节点的判断结果，人工标注每条判断是否正确
- **决策标准**：
  - 误判率 < 10% → 保持二元 yes/no，只调 prompt
  - 误判率 10–25% → 考虑改为 1-5 分粒度 + 阈值设计
  - 误判率 > 25% → 引入交叉验证（多模型投票）或更换评分策略
- **影响文件**：`src/agent/graph/nodes.py`（grade 节点 prompt + 阈值）
- 详见 `设计讨论临时记录_ly.md` #4、#16

---

## 𐄂 再下一轮——四分库架构改造（Phase 4）

> **代码结构影响**：`knowledge/` 新增 `router.py`；`agent/tools.py` 拆为多工具。详见 [`src架构设计_ly.md` §Phase 4](src架构设计_ly.md#phase-4-四分库架构)。

### 1. config.json 结构调整
- `knowledge_base` 从单对象改为四个独立知识源配置，各有独立 collection、持久化路径、分块参数
- `tools` 拆为四个：`glossary_lookup` / `search_game_scripts` / `search_reference_mods` / `search_local_docs`
- **影响文件**：`config.json`、`agent/tools.py`、`knowledge/store.py`、`管理面板.py`、`批量导入mod代码.py`

### 2. 管理面板适配四库
- 文档上传增加「目标知识源」下拉框，已索引文档按知识源分组
- **影响文件**：`管理面板.py`

### 3. glossary-lookup 工具实现

> 📐 **设计决策（2026-06-29 grill-with-docs）**：glossary-lookup 应归类为**工具**（与 search_knowledge_base 平级的独立工具），而非"知识库四分法"的第四库。前三者走向量语义检索，glossary-lookup 是精确键值匹配（ID↔中文名↔参数值），查询模式完全不同。
> - **近期**：沿用当前 RAG 方案（向量匹配存入 ChromaDB），先跑通链路
> - **远期**：验证通过后改为 grep 精确字符串匹配（本质是键值查找，向量检索在此场景下不是最优解）
> - 详见 `设计讨论临时记录_ly.md` #1

- 加载 chinese_s.po → 中文名→英文 ID；prefablist.lua → 有效 Prefab ID；tuning.lua → 参数名→值
- **影响文件**：`agent/tools.py`、`knowledge/store.py`

### 4. 🔬 复审问题（依赖 glossary-lookup）

> **类型**：交互设计决策——两种断点位置都先尝试，试错成本低。依赖 glossary-lookup 工具先建成。

- **背景**：当前设计是"检索前"确认——词典重组 → 弹出卡片 → 用户确认/超时自动通过 → 检索。但 30 秒超时意味着用户切窗口后大概率错过。
- **两种方案**：
  - **方案 A（检索前确认）**：词典重组后弹出卡片，用户可选"直接用"/"微调"/"回退"
  - **方案 B（回答后纠正）**：先检索+回答，回答末尾标注"以上基于 X、Y、Z 的词典映射，若有误请点击修正"
- **实验方法**：两种方案均在 Streamlit 聊天端中实现并实际使用一段时间，收集用户反馈
- **影响文件**：`app.py`（UI 卡片）、`src/agent/graph/nodes.py`（可能需要新增 review 节点）
- **依赖**：Phase 4 §3（glossary-lookup 工具实现）必须先完成
- 详见 `设计讨论临时记录_ly.md` #6，创新点清单「复审问题」章节

### 5. 词典增强查询重写（Glossary-Informed Query Rewriting）

> 📐 **设计决策（2026-06-29 grill-with-docs）**：这是**查询重写的一种变体**，信息源是 glossary-lookup 查表结果（非 LLM 内部知识）。
> - 四种查询重写策略骨架相同（输入问题 → 输出重写查询），区别在信息源。词典信息源代价为零（查表不需额外 LLM 调用），因此是**基础链路**（必经管道，始终开启）。
> - Phase 3 §3 的 Step-Back / HyDE / Decomposition 是 LLM 自主变体，信息源为 LLM 内部知识/生成能力，各需一次 LLM 调用，是**上层策略**（条件触发）。
> - 两个变体最终共用同一个 `rewrite_question` 节点，LLM 的输入在词典命中时多一份候选标识符列表。
> - 详见 `设计讨论临时记录_ly.md` #3

- System prompt 注入两阶段检索规则：先 glossary-lookup → LLM 理解上下文后融入标识符重写 query → 并行检索三个知识源
- **影响文件**：`agent/prompt.py`、`knowledge/router.py`

### 6. 词典缺失降级策略
- glossary 返回空 → 自动并行全源 + 标注「词典未命中」→ 全局无果 → 提示手动指定
- **影响文件**：`knowledge/router.py`

### 7. 大规模文档导入
- 本体代码：DST scripts/ ~4000 .lua 文件；词典数据：prefablist.lua + tuning.lua + chinese_s.po；本地文档 ~30 .md
- **影响文件**：仅入库操作

### 8. 📦 社区术语映射表（词典第四张表）

> **类型**：新功能开发——依赖 glossary-lookup 基础设施建成。

- **背景**：当前 glossary-lookup 三张表（prefablist.lua / tuning.lua / chinese_s.po）均来自官方数据，无法覆盖 Mod 完整名↔缩写↔玩家俗称（如 "Beneath the World Below" → "BWB" → "深埋之下"）
- **内容**：社区术语映射表（Mod 名↔缩写↔俗称），由用户反馈持续补充
- **影响文件**：新增数据文件 + `agent/tools.py`（加载+查询逻辑）
- **依赖**：Phase 4 §3（glossary-lookup 工具实现）必须先完成
- 详见 `设计讨论临时记录_ly.md` #9

### 9. 🔬 混合库 vs 分库检索质量对比

> **类型**：依赖实验的决策——必须在四分库建成后才能跑对比测试。这是对 Phase 4 整体收益的验证。

- **背景**：当前"单库够用但不够好"的判断是基于单库内混合了 4 个 Mod 代码的情况，并非基于"四个来源混入同一 collection"的实测。四分库设计更多是"来源性质不同"的理论推断。本实验回答：分库的边际收益是否值得 Phase 4 的全部复杂度。
- **实验目标**：量化分库 vs 混合库的检索质量差异
- **实验方法**：
  1. 构建两套 collection——混合库（所有来源同一 collection）+ 四分库（四个独立 collection）
  2. 准备 ~20 条标注查询（涵盖中文俗称、代码 ID、跨库概念等类别）
  3. 两套各自检索，人工标注 Top-K 相关度
  4. 对比 recall@k、MRR、来源多样性
- **决策标准**：若分库在 recall@5 上提升 < 5pp 且 MRR 提升 < 0.05 → 考虑回退到混合库，降低系统复杂度
- **影响文件**：实验脚本（不在正式代码中）
- **依赖**：Phase 4 §1-§7 全部完成后才能进行
- 详见 `设计讨论临时记录_ly.md` #5

---

## 𐄂 远期——多跳与交叉验证（Phase 5）

- Query Decomposition：Planner 拆解复杂问题为子问题链（参考来源：参考项目 `rag/pipeline.py` 的 `decompose_question` + LangGraph `Send` API 并行子 Agent）
- 跨源交叉验证：同一概念在本体 vs Mod vs 文档中的差异比对

### 📦 向量语义 + grep 精确混合检索

> **类型**：远期新功能开发——远离当前阶段。

- **背景**：bge-m3 训练语料中 Lua 代码占比极低，代码语义（函数名、变量名、模块路径）在自然语言 embedding 空间中理解弱。向量检索匹配自然语言描述，grep 精确匹配代码标识符，两路融合可互补。
- **方案**：语义向量检索（自然语言查询 → ChromaDB） + grep 精确检索（代码标识符 → 文件定位）→ 结果融合去重 → 统一排序
- **影响文件**：`knowledge/hybrid_search.py`（新建）、`src/agent/graph/nodes.py`
- 详见 `设计讨论临时记录_ly.md` #12

---
