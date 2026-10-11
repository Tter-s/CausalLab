"""Decision Time Machine Schemas。"""
from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.enums import DTMStatus, Significance, UTCDateTime
from app.schemas.kd import ORMModel


class DecisionOption(BaseModel):
    key: str
    label: str
    description: str = ""


class DecisionIn(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    context: str = ""
    goals: str = ""
    options: list[DecisionOption] = []
    basis: str = ""
    risks: str = ""
    review_at: UTCDateTime = None  # type: ignore[assignment]


class DecisionUpdateIn(BaseModel):
    title: str | None = None
    context: str | None = None
    goals: str | None = None
    options: list[DecisionOption] | None = None
    basis: str | None = None
    risks: str | None = None
    review_at: UTCDateTime = None  # type: ignore[assignment]
    status: DTMStatus | None = None


class DecisionOut(ORMModel):
    id: int
    title: str
    context: str
    goals: str
    options: list[DecisionOption]
    basis: str
    risks: str
    status: DTMStatus
    review_at: UTCDateTime
    reviewed_at: UTCDateTime
    created_at: UTCDateTime
    updated_at: UTCDateTime


class DecisionDetailOut(DecisionOut):
    predictions: list[PredictionOut] = []
    updates: list[DecisionUpdateOut] = []
    reviews: list[DecisionReviewOut] = []
    counterfactuals: list[CounterfactualOut] = []
    snapshots: list[SnapshotOut] = []


class SnapshotOut(ORMModel):
    id: int
    decision_id: int
    reason: str
    payload: dict
    snapshot_at: UTCDateTime


class PredictionIn(BaseModel):
    statement: str = Field(min_length=1)
    option_key: str | None = None
    probability: float = Field(ge=0, le=1)


class PredictionResolveIn(BaseModel):
    resolved: bool
    actual_note: str = ""


class PredictionOut(ORMModel):
    id: int
    decision_id: int
    statement: str
    option_key: str | None
    probability: float
    resolved: bool | None
    actual_note: str | None
    resolved_at: UTCDateTime
    created_at: UTCDateTime


class DecisionUpdateRecordIn(BaseModel):
    content: str = Field(min_length=1)
    source: str = ""
    significance: Significance = "minor"
    occurred_at: UTCDateTime = None  # type: ignore[assignment]


class DecisionUpdateOut(ORMModel):
    id: int
    decision_id: int
    content: str
    source: str
    significance: Significance
    occurred_at: UTCDateTime
    created_at: UTCDateTime


class DecisionReviewIn(BaseModel):
    summary: str = Field(min_length=1)
    process_score: int | None = Field(default=None, ge=1, le=5)
    lessons: list[str] = []
    bias_flags: list[str] = []


class DecisionReviewOut(ORMModel):
    id: int
    decision_id: int
    summary: str
    process_score: int | None
    lessons: list[str]
    bias_flags: list[str]
    source: str
    reviewed_at: UTCDateTime


class CounterfactualIn(BaseModel):
    scenario: str = Field(min_length=1)
    analysis: str = ""


class CounterfactualOut(ORMModel):
    id: int
    decision_id: int
    scenario: str
    analysis: str
    is_hypothetical: bool
    source: str
    created_at: UTCDateTime


class CalibrationBin(BaseModel):
    label: str
    lower: float
    upper: float
    n: int
    avg_predicted: float
    actual_rate: float


class CalibrationOut(BaseModel):
    n_predictions: int
    brier_score: float
    bins: list[CalibrationBin]
    caveat: str
