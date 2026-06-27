# 项目操作速查

> 面向人类和 Agent 的操作参考。每条命令可直接复制执行。
> 项目根目录：`agent_RAG_1_ly/`

---

## 当前版本

| 项目 | 值 |
|------|-----|
| 版本号 | **v0.2.0-poc** |
| 当前阶段 | **RAG 过程可视化（Phase 1，待开工）** |
| 已完成 | PoC 跑通 → Docker 容器化 → 代码分包（src/） → 5 条基准测试采集 |
| 下一步 | `agent.invoke()` → `agent.astream()` 流式改造 |

> 版本号约定：`主版本.功能阶段.补丁`。`-poc` 表示底层仍是 LangChain `create_agent` 原型。
> v1.0.0 将在迁移到 LangGraph 后打出。

---

## 一、Docker 运维

### 启动

```bash
cd d:\饥荒mod流水线GitHub\agent_RAG_1_ly
docker compose up -d
```

`-d` = 后台运行。首次或改代码后加 `--build` 重建镜像：

```bash
docker compose up -d --build
```

| 服务 | 端口 | 地址 |
|------|------|------|
| rag-chat（聊天） | 8000 | http://localhost:8000 |
| rag-admin（管理） | 8501 | http://localhost:8501 |

### 停止

```bash
docker compose down          # 停止并移除容器，保留 volume 数据
docker compose down -v       # 停止并删除 volume（清空向量库！慎用）
```

### 查看日志

```bash
docker compose logs -f chat       # 聊天端日志（实时滚动）
docker compose logs -f admin      # 管理端日志
docker compose logs -f chat admin # 两个一起看
```

### 查看运行状态

```bash
docker compose ps
```

### 重建镜像（改了代码/依赖后）

```bash
docker compose build               # 增量重建（利用缓存）
docker compose up -d               # 用新镜像启动
```

代码改动需要重建镜像——`COPY . .` 在构建时复制源码。

### 容器内执行命令

> **注意**：Windows 上 `docker exec` 直接传含 `/` 的路径可能被 mangling。路径参数用 `sh -c "..."` 包裹。

```
docker exec <容器名> <命令>               # 简单命令（不含路径）直接可用
docker exec <容器名> sh -c "<命令>"       # 带 Linux 路径参数时必须这样
```

| 用途 | 命令 |
|------|------|
| 进入容器 Bash | `docker exec -it rag-chat bash` |
| 查看向量库文件 | `docker exec rag-chat sh -c "ls -la /app/chroma_data/"` |
| 查看配置文件 | `docker exec rag-chat sh -c "cat /app/config.json"` |
| 验证 GPU 可用 | `docker exec rag-chat python -c "import torch; print(torch.cuda.is_available())"` |

### 数据目录

| 数据 | 宿主机路径 | 容器内路径 |
|------|-----------|-----------|
| 向量库（Chromadb） | Docker volume `chroma_data` | `/app/chroma_data/v1` |
| Mod 源码（只读） | `../好mod全部代码供观看/` | `/mod_source/` |
| 配置文件 | `./config.json` | `/app/config.json` |
| API Key | `./.env` | `/app/.env`（由 env_file 注入） |

### 常见问题

**看到 0 文档**：新部署的 Docker volume 是空的，需运行入库脚本。

**修改 config.json 后不生效**：聊天端/管理端在启动时读取配置，修改后 `docker compose restart chat`。

**GPU 在容器内不可用**：验证 `docker exec rag-chat python -c "import torch; print(torch.cuda.is_available())"`。若输出 `False`：Docker Desktop → Settings → Resources → WSL Integration → 确保已启用。仍不可用则注释掉 `docker-compose.yml` 中 `deploy.resources...` 段，切 CPU Embedding。

**Agent 死循环报错 `GraphRecursionError`**：刷新 Chainlit 网页即可（重新创建会话）。后续 Phase 2 用图的边做硬限制根除此问题。

---

## 二、知识库入库

### 批量导入所有 Mod（初次部署）

```bash
docker exec rag-admin sh -c "python 批量导入mod代码.py --source /mod_source"
```

导入 4 个 Mod（~35,000 片段），GPU Embedding 约需数分钟。

### 只导入指定 Mod

```bash
docker exec rag-admin sh -c "python 批量导入mod代码.py --source /mod_source --mod 棱镜"
```

### 通过管理面板上传少量文件

http://localhost:8501 →「知识库」标签 → 上传 `.txt` / `.md` / `.lua` → 点击「切分并入库」。

---

## 三、测试

> 测试案例记录在 [`测试案例_ly.md`](测试案例_ly.md)，编辑后运行 `python 测试案例转json_ly.py` 同步到 JSON。
> JSON 目前仅备未来 LangSmith 等自动化工具取用，日常不用关心。

### 手工测试流程

1. 打开 http://localhost:8000（聊天端）
2. 在 [`测试案例_ly.md`](测试案例_ly.md) 中选一个问题，粘贴到聊天框发送
3. 把 AI 回答粘贴到对应 `<details>` 块中，填写「评价」
4. 运行 `python 测试案例转json_ly.py` 同步 JSON
5. 重复

### 当前测试基线（v0.2.0-poc，5 条）

| # | 问题 | 评价要点 |
|---|------|---------|
| 1 | 列举3个棱镜mod的带有护甲值的装备 | 不及格——全面程度差 |
| 2 | 棱镜 mod 的月光武器是怎么注册的？ | 切片/检索策略导致漏检 |
| 3 | 怎么制作一个可以随身携带的容器？ | 待评价 |
| 4 | Beneath the World Below（深埋之下）mod 里有哪些自定义生物？ | 中英文兼容问题 |
| 5 | DST 中食物的腐败速度怎么修改？ | 比较丰富，及格 |

### 后续阶段补充测试的时机

- **Phase 1（RAG 可视化）完成后**：重测现有 5 条，对比流式体验；新增 2-3 条覆盖可视化效果
- **Phase 2（LangGraph）完成后**：重测全部，对比 Agent 循环控制的可靠性
- **Phase 3（检索质量）完成后**：重测 #1 #4（这两条对检索最敏感），验证提升幅度

---

## 四、相关文档索引

| 文档 | 用途 |
|------|------|
| [`README.md`](README.md) | 项目介绍、快速开始 |
| [`TODO.md`](TODO.md) | 待办清单（5 个阶段路线图） |
| [`CONTEXT.md`](CONTEXT.md) | 领域术语、检索策略、技术选型 |
| [`src架构设计_ly.md`](src架构设计_ly.md) | src/ 包结构设计与演进路线 |
| [`项目优化记录_ly.md`](项目优化记录_ly.md) | 已完成优化 + 领域创新点 |
| [`测试案例_ly.md`](测试案例_ly.md) | 手工测试案例（人类阅读） |
| [`测试案例_ly.json`](测试案例_ly.json) | 测试案例 JSON（脚本自动生成） |
| [`参考项目对比分析_ly.md`](参考项目对比分析_ly.md) | 参考项目 SuperMew 对比分析 |
| [`踩坑记录/`](踩坑记录/) | 9 篇技术踩坑文档 |
