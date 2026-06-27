# 参考项目「SuperMew」对比分析

> 分析对象：
> - **参考项目**：「agent RAG 参考」(SuperMew) — 开源通用 RAG Agent 项目
> - **本项目**：「agent_RAG_1_ly」— 面向 DST Mod 开发的领域专用 RAG Agent
>
> 分析日期：2026-06-24

---

## 1. 项目概览对比

| 维度 | 参考项目 | 本项目 | 差距判断 |
|------|---------|--------|----------|
| 项目定位 | 通用 RAG Agent（无领域限定） | DST Mod 开发专用 RAG Agent | 本项目的领域性更强 |
| 后端框架 | FastAPI + 分层包架构 | Chainlit（框架托管） | 参考项目更灵活可控 |
| 前端方式 | Vue 3 + TypeScript 自研 SPA | Chainlit 内置 UI | 参考项目可定制度远高 |
| 向量库 | Milvus 2.5+ (分布式) | ChromaDB (本地单机) | 参考项目更生产级 |
| 数据库 | PostgreSQL + Redis | 无（纯文件配置） | 参考项目有完整持久化 |
| 部署方式 | Docker Compose 全容器化 | Python 脚本直接运行 | 参考项目标准化程度高 |
| 文档格式 | PDF / Word / Excel | .lua / .txt / .md | 场景不同，各有侧重 |
| 代码规模 | ~60+ 源文件（前后端分离） | ~5 个核心脚本 | 参考项目工程量大得多 |
| Agent 框架 | LangGraph + LangChain | LangChain 1.0 `create_agent` | 参考项目用图编排更复杂 |
| 多用户支持 | JWT + RBAC (admin/user) | 无 | 参考项目具备多用户能力 |
| 成熟度 | 生产可用（含降级/容错） | PoC 完成，质量待提升 | 参考项目打磨时间更长 |

---

## 2. 参考项目独有内容（本项目完全缺失的模块）

### 2.1 后端分层架构

```
参考项目 backend/ 结构：
├── app.py                  # FastAPI 入口 + CORS + 静态资源托管
├── env.py                  # 环境变量统一加载
├── api/                    # HTTP 层
│   ├── router.py           # 路由聚合
│   ├── resources.py        # Milvus/上传目录等共享资源
│   └── routes/             # auth.py / chat.py / sessions.py / documents.py
├── chat/                   # 对话域
│   ├── service.py          # 流式/非流式聊天入口
│   ├── runtime.py          # LangChain Agent 实例
│   ├── storage.py          # 会话 PostgreSQL + Redis 存储
│   ├── streaming.py        # RAG 步骤 SSE 跨线程推送
│   └── rag_context.py      # 单轮 RAG trace 暂存
├── rag/                    # 检索增强核心
│   ├── pipeline.py         # LangGraph RAG 工作流（~680行）
│   └── utils.py            # 混合检索/Rerank/Auto-merging
├── indexing/               # 文档向量化入库
│   ├── embedding.py        # 稠密 + BM25 稀疏向量
│   ├── document_loader.py  # PDF/Word/Excel 分块
│   ├── milvus_client.py    # Milvus 客户端封装
│   ├── milvus_writer.py    # 向量写入
│   ├── parent_chunk_store.py # 父级分块 DocStore
│   └── html_processor.py   # HTML 清洗
├── infra/                  # 基础设施
│   ├── database.py         # SQLAlchemy 初始化
│   ├── cache.py            # Redis 缓存策略
│   └── auth.py             # JWT 鉴权中间件
├── db/models.py            # ORM 数据模型（User/ChatSession/ChatMessage/ParentChunk）
├── schemas/                # Pydantic 请求/响应模型
├── tools/                  # Agent 工具（knowledge/weather）
└── jobs/upload_jobs.py     # 异步上传/删除任务进度跟踪
```

**本项目缺失**：完全不具备这种分层结构。本项目只有 `app.py`（约 208 行）+ `管理面板.py`（约 368 行）+ `批量导入mod代码.py`（约 207 行），所有逻辑混在一起。

**参考价值**：如果本项目未来需要做多用户、持久化会话、生产部署，这个分层架构是直接可参考的模板。

---

### 2.2 自研前端（Vue 3 + TypeScript + Pinia）

参考项目的前端是一个**完整的现代 SPA 工程**，而非框架生成的 UI。

| 组件/模块 | 功能 | 本项目对应 |
|-----------|------|-----------|
| `stores/chat.ts` (244行) | 消息管理、SSE 流解析、RAG 步骤状态机 | Chainlit 内置 |
| `stores/auth.ts` | JWT 登录/注册状态管理 | 无 |
| `stores/sessions.ts` | 多会话列表/切换/删除 | Chainlit 内置 |
| `stores/documents.ts` | 文档上传进度轮询 | 管理面板（Streamlit） |
| `ChatArea.vue` | 聊天消息列表 + 自动滚动 | Chainlit 内置 |
| `ChatInput.vue` | 输入框 + 终止按钮 | Chainlit 内置 |
| `MessageItem.vue` | 单条消息渲染（引用/思考/内容） | Chainlit 内置 |
| `ThinkingTrace.vue` | 动态渲染 RAG 思考步骤 | **无**（本项目无法看到思考过程） |
| `RetrievalTraceDetails.vue` | 子问题分组 + 召回详情 | **无** |
| `References.vue` | 折叠卡片展示来源/RRF名次/Rerank分 | **无**（本项目仅在文本中列出来源） |
| `UploadSection.vue` | 上传多阶段状态机进度 | Streamlit 原生组件 |
| `HistorySidebar.vue` | 历史会话侧边栏 | Chainlit 内置 |
| `utils/api.ts` | ReadableStream + SSE 逐块解析 | Chainlit 内置 |

**关键差距**：参考项目的前端有**两个本项目完全不存在的功能**：
1. **RAG 思考过程实时可视化** — 用户能看到 Agent 正在"检索 → 评分 → 重写 → 二次检索"的每一步
2. **参考文献的可交互展示** — 来源卡片可折叠、显示 RRF 名次/Rerank 分数/层级/页码，支持点击跳转

---

### 2.3 混合检索体系（Hybrid Search）

参考项目的检索是本项目最值得学习的部分，它实现了完整的**混合检索 + 精排 + 自动合并**流水线：

```
本项目的检索路径：
  用户问题 → ChromaDB 稠密向量检索(top_k=3) → 返回文本

参考项目的检索路径：
  用户问题 → Milvus Hybrid Search(Dense + Sparse/BM25)
           → RRF 融合排名 (k=60)
           → Auto-merging (L3→L2→L1 父块合并)
           → Jina Rerank 精排
           → 截断 top_k 返回
```

| 检索能力 | 参考项目 | 本项目 | 差距 |
|----------|---------|--------|------|
| 稠密向量检索 | ✅ HuggingFace bge-m3 (1024维) | ✅ HuggingFace all-MiniLM-L6-v2 (384维) | 参考项目的模型更强 |
| 稀疏向量检索(BM25) | ✅ Milvus 原生 BM25 (服务端自动分词) | ❌ 无 | 关键词匹配完全缺失 |
| RRF 融合 | ✅ 倒数排名融合 (k=60) | ❌ 无 | 无法融合多路召回 |
| Rerank 精排 | ✅ Jina Rerank API 级重排序 | ❌ 无 | 检索精度上限低 |
| 降级策略 | ✅ Hybrid 失败→纯 Dense | ❌ 无 | 无容错能力 |
| 相关性评分门控 | ✅ 结构化输出 yes/no | ❌ 无 | 无法判断检索质量 |
| 查询重写 | ✅ Step-Back / HyDE / Complex 三策略路由 | ❌ 无（设计阶段） | 低召回时无补救手段 |
| Auto-merging | ✅ L3→L2→L1 父块自动合并 | ❌ 单层分块 | 无法保留上下文完整性 |
| 三级分块 | ✅ L1(大)/L2(中)/L3(小) 滑动窗口 | ❌ 单一 chunk_size | 无法平衡粒度与上下文 |

**核心差异**：参考项目的检索是一个**有自检、可纠错、多策略自适应**的系统，本项目的检索是**一次性的纯向量最近邻查询**。

---

### 2.4 LangGraph RAG 工作流（~680 行 StateGraph）

参考项目的 `backend/rag/pipeline.py` 是整个系统的核心，实现了完整的状态图：

```
                 ┌──────────────────┐
                 │ classify_complexity│ ← LLM 判断简单/复杂
                 └──────┬───────────┘
                        │
            ┌───────────┴───────────┐
            ▼                       ▼
    ┌──────────────┐       ┌──────────────────┐
    │retrieve_initial│      │ decompose_question│ ← LLM 拆解 2-4 子问题
    └──────┬───────┘       └────────┬─────────┘
           │                        │
    ┌──────┴──────┐         ┌──────┴──────┐
    ▼             ▼         ▼             ▼
┌─────────┐ ┌──────────┐ ┌─────────┐  ┌─────────┐
│grade    │ │rewrite   │ │sub-agent│  │sub-agent│  ...(并行 Send API)
│documents│ │question  │ │   1     │  │   2     │
└────┬────┘ └────┬─────┘ └────┬────┘  └────┬────┘
     │           │             │            │
     ▼           ▼             └─────┬──────┘
  ┌──────┐ ┌──────────┐             ▼
  │ END  │ │retrieve   │     ┌────────────┐
  └──────┘ │expanded   │     │ synthesis  │ ← 去重合并
           └────┬───────┘     └─────┬──────┘
                │                   │
                ▼                   ▼
             ┌──────┐           ┌──────┐
             │ END  │           │ END  │
             └──────┘           └──────┘
```

**节点清单**：
- `classify_complexity` — LLM 分类器判断问题简单/复杂
- `decompose_question` — 复杂问题拆解为 2-4 个独立子问题
- `rag_sub_agent` — 并行执行的子 Agent（每个走完整 RAG 流程）
- `synthesis` — 多子问题结果去重合并
- `retrieve_initial` — 初次混合检索 + Auto-merging + Rerank
- `grade_documents` — 结构化输出评分（yes/no）
- `rewrite_question` — 三策略路由（step_back / hyde / complex）
- `retrieve_expanded` — 二次扩展检索

**本项目完全缺失**：本项目的 Agent 只有一个 `search_knowledge_base` 工具，调用一次就出结果。

---

### 2.5 用户与权限体系

| 能力 | 参考项目 | 本项目 |
|------|---------|--------|
| 用户注册 | `POST /auth/register`（含 admin 邀请码） | ❌ |
| 用户登录 | `POST /auth/login` → JWT Bearer Token | ❌ |
| 密码安全 | PBKDF2-SHA256（兼容历史 bcrypt） | ❌ |
| RBAC 权限 | admin（可管理文档）/ user（仅聊天） | ❌ |
| 会话隔离 | 按 user_id 隔离全部数据 | ❌ |
| 中间件鉴权 | FastAPI Depends 注入 | ❌ |

本项目假设单用户使用，无任何鉴权。

---

### 2.6 会话持久化与记忆管理

| 能力 | 参考项目 | 本项目 |
|------|---------|--------|
| 消息持久化 | PostgreSQL `chat_messages` 表 | Chainlit 默认（本地 JSON） |
| 会话元数据 | `chat_sessions` 表 + Redis 缓存 | 无 |
| 会话摘要记忆 | `persistent_note`：自动压缩旧消息为笔记 | ❌ |
| 智能标题生成 | 首条消息 → LLM 生成 10 字标题 | ❌ |
| Redis 三级缓存 | 会话消息 / 会话列表 / 父文档 | ❌ |
| 缓存失效策略 | 写入/删除后主动失效 | ❌ |
| 会话安全性 | `DELETE /sessions/{id}` 仅删自己的 | 无 |

本项目目前完全依赖 Chainlit 的默认行为（本地会话存储），无额外控制。

---

### 2.7 流式输出架构（Streaming SSE）

参考项目的流式输出经历了**深度打磨**，解决了几个关键问题：

**问题一：同步工具阻塞异步事件循环**

- **痛点**：LangChain 将同步工具放到 `ThreadPoolExecutor` 中运行，子线程无法访问主线程的 `asyncio.Queue`
- **方案**：Global Loop Capture + `call_soon_threadsafe` 跨线程注入（见 `streaming.py`）

**问题二：思考过程"静默"**

- **痛点**：Agent 执行工具时，前端只能显示静态的"思考中…"动画
- **方案**：RAG pipeline 在每个关键节点调用 `emit_rag_step()`，通过统一输出队列即时推送检索阶段

**问题三：流生成与步骤推送共用一个队列**

- **方案**：`_RagStepProxy` 代理对象将 step 包装为 `{"type": "rag_step"}` 放入统一队列，Agent worker 在后台任务中运行 `agent.astream()` 逐 token 产出 `{"type": "content"}`。主生成器只负责从队列取事件 → yield SSE。

**问题四：用户主动终止回答**

- **前端**：`AbortController.abort()` 取消 fetch
- **后端**：`GeneratorExit` 捕获 → `agent_task.cancel()` → `httpx` 关闭 TCP 连接 → 服务端停止推理。**不是等框架自动取消，而是显式调用 `.cancel()` 确保确定性的资源回收**

**SSE 协议格式**：
```
data: {"type":"rag_step","step":{"icon":"🔍","label":"正在检索知识库..."}}

data: {"type":"content","content":"根据知识库"}

data: {"type":"content","content":"中的信息"}

data: {"type":"trace","rag_trace":{...}}

data: [DONE]
```

本项目使用 Chainlit 默认的流式机制，无法在工具执行期间推送中间状态。

---

### 2.8 文档处理链路

| 能力 | 参考项目 | 本项目 |
|------|---------|--------|
| 支持格式 | PDF / Word / Excel | .txt / .md / .lua |
| 文档解析 | `langchain_community.loaders` | `utf-8.decode()` |
| HTML 清洗 | `html_processor.py`（NFC 归一化 + PUA 过滤） | 无 |
| 分块策略 | 三级滑动窗口（L1>L2>L3） | 单级 `RecursiveCharacterTextSplitter` |
| 层级元数据 | `chunk_id/parent_chunk_id/root_chunk_id/chunk_level` | 仅 `source/chunk/mod_name` |
| 父块存储 | L1/L2 写入 PostgreSQL | 无 |
| 叶子向量化 | 仅 L3 写入 Milvus | 所有 chunk 写入 ChromaDB |
| 重复上传处理 | 先清除旧向量+PG+Redis，再入库 | 无检测（ChromaDB 会重复） |
| 删除事务性 | Milvus+PG+Redis 三端协同删除 | 只能删整个持久化目录 |
| 上传进度 | 异步任务 + 前端轮询 | 同步等待（Streamlit 内阻塞） |
| 文件编码处理 | 统一 UTF-8（上游清洗） | 自动尝试 UTF-8/GBK |

---

### 2.9 基础设施与部署

参考项目的 `docker-compose.yml` 管理 **6 个容器**：
- `postgres:15` — 业务数据库
- `redis:7-alpine` — 缓存层
- `etcd:v3.5.18` — Milvus 元数据协调
- `minio` — Milvus 对象存储
- `milvus-standalone:v2.5.14` — 向量数据库
- `attu:v2.5.11` — Milvus 管理 UI

本项目无容器化，依赖纯 Python 生态。

---

### 2.10 前端"思考状态机"

参考项目的前端维护了一个复杂的响应式状态机：

```
Idle → Thinking(Initial) → Thinking(Active RAG) → Streaming → Complete
                                    ↑                    │
                                    │                    │
                              [收到 rag_step]      [收到 content token]
                              更新 thinkingLabel     isThinking=false
                              追加 ragSteps[]        同一气泡切换
                              UI 显示具体步骤        Markdown 流式追加
```

**本项目**：Chainlit 提供基本的"思考中"动画 + 回答渲染。无法看到 Agent 内部的检索→评分→重写过程。

---

## 3. 两项目共有部分的实现对比

### 3.1 聊天界面 (RAG UI)

| 维度 | 参考项目 | 本项目 |
|------|---------|--------|
| UI 方案 | 自研 Vue 3 SPA | **Chainlit**（Python 框架托管） |
| 开发成本 | 高（需写 20+ 组件、状态管理、SSE 解析） | 低（`@cl.on_message` 装饰器即可） |
| 可定制性 | 完全可控（每个像素） | 受限于 Chainlit 组件模型 |
| 消息渲染 | 自研 Markdown（marked + highlight.js） | Chainlit 内置 |
| 思考动画 | 自研状态机（跳动圆点 + 动态文字） | Chainlit 默认步骤 |
| 参考文献展示 | 自研折叠卡片（RRF/Rerank/层级/页码） | 纯文本嵌入回答 |
| 终止按钮 | 红色按钮 + AbortController | Chainlit 内置停止 |
| 历史会话 | 自研侧边栏 | Chainlit 内置 |
| 流式效果 | ReadableStream + 手动 SSE 解析 | Chainlit 内置 |
| 调试能力 | 需要前端工具链（Vite dev server） | 直接用 Python 调试 |

**结论**：Chainlit 大幅降低了开发成本，但牺牲了"RAG 过程可视化"这个关键的用户体验维度。

---

### 3.2 Agent 框架

| 维度 | 参考项目 | 本项目 |
|------|---------|--------|
| 框架 | **LangGraph** StateGraph（图编排） | **LangChain 1.0** `create_agent`（工具调用循环） |
| Agent 复杂度 | 多节点有向图 + 条件路由 + 并行 Send API | 单一工具调用循环 |
| 工作流控制 | 显式图边/条件边，确定性路由 | Agent 自行决策何时调工具 |
| recursion_limit | 8 | 10 |
| 工具数量 | 2（search_knowledge_base + weather） | 1（search_knowledge_base） |
| 工具调用限制 | 硬限制：`search_knowledge_base` 每轮最多 1 次 | 软约束：system prompt "最多 3 次" |
| 流式模式 | `agent.astream(stream_mode="messages")` | `agent.invoke()`（非流式） |
| LLM Provider | 兼容 OpenAI API 格式（通过环境变量切换） | DeepSeek（硬编码在 config） |
| 温度 | 按场景分离（主模型 0 + 路由模型 0 + 评分模型 0） | 统一 0.0 |

**关键差异**：
- 参考项目用 **LangGraph 图编排**，RAG 流程在图中显式定义，不依赖 Agent 的"自主决策"
- 本项目用 **Agent 的 tool-calling 能力**，Agent 自己决定"现在要不要搜"
- 参考项目的工具调用是**确定性的**（由图的边控制），本项目的工具调用是**概率性的**（依赖 LLM 判断）

---

### 3.3 Embedding 与向量库

| 维度 | 参考项目 | 本项目 |
|------|---------|--------|
| Embedding 模型 | `BAAI/bge-m3` (1024维，多语言) | `all-MiniLM-L6-v2` (384维，英文为主) |
| 向量维度 | 1024（DENSE_EMBEDDING_DIM） | 384（HuggingFace 默认） |
| 运行设备 | 可配置（`EMBEDDING_DEVICE`） | 本地 GPU（RTX 4060） |
| 模型来源 | `langchain_huggingface` | `langchain_huggingface` |
| HF 镜像 | 通过 `HF_ENDPOINT` 环境变量 | 通过 `HF_ENDPOINT` 环境变量 |
| 向量库 | **Milvus**（HNSW 稠密 + INVERTED 稀疏双索引） | **ChromaDB**（HNSW 单索引） |
| 持久化 | 分布式（etcd + MinIO） | 本地文件（`~/.chromadb_rag/v1`） |
| 删除能力 | 按文件名精确删除（分页 query_all） | 只能删整个目录 |
| 文档计数 | 按文件名分页统计 | `_collection.count()` |
| 中文路径 | 无影响（容器内部） | **有坑**（已迁至 `~/.chromadb_rag/v1`） |

---

### 3.4 文档导入/入库

| 维度 | 参考项目 | 本项目 |
|------|---------|--------|
| 入口 | Web UI 上传 → FastAPI → 异步任务 | Streamlit 上传 / 命令行脚本 |
| 分块器 | `RecursiveCharacterTextSplitter`（三级） | `RecursiveCharacterTextSplitter`（单级） |
| 分隔符 | 按文件类型适配 | `["\n\n\n", "\n\n", "\n", "end\n", " ", ""]`（Lua 偏好） |
| 元数据 | `filename / page_number / file_type / file_path / chunk_id / parent_chunk_id / root_chunk_id / chunk_level` | `mod_name / source / chunk / knowledge_source` |
| 编码处理 | 上游统一处理 | UTF-8 → GBK 自动回退 |
| 去重策略 | 同名文件先删旧再导新 | 无（直接追加） |

---

### 3.5 配置管理

| 维度 | 参考项目 | 本项目 |
|------|---------|--------|
| 环境变量 | `.env`（15+ 变量） | `.env`（仅 API Key） |
| 应用配置 | 环境变量 + 代码默认值 | `config.json`（通过管理面板编辑） |
| 配置热更新 | 重启服务 | 重启服务 |
| 配置项数量 | ~25 个 | ~12 个 |
| 管理界面 | 无（直接改文件） | Streamlit 管理面板 |

**本项目在配置管理的 UX 上做得更好**：有专门的管理面板，可以可视化修改配置。参考项目全靠改 `.env` 文件。

---

### 3.6 踩坑记录

**本项目独有**：`踩坑记录/` 目录下有 9 个详细的技术踩坑文档，每篇包含症状/根因/修复/影响范围。

参考项目 README 的"更新日志"部分记录了版本迭代中的重要修复，但不是结构化的踩坑文档。

---

## 4. 参考项目对 TODO 的参考价值

以下按 `/agent_RAG_1_ly/TODO.md` 中的待办项，逐一标注参考项目中**已有的对应实现**：

### 4.1 下一轮——四分库架构改造

| TODO | 参考项目对应 | 可直接参考程度 |
|------|------------|--------------|
| 1. 升级 Embedding 模型 | 使用 `BAAI/bge-m3`（1024维），远强于 `all-MiniLM-L6-v2` | ⭐⭐⭐ 直接可用：bge-m3 对中英文混合更友好 |
| 2. config.json 四库拆分 | 无直接对应（参考项目无"知识源分类"概念） | ⭐ 本项目是领域创新，参考项目不涉及 |
| 3. 管理面板适配四库 | 无管理面板（全靠 `.env` 文件） | ⭐⭐ 管理面板的思路可保留，四库是领域特有 |
| 4. glossary-lookup 工具 | 无（通用项目不需要术语映射） | ⭐ 本项目领域创新 |
| 5. Query Expansion 管道 | `rewrite_question_node` 中的三策略路由 | ⭐⭐⭐ 核心参考：Step-Back / HyDE / Complex 路由设计的完整实现 |
| 6. 词典缺失降级 | Hybrid 失败→纯 Dense 降级；精排为空→强制 Step-Back | ⭐⭐⭐ 降级思维完全相同，只是触发条件不同 |
| 7. 大规模文档导入 | `批量导入mod代码.py` 的设计已经足够好 | ⭐ 本项目已有成熟方案 |

---

### 4.2 再下一轮——查询增强

| TODO | 参考项目对应 | 可直接参考程度 |
|------|------------|--------------|
| Step-Back Prompting | `step_back_expand()` 函数（在 `rag/utils.py` 中） | ⭐⭐⭐ **完整实现可直接参考**：生成退步问题 → 回退检索 |
| HyDE | `generate_hypothetical_document()` 函数 | ⭐⭐⭐ **完整实现可直接参考**：LLM 生成假设答案 → 用假答案向量检索 |
| 重排序(Rerank) | Jina Rerank API 接入 + `rerank_score` 前端展示 | ⭐⭐⭐ **完整实现可直接参考**：API 调用方式、分数字段、前端渲染 |

---

### 4.3 远期——多跳与交叉验证

| TODO | 参考项目对应 | 可直接参考程度 |
|------|------------|--------------|
| Query Decomposition | `decompose_question` 节点 + LangGraph `Send` API 并行子 Agent | ⭐⭐⭐ **核心参考**：LLM 拆解 2-4 子问题 + 并行执行 + synthesis 合并 |
| 跨源交叉验证 | 无直接对应（参考项目只有单一知识库） | ⭐ 本项目领域创新 |

---

### 4.4 参考项目 README「未来迭代」与本项目 TODO 的重叠

参考项目 README 的未来迭代清单中，以下条目与本项目 TODO 高度重合，说明**这些是 RAG 领域的通用改进方向**：

| 参考项目 TODO | 本项目 TODO | 重合度 |
|--------------|-----------|--------|
| 做一个小型标注集比较 dense/sparse/hybrid/rerank | 评估检索质量、调整分块策略 | 🟡 思路一致，实现层次不同 |
| 子问题分解（CoT） | Query Decomposition | 🟢 完全一致 |
| 多文档冲突处理 | 跨源交叉验证 | 🟢 方向一致 |
| 多模态 embedding | ⚪ 未设计 | 参考项目领先一步 |
| RAG 评估体系 | ⚪ 未设计 | 参考项目领先一步 |
| 死循环检测与恢复 | PoC 中已加 `recursion_limit=10` | 🟢 参考项目的工具调用限次 `_try_acquire_knowledge_tool_call` 更硬更可靠 |
| 自动生成会话名称 | ⚪ 未设计 | 参考项目已实现 |

---

## 5. 参考项目独有但与本项目目标未必相关的部分

以下功能在参考项目中很亮眼，但对**本项目的领域和阶段**来说未必需要优先实现：

| 功能 | 不紧迫的原因 |
|------|------------|
| 多用户登录/注册/JWT | 本项目是个人开发辅助工具，单用户即可 |
| 容器化部署（Docker Compose） | PoC 阶段本地 Python 脚本运行足够 |
| PostgreSQL + Redis | ChromaDB 本地持久化已满足当前数据量（3.5万片段） |
| 多格式文档解析（PDF/Word/Excel） | DST Mod 知识全部是 .lua / .md / .txt |
| 天气查询等第三方工具 | 与 Mod 开发无关 |
| RBAC 权限控制 | 个人使用无需权限分层 |
| Vite + Vue 3 自研前端 | Chainlit 已提供够用的 UI，重建成本极高 |

---

## 6. 本项目相对于参考项目的独特优势

这些是参考项目**完全没有**、但本项目具备的能力/设计：

| 优势 | 说明 |
|------|------|
| 🎯 **领域知识深度** | 面向 DST Mod 开发的领域知识体系（CONTEXT.md），含术语、检索策略、分库设计 |
| 📖 **词典解析层设计** | "先词典后知识库"的两阶段检索策略，将用户的中文俗称映射为英文 ID，这是通用 RAG 不需要的 |
| 🗂️ **认知类型四分法** | 本体/范例/文档/词典按"认知类型"而非"数据来源"分类，每个库有独立检索语义 |
| 📝 **踩坑记录体系** | 9 篇结构化踩坑文档（症状→根因→修复→影响范围），对后续维护极有价值 |
| 🖥️ **管理面板** | Streamlit 可视化管理配置、上传文档、开关工具，参考项目全靠命令行 |
| 🔧 **批量导入脚本** | 针对 .lua 文件优化的批量导入工具（编码回退、mod 元数据标记） |
| 📊 **降级透明度设计** | 两阈值三路径降级策略，每级降级告知用户（参考项目降级是静默的） |
| 🌐 **中文友好** | 全中文注释、文档、界面，面向中文 Mod 开发者 |

---

## 7. 建议实施优先级

基于以上分析，对 `TODO.md` 的实施顺序建议：

### 第一优先级：检索质量（高收益、可参考代码最丰富）

| 行动 | 参考来源 | 工作量 |
|------|---------|--------|
| 升级 Embedding → `BAAI/bge-m3` | 参考项目 `backend/indexing/embedding.py` | 小（改 config + 重建向量库） |
| ⚠️ 评估 Milvus 替代 ChromaDB 的必要性 | 参考项目 `docker-compose.yml` + `milvus_client.py` | 大（若引入 Milvus，整个基础设施会变） |
| Query Expansion（Step-Back + HyDE） | 参考项目 `rag/pipeline.py` 的 `rewrite_question_node` + `rag/utils.py` | 中（可在 ChromaDB 上实现，不需要 Milvus） |
| Rerank 精排 | 参考项目 `rag/utils.py` 的 Jina Rerank 调用 | 小（纯 API 调用） |

### 第二优先级：Agent 行为改进（参考代码充分、无基础设施依赖）

| 行动 | 参考来源 | 工作量 |
|------|---------|--------|
| 工具调用硬限制（替代软 prompt 约束） | 参考项目 `tools/knowledge.py` 的 `_try_acquire_knowledge_tool_call` | 极小（20 行） |
| 检索相关性评分门控 | 参考项目 `rag/pipeline.py` 的 `grade_documents_node` | 中（需引入结构化输出） |
| 检索过程可观测（emit_rag_step 思路） | 参考项目 `chat/streaming.py` + `chat/service.py` 的 `_RagStepProxy` | 中（需研究 Chainlit 的 Step 机制是否支持） |

### 第三优先级：架构改造（领域特有、无参考代码）

| 行动 | 说明 |
|------|------|
| 四分库架构 | 本项目独有设计，需独立实现 |
| glossary-lookup 工具 | 本项目独有设计，需独立实现 |
| 词典缺失降级策略 | 可参考参考项目的降级思路，但触发条件不同 |

### 第四优先级：工程化（个人项目暂不需要）

| 行动 | 说明 |
|------|------|
| 容器化部署 | 等需要分享给他人使用时再做 |
| 多用户/鉴权 | 暂不需要 |
| 自研前端 | Chainlit 目前够用 |

---

## 8. 技术细节速查表

### 8.1 参考项目中可直接借鉴的代码片段

| 代码位置 | 功能 | 适合场景 |
|----------|------|---------|
| `backend/tools/knowledge.py:16-20` | 工具调用硬限次 `_try_acquire_knowledge_tool_call` | 替代本项目的软 prompt 约束 |
| `backend/rag/pipeline.py:238-293` | `rewrite_question_node` 三策略路由 | 实现 Query Expansion |
| `backend/rag/pipeline.py:204-235` | `grade_documents_node` 结构化评分 | 实现检索相关性门控 |
| `backend/rag/pipeline.py:388-416` | `classify_complexity` 问题复杂度分类 | 实现简单问题快速通道 |
| `backend/rag/pipeline.py:419-443` | `decompose_question` 子问题拆解 | 实现多跳问题分解 |
| `backend/chat/service.py:152-274` | 流式输出 + `_RagStepProxy` + `agent_task.cancel()` | 若未来要做流式 |
| `backend/chat/streaming.py` 全部 | `call_soon_threadsafe` 跨线程事件调度 | 若要做实时思考展示 |
| `backend/indexing/embedding.py` | bge-m3 本地 embedding 加载 | 升级 Embedding 模型 |

### 8.2 环境变量对照

| 参考项目 | 本项目 | 对应用途 |
|----------|--------|----------|
| `ARK_API_KEY` / `MODEL` / `BASE_URL` | `DEEPSEEK_API_KEY` / `config.llm` | LLM 连接 |
| `EMBEDDING_MODEL` / `DENSE_EMBEDDING_DIM` | `config.embedding.model_name` | Embedding 模型 |
| `MILVUS_HOST` / `MILVUS_PORT` / `MILVUS_COLLECTION` | `config.knowledge_base.persist_directory` | 向量库地址 |
| `DATABASE_URL` / `REDIS_URL` | ⚪ 不存在 | 业务数据库 |
| `RERANK_MODEL` / `RERANK_BINDING_HOST` | ⚪ 不存在 | Rerank API |
| `RETRIEVAL_CANDIDATE_K` / `RETRIEVAL_CANDIDATE_MULTIPLIER` | ⚪ 不存在（ChromaDB k=3 硬编码） | 检索候选池 |
| `AUTO_MERGE_ENABLED` / `AUTO_MERGE_THRESHOLD` / `LEAF_RETRIEVE_LEVEL` | ⚪ 不存在 | Auto-merging |
| `JWT_SECRET_KEY` / `ADMIN_INVITE_CODE` | ⚪ 不存在 | 鉴权 |

---

> **结论**：参考项目在 RAG 检索链路的深度（混合检索、相关性评分、查询重写、子问题分解、Rerank 精排）、工程化程度（FastAPI 分层架构、Vue 3 自研前端、Docker 部署）、和可观测性（流式输出、实时思考展示、完整 trace 记录）三个方面远超本项目。但本项目的**领域知识设计**（词典解析、认知类型四分法、中英术语映射）是参考项目完全不具备的独特优势。建议优先吸收参考项目的**检索增强技术**（Step-Back / HyDE / Rerank / 硬限次），保留本项目的**领域特色**（四分库、词典解析、管理面板），形成"领域专用 + 检索增强"的混合方案。
