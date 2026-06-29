# 01 — ChromaDB 中文路径导致 HNSW 索引损坏

## 症状

- 聊天端（app.py）启动时 `on_chat_start` 中 `vectorstore._collection.count()` 报错
- 错误栈：`InternalError: Error loading hnsw index`
- 同一库经 `rm -rf` 后重建，运行一次能工作，重启后再次报同样错误
- 库文件结构中只有 `chroma.sqlite3` 和 `index_metadata.pickle`，缺少 `.bin` 文件

## 根因

**Windows 上 Rust 的 Path/OsString 对含中文（非 ASCII）路径的处理问题，导致 ChromaDB 的 HNSW 索引文件写出静默失败。**

项目路径为 `d:/饥荒mod流水线GitHub/agent_RAG_1_ly/`，ChromaDB 的 `persist_directory` 指向该路径下的 `chroma_db_v1/`。创建 collection 并写入数据时：
- SQLite 层正常（`chroma.sqlite3` 中生成了 35039 条 embedding 记录）
- HNSW 索引写出时静默失败——`.bin` 文件（`data_level0.bin`、`header.bin`、`length.bin`、`link_lists.bin`）没有写入磁盘

对比测试：

| 平台 | 路径 | 结果 |
|------|------|------|
| Windows | `C:/Users/ADMIN/.../tmpXXX/`（纯 ASCII） | ✅ 正常生成 4 个 `.bin` 文件 |
| Windows | `d:/饥荒mod流水线GitHub/.../`（含中文） | ❌ 只有 `chroma.sqlite3`，无 `.bin` |
| Windows | `测试中文_chromadb/`（含中文） | ❌ 只有 `chroma.sqlite3`，无 `.bin` |
| Linux (Docker) | `/tmp/测试中文路径_xxxxx/`（含中文） | ✅ 正常生成 4 个 `.bin` 文件，重启后可正常读取 |

**结论**：不是 ChromaDB 的 bug，而是 Windows 上 Rust 标准库对非 UTF-8 路径的处理问题。Linux 的中文路径完全正常。ChromaDB 的 HNSW 索引实现本身没有问题——问题出在 Windows + Rust + 中文路径的组合。

### 为什么第二次启动才报错？

`Chroma()` 构造函数在第一次打开时能工作——SQLite 中有数据，Chromadb 会在内存中重建必要的结构用于读写。但重启后需要从磁盘读 HNSW 索引时，发现 `.bin` 文件不存在，报错。

## 修复

将 ChromaDB 持久化目录移到纯 ASCII 路径 `~/.chromadb_rag/v1/`（解析为 `C:\Users\ADMIN\.chromadb_rag\v1`）。

改动文件：
- [config.json](../config.json) — `persist_directory` 改为 `~/.chromadb_rag/v1`
- [app.py](../app.py) — `_setup_vectorstore()` 添加 `~` 展开逻辑
- [管理面板.py](../管理面板.py) — `get_chroma_dir()` 添加 `~` 展开逻辑
- [批量导入mod代码.py](../批量导入mod代码.py) — 同上

```python
# 修复后的路径处理
pd = kb_cfg.get("persist_directory", "./chroma_db")
persist_dir = str(Path(pd).expanduser()) if pd.startswith("~") else str(PROJECT_DIR / pd)
```

## 影响范围

- **Windows 环境**：所有含非 ASCII 字符路径的场景
- **Linux / macOS**：不受影响——中文路径在 Linux 上正常工作
- 变通方案：始终将 `persist_directory` 设到纯 ASCII 路径（Windows 下最安全）

## 排查方法

写一个最小化测试，分别用 ASCII 和中文路径创建 ChromaDB，对比文件结构：

```python
import tempfile, os
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

emb = HuggingFaceEmbeddings(model_name='all-MiniLM-L6-v2')

# ASCII 路径 — 应生成 .bin 文件
tmp_ascii = tempfile.mkdtemp()
v1 = Chroma(persist_directory=tmp_ascii, embedding_function=emb)
v1.add_texts(['hello'])

# 检查文件列表
for root, dirs, files in os.walk(tmp_ascii):
    for f in files:
        print(os.path.join(root, f))
```
