# TODO.md — agent_RAG_1_ly 待办清单

## ✅ PoC 阶段——已完成

### 0a. 参考 Mod 入库 ✅
- 4 个 Mod 全部入库：棱镜 11,777 + 小穹 5,403 + 深埋之下 8,729 + 能力勋章 9,130 = 35,039 片段
- 通过 `批量导入mod代码.py` 一键导入
- GPU Embedding（RTX 4060, PyTorch CUDA 12.4）
- 踩坑：ChromaDB 中文路径 → 持久化目录迁至 `~/.chromadb_rag/v1`

### 0b. 聊天端 + 管理面板跑通 ✅
- Chainlit（:8000）— Agent 工具调用 → 检索 → 回答流程正常
- Streamlit（:8501）— 配置修改、文档入库可用
- 踩坑：LangChain 1.0 `agent.invoke` 输入格式、Agent 死循环、GBK 编码等 9 项已记录到 `踩坑记录/`

### 0c. PoC 实测发现
- **检索质量是当前瓶颈**：`all-MiniLM-L6-v2` 对中英混排 Lua 代码语义不准，检索结果常不相关
- **Agent 容易反复搜索**：已加 `recursion_limit=10` + system prompt 约束（最多 3 次），属软控制
- **单库够用但不够好**：四分库 + 词典扩展是提升精度的关键路径
- **影响**：检索质量问题不解决，后续增强（Step-Back/HyDE/多跳）效果会打折扣

---

## 𐄂 下一轮——四分库架构改造

### 1. 升级 Embedding 模型（优先）
- 候选：`bge-large-zh-v1.5`（中文能力强）、`multilingual-e5-large`（多语言）
- 需评估：GPU 显存占用（RTX 4060 8GB）、推理速度、与 ChromaDB 兼容性
- **依赖**：无
- **影响文件**：`config.json`、所有调用 embedding 的脚本

### 2. config.json 结构调整
- `knowledge_base` 从单对象改为四个独立知识源配置
- 每个知识源：独立 collection 名、持久化路径、分块参数
- `tools` 拆为四个：`glossary_lookup` / `search_game_scripts` / `search_reference_mods` / `search_local_docs`
- **依赖**：无（可与 1 并行）
- **影响文件**：`config.json`、`app.py`、`管理面板.py`、`批量导入mod代码.py`

### 3. 管理面板适配四库
- 文档上传增加「目标知识源」下拉框
- 已索引文档按知识源分组显示
- **依赖**：任务 2
- **影响文件**：`管理面板.py`

### 4. glossary-lookup 工具实现
- 加载 chinese_s.po → 中文名→英文 ID 映射
- 加载 prefablist.lua → 解析所有有效 Prefab ID
- 加载 tuning.lua → 解析参数名→值映射
- **依赖**：任务 2
- **影响文件**：`app.py`（新增 tool + 词表加载）

### 5. Query Expansion 管道
- system prompt 注入两阶段检索规则：先 glossary-lookup → 拼 ID 重写 query → 并行检索三个知识源
- **依赖**：任务 4
- **影响文件**：`app.py`

### 6. 词典缺失降级策略
- glossary 返回空 → 自动并行全源 + 标注「词典未命中」
- 全局无果 → 提示用户手动指定知识源
- **依赖**：任务 5
- **影响文件**：`app.py`

### 7. 大规模文档导入
- 本体代码：DST scripts/ ~4000 .lua 文件
- 词典数据：prefablist.lua + tuning.lua + chinese_s.po
- 本地文档：教程/犯错经验/功能摘抄/设计决策 ~30 个 .md
- **依赖**：任务 3+4
- **影响文件**：仅入库操作

---

## 𐄂 再下一轮——查询增强

- Step-Back Prompting：初检结果不足时，生成抽象回退问题重检
- HyDE：低召回时 LLM 生成假设答案，用假设答案向量检索
- 重排序：多路结果合并后用 LLM 打分，取 top-K

---

## 𐄂 远期——多跳与交叉验证

- Query Decomposition：Planner 拆解复杂问题为子问题链
- 跨源交叉验证：同一概念在本体 vs Mod vs 文档中的差异比对

---

## 维护类

- 踩坑记录：[`踩坑记录/`](踩坑记录/) — 9 项，已按「已避免/使用方式依赖/仍可能触发」分类
- `.env` 编码 / HuggingFace 镜像 / Streamlit 文件监视器 / `RecursiveCharacterTextSplitter` 路径 — 已修复
- ChromaDB 持久化目录已迁至 `~/.chromadb_rag/v1`（避中文路径，`config.json` 中配置）
