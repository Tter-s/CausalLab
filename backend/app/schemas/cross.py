"""跨模块 Schemas：事件 / 证据 / 链接 / 假设 / 循环 / 搜索 / 仪表盘 / AI 设置。"""
from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field

from app.schemas.enums import (
    EvidenceKind,
    HypStatus,
    LinkRelation,
    LoopStageName,
    LoopVerdict,
    Module,
    UTCDateTime,
)
from app.schemas.kd import ORMModel


# ---------- 事件 ----------
class EventOut(ORMModel):
    id: int
    module: Module
    event_type: str
    ref_type: str
    ref_id: int
    title: str
    detail: dict
    importance: int
    occurred_at: UTCDateTime


class EventPage(BaseModel):
    items: list[EventOut]
    total: int


# ---------- 证据 ----------
class EvidenceIn(BaseModel):
    module: Module
    ref_type: str
    ref_id: int
    kind: EvidenceKind
    content: str = Field(min_length=1)
    source: str = ""
    confidence: float | None = Field(default=None, ge=0, le=1)


class EvidenceOut(ORMModel):
    id: int
    module: Module
    ref_type: str
    ref_id: int
    event_id: int | None
    kind: EvidenceKind
    content: str
    source: str
    confidence: float | None
    created_at: UTCDateTime


# ---------- 链接 ----------
class LinkIn(BaseModel):
    from_module: Module
    from_ref_type: str
    from_ref_id: int
    to_module: Module
    to_ref_type: str
    to_ref_id: int
    relation: LinkRelation = "associated_with"
    note: str = ""


class LinkOut(ORMModel):
    id: int
    from_module: Module
    from_ref_type: str
    from_ref_id: int
    to_module: Module
    to_ref_type: str
    to_ref_id: int
    relation: LinkRelation
    note: str
    created_at: UTCDateTime


# ---------- 假设实验室 ----------
class HypothesisIn(BaseModel):
    statement: str = Field(min_length=1)
    rationale: str = ""
    design: dict | None = None
    criteria: dict | None = None


class HypothesisUpdateIn(BaseModel):
    statement: str | None = None
    rationale: str | None = None
    design: dict | None = None
    criteria: dict | None = None
    status: HypStatus | None = None


class HypothesisOut(ORMModel):
    id: int
    statement: str
    rationale: str
    design: dict | None
    criteria: dict | None
    status: HypStatus
    created_at: UTCDateTime
    updated_at: UTCDateTime


class ObservationIn(BaseModel):
    value: float
    context: dict = {}
    note: str = ""
    observed_at: UTCDateTime = None  # type: ignore[assignment]


class ObservationOut(ORMModel):
    id: int
    hypothesis_id: int
    observed_at: UTCDateTime
    value: float
    context: dict
    note: str
    source: str


class HypothesisAnalysisOut(BaseModel):
    hypothesis_id: int
    n_observations: int
    overall_mean: float | None
    overall_std: float | None
    groups: list[GroupComparison]
    limitations: list[str]
    verdict_hint: str


class GroupComparison(BaseModel):
    label: str
    n: int
    mean: float
    std: float | None


# ---------- 改进循环 ----------
class LoopIn(BaseModel):
    title: str = Field(min_length=1)
    problem: str = ""


class LoopUpdateIn(BaseModel):
    title: str | None = None
    problem: str | None = None
    current_stage: LoopStageName | None = None
    intervention: str | None = None
    outcome_note: str | None = None
    hypothesis_id: int | None = None
    status: str | None = None
    verdict: LoopVerdict | None = None


class LoopOut(ORMModel):
    id: int
    title: str
    problem: str
    status: str
    current_stage: LoopStageName
    hypothesis_id: int | None
    intervention: str
    outcome_note: str
    verdict: LoopVerdict | None
    created_at: UTCDateTime
    updated_at: UTCDateTime


class LoopStageIn(BaseModel):
    stage: LoopStageName
    content: dict = {}


class LoopStageOut(ORMModel):
    id: int
    loop_id: int
    stage: LoopStageName
    content: dict
    entered_at: UTCDateTime


# ---------- 搜索 ----------
class SearchHit(BaseModel):
    module: Module
    ref_type: str
    ref_id: int
    title: str
    snippet: str = ""


class SearchOut(BaseModel):
    query: str
    groups: dict[str, list[SearchHit]]
    total: int


# ---------- 仪表盘 ----------
class DashboardOut(BaseModel):
    today: date
    stats: dict[str, int]
    due_decision_reviews: list[EventOut]
    recent_events: list[EventOut]
    charts: dict[str, list[DayCount]]
    demo_mode: bool


class DayCount(BaseModel):
    date: str
    count: int


# ---------- AI 设置 ----------
class AITaskModelConfig(BaseModel):
    """按任务类型的模型覆盖（简单任务可用低成本模型）。"""

    task_type: str = "general"
    model_id: str | None = None
    temperature: float | None = Field(default=None, ge=0, le=2)


class AIConfigIn(BaseModel):
    provider: str = "none"
    base_url: str = ""
    api_key: str | None = None  # None 表示保持原值
    model_id: str = ""
    temperature: float | None = Field(default=None, ge=0, le=2)
    max_tokens: int = Field(default=2048, ge=64, le=65536)
    timeout_seconds: float = Field(default=60, ge=5, le=600)
    monthly_budget: float = Field(default=0, ge=0)
    auto_confirm_send: bool = False
    task_models: list[AITaskModelConfig] = []
    price_prompt_per_m: float = Field(default=2.0, ge=0)  # 每百万 prompt token 价格（元）
    price_completion_per_m: float = Field(default=8.0, ge=0)


class AIConfigOut(BaseModel):
    provider: str
    base_url: str
    api_key_masked: str
    model_id: str
    temperature: float | None
    max_tokens: int
    timeout_seconds: float
    monthly_budget: float
    auto_confirm_send: bool
    task_models: list[AITaskModelConfig]
    price_prompt_per_m: float
    price_completion_per_m: float
    configured: bool


class AIStatusOut(BaseModel):
    enabled: bool
    provider: str
    model_id: str
    configured: bool
    auto_confirm_send: bool
    notice: str


class AIPreviewOut(BaseModel):
    """确认发送前的内容预览（428 响应体）。"""

    code: str = "ai_confirm_required"
    message: str
    provider: str
    model_id: str
    payload_preview: str


class UsageRow(BaseModel):
    id: int
    provider: str
    model: str
    task_type: str
    prompt_tokens: int
    completion_tokens: int
    cost_estimated: float
    latency_ms: int
    ok: bool
    error: str | None
    created_at: UTCDateTime


class UsageSummaryOut(BaseModel):
    rows: list[UsageRow]
    total_calls: int
    total_prompt_tokens: int
    total_completion_tokens: int
    total_cost: float
    month: str
