# 仅后端镜像（本机 Docker 不可用，此文件未在本机验证 —— 见 README「未在本机验证」清单）
FROM python:3.12-slim

WORKDIR /app

# 系统依赖保持最小；psycopg 仅在连接 PostgreSQL 时需要
COPY pyproject.toml uv.lock ./
RUN pip install --no-cache-dir uv && uv sync --frozen --no-dev

COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./

ENV CAUSALAB_DATA_DIR=/app/data
EXPOSE 8000

# 启动时自动执行 Alembic 迁移（app.main 的 lifespan 内完成）
CMD ["uv", "run", "--no-dev", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
