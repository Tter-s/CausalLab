"""CausaLab FastAPI 主入口。启动时自动执行 Alembic 迁移（对 SQLite 亦适用）。"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import BASE_DIR, settings
from app.services.ai import AIError

logger = logging.getLogger("causalab")


def _run_migrations() -> None:
    """启动时升级数据库到最新迁移。失败时回退 create_all（并记录告警）。"""
    try:
        from alembic.config import Config

        from alembic import command

        ini = BASE_DIR / "alembic.ini"
        cfg = Config(str(ini))
        cfg.set_main_option("script_location", str(BASE_DIR / "alembic"))
        cfg.set_main_option("sqlalchemy.url", settings.database_url)
        command.upgrade(cfg, "head")
        logger.info("Alembic migration finished.")
    except Exception:  # noqa: BLE001 — 迁移失败时兜底建表，保证应用可用
        logger.exception("Alembic migration failed, falling back to create_all()")
        from app.db import engine
        from app.models import Base

        Base.metadata.create_all(engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    _run_migrations()
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="CausaLab API",
        version=settings.app_version,
        description="个人学习、决策与行动实验室 —— 后端 API。开发环境下访问 /docs 查看交互式文档。",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    from app.api import ai, cross, data, dtm, kd, ml, ta
    from app.api import settings as settings_api

    app.include_router(kd.router, prefix="/api")
    app.include_router(ml.router, prefix="/api")
    app.include_router(dtm.router, prefix="/api")
    app.include_router(ta.router, prefix="/api")
    app.include_router(cross.router, prefix="/api")
    app.include_router(settings_api.router, prefix="/api")
    app.include_router(ai.router, prefix="/api")
    app.include_router(data.router, prefix="/api")

    @app.get("/api/health", tags=["meta"])
    def health():
        return {"status": "ok", "app": settings.app_name, "version": settings.app_version}

    @app.exception_handler(AIError)
    async def ai_error_handler(request: Request, exc: AIError):
        from app.api.deps import ai_error_to_http

        return JSONResponse(status_code=ai_error_to_http(exc).status_code, content=ai_error_to_http(exc).detail)

    return app


app = create_app()
