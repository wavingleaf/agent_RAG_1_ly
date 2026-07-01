# agent_RAG_1_ly

基于 LangGraph + DeepSeek 的 RAG Agent，面向饥荒联机版（DST）Mod 开发知识问答。

## 项目状态

```
🟢 已实现：单库跑通，4 个参考 Mod 已入库（35,039 片段），GPU Embedding
🟢 PoC 完成：聊天端 + 管理面板可用
🟢 Phase 1 完成：流式输出、工具调用可视化、思考路径透传
🟢 Phase 2 完成：LangGraph 确定性图编排（替代 LangChain create_agent）
🟢 Phase 3 首项完成：Embedding 模型升级（all-MiniLM-L6-v2 → bge-m3 1024d）
🟡 已设计未实现：四分库架构、词典速查、词典增强查询重写
⚪ 规划中：LLM 自主查询重写（Step-Back / HyDE）、Query Decomposition
```

完整路线图见 [TODO.md](TODO.md)，域设计见 [CONTEXT.md](CONTEXT.md)。

## 已实现

| 条目 | 说明 |
|------|------|
| LangGraph 确定性图编排 | 检索 + 评分门控 + 重写 + 二次检索，图的边 = 硬限制（最多 2 次检索） |
| bge-m3 多语言 Embedding | 1024d 多语言模型，解决了 MiniLM 的中文"语义失明"（棱镜命中率 0%→100%） |
| 三色折叠过程可视化 | 检索🔍 / 评分门控📊 / 查询重写✏️ 在聊天 UI 中可展开查看系统心路历程 |
| 评分门控 + 查询重写链路 | LLM structured output 判断检索相关性 → 不相关自动重写查询 → 二次检索 |
| 流式输出 + 打字机效果 | `astream_events`(v2) 逐 token 推送 + Chainlit `stream_token()` 实时渲染 |

更多：[创新点清单_ly.md](创新点清单_ly.md)（创新与改进全览） · [项目优化记录_ly.md](项目优化记录_ly.md)（已完成优化详情）

## 下一步（近期重点）

| 条目 | 说明 | Phase |
|------|------|-------|
| 四分库架构 | 本体 / Mod / 文档 / 词典按来源独立建库，各适配检索策略 | 4 |
| 词典术语解析层 | 中文俗称→英文标识符映射（glossary-lookup + 词典增强查询重写） | 4 |
| LLM 自主查询重写 | Step-Back / HyDE 二策略条件触发，挂在词典基础链路之上 | 3 |
| 本体代码入库 | DST 官方 ~4000 .lua 文件，覆盖游戏引擎核心代码 | 数据 |
| 复审问题 | 词典重组后插入用户校验断点：直接用 / 微调 / 重新描述 | 4 |

全部待办见 [TODO.md](TODO.md)，设计讨论见 [设计讨论临时记录_ly.md](设计讨论临时记录_ly.md)。

## 领域

覆盖 DST Mod 开发中的部分有用知识，计划包含四类知识源：

| 知识源 | 内容 | 状态 |
|--------|------|------|
| 本体代码（game-scripts） | DST 官方 scripts/*.lua，~4000 文件 | ⚪ 待入库 |
| 优秀 Mod（reference-mods） | 棱镜/小穹/深埋之下/能力勋章 共 819 文件 | 🟢 已入库 35,039 片段 |
| 本地文档（local-docs） | 自编教程、犯错经验、功能摘抄、设计决策 | ⚪ 待入库 |
| 词典速查（glossary-lookup） | prefablist.lua / tuning.lua / chinese_s.po | ⚪ 待入库 |

检索策略为「两阶段先词典后知识库」：先通过词典将用户问题中的中文名/俗称映射为英文 ID，再由 LLM 理解上下文后融入精确标识符重编问题，最后并行检索三个知识源。详见 [CONTEXT.md](CONTEXT.md)。

## 准备工作（必读）

无论选哪种方式，都需要准备以下四样东西。其中向量库获取方式决定了后续的 config 怎么改：

| 准备工作 | 怎么做 | 备注 |
|----------|--------|------|
| API Key | 复制 `.env.example` → `.env`，填入 `DEEPSEEK_API_KEY` | 去 [DeepSeek 开放平台](https://platform.deepseek.com) 注册获取 |
| Embedding 模型 | 首次运行时自动从 HuggingFace 下载 bge-m3（~2.2 GB） | 国内用户设 `export HF_ENDPOINT=https://hf-mirror.com`；网络受限见踩坑记录/06 |
| 向量库 | **A）下载 Release**（推荐）或 **B）从 Mod 源码构建** | 两种方案对 config 的影响不同，见下表 |
| Docker（可选） | `docker compose` 可用；GPU 仅入库时需要，聊天端 CPU 即可 | 不用 Docker 则裸 Python ≥ 3.10 |

**向量库方案对比——config 和 docker-compose 分别改什么：**

| | 方案 A：下载 Release | 方案 B：从源码构建 |
|---|---|---|
| 操作 | 下载 tar.gz → 解压到项目目录 | 等 admin 启动后跑 `批量导入mod代码.py` |
| 前置条件 | 无需额外准备 | **需自备 Mod 源码**（.lua 文件），本项目不包含 |
| 耗时 | 较短（仅下载+解压） | GPU 较短 / CPU 较长 |
| Docker 用户 | `docker-compose.yml` 加一行 bind mount（见下方） | 无需改 compose，直接用默认 volume |
| Docker 的 `persist_directory` | **不用改**（bind mount 对容器透明） | **不用改**（`/app/chroma_data/bge-m3`） |
| 裸 Python 的 `persist_directory` | **必须改**为 `"./rag-chroma-bge-m3_v1.0.0-pre"` | 保持 `"./chroma_db"`（或你自定义的路径） |

> **config.json 的 `persist_directory` 决定 ChromaDB 读写哪个目录。** Docker 和裸 Python 的路径体系不同（容器内 `/app/...` vs 宿主机相对路径），选错会导致"库被清空"的错觉。`config.py` 会在环境不匹配时打印警告。

下面按 Docker 和裸 Python 分别展开。如果你只是试一下，选 **Docker + 方案 A**——2 分钟就能聊上天。

---

## 快速开始（Docker，推荐）

### 1. 准备向量库（二选一）

**方案 A：下载预构建 Release（推荐，2 分钟）**

从 [GitHub Releases](../../releases) 下载 `rag-chroma-bge-m3_v1.0.0-pre.tar.gz`（183 MB，35,039 片段），解压到项目目录：

```bash
tar -xzf rag-chroma-bge-m3_v1.0.0-pre.tar.gz
```

在 `docker-compose.yml` 的 chat 和 admin 的 `volumes:` 中**追加**一行，用本地目录覆盖 bge-m3 子目录：

```yaml
volumes:
  - chroma_data:/app/chroma_data          # 保留（存 hf_cache）
  - ./rag-chroma-bge-m3_v1.0.0-pre:/app/chroma_data/bge-m3  # 🆕 用本地向量库覆盖
```

> `config.json` 的 `persist_directory` 无需改动——容器内仍看到 `/app/chroma_data/bge-m3`，bind mount 直接映射到这个路径。

**方案 B：从 Mod 源码导入（需自备 .lua 文件 + GPU）**

> ⚠️ 本项目不包含 Mod 源码。你需要自行将 Mod 的 `.lua` 文件放入一个目录，并确保 `docker-compose.yml` 中已挂载该目录（默认映射 `../好mod全部代码供观看:/mod_source:ro`）。

跳过方案 A，等 admin 容器启动后执行：

```bash
docker exec -it rag-admin python 批量导入mod代码.py --source /mod_source
```

前提：`docker-compose.yml` 中已挂载 Mod 源码目录（默认 `../好mod全部代码供观看:/mod_source:ro`）。

### 2. 首次启动（先 admin 后 chat）

Embedding 模型（bge-m3，~2.2 GB）需要联网下载一次。admin 容器不设 `HF_HUB_OFFLINE`，会自动下载到共享 volume；chat 容器设了 `HF_HUB_OFFLINE=1`（避免每次启动校验网络），所以**必须先启动 admin 一次**：

```bash
# 先启动管理面板——它会自动从 HuggingFace 下载 bge-m3 模型
docker compose up -d admin

# 等模型下载完成（docker logs -f rag-admin 出现 "You can now view"）
# 再启动聊天端
docker compose up -d chat
```

> 国内用户下载慢？在 `.env` 中加 `HF_ENDPOINT=https://hf-mirror.com`，或在宿主机设 `export HF_ENDPOINT=https://hf-mirror.com` 后重启 admin 容器。详见 [踩坑记录/06](踩坑记录/06_HuggingFace国内网络问题.md)。

第二次及以后直接 `docker compose up -d` 即可，模型已缓存。

```
聊天端 → http://localhost:8000
管理面板 → http://localhost:8501
```

完整操作参考：[项目操作速查_ly.md](项目操作速查_ly.md)。

---

## 快速开始（裸 Python，备选）

```bash
# 1. 安装依赖（Python ≥ 3.10）
pip install -r requirements.txt

# 2. 配置 API Key
cp .env.example .env
# 编辑 .env：DEEPSEEK_API_KEY=sk-你的密钥

# 3. 准备向量库（二选一）
#    A) 下载 Release：tar -xzf rag-chroma-bge-m3_v1.0.0-pre.tar.gz
#       然后修改 config.json：
#         "persist_directory": "./rag-chroma-bge-m3_v1.0.0-pre"
#    B) 从源码导入（需自备 .lua 文件）：
#       python 批量导入mod代码.py --source <你的Mod源码目录>

# 4. 首次运行会自动从 HuggingFace 下载 bge-m3 模型（~2.2 GB）。
#    国内用户先设置：export HF_ENDPOINT=https://hf-mirror.com
#    网络受限时见：踩坑记录/06_HuggingFace国内网络问题.md

# 5. 启动管理面板
python 启动管理面板.py       # → http://localhost:8501

# 6. 另开终端，启动聊天端
python 启动rag助手.py        # → http://localhost:8000
```

## 启动方式

| | Docker（推荐） | 裸 Python |
|------|------|------|
| 聊天端 | `docker compose up -d chat` | `python 启动rag助手.py` |
| 管理面板 | `docker compose up -d admin` | `python 启动管理面板.py` |
| 一起启动 | `docker compose up -d` | 需开两个终端 |

聊天端 → `:8000`，管理面板 → `:8501`。

## 项目结构

```
agent_RAG_1_ly/
├── app.py                  # 聊天端（Chainlit）
├── 管理面板.py              # 管理端（Streamlit）
├── config.json             # 共享配置
├── .env                    # API Key（不提交）
├── requirements.txt
├── 启动rag助手.py           # 双击启动聊天端
├── 启动管理面板.py          # 双击启动管理面板
├── 批量导入mod代码.py        # 批量导入 .lua 文件到向量库
├── Dockerfile / docker-compose.yml / .dockerignore
├── src/                    # 共享源码
│   ├── config.py / llm.py / embedding.py
│   ├── knowledge/          # 向量库子包
│   └── agent/              # Agent 子包
│       ├── factory.py / prompt.py
│       └── graph/          # LangGraph 图编排（nodes + pipeline）
```

架构详情见 [src架构设计_ly.md](src架构设计_ly.md)。

## 已知限制

- **本体代码未入库**：DST 官方 ~4000 .lua 文件，当前仅覆盖 4 个参考 Mod
- **词典数据未入库**：中文俗称→英文 ID 的术语映射链路无数据支撑
- **单库架构**：尚未按四分法拆分为四个独立知识源
- **重写策略单一**：当前只有一种重写方式，三策略路由（Step-Back/HyDE/Decomposition）待后续实现

## 相关文档

- [CONTEXT.md](CONTEXT.md) — 领域术语、检索策略、知识库四分法
- [TODO.md](TODO.md) — 待办清单与各阶段路线图
- [创新点清单_ly.md](创新点清单_ly.md) — 创新点与改进点全览
- [项目优化记录_ly.md](项目优化记录_ly.md) — 已完成的工程优化与实测发现
- [项目操作速查_ly.md](项目操作速查_ly.md) — 日常操作命令大全
- [src架构设计_ly.md](src架构设计_ly.md) — 源代码架构设计与演进路线
- [参考项目对比分析_ly.md](参考项目对比分析_ly.md) — 参考项目 SuperMew 对比分析
- [设计讨论临时记录_ly.md](设计讨论临时记录_ly.md) — grill-with-docs 审查的 17 条发现与决策
- [踩坑记录/](踩坑记录/) — 11 篇技术踩坑文档（症状 → 根因 → 修复 → 影响）
