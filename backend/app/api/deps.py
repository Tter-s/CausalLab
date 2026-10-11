"""公共依赖与异常处理。"""
from __future__ import annotations

from collections.abc import Iterator

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.db import get_db as _get_db
from app.services.ai import (
    AIBudgetExceeded,
    AIConfirmRequired,
    AIError,
    AINotConfigured,
    AIResponseInvalid,
    AIUpstreamError,
)


def get_db() -> Iterator[Session]:
    yield from _get_db()


def ai_error_to_http(exc: AIError) -> HTTPException:
    """把 AI 异常映射为对前端友好的 HTTP 错误。"""
    if isinstance(exc, AIConfirmRequired):
        return HTTPException(
            status_code=428,
            detail={
                "code": "ai_confirm_required",
                "message": "向云端模型发送内容前需要你的确认",
                "provider": exc.provider,
                "model_id": exc.model_id,
                "payload_preview": exc.payload_preview,
            },
        )
    if isinstance(exc, AINotConfigured):
        return HTTPException(status_code=409, detail={"code": "ai_not_configured", "message": exc.user_message})
    if isinstance(exc, AIBudgetExceeded):
        return HTTPException(status_code=402, detail={"code": "ai_budget_exceeded", "message": exc.user_message})
    if isinstance(exc, AIResponseInvalid):
        return HTTPException(status_code=502, detail={"code": "ai_response_invalid", "message": exc.user_message})
    if isinstance(exc, AIUpstreamError):
        return HTTPException(status_code=502, detail={"code": "ai_upstream_error", "message": exc.user_message})
    return HTTPException(status_code=500, detail={"code": "ai_error", "message": exc.user_message})


__all__ = ["get_db", "ai_error_to_http"]
