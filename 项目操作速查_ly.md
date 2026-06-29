# 项目操作速查

> 面向人类和 Agent 的操作参考。每条命令可直接复制执行。
> 项目根目录：`agent_RAG_1_ly/`

---

## 当前版本

| 项目 | 值 |
|------|-----|
| 版本号 | **v1.0.0** |
| 当前阶段 | **Phase 2+3 已完成：LangGraph 图编排 + bge-m3 多语言嵌入** |
| 已完成 | PoC 跑通 → Docker 容器化 → 代码分包（src/） → Phase 1（流式+可视化） → Phase 2（LangGraph 替代 LangChain create_agent） → Phase 3 首项（Embedding bge-m3 升级） |
| 下一步 | Phase 3 后续（Rerank 精排）或 Phase 4（词典术语解析 + 四分库） |

> 版本号约定：`主版本.功能阶段.补丁`。v1.0.0 已打出——LangGraph + bge-m3 构成确定性图编排 + 多语言检索的可用基线。

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
| 向量库（Chromadb） | Docker volume `chroma_data` | `/app/chroma_data/bge-m3` |
| Mod 源码（只读） | `../好mod全部代码供观看/` | `/mod_source/` |
| 配置文件 | `./config.json` | `/app/config.json` |
| API Key | `./.env` | `/app/.env`（由 env_file 注入） |

### 常见问题

**看到 0 文档**：新部署的 Docker volume 是空的，需运行入库脚本。

**修改 config.json 后不生效**：聊天端/管理端在启动时读取配置，修改后 `docker compose restart chat`。

**GPU 在容器内不可用**：验证 `docker exec rag-chat python -c "import torch; print(torch.cuda.is_available())"`。若输出 `False`：Docker Desktop → Settings → Resources → WSL Integration → 确保已启用。仍不可用则注释掉 `docker-compose.yml` 中 `deploy.resources...` 段，切 CPU Embedding。

**Agent 死循环报错 `GraphRecursionError`**：Phase 2 LangGraph 图的边已固化检索次数（最多 2 次），物理上不可能有第三次搜索。此问题已根除，刷新页面重新提问即可。

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

> 测试案例有两份：
> - v0.2.0-poc 基线：[`测试案例_v0.2.0-poc_ly.md`](测试案例_v0.2.0-poc_ly.md) — LangChain `create_agent` + MiniLM 384d
> - v1.0.0 当前：[`测试案例_v1.0.0_ly.md`](测试案例_v1.0.0_ly.md) — LangGraph + bge-m3 1024d（含过程块🔍📊✏️）

### 手工测试流程

1. 打开 http://localhost:8000（聊天端）
2. 在测试案例文档中选一个问题，粘贴到聊天框发送
3. 把 AI 回答粘贴到对应 `<details>` 块中，填写「评价」
4. 重复

### 测试基线概览（v1.0.0，5 条）

| # | 问题 | v1.0.0 评价要点 |
|---|------|---------|
| 1 | 列举3个棱镜mod的带有护甲值的装备 | 仍未找到真正目标，提升空间：切片策略、查字典 |
| 2 | 棱镜 mod 的月光武器是怎么注册的？ | 检索命中 recipes_legion + datafix_legion，有代码但不够完整 |
| 3 | 怎么制作一个可以随身携带的容器？ | （待评价） |
| 4 | Beneath the World Below（深埋之下）mod 里有哪些自定义生物？ | bge-m3 对纯英文 Mod 名仍有盲区 |
| 5 | DST 中食物的腐败速度怎么修改？ | 检索命中 TUNING 常量表，回答含完整示例 |

### 后续阶段补充测试的时机

- **Phase 3（Rerank 精排）后**：重测全部，对比检索精度
- **Phase 4（词典 + 四分库）后**：重测 #1 #2 #4（对检索质量最敏感），验证大版本提升
- **Phase 5（复杂度分类 + 三策略）后**：新增 2-3 条复杂问题的多轮测试

---

## 四、相关文档索引

| 文档 | 用途 |
|------|------|
| [`README.md`](README.md) | 项目介绍、快速开始 |
| [`TODO.md`](TODO.md) | 待办清单（5 个阶段路线图） |
| [`创新点清单_ly.md`](创新点清单_ly.md) | 项目创新点与改进点全览 |
| [`CONTEXT.md`](CONTEXT.md) | 领域术语、检索策略、技术选型 |
| [`src架构设计_ly.md`](src架构设计_ly.md) | src/ 包结构设计与演进路线 |
| [`项目优化记录_ly.md`](项目优化记录_ly.md) | 已完成工程改进 + 实测发现 |
| [`测试案例_v0.2.0-poc_ly.md`](测试案例_v0.2.0-poc_ly.md) | v0.2.0-poc 基线测试案例 |
| [`测试案例_v1.0.0_ly.md`](测试案例_v1.0.0_ly.md) | v1.0.0 当前测试案例（含过程块） |
| [`参考项目对比分析_ly.md`](参考项目对比分析_ly.md) | 参考项目 SuperMew 对比分析 |
| [`踩坑记录/`](踩坑记录/) | 11 篇技术踩坑文档 |
