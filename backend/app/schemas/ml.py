"""Memory Laboratory Schemas。"""
from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.enums import MLExperimentStatus, MLMetric, MLRating, UTCDateTime
from app.schemas.kd import ORMModel


class DeckIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = ""


class DeckOut(ORMModel):
    id: int
    name: str
    description: str
    created_at: UTCDateTime


class CardIn(BaseModel):
    deck_id: int
    front: str = Field(min_length=1)
    back: str = ""
    tags: list[str] = []


class CardUpdateIn(BaseModel):
    front: str | None = None
    back: str | None = None
    tags: list[str] | None = None
    suspended: bool | None = None


class CardOut(ORMModel):
    id: int
    deck_id: int
    front: str
    back: str
    tags: list[str]
    suspended: bool
    created_at: UTCDateTime


class CardWithStateOut(CardOut):
    state: ReviewStateOut | None = None


class ReviewStateOut(ORMModel):
    card_id: int
    stability: float
    difficulty: float
    due_at: UTCDateTime
    last_review_at: UTCDateTime
    reps: int
    lapses: int
    state_str: str
    retrievability: float | None = None
    # 学习/重学步骤细分：step 为 0 起始索引（Review 状态为 None）；
    # steps_minutes 为该状态下全部步骤时长（分钟），如 [1.0, 10.0]
    step: int | None = None
    steps_minutes: list[float] | None = None


class ReviewIn(BaseModel):
    card_id: int
    rating: MLRating
    duration_ms: int = Field(default=0, ge=0)
    # 纯回忆用时（题目显示→首次揭晓）；无则实验指标回退 duration_ms
    recall_ms: int | None = Field(default=None, ge=0)


class ReviewResultOut(BaseModel):
    card_id: int
    rating: int
    due_at: UTCDateTime
    interval_display: str
    state: ReviewStateOut


class ReviewLogOut(ORMModel):
    id: int
    card_id: int
    rating: int
    reviewed_at: UTCDateTime
    duration_ms: int
    recall_ms: int | None = None
    scheduled_days: float | None
    elapsed_days: float | None
    experiment_id: int | None
    group_tag: str | None


class DueQueueOut(BaseModel):
    cards: list[CardWithStateOut]
    total_due: int


class StepBucket(BaseModel):
    """学习/重学步骤细分：处于某步骤的卡片数。"""

    state: str  # learning | relearning
    step: int  # 1 起始（展示用）
    minutes: float  # 该步骤时长
    count: int


class MLStatsOut(BaseModel):
    total_cards: int
    due_now: int
    reviews_last_7d: int
    retention_7d: float | None  # 近7天 good/easy 占比
    again_rate_7d: float | None
    reviews_per_day: list[DayCount]
    interval_distribution: list[IntervalBucket]
    maturity: dict[str, int]  # new/learning/relearning/review 计数
    step_breakdown: list[StepBucket] = []


class DayCount(BaseModel):
    date: str
    count: int


class IntervalBucket(BaseModel):
    label: str
    count: int


# ---------- 实验 ----------
class ExperimentIn(BaseModel):
    question: str = Field(min_length=1)
    strategy_a: str = Field(min_length=1)
    strategy_b: str = Field(min_length=1)
    metric: MLMetric = "retention"
    delayed_test_days: int = Field(default=7, ge=1, le=365)
    notes: str = ""


class ExperimentUpdateIn(BaseModel):
    status: MLExperimentStatus | None = None
    notes: str | None = None


class ExperimentOut(ORMModel):
    id: int
    question: str
    strategy_a: str
    strategy_b: str
    metric: MLMetric
    status: MLExperimentStatus
    started_at: UTCDateTime
    ends_at: UTCDateTime
    delayed_test_days: int
    notes: str
    created_at: UTCDateTime


class AssignIn(BaseModel):
    card_ids: list[int] = Field(min_length=2)


class GroupResult(BaseModel):
    name: str
    strategy: str
    n_cards: int
    n_reviews: int
    again_rate: float | None
    mean_duration_ms: float | None
    # 纯回忆用时中位数（显示→揭晓，剔除 200ms 以下与 5 分钟以上的异常值）
    median_recall_ms: float | None = None
    recall_samples: int = 0
    delayed_test_pass_rate: float | None


class ExperimentResultsOut(BaseModel):
    experiment_id: int
    groups: list[GroupResult]
    difference_note: str | None
    disclaimer: str
