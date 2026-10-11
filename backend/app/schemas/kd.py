"""Knowledge Debt Schemas。"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.enums import (
    KDDiagCategory,
    KDDiagStatus,
    KDSource,
    UTCDateTime,
)


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------- Subject ----------
class SubjectIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = ""
    color: str = "#6366f1"


class SubjectOut(ORMModel):
    id: int
    name: str
    description: str
    color: str
    created_at: UTCDateTime
    updated_at: UTCDateTime


# ---------- Topic ----------
class TopicIn(BaseModel):
    subject_id: int
    name: str = Field(min_length=1, max_length=200)
    description: str = ""
    status: str = "normal"


class TopicUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    status: str | None = None


class TopicOut(ORMModel):
    id: int
    subject_id: int
    name: str
    description: str
    status: str
    created_at: UTCDateTime
    updated_at: UTCDateTime


class TopicEdgeIn(BaseModel):
    from_topic_id: int
    to_topic_id: int
    relation: str = "prerequisite"
    note: str = ""


class TopicEdgeOut(ORMModel):
    id: int
    from_topic_id: int
    to_topic_id: int
    relation: str
    note: str


class GraphOut(BaseModel):
    nodes: list[TopicOut]
    edges: list[TopicEdgeOut]
    subjects: list[SubjectOut]


# ---------- StudyTask ----------
class StudyTaskIn(BaseModel):
    topic_id: int
    title: str = Field(min_length=1, max_length=300)
    question_text: str = ""
    my_answer: str = ""
    is_verification: bool = False


class StudyTaskOut(ORMModel):
    id: int
    topic_id: int
    title: str
    question_text: str
    my_answer: str
    status: str
    is_verification: bool
    source_suggestion_id: int | None
    verification_status: str | None
    created_at: UTCDateTime


# ---------- Attempt ----------
class AttemptIn(BaseModel):
    correct: bool
    error_category: str = "none"
    independent: bool = False
    duration_minutes: float | None = None
    notes: str = ""
    occurred_at: UTCDateTime = None  # type: ignore[assignment]


class AttemptOut(ORMModel):
    id: int
    task_id: int
    topic_id: int
    correct: bool
    error_category: str
    independent: bool
    duration_minutes: float | None
    notes: str
    occurred_at: UTCDateTime
    created_at: UTCDateTime


# ---------- Diagnosis ----------
class AlternativeOut(BaseModel):
    category: str
    likelihood: str  # high | medium | low
    reason: str = ""


class DiagnosisOut(ORMModel):
    id: int
    topic_id: int
    category: KDDiagCategory
    confidence: float
    rationale: str
    evidence_attempts: list[int]
    alternatives: list[AlternativeOut]
    basis_attempt_count: int
    source: KDSource
    status: KDDiagStatus
    corrected_category: str | None
    correction_note: str | None
    created_at: UTCDateTime
    updated_at: UTCDateTime


class DiagnosisCorrectionIn(BaseModel):
    corrected_category: KDDiagCategory
    correction_note: str = ""


class SuggestionIn(BaseModel):
    diagnosis_id: int
    content: str = Field(min_length=1)


class SuggestionOut(ORMModel):
    id: int
    diagnosis_id: int
    content: str
    verification_task_id: int | None
    status: str
    effectiveness_note: str
    created_at: UTCDateTime


class VerificationResultIn(BaseModel):
    success: bool
    note: str = ""
