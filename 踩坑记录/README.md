# 踩坑记录 — agent_RAG_1_ly

本项目在搭建 RAG Agent 过程中踩过的技术坑。每个坑单独成文，按时间顺序编号。

---

## 阅读指引（先看这里）

不是所有坑都需要细读。按"你现在在干什么"分类：

### 🟢 已避免 / 开发过程坑（8 个）

修复已写入代码，**正常使用无需关心**。除非你要修改核心脚本（`app.py`/`管理面板.py`/`批量导入mod代码.py`），否则不会重新触发。

| # | 标题 | 修复方式 |
|---|------|---------|
| 01 | ChromaDB 中文路径 | `persist_directory` 已迁到 `~/.chromadb_rag/v1`（纯 ASCII），三个脚本均加了 `~` 展开逻辑 |
| 02 | agent invoke 输入格式 | `app.py` 已改为 `{"messages": [HumanMessage(...)]}` |
| 03 | Agent 反复搜索死循环 | Phase 2 LangGraph 图的边 = 硬约束，最多 2 次检索，物理上不可能有第三次。**已根除** |
| 05 | .env UTF-16 编码 | 文件本体已转 UTF-8，`.gitignore` 排除，不会回退 |
| 06 | HuggingFace 国内网络 | 所有脚本启动时写入 `HF_ENDPOINT` + `HF_HUB_OFFLINE`，模型已本地缓存 |
| 08 | RecursiveCharacterTextSplitter | import 已改为 `langchain_classic.text_splitter` |
| 09 | PyTorch CPU → GPU | CUDA 版 PyTorch 已安装，GPU Embedding 已验证 |
| 10 | LangGraph 节点闭包依赖注入 | pipeline.py 的 lambda 闭包已同步更新 `model_name` 参数 |
| 11 | HuggingFaceEmbeddings 不支持 query_instruction | 改为在 nodes.py 中手动调用 `add_query_prefix()` |

### 🟡 使用方式依赖（2 个）

**走启动脚本就安全，直接运行则触发。** 每次使用都可能碰到，需要知道。

| # | 标题 | 安全做法 | 触发条件 |
|---|------|---------|---------|
| 04 | Windows 终端 GBK 编码 | 用 `python 启动rag助手.py` / `python 启动管理面板.py` | 直接运行 `chainlit run app.py` 或 `streamlit run 管理面板.py` 时不触发修复 |
| 07 | Streamlit 文件监视器 | 用 `python 启动管理面板.py` | 直接 `streamlit run 管理面板.py` 时不带 `--server.fileWatcherType none` 参数 |

**规则**：永远使用项目根目录的两个启动脚本，不要直接调用底层命令。

---

## 坑列表（完整）

| # | 标题 | 领域 | 一句话 |
|---|------|------|--------|
| 01 | [ChromaDB 中文路径导致 HNSW 索引损坏](01_chromadb中文路径导致HNSW索引损坏.md) | ChromaDB | Rust 后端无法写入含中文的路径，索引静默丢失 |
| 02 | [LangChain 1.0 `create_agent` 输入格式错误](02_LangChain1.0_agent_invoke输入格式.md) | LangChain | 用了 `{"role":"user"}` 而非 `{"messages":[...]}` 导致 Agent 收不到问题 |
| 03 | [Agent 反复搜索陷入死循环](03_Agent反复搜索陷入死循环.md) | Agent | 检索结果不足时反复调工具，网页端超时无响应 |
| 04 | [Windows 终端 GBK 编码报错](04_Windows终端GBK编码报错.md) | 环境 | emoji/中文输出时 `UnicodeEncodeError: 'gbk'` |
| 05 | [.env 文件 UTF-16 编码导致 dotenv 失败](05_env文件UTF16编码问题.md) | 环境 | IDE 保存 .env 为 UTF-16 LE，`python-dotenv` 解析崩溃 |
| 06 | [HuggingFace 国内无法连接](06_HuggingFace国内网络问题.md) | Embedding | `huggingface.co` 被墙，需走镜像站 |
| 07 | [Streamlit 文件监视器触发 torchvision 缺失](07_Streamlit文件监视器问题.md) | 管理面板 | Streamlit 扫描 `transformers` 时懒加载触发 `torchvision` 报错 |
| 08 | [RecursiveCharacterTextSplitter 在 LangChain 1.0 中位置变更](08_RecursiveCharacterTextSplitter位置变更.md) | LangChain | 从 `langchain.text_splitter` 移到 `langchain_classic.text_splitter` |
| 09 | [PyTorch CPU 版本无法使用 GPU](09_PyTorch_CPU_GPU版本.md) | GPU/Embedding | CPU 版 `torch` 不包含 CUDA，Embedding 推理慢 20-50 倍 |
| 10 | [LangGraph 节点闭包依赖注入](10_LangGraph节点闭包依赖注入.md) | LangGraph | 检索节点新增 `model_name` 参数后，pipeline.py 的 lambda 闭包需同步更新，否则 bge-m3 查询前缀不生效 |
| 11 | [HuggingFaceEmbeddings 不支持 query_instruction](11_HuggingFaceEmbeddings不支持query_instruction.md) | Embedding | bge-m3 需要查询指令前缀但 LangChain 新版无此字段，改为在 nodes.py 中手动调用 `add_query_prefix()` |

## 通用教训

1. **Windows 中文环境是坑的高发区** — 路径编码、终端编码、文件编码三个维度都可能出问题
2. **LangChain 1.0 大改版** — 大量 API 和包结构变化，网上绝大多数教程针对旧版，不能照搬
3. **ChromaDB 的 Rust 后端对非 ASCII 路径不友好** — 开发时尽量用纯英文路径
4. **先做最小化测试** — 每次改配置/装包后用几行代码验证，避免到全流程才发现问题
5. **永远通过启动脚本运行** — `启动rag助手.py` 和 `启动管理面板.py` 内部处理了编码、参数等环境问题，直接跑底层命令会漏掉这些修复
