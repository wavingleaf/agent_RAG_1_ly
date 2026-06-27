# agent_RAG_1_ly Docker 镜像
# 基于支持 CUDA 的 Python 镜像（GPU Embedding 推理需要）
# 若无需 GPU，将镜像改为 python:3.10-slim 即可
FROM pytorch/pytorch:2.6.0-cuda12.4-cudnn9-runtime

# 避免交互式安装（如 tzdata）卡住构建
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# 先装系统级依赖（ChromaDB 的 Rust 后端需要）
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 先复制依赖文件（利用 Docker 缓存层：依赖没变就不用重装）
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目文件
COPY . .

# ChromaDB 持久化目录（通过 volume 挂载到宿主机）
VOLUME ["/app/chroma_data"]

# 默认暴露两个端口：
# 8000 — Chainlit 聊天端
# 8501 — Streamlit 管理面板
EXPOSE 8000 8501

# 默认启动命令（可被 docker-compose 覆盖）
CMD ["sh", "-c", "python 启动rag助手.py & python 启动管理面板.py & wait"]
