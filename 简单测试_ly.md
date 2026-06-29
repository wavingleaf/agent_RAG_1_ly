# 简单测试

> 目标：快速确认系统没坏。与「测试案例」的区别——这里只关心"跑通了没"，不关心"答得好不好"。

---

## 一键命令

```bash
docker exec rag-chat python -c "
from src.config import load_config
from src.embedding import create_embedding
from src.llm import create_model
from src.knowledge.store import create_vectorstore
from src.agent.prompt import build_system_prompt
from src.agent.factory import create_agent, run_agent

cfg = load_config()
embedding = create_embedding(cfg)
vs = create_vectorstore(cfg, embedding)
retriever = vs.as_retriever(search_kwargs={'k': 3})
model = create_model(cfg)
sp = build_system_prompt(cfg)
agent = create_agent(model=model, system_prompt=sp, retriever=retriever, query_prefix=cfg['embedding'].get('query_prefix', ''))

result = run_agent(agent, '棱镜mod有哪些装备？')

checks = [
    ('Graph type', type(agent).__name__, 'CompiledStateGraph'),
    ('Docs found', len(result.get('docs',[])) > 0, True),
    ('Route present', result.get('route') in ('generate_answer','rewrite_question'), True),
    ('Response not empty', len(result.get('response','')) > 50, True),
]
all_ok = True
for name, actual, expected in checks:
    ok = actual == expected
    if not ok:
        all_ok = False
    print(f'  {\"✅\" if ok else \"❌\"} {name}: {actual}')
print('PASS' if all_ok else 'FAIL')
" && echo "OK" || echo "FAIL"
```

期望输出：4 行 ✅ + `PASS`。

---

## 逐项手工检查

如果一键命令不通过，逐项定位：

### 1. 模型加载

```bash
docker exec rag-chat python -c "
from src.embedding import create_embedding
from src.config import load_config
cfg = load_config()
emb = create_embedding(cfg)
print('Embedding OK')
"
```

### 2. 向量库连接

```bash
docker exec rag-chat python -c "
from src.embedding import create_embedding
from src.knowledge.store import create_vectorstore
from src.config import load_config
cfg = load_config()
emb = create_embedding(cfg)
vs = create_vectorstore(cfg, emb)
print(f'Collection docs: {vs._collection.count()}')
"
```

期望：`Collection docs: 35039`（或接近此数）。

### 3. 检索

```bash
docker exec rag-chat python -c "
from src.embedding import create_embedding
from src.knowledge.store import create_vectorstore
from src.config import load_config
cfg = load_config()
emb = create_embedding(cfg)
vs = create_vectorstore(cfg, emb)
retriever = vs.as_retriever(search_kwargs={'k': 3})
docs = retriever.invoke('棱镜mod有哪些装备')
print(f'Retrieved: {len(docs)} docs')
for d in docs:
    print(f'  {d.metadata.get(\"mod_name\",\"?\")}/{d.metadata.get(\"source\",\"?\")[-40:]}')
"
```

期望：3 条结果，mod_name 合理。

### 4. 图编译

```bash
docker exec rag-chat python -c "
from src.llm import create_model
from src.embedding import create_embedding
from src.knowledge.store import create_vectorstore
from src.agent.prompt import build_system_prompt
from src.agent.factory import create_agent
from src.config import load_config
cfg = load_config()
emb = create_embedding(cfg)
vs = create_vectorstore(cfg, emb)
retriever = vs.as_retriever(search_kwargs={'k': 3})
model = create_model(cfg)
sp = build_system_prompt(cfg)
agent = create_agent(model=model, system_prompt=sp,
                     retriever=retriever, query_prefix=cfg['embedding'].get('query_prefix', ''))
print(f'Graph type: {type(agent).__name__}')
"
```

期望：`Graph type: CompiledStateGraph`。

### 5. UI 可达

```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000
curl -s -o /dev/null -w "%{http_code}" http://localhost:8501
```

期望：两次 `200`。

### 6. 流式事件

```bash
docker exec rag-chat python -c "
import asyncio
from src.config import load_config
from src.llm import create_model
from src.embedding import create_embedding
from src.knowledge.store import create_vectorstore
from src.agent.prompt import build_system_prompt
from src.agent.factory import create_agent, run_agent_stream

cfg = load_config()
emb = create_embedding(cfg)
vs = create_vectorstore(cfg, emb)
retriever = vs.as_retriever(search_kwargs={'k': 3})
model = create_model(cfg)
sp = build_system_prompt(cfg)
agent = create_agent(model=model, system_prompt=sp,
                     retriever=retriever, query_prefix=cfg['embedding'].get('query_prefix', ''))

async def test():
    types = set()
    names = set()
    async for e in run_agent_stream(agent, 'test'):
        types.add(e['type'])
        if e.get('name'):
            names.add(e['name'])
    print('Event types:', sorted(types))
    print('Tool names:', sorted(names))

asyncio.run(test())
"
```

期望：`Event types: ['token', 'tool_end', 'tool_start']`，`Tool names: ['search_knowledge_base', '相关性评估', '查询重写']`。

---

## 何时运行

- 每次 `docker compose build` 后
- 每次改完 `src/agent/` 下文件后
- 每次怀疑"是不是刚才改坏了"时

全量跑完 < 30 秒（不含 rebuild）。
