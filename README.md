# agent_RAG_1_ly

基于 LangChain 1.0 + DeepSeek 的 RAG（检索增强生成）Agent，面向饥荒联机版（DST）Mod 开发知识问答。

## 项目状态

```
🟢 已实现：单库跑通，4 个参考 Mod 已入库（35,039 片段），GPU Embedding
🟢 PoC 完成：聊天端 + 管理面板可用
🟢 Phase 1 完成：流式输出、工具调用可视化、思考路径透传
🟢 Phase 2 完成：LangGraph 确定性图编排（替代 LangChain create_agent）
🟢 Phase 3 首项完成：Embedding 模型升级（all-MiniLM-L6-v2 → bge-m3 1024d）
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

## 差异化设计

相较于经典 Agent RAG 项目（Dify / Danswer-Onyx / R2R），本项目的差异化设计分为创新（领域特有）与改进（业界成熟选型）两类。详见 [创新点清单_ly.md](创新点清单_ly.md)。

### 领域创新

| 条目 | 一句话 |
|------|--------|
| 词典术语解析层 | 用户中文俗称 → 英文代码标识符，跨越中英 + 俗称双重语言鸿沟 |
| 四分库按来源独立建库 | 本体/Mod/文档/词典四类来源性质差异大，各自独立检索策略 |
| 两阈值三路径降级 + 透明告知 | 每次降级明确告知用户，而非悄悄兜底 |
| 🆕 复审问题 | 词典重组后插入用户校验断点——直接用/微调/重新描述 |

### 交互创新

| 条目 | 一句话 |
|------|--------|
| 三色折叠过程可视化 | 检索🔍 / 评分📊 / 重写✏️ 在聊天 UI 中可折叠展示 |
| 检索来源标签 + 跨源对比 | 每条结果标注 Mod 名和文件路径，可对比不同实现 |

### 工程改进

| 条目 | 一句话 |
|------|--------|
| LangGraph 确定性图编排 | 图的边 = 检索次数硬约束 |
| bge-m3 多语言 Embedding | 1024d 多语言，根治中文语义失明 |
| 评分门控 + 查询重写 | LLM 判断相关性，不相关自动重写再检索 |

## 核心组件

| 组件 | 说明 | 选型 |
|------|------|------|
| 聊天界面 | 浏览器中与知识库对话 | Chainlit（:8000） |
| 管理面板 | 可视化配置、上传文档 | Streamlit（:8501） |
| 对话模型 | 理解问题 + 生成回答 | DeepSeek (deepseek-chat) |
| Embedding | 文本→向量 | HuggingFace 本地模型 (BAAI/bge-m3, 1024d, 多语言) |
| 向量库 | 文档片段存储与检索 | ChromaDB（持久化） |
| Agent 框架 | 确定性图编排（节点+边替代 LLM 自主决策） | LangGraph StateGraph |
| 检索链路 | 初次检索 → 评分门控 → 直接回答/重写重检索 | 图结构硬约束（最多 2 次检索） |

## LangGraph 图结构（Phase 2）

从 LangChain `create_agent`（LLM 自主决定何时检索）迁移到 LangGraph `StateGraph`（开发者定义节点+边的确定性编排）。

### 图

```
                    ┌──────────────┐
                    │   START      │
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │ retrieve     │  ← 用户问题 → ChromaDB k=3 检索
                    │ _initial     │     (bge-m3 加查询前缀)
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │ grade        │  ← LLM structured_output(yes/no)
                    │ _documents   │     判断文档是否与问题相关
                    └──────┬───────┘
                           │
              ┌────────────┴────────────┐
              │ yes                     │ no
              ▼                         ▼
      ┌──────────────┐          ┌──────────────┐
      │ generate     │          │ rewrite      │  ← LLM 换个角度重述问题
      │ _answer      │          │ _question    │
      └──────┬───────┘          └──────┬───────┘
             │                         │
             ▼                  ┌──────▼───────┐
         ┌──────┐               │ retrieve     │  ← 用重写后的查询再搜
         │ END  │               │ _expanded    │
         └──────┘               └──────┬───────┘
                                       │
                                ┌──────▼───────┐
                                │ generate     │  ← 同一节点，两个入口
                                │ _answer      │
                                └──────┬───────┘
                                       │
                                       ▼
                                   ┌──────┐
                                   │ END  │
                                   └──────┘
```

- **最多 2 次检索**：`retrieve_initial` + `retrieve_expanded` 各出现一次，图的边 = 硬限制，物理上不可能有第三次搜索
- **条件路由**：`grade_documents` 写入 `state.route` → `"generate_answer"` 或 `"rewrite_question"`
- **汇聚点**：`generate_answer` 是两个分支的共同出口

### 6 个 State 字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `question` | `str` | 用户原始问题（不变） |
| `query` | `str` | 当前检索查询（可能被 `rewrite_question` 更新） |
| `context` | `str` | 格式化后的检索结果（给 LLM 阅读） |
| `docs` | `List[dict]` | 检索到的原始文档列表 |
| `route` | `Optional[str]` | 条件边路由标记：`"generate_answer"` / `"rewrite_question"` |
| `response` | `str` | 最终回答文本 |

### 可视化

三种节点执行过程在聊天 UI 中以 `<details>` 折叠卡片展示：

| 图标 | 卡片 | 内容 |
|------|------|------|
| 🔍 | 检索（search_knowledge_base） | 检索词 + 每条结果的来源/代码片段 |
| 📊 | 相关性评估 | LLM 的 yes/no 判断 + 路由决策 |
| ✏️ | 查询重写 | 原问题 → 重写后的查询（含流式 token 文字段） |

### 代码位置

```
src/agent/
├── __init__.py
├── factory.py         → create_agent() 委托给 graph；run_agent_stream() 事件映射
├── tools.py           → (保留，未来 Phase 在图中集成工具调用)
├── prompt.py          → system prompt 拼装（generate_answer 节点使用）
└── graph/             → 🆕 LangGraph 子包
    ├── __init__.py
    ├── nodes.py       → RAGState + 5 个节点函数 + Pydantic 评分模型
    └── pipeline.py    → StateGraph 构建 + 条件边 + 编译
```

## 快速开始（Docker，推荐）

```bash
cd agent_RAG_1_ly

# 1. 确保 .env 已配置 API Key
#    DEEPSEEK_API_KEY=sk-你的密钥

# 2. 启动所有服务（后台运行）
docker compose up -d

# 3. 初次部署需导入数据（一次性操作）
docker exec -it rag-admin python 批量导入mod代码.py --source /mod_source

# → 聊天端 http://localhost:8000
# → 管理面板 http://localhost:8501
```

详细操作参考：[项目操作速查_ly.md](项目操作速查_ly.md)。

---

## 快速开始（裸 Python，备选）

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
├── app.py                  # 聊天端（Chainlit）
├── 管理面板.py              # 管理端（Streamlit）
├── config.json             # 共享配置
├── .env                    # API Key（不提交）
├── .env.example
├── requirements.txt
├── 启动rag助手.py           # 双击启动聊天端
├── 启动管理面板.py          # 双击启动管理面板
├── 批量导入mod代码.py        # 批量导入 .lua 文件到向量库
├── Dockerfile              # Docker 镜像定义
├── docker-compose.yml      # Docker 服务编排
├── .dockerignore
├── .gitignore
├── README.md               # 本文件
├── CONTEXT.md              # 领域术语与设计决策
├── TODO.md                 # 待办清单（含各阶段路线图）
├── src架构设计_ly.md        # 源代码架构设计与演进路线
├── 项目操作速查_ly.md     # 项目日常操作命令大全
├── 参考项目对比分析_ly.md    # 参考项目 SuperMew 对比分析
├── 踩坑记录/                # 搭建过程中踩过的技术坑（11 个，独立分项）
├── chroma_db/              # 向量库（本地宿主机模式；Docker 用 volume）
├── src/                    # 共享源码
│   ├── config.py           # 配置加载
│   ├── llm.py              # LLM 模型初始化 (ChatOpenAI + streaming)
│   ├── embedding.py        # Embedding 模型初始化 (bge-m3 + 查询前缀)
│   ├── knowledge/          # 知识库子包
│   │   ├── __init__.py
│   │   └── store.py        # ChromaDB 向量库创建
│   └── agent/              # Agent 子包
│       ├── __init__.py
│       ├── factory.py      # create_agent() 委托给 graph；run_agent_stream() 事件映射
│       ├── prompt.py       # System prompt 拼装
│       └── graph/          # LangGraph 图编排（Phase 2）
│           ├── __init__.py
│           ├── nodes.py    # RAGState + 5 节点 + Pydantic 评分模型
│           └── pipeline.py # StateGraph 构建 + 条件边 + 编译
```

## 已知限制

- **本体代码未入库**：DST 官方 ~4000 个 .lua 文件尚未导入，当前检索只能覆盖 4 个参考 Mod 的实现，游戏引擎核心代码（components/stategraphs/brains）检索不到
- **词典数据未入库**：prefablist.lua / tuning.lua / chinese_s.po 均未导入，中文俗称→英文 ID 的术语映射链路无数据支撑
- **单库架构**：当前使用单一向量库，尚未按四分法拆分为四个独立知识源
- **词典工具未实现**：glossary-lookup 工具尚未注册
- **降级策略未实现**：词典缺失时的自动并行全源检索尚未编码
- **重写策略为单策略**：当前 `rewrite_question` 只有一种重写方式，参考项目的三策略路由（step_back/hyde/complex）留到后续 Phase 实现

## 相关文档

- [CONTEXT.md](CONTEXT.md) — 领域术语、检索策略、技术选型
- [TODO.md](TODO.md) — 待办清单与各阶段路线图
- [创新点清单_ly.md](创新点清单_ly.md) — 项目创新点与改进点全览
- [项目优化记录_ly.md](项目优化记录_ly.md) — 已完成的工程优化与实测发现
- [项目操作速查_ly.md](项目操作速查_ly.md) — 项目日常操作命令大全
- [src架构设计_ly.md](src架构设计_ly.md) — src/ 源代码架构设计与演进路线
- [参考项目对比分析_ly.md](参考项目对比分析_ly.md) — 参考项目 [SuperMew](https://github.com/icey1287/SuperMew) 对比分析
- [踩坑记录/](踩坑记录/) — 11 个技术踩坑文档，含症状/根因/修复/影响范围
