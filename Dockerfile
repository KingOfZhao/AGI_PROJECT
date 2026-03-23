# AGI v13.3 Cognitive Lattice - Multi-stage Docker Build
# 对应维度43: Docker容器化配置生成

# ==================== Stage 1: Builder ====================
FROM python:3.12-slim AS builder

WORKDIR /build

# 系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Python依赖安装(利用Docker层缓存)
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ==================== Stage 2: Runtime ====================
FROM python:3.12-slim AS runtime

LABEL maintainer="AGI v13.3 Cognitive Lattice"
LABEL version="13.3"
LABEL description="Multi-model collaborative coding AGI system"

WORKDIR /app

# 从builder阶段复制已安装的Python包
COPY --from=builder /install /usr/local

# 安全: 创建非root用户
RUN groupadd -r agi && useradd -r -g agi -d /app -s /sbin/nologin agi

# 复制应用代码
COPY --chown=agi:agi . .

# 创建必要目录
RUN mkdir -p /app/workspace/skills /app/workspace/outputs /app/workspace/logs \
    /app/logs /app/data \
    && chown -R agi:agi /app

# 环境变量(外部化配置 - 12-Factor App)
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    AGI_ENV=production \
    AGI_DB_PATH=/app/data/memory.db \
    AGI_LOG_LEVEL=INFO \
    AGI_API_PORT=5000 \
    AGI_API_HOST=0.0.0.0 \
    ZHIPU_API_KEY="" \
    OLLAMA_HOST=host.docker.internal:11434

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/api/health')" || exit 1

# 暴露端口
EXPOSE 5000

# 切换到非root用户
USER agi

# 启动命令
CMD ["python", "api_server.py"]
