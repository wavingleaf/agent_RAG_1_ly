# agent_RAG_1_ly

基于 LangChain 1.0 + DeepSeek 的 RAG（检索增强生成）Agent，面向饥荒联机版（DST）Mod 开发知识问答。

## 项目状态

```
🟢 已实现：单库跑通，4 个参考 Mod 已入库（35,039 片段），GPU Embedding
🟢 PoC 完成：聊天端 + 管理面板可用，Agent 工具调用正常工作
🟡 进行中：评估检索质量，调整分块策略/Embedding 模型
🟡 已设计未实现：四分库架构、词典速查、Query Expansion 管道
⚪ 规划中：Step-Back Prompting / HyDE / Query Decomposition
```

详见 [TODO.md](TODO.md) 和 [CONTEXT.md](CONTEXT.md)。

## 领域

覆盖 DST Mod 开发中的全部必要知识，最终包含四类知识源：

| 知识源 | 内容 | 状态 |
|--------|------|------|
| 本体代码（game-scripts） | DST 官方 scripts/*.lua，~4000 文件 | ⚪ 待入库 |
| 优秀 Mod（reference-mods） | 棱镜/小穹/深埋之下/能力勋章 共 819 文件 | 🟢 已入库 35,039 片段 |
| 本地文档（local-docs） | 自编教程、犯错经验、功能摘抄、设计决策 | ⚪ 待入库 |
| 词典速查（glossary-lookup） | prefablist.lua / tuning.lua / chinese_s.po | ⚪ 待入库 |

检索策略为「两阶段先词典后知识库」：先通过词典将用户问题中的中文名/俗称映射为英文 ID，再用精确标识符重编问题后检索三个知识源。详见 [CONTEXT.md](CONTEXT.md)。

## 改进点

相较于经典 Agent RAG 项目（Dify / Danswer-Onyx / R2R），本项目的差异化设计：

| # | 改进点 | 关键词 |
|---|--------|--------|
| 1 | 检索前插入**词典术语解析层**，将用户的中文俗称映射为英文代码标识符，跨越"用户语言≠文档语言"的领域鸿沟 | `术语解析` `中英映射` |
| 2 | 知识源按**认知类型四分**（本体/范例/文档/词典），而非按数据来源切分，每个源有独立检索语义 | `认知分类` `独立 collection` |
| 3 | 领域最优检索路径固化到 system prompt——**先词典后知识源**，减少 Agent 在无关分支上的试错 | `检索顺序` `路径固化` |
| 4 | 词典命中后驱动 **Query Expansion**——用精确标识符重写查询再检索，提升代码库命中率 | `查询重写` `标识符拼接` |
| 5 | **两阈值三路径降级**：词典命中→精确检索 / 词典缺失→自动并行全源 / 知识库全空→手动指定，每级降级告知用户 | `降级透明度` `兜底策略` |
| 6 | 四种查询增强技术（Step-Back / HyDE / Query Decomposition / Expansion）各有**领域触发条件**，非全开全关 | `条件触发` `token 节省` |
| 7 | 检索结果全程携带**来源标签**（game-scripts / reference-mods / local-docs），可跨源对比"本体实现 A，棱镜实现 B" | `来源溯源` `跨源对比` |

## 核心组件

| 组件 | 说明 | 选型 |
|------|------|------|
| 聊天界面 | 浏览器中与知识库对话 | Chainlit（:8000） |
| 管理面板 | 可视化配置、上传文档 | Streamlit（:8501） |
| 对话模型 | 理解问题 + 生成回答 | DeepSeek (deepseek-chat) |
| Embedding | 文本→向量 | HuggingFace 本地模型 (all-MiniLM-L6-v2) |
| 向量库 | 文档片段存储与检索 | ChromaDB（持久化） |
| Agent 框架 | 思考→调工具→读结果→回答 循环 | LangChain 1.0 `create_agent` |

## 快速开始

```bash
# 1. 安装依赖（Python ≥ 3.10）
pip install -r requirements.txt

# 2. 设置 API Key
cp .env.example .env
# 编辑 .env：DEEPSEEK_API_KEY=sk-你的密钥

# 3. 启动管理面板
python 启动管理面板.py
# → http://localhost:8501

# 4. 另开终端，启动聊天端
python 启动rag助手.py
# → http://localhost:8000
```

## 两个界面

| | 聊天端 | 管理面板 |
|------|---------|----------|
| 干什么 | 与知识库对话 | 改配置、上传文档 |
| 端口 | `:8000` | `:8501` |
| 怎么启动 | `python 启动rag助手.py` | `python 启动管理面板.py` |

## 项目结构

```
agent_RAG_1_ly/
├── app.py              # 聊天端（Chainlit）
├── 管理面板.py          # 管理端（Streamlit）
├── config.json         # 共享配置
├── .env                # API Key（不提交）
├── .env.example
├── requirements.txt
├── 启动rag助手.py       # 双击启动聊天端
├── 启动管理面板.py      # 双击启动管理面板
├── 批量导入mod代码.py    # 批量导入 .lua 文件到向量库
├── .gitignore
├── README.md           # 本文件
├── CONTEXT.md          # 领域术语与设计决策
├── TODO.md             # 待办清单
├── 踩坑记录/            # 搭建过程中踩过的技术坑（9 个，独立分项）
└── chroma_db/          # 向量库（本地索引，不提交 — 实际持久化在 ~/.chromadb_rag/v1）
```

## 已知限制

- **检索质量**：`all-MiniLM-L6-v2` 对中英文混合 Lua 代码的语义理解有限，检索结果有时不够精准
- **单库架构**：当前代码使用单一向量库，尚未按四分法拆分为四个独立知识源
- **词典工具未实现**：glossary-lookup 工具尚未注册，Agent 目前仅有 `search_knowledge_base` 一个工具
- **降级策略未实现**：词典缺失时的"软化 B"策略尚未编码

## 相关文档

- [CONTEXT.md](CONTEXT.md) — 领域术语、检索策略、技术选型
- [TODO.md](TODO.md) — 待办清单与优先级
- [踩坑记录/](踩坑记录/) — 9 个技术踩坑文档，含症状/根因/修复/影响范围
