"""Alembic 迁移环境：元数据来自 app.models，连接串优先取环境变量 CAUSALAB_DB_URL。"""
from __future__ import annotations

import sys
from pathlib import Path

# 保证可从仓库任意位置运行 alembic
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from alembic import context  # noqa: E402
from sqlalchemy import pool  # noqa: E402

from app.config import settings  # noqa: E402
from app.models import Base  # noqa: E402
from app.models.base import utcnow  # noqa: E402,F401  (确保 default 可序列化)

config = context.config
target_metadata = Base.metadata


def _db_url() -> str:
    return settings.database_url


def run_migrations_offline() -> None:
    context.configure(
        url=_db_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,  # SQLite 变更表结构需要 batch 模式
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    from sqlalchemy import engine_from_config

    cfg = config.get_section(config.config_ini_section, {})
    cfg["sqlalchemy.url"] = _db_url()

    connectable = engine_from_config(
        cfg,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
