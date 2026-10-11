"""Task Autopsy Schemas。"""
from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.enums import (
    ImprovementStatus,
    TAProjectStatus,
    TATaskEventType,
    TATaskStatus,
    UTCDateTime,
)
from app.schemas.kd import ORMModel


class ProjectIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = ""
    deadline: UTCDateTime = None  # type: ignore[assignment]


class ProjectUpdateIn(BaseModel):
    name: str | None = None
    description: str | None = None
    status: TAProjectStatus | None = None
    deadline: UTCDateTime = None  # type: ignore[assignment]


class ProjectOut(ORMModel):
    id: int
    name: str
    description: str
    status: TAProjectStatus
    started_at: UTCDateTime
    deadline: UTCDateTime
    created_at: UTCDateTime
    updated_at: UTCDateTime


class TaskIn(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    description: str = ""
    parent_id: int | None = None
    estimated_hours: float | None = Field(default=None, ge=0)
    due_at: UTCDateTime = None  # type: ignore[assignment]
    depends_on: list[int] = []


class TaskUpdateIn(BaseModel):
    title: str | None = None
    description: str | None = None
    status: TATaskStatus | None = None
    estimated_hours: float | None = Field(default=None, ge=0)
    actual_hours: float | None = Field(default=None, ge=0)
    due_at: UTCDateTime = None  # type: ignore[assignment]


class TaskOut(ORMModel):
    id: int
    project_id: int
    parent_id: int | None
    title: str
    description: str
    status: TATaskStatus
    estimated_hours: float | None
    actual_hours: float | None
    started_at: UTCDateTime
    finished_at: UTCDateTime
    due_at: UTCDateTime
    created_at: UTCDateTime
    updated_at: UTCDateTime


class TaskDepIn(BaseModel):
    depends_on_task_id: int


class TaskDepOut(ORMModel):
    id: int
    task_id: int
    depends_on_task_id: int


class TaskEventIn(BaseModel):
    type: TATaskEventType
    description: str = ""
    duration_minutes: float | None = Field(default=None, ge=0)
    occurred_at: UTCDateTime = None  # type: ignore[assignment]


class TaskEventOut(ORMModel):
    id: int
    task_id: int
    type: TATaskEventType
    description: str
    duration_minutes: float | None
    occurred_at: UTCDateTime
    created_at: UTCDateTime


class ProjectStatsOut(BaseModel):
    project_id: int
    tasks_total: int
    tasks_done: int
    tasks_blocked: int
    tasks_cancelled: int
    total_estimated_hours: float
    total_actual_hours: float
    avg_overrun_ratio: float | None  # done 且有预估的任务的平均实际/预估
    blocked_minutes_total: float
    rework_count: int
    interrupted_count: int
    requirement_change_count: int
    per_task: list[TaskStatRow]
    event_type_counts: dict[str, int]


class TaskStatRow(BaseModel):
    task_id: int
    title: str
    status: str
    estimated_hours: float | None
    actual_hours: float | None
    overrun_ratio: float | None
    blocked_minutes: float
    rework_count: int


class ReviewSection(BaseModel):
    items: list[str]


class ProjectReviewIn(BaseModel):
    summary: str
    facts: list[str] = []
    speculations: list[str] = []
    missing_evidence: list[str] = []
    improvements: list[str] = []


class ProjectReviewOut(ORMModel):
    id: int
    project_id: int
    summary: str
    facts: list[str]
    speculations: list[str]
    missing_evidence: list[str]
    improvements: list[str]
    source: str
    created_at: UTCDateTime


class ImprovementIn(BaseModel):
    action: str = Field(min_length=1)
    project_id: int | None = None
    review_id: int | None = None
    status: ImprovementStatus = "proposed"


class ImprovementUpdateIn(BaseModel):
    status: ImprovementStatus | None = None
    followup_note: str | None = None
    effect: dict | None = None


class ImprovementOut(ORMModel):
    id: int
    project_id: int | None
    review_id: int | None
    action: str
    status: ImprovementStatus
    followup_note: str
    effect: dict | None
    created_at: UTCDateTime
    updated_at: UTCDateTime
