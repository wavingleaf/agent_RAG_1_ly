# 11. HuggingFaceEmbeddings 不支持 query_instruction 入参

**领域**：Embedding / LangChain

**症状**：尝试 `HuggingFaceEmbeddings(model_name="BAAI/bge-m3", query_instruction="...")` 报 `ValidationError: Extra inputs are not permitted`

**根因**：bge 系列模型在预训练时使用了查询指令前缀（`"Represent this sentence for searching relevant passages:"`），需要 `embed_query()` 时自动添加、`embed_documents()` 时不添加。旧版 sentence-transformers 的 `HuggingFaceEmbeddings` 可能支持 `prompt` 或 `query_instruction` 字段，但本项目使用的 `langchain-huggingface` 版本已移除该字段。

**修复**：
- `embedding.py` 新增 `add_query_prefix(query, model_name)` 工具函数
- 在 `nodes.py` 的 `retrieve_initial()` 和 `retrieve_expanded()` 中，调用 `retriever.invoke()` 之前手动添加前缀：`search_query = add_query_prefix(question, model_name)`
- 前缀仅用于 `embed_query()` 路径（查询端），不影响 `embed_documents()`（入库端）

**影响范围**：bge-m3 检索精度——不加前缀的嵌入和加前缀的嵌入不在同一个语义空间中，检索质量会下降

**教训**：LangChain 的 HuggingFaceEmbeddings 在不同版本间 API 不稳定，不要依赖构造函数中的高级参数。最稳妥的做法是在业务层（nodes.py）手动控制文本预处理
