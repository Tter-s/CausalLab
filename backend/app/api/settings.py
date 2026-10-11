"""设置 API：AI 配置（Key 掩码返回）、AI 状态、用量统计。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models import AIUsageLog
from app.schemas.cross import AIConfigIn, AIConfigOut, AIStatusOut, UsageRow, UsageSummaryOut
from app.services.ai import (
    get_ai_config,
    get_provider,
    mask_config,
    month_cost_so_far,
    save_ai_config,
)
from app.services.ai.base import AINotConfigured, AIRequest
from app.services.base import utcnow

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("/ai", response_model=AIConfigOut)
def read_ai_config(db: Session = Depends(get_db)):
    return mask_config(get_ai_config(db))


@router.put("/ai", response_model=AIConfigOut)
def update_ai_config(payload: AIConfigIn, db: Session = Depends(get_db)):
    if payload.provider not in ("none", "deepseek", "mimo", "moonshot", "openai-compat", "mock"):
        raise HTTPException(status_code=422, detail="不支持的 provider 类型")
    out = save_ai_config(db, payload)
    db.commit()
    return out


@router.get("/ai/status", response_model=AIStatusOut)
def ai_status(db: Session = Depends(get_db)):
    cfg = get_ai_config(db)
    provider = cfg.get("provider", "none")
    configured = provider not in (None, "none")
    notice = ""
    if provider == "none":
        notice = "当前为无 AI 模式：核心记录、统计、实验与可视化功能完整可用；诊断与复盘将使用内置规则分析。"
    elif provider == "mock":
        notice = "当前为演示模式：AI 输出为固定模拟数据，仅用于预览交互流程。"
    else:
        notice = "已连接云端模型。所有请求经本服务端代理，API Key 不会返回给前端。"
    try:
        get_provider(db)
        ok = configured
    except AINotConfigured:
        ok = False
        notice = "AI 配置不完整（缺少 Base URL、模型名或 API Key），分析将回退到规则模式。"
    return AIStatusOut(
        enabled=ok,
        provider=provider,
        model_id=cfg.get("model_id", ""),
        configured=ok,
        auto_confirm_send=bool(cfg.get("auto_confirm_send", False)),
        notice=notice,
    )


@router.post("/ai/test")
async def test_ai_connection(db: Session = Depends(get_db)):
    """发送一条最小请求测试连通性。不发送任何用户私人资料。"""
    try:
        provider = get_provider(db)
        resp = await provider.complete(
            AIRequest(system="You are a health check.", user="Reply with exactly: ok", task_type="general", max_tokens=8)
        )
        return {"ok": True, "provider": resp.provider, "model": resp.model, "latency_ms": resp.latency_ms}
    except Exception as exc:  # noqa: BLE001 — 连通性测试需把所有失败原因返回前端
        return {"ok": False, "error": getattr(exc, "user_message", None) or str(exc)[:300]}


@router.get("/ai/usage", response_model=UsageSummaryOut)
def ai_usage(month: str | None = None, db: Session = Depends(get_db)):
    now = utcnow()
    target = month or now.strftime("%Y-%m")
    rows = list(
        db.scalars(
            select(AIUsageLog)
            .where(AIUsageLog.created_at >= f"{target}-01")
            .order_by(AIUsageLog.created_at.desc())
            .limit(500)
        )
    )
    rows = [r for r in rows if r.created_at.strftime("%Y-%m") == target]
    return UsageSummaryOut(
        rows=[
            UsageRow(
                id=r.id,
                provider=r.provider,
                model=r.model,
                task_type=r.task_type,
                prompt_tokens=r.prompt_tokens,
                completion_tokens=r.completion_tokens,
                cost_estimated=r.cost_estimated,
                latency_ms=r.latency_ms,
                ok=r.ok,
                error=r.error,
                created_at=r.created_at,
            )
            for r in rows
        ],
        total_calls=len(rows),
        total_prompt_tokens=sum(r.prompt_tokens for r in rows),
        total_completion_tokens=sum(r.completion_tokens for r in rows),
        total_cost=round(sum(r.cost_estimated for r in rows), 4),
        month=target,
    )


@router.get("/budget")
def budget_status(db: Session = Depends(get_db)):
    cfg = get_ai_config(db)
    spent = month_cost_so_far(db)
    return {
        "monthly_budget": float(cfg.get("monthly_budget") or 0),
        "spent_this_month": round(spent, 4),
        "remaining": round(max(0.0, float(cfg.get("monthly_budget") or 0) - spent), 4),
        "price_prompt_per_m": cfg.get("price_prompt_per_m"),
        "price_completion_per_m": cfg.get("price_completion_per_m"),
        "currency": "CNY（估算）",
    }


from app.schemas.enums import UTCDateTime  # noqa: E402  (re-export for typing users)

__all__ = ["router", "UTCDateTime"]
