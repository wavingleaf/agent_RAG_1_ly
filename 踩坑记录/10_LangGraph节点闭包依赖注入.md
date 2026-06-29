# 10. LangGraph 节点闭包依赖注入

**领域**：LangGraph / Agent

**症状**：检索节点的 bge-m3 查询前缀不生效，因为 `model_name` 参数没有正确传入节点闭包

**根因**：LangGraph 节点通过 `pipeline.py` 的 lambda 闭包注入 `retriever` / `model` / `system_prompt`。当 `nodes.py` 的 `retrieve_initial()` 和 `retrieve_expanded()` 新增 `model_name` 参数后，如果只改 `nodes.py` 不改 `pipeline.py`，lambda 闭包仍传旧签名，导致 `model_name` 永远为默认的空字符串。

**修复**：
- `pipeline.py` 的 `create_agent()` 新增 `model_name` 参数
- `retrieve_initial` 和 `retrieve_expanded` 的 lambda 闭包改为 `lambda s: retrieve_initial(s, retriever, model_name)`
- `factory.py` 的 `create_agent()` 透传 `model_name`
- `app.py` 从 `cfg["embedding"]["model_name"]` 取值传入

**影响范围**：全部检索质量——如果漏改，bge-m3 等同于无查询前缀的普通检索，命中率下降

**教训**：LangGraph 的闭包依赖注入链是 `app.py → factory.py → pipeline.py → nodes.py` 四层。任何节点函数签名的增删改，必须整条链路同步更新，漏一层就退化到默认值且不报错
