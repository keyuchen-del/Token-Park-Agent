# syntax=docker/dockerfile:1.7

# 多阶段构建，最终镜像只含运行时依赖
# Base: Python 3.13 slim + uv（10x 快于 pip）
FROM python:3.13-slim AS base

# 装 uv（官方静态二进制，避免再装 pip）
COPY --from=ghcr.io/astral-sh/uv:0.5.21 /uv /usr/local/bin/uv

# 系统依赖：Pillow 需要 libjpeg / zlib，curl 用于 healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    libjpeg-dev \
    zlib1g-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ============================================================
# Builder: 装依赖到 /app/.venv
# ============================================================
FROM base AS builder

# uv 设置：开启 bytecode 编译，加速冷启
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv

# 先装依赖（利用 Docker layer 缓存）
COPY backend/pyproject.toml backend/uv.lock /app/backend/
WORKDIR /app/backend
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

# 再 copy 源码 + 重装项目本身
COPY backend/src /app/backend/src
COPY backend/tests /app/backend/tests
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# ============================================================
# Runtime: 最小镜像
# ============================================================
FROM base AS runtime

# 不用 root 运行
RUN useradd --create-home --shell /bin/bash tpagent

# 拷贝已构建好的 venv
COPY --from=builder --chown=tpagent:tpagent /app/.venv /app/.venv
COPY --from=builder --chown=tpagent:tpagent /app/backend /app/backend

# 拷贝配置目录（部署时也可以 mount volume 覆盖）
COPY --chown=tpagent:tpagent config /app/config

# 让 uvicorn 等命令进 PATH
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    CONFIG_DIR=/app/config \
    DATA_DIR=/app/data \
    SESSIONS_DIR=/app/sessions \
    DB_PATH=/app/data/tpagent.db

USER tpagent
WORKDIR /app/backend

# 确保运行时目录存在
RUN mkdir -p /app/data /app/sessions

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -fsS http://localhost:8000/health || exit 1

CMD ["uvicorn", "tpagent.main:app", "--host", "0.0.0.0", "--port", "8000"]
