# Docker 操作速查

> 面向人类和 Agent 的操作参考。每条命令可直接复制执行。
> 项目根目录：`agent_RAG_1_ly/`

---

## 启动

```bash
cd d:\饥荒mod流水线GitHub\agent_RAG_1_ly
docker compose up -d
```

`-d` = 后台运行，终端不会被日志占用。首次启动时加上 `--build` 重新构建镜像：

```bash
docker compose up -d --build
```

两个服务：

| 服务 | 端口 | 地址 |
|------|------|------|
| rag-chat（聊天） | 8000 | http://localhost:8000 |
| rag-admin（管理） | 8501 | http://localhost:8501 |

---

## 停止

```bash
docker compose down          # 停止并移除容器，保留 volume 数据
docker compose down -v       # 停止并删除 volume（清空向量库！慎用）
```

---

## 查看日志

```bash
docker compose logs -f chat       # 聊天端日志（实时滚动）
docker compose logs -f admin      # 管理端日志
docker compose logs -f chat admin # 两个一起看
```

---

## 查看运行状态

```bash
docker compose ps
```

---

## 入库操作

### 方法 1：批量导入所有 Mod（初次部署用）

**前提**：宿主机上 `d:\饥荒mod流水线GitHub\好mod全部代码供观看\` 目录存在，且已在 `docker-compose.yml` 中挂载为 `/mod_source`（只读）。

```bash
docker exec -it rag-admin python 批量导入mod代码.py --source /mod_source
```

导入全部 4 个 Mod（~35,000 片段），GPU Embedding 约需数分钟。

### 只导入指定一个 Mod

```bash
docker exec -it rag-admin python 批量导入mod代码.py --source /mod_source --mod 棱镜
```

### 方法 2：通过管理面板上传少量文件

打开 http://localhost:8501 →「知识库」标签 → 上传 `.txt` / `.md` / `.lua` 文件 → 点击「切分并入库」。

---

## 在容器内执行命令

```
docker exec -it <容器名> <命令>
```

| 用途 | 命令 |
|------|------|
| 进入容器 Bash | `docker exec -it rag-chat bash` |
| 查看向量库文件 | `docker exec -it rag-chat ls -la /app/chroma_data/` |
| 查看配置文件 | `docker exec -it rag-chat cat /app/config.json` |
| 验证 GPU 可用 | `docker exec -it rag-chat python -c "import torch; print(torch.cuda.is_available())"` |

---

## 重建镜像（改了代码/依赖后）

```bash
docker compose build --no-cache    # 完全重建
docker compose build               # 增量重建（利用缓存）
docker compose up -d               # 用新镜像启动
```

通常情况代码改动不需要重建——`docker-compose.yml` 通过 bind mount 把 `config.json` 挂进去了，代码改动需要重建镜像（因为源码是在 `COPY . .` 时复制进去的）。

---

## 数据目录

| 数据 | 宿主机路径 | 容器内路径 |
|------|-----------|-----------|
| 向量库（Chromadb） | Docker volume `chroma_data` | `/app/chroma_data/v1` |
| Mod 源码（只读） | `../好mod全部代码供观看/` | `/mod_source/` |
| 配置文件 | `./config.json` | `/app/config.json` |
| API Key | `./.env` | `/app/.env`（由 env_file 注入） |

Docker volume 的物理位置（Windows）：`\\wsl$\docker-desktop-data\data\docker\volumes\`，一般不需要手动碰。

---

## 常见问题

### 看到 0 文档

新部署的 Docker volume 是空的，需要运行入库脚本（见上方「入库操作」）。

### 修改 config.json 后不生效

聊天端和管理端在启动时读取配置，修改后重启容器：

```bash
docker compose restart chat
```

### 端口被占用

```bash
netstat -ano | findstr 8000    # 看谁占了 8000
netstat -ano | findstr 8501    # 看谁占了 8501
```

### GPU 在容器内不可用

```bash
docker exec -it rag-chat python -c "import torch; print(torch.cuda.is_available())"
```

如果输出 `False`：打开 Docker Desktop → Settings → Resources → WSL Integration → 确保已启用。

如果仍不可用：在 `docker-compose.yml` 的 chat 服务下注释掉 `deploy.resources.reservations.devices` 段，切换到 CPU Embedding（会慢但能跑）。

### 查看容器用了多少磁盘

```bash
docker system df
```
