"""AI 配置存储、Provider 工厂、结构化调用与预算/用量管理。

隐私默认策略：不自动向第三方云端模型发送私人资料；需要发送的内容必须经用户确认
（confirm_send=True），确认内容以 payload_preview 形式返回给前端展示。
"""
from __future__ import annotations

import json
from datetime import datetime

from pydantic import BaseModel, ValidationError
from sqlalchemy.orm import Session

from app.models import AIUsageLog, Setting
from app.models.base import utcnow
from app.schemas.cross import AIConfigIn, AIConfigOut, AITaskModelConfig
from app.services.ai.base import (
    AIBudgetExceeded,
    AIConfirmRequired,
    AIError,
    AINotConfigured,
    AIProvider,
    AIRequest,
    AIResponse,
    AIResponseInvalid,
)
from app.services.ai.mock import MockProvider
from app.services.ai.openai_compat import OpenAICompatProvider
from app.services.crypto import decrypt_secret, encrypt_secret, mask_secret

AI_CONFIG_KEY = "ai_config"

_DEFAULTS = {
    "provider": "none",
    "base_url": "",
    "api_key_encrypted": "",
    "model_id": "",
    "temperature": 0.4,
    "max_tokens": 2048,
    "timeout_seconds": 60,
    "monthly_budget": 20.0,
    "auto_confirm_send": False,
    "task_models": [],
    "price_prompt_per_m": 2.0,
    "price_completion_per_m": 8.0,
}




def _load_raw(db: Session) -> dict:
    row = db.get(Setting, AI_CONFIG_KEY)
    data = dict(_DEFAULTS)
    if row and isinstance(row.value, dict):
        data.update(row.value)
    return data


def get_ai_config(db: Session) -> dict:
    return _load_raw(db)


def save_ai_config(db: Session, patch: AIConfigIn) -> AIConfigOut:
    data = _load_raw(db)
    data["provider"] = patch.provider
    data["base_url"] = patch.base_url.strip()
    if patch.api_key is not None and patch.api_key != "":
        data["api_key_encrypted"] = encrypt_secret(patch.api_key)
    data["model_id"] = patch.model_id.strip()
    data["temperature"] = patch.temperature
    data["max_tokens"] = patch.max_tokens
    data["timeout_seconds"] = patch.timeout_seconds
    data["monthly_budget"] = patch.monthly_budget
    data["auto_confirm_send"] = patch.auto_confirm_send
    # None = 保持原值（与 api_key 同约定）；否则整体替换为客户端传来的列表
    if patch.task_models is not None:
        data["task_models"] = [tm.model_dump() for tm in patch.task_models]
    data["price_prompt_per_m"] = patch.price_prompt_per_m
    data["price_completion_per_m"] = patch.price_completion_per_m

    row = db.get(Setting, AI_CONFIG_KEY)
    if row is None:
        row = Setting(key=AI_CONFIG_KEY, value=data)
        db.add(row)
    else:
        row.value = data
    db.flush()
    return mask_config(data)


def mask_config(data: dict) -> AIConfigOut:
    key_plain = decrypt_secret(data.get("api_key_encrypted", ""))
    return AIConfigOut(
        provider=data.get("provider", "none"),
        base_url=data.get("base_url", ""),
        api_key_masked=mask_secret(key_plain),
        model_id=data.get("model_id", ""),
        temperature=data.get("temperature"),
        max_tokens=data.get("max_tokens", 2048),
        timeout_seconds=data.get("timeout_seconds", 60),
        monthly_budget=data.get("monthly_budget", 0),
        auto_confirm_send=data.get("auto_confirm_send", False),
        task_models=[AITaskModelConfig(**tm) for tm in data.get("task_models", [])],
        price_prompt_per_m=data.get("price_prompt_per_m", 2.0),
        price_completion_per_m=data.get("price_completion_per_m", 8.0),
        configured=bool(data.get("provider") not in (None, "none", "mock") and data.get("model_id")),
    )


def _provider_label(provider: str) -> str:
    return provider if provider in ("deepseek", "mimo", "moonshot") else "openai-compat"


# 各服务商的默认 Base URL（用户可覆盖；模型名一律由用户填写，不硬编码“永久有效”的版本）
KNOWN_BASE_URLS = {
    "deepseek": "https://api.deepseek.com",
    "mimo": "https://api.mimo.example.com",  # MiMo 官方地址由用户按其文档填写
    "moonshot": "https://api.moonshot.cn",
}


def get_provider(db: Session, task_type: str = "general") -> AIProvider:
    data = _load_raw(db)
    provider_kind = data.get("provider", "none")

    # 按任务类型选择模型：简单任务优先用低成本模型
    model_id = data.get("model_id", "")
    temperature = data.get("temperature")
    for tm in data.get("task_models", []):
        if tm.get("task_type") == task_type and tm.get("model_id"):
            model_id = tm["model_id"]
            if tm.get("temperature") is not None:
                temperature = tm["temperature"]
            break

    if provider_kind == "none":
        raise AINotConfigured()
    if provider_kind == "mock":
        return MockProvider()

    api_key = decrypt_secret(data.get("api_key_encrypted", ""))
    base_url = data.get("base_url", "") or KNOWN_BASE_URLS.get(provider_kind, "")
    if not model_id or not base_url:
        raise AINotConfigured()
    if provider_kind in ("deepseek", "moonshot") and not api_key:
        raise AINotConfigured()

    return OpenAICompatProvider(
        base_url=base_url,
        api_key=api_key,
        model=model_id,
        timeout=float(data.get("timeout_seconds", 60)),
        temperature=temperature,
        max_tokens=int(data.get("max_tokens", 2048)),
        label=_provider_label(provider_kind),
    )


def month_cost_so_far(db: Session, now: datetime | None = None) -> float:
    now = now or utcnow()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    rows = db.query(AIUsageLog.cost_estimated).filter(
        AIUsageLog.created_at >= month_start, AIUsageLog.ok.is_(True)
    )
    return float(sum(r[0] or 0 for r in rows))


def estimate_cost(
    prompt_tokens: int, completion_tokens: int, price_prompt_per_m: float, price_completion_per_m: float
) -> float:
    return round(
        prompt_tokens / 1_000_000 * price_prompt_per_m + completion_tokens / 1_000_000 * price_completion_per_m,
        6,
    )


def _log_usage(db: Session, resp_or_error: AIResponse | str, task_type: str, ok: bool, cfg: dict) -> None:
    err = None if ok else str(resp_or_error)[:500]
    resp = resp_or_error if isinstance(resp_or_error, AIResponse) else None
    db.add(
        AIUsageLog(
            provider=resp.provider if resp else "unknown",
            model=resp.model if resp else "-",
            task_type=task_type,
            prompt_tokens=resp.prompt_tokens if resp else 0,
            completion_tokens=resp.completion_tokens if resp else 0,
            cost_estimated=(
                estimate_cost(
                    resp.prompt_tokens,
                    resp.completion_tokens,
                    cfg.get("price_prompt_per_m", 2.0),
                    cfg.get("price_completion_per_m", 8.0),
                )
                if resp
                else 0.0
            ),
            latency_ms=resp.latency_ms if resp else 0,
            ok=ok,
            error=err,
        )
    )
    db.flush()


JSON_INSTRUCTION = (
    "请只输出一个 JSON 对象，不要输出任何解释、前后缀或 Markdown 代码块标记。"
    "JSON 必须符合给定的字段结构。"
)


async def run_structured[T: BaseModel](
    db: Session,
    *,
    task_type: str,
    system: str,
    user: str,
    schema: type[T],
    confirm_send: bool = False,
) -> tuple[T, AIResponse]:
    """执行一次结构化 AI 调用：隐私确认 → 预算检查 → 调用 → 用量记录 → JSON 解析与校验（含一次修复重试）。

    AI 输出永远不直接写库；由调用方拿校验后的对象走正常服务函数。
    """
    cfg = _load_raw(db)
    if cfg.get("provider", "none") == "none":
        raise AINotConfigured()

    # 隐私闸门：默认需要用户确认发送内容
    if not confirm_send and not cfg.get("auto_confirm_send", False):
        provider = get_provider(db, task_type)
        raise AIConfirmRequired(payload_preview=user, provider=provider.provider_id, model_id=cfg.get("model_id", ""))

    # 预算检查（mock 不计费，直接放行）
    budget = float(cfg.get("monthly_budget") or 0)
    if budget > 0 and cfg.get("provider") != "mock":
        spent = month_cost_so_far(db)
        if spent >= budget:
            raise AIBudgetExceeded()

    provider = get_provider(db, task_type)
    schema_json = json.dumps(schema.model_json_schema(), ensure_ascii=False)
    request = AIRequest(
        system=f"{system}\n\n{JSON_INSTRUCTION}\n字段结构（JSON Schema）：{schema_json}",
        user=user,
        task_type=task_type,
        temperature=None,
        max_tokens=None,
    )

    try:
        resp = await provider.complete(request)
    except AIError as exc:
        _log_usage(db, getattr(exc, "user_message", str(exc)), task_type, ok=False, cfg=cfg)
        db.commit()
        raise

    _log_usage(db, resp, task_type, ok=True, cfg=cfg)
    db.commit()

    parsed = _parse_and_validate(resp.text, schema)
    if parsed is None:
        # 一次修复重试：把错误反馈给模型要求重新输出
        retry_req = AIRequest(
            system=request.system,
            user=(f"{request.user}\n\n你上一次的输出无法解析为符合结构的 JSON。"
                  f"上次输出（截断）：{resp.text[:800]}\n请重新只输出符合要求的 JSON 对象。"),
            task_type=task_type,
        )
        resp2 = await provider.complete(retry_req)
        _log_usage(db, resp2, task_type, ok=True, cfg=cfg)
        db.commit()
        parsed = _parse_and_validate(resp2.text, schema)
        if parsed is None:
            raise AIResponseInvalid()

    return parsed, resp


def _parse_and_validate[T: BaseModel](text: str, schema: type[T]) -> T | None:
    if not text or not text.strip():
        return None
    cleaned = _strip_json(text)
    try:
        obj = json.loads(cleaned)
        return schema.model_validate(obj)
    except (json.JSONDecodeError, ValidationError):
        return None


def _strip_json(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        t = t.strip("`")
        if t.lower().startswith("json"):
            t = t[4:]
    start = t.find("{")
    end = t.rfind("}")
    if start >= 0 and end > start:
        t = t[start : end + 1]
    return t
