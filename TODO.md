# TODO.md — agent_RAG_1_ly 待办清单

## ✅ PoC 阶段（当前）——用单一优质 Mod 库跑通 RAG

四分库方案先用现有单库代码验证检索质量。通过后从实际体验反馈中判断哪些设计需要调整，
再进入架构改造。避免设计过度、实现不足。

### 0. 棱镜 mod 入库 + 测试问答
- 通过管理面板上传「好mod全部代码供观看/棱镜/」下 ~140 个 .lua 文件
- 分块策略暂用默认值（chunk_size=500, chunk_overlap=50），后续根据检索效果调整
- 用 5-10 个典型 Mod 开发问题测试检索质量：
  - "棱镜的随身容器是怎么实现的？"
  - "月轮宝盘涉及哪些文件和组件？"
  - "棱镜的容器系统和原版有什么不同？"
- 记录：哪些问题检索效果好、哪些差、差的原因是什么
- **依赖**：无（现有代码直接可用）
- **影响文件**：无（仅操作，不改代码）

### 0b. 搜集小穹 mod 代码 + 入库
- 小穹 mod 不在当前项目中，需要去 Steam 创意工坊或相关渠道搜集
- 搜集到后同样通过管理面板入库
- **依赖**：搜集完成
- **影响文件**：无（仅操作）

### 0c. 根据 PoC 结果调整设计
- 检索质量达标 → 继续进入四分库改造
- 检索质量差 → 分析原因（分块策略？Embedding 模型中文能力不足？query 写法？），先修再进
- 发现设计文档中未预见到的问题 → 更新 CONTEXT.md
- **依赖**：任务 0a/0b 完成
- **影响文件**：未知（取决于发现什么问题）

---

## 𐄂 下一轮——四分库架构改造

PoC 验证通过后执行，任务有先后依赖。

### 1. config.json 结构调整
- 将 `knowledge_base` 从单个对象改为四个独立知识源配置
- 每个知识源有独立的 collection 名、持久化路径、分块参数
- 将 `tools` 中的单一 `search_knowledge_base` 拆为四个工具条目：
  `glossary_lookup` / `search_game_scripts` / `search_reference_mods` / `search_local_docs`
- **依赖**：PoC 阶段完成
- **影响文件**：`config.json`、`app.py` 的 `load_config()` 兜底默认值、`管理面板.py`

### 2. 管理面板适配四库
- 文档上传时增加「目标知识源」下拉框（game-scripts / reference-mods / local-docs / glossary-lookup）
- "已索引文档"列表按知识源分组显示
- "清空知识库"增加"选择要清空哪个库"
- **依赖**：任务 1 完成
- **影响文件**：`管理面板.py`

### 3. glossary-lookup 工具实现
- 加载 chinese_s.po → 构建中文名→英文 ID 映射
- 加载 prefablist.lua → 解析所有有效 Prefab ID
- 加载 tuning.lua → 解析参数名→值映射
- 实现三种查询：中文名查 ID / 英文 ID 查中文名 / 参数名查值
- 返回结构化结果，含来源标记（po / prefablist / tuning）
- **依赖**：任务 1 完成
- **影响文件**：`app.py`（新增 `glossary_lookup` tool + 词表加载逻辑）

### 4. Query Expansion 管道
- Agent system prompt 中注入两阶段检索规则
- 每次收到用户问题，先调用 `glossary_lookup`
- 词典返回的 ID / 参数名拼入原问题字符串
- 用重写后的问题并行检索三个知识源
- **依赖**：任务 3 完成
- **影响文件**：`app.py`（system prompt 重写、检索流程改造）

### 5. 词典缺失降级策略（"软化的 B"）
- glossary_lookup 返回空时，跳过两阶段流程
- 自动并行检索三个知识源（不再强制先词典）
- 回复中追加标注：「词典中未找到 "xxx"，以下结果未经词典校译」
- 全局无结果时提示用户手动指定知识源
- **依赖**：任务 4 完成
- **影响文件**：`app.py`（检索流程分支逻辑）

### 6. 大规模文档导入
- 本体代码：DST 本体 scripts/ 目录下 ~4000 个 .lua 文件
- 词典数据：prefablist.lua + tuning.lua + chinese_s.po
- 本地文档：教程/犯错经验/功能摘抄/设计决策 ~30 个 .md 文件
- 每种文件类型可能需要不同的切分策略（lua 函数级、md 段落级、词典条目级）
- **依赖**：任务 2+3 完成
- **影响文件**：无代码改动，批量入库操作

---

## 𐄂 再下一轮——查询增强（各任务相互独立）

### Step-Back Prompting 回退触发
- 初检结果文档数 < 阈值时，触发生成回退问题，用更抽象的问题重新检索

### HyDE 低召回补偿
- 第一次检索文档数 < 阈值时，让 LLM 生成假设答案，用假设答案的向量重检

### 检索结果重排序
- 多路检索结果合并后，用 LLM 对文档片段做相关性打分，取 top-K 喂入生成阶段

---

## 𐄂 远期——Plan-and-Execute 多跳问题

### Query Decomposition
- 引入 Planner 角色拆解复杂问题为子问题链，每个子问题分派到对应知识源

### 跨知识源交叉验证
- 同一概念在本体 vs Mod vs 文档中的差异比对，自动标注来源差异

---

## 维护类（已完成）

- `.env` 编码问题（UTF-8 vs UTF-16）— 已修复
- HuggingFace 国内网络问题（hf-mirror 镜像）— 已修复
- Streamlit 文件监视器 + transformers 兼容性（torchvision 缺失）— 已修复
- RecursiveCharacterTextSplitter 迁至 langchain-classic 包 — 已修复
