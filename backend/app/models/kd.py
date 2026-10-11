"""Knowledge Debt 模块模型：学科 / 知识点 / 依赖边 / 学习任务 / 答题记录 / 诊断 / 建议。"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, utcnow


class Subject(Base, TimestampMixin):
    __tablename__ = "kd_subjects"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    color: Mapped[str] = mapped_column(String(20), default="#6366f1")


class Topic(Base, TimestampMixin):
    __tablename__ = "kd_topics"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("kd_subjects.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    # normal | weak | mastered
    status: Mapped[str] = mapped_column(String(20), default="normal")


class TopicEdge(Base, TimestampMixin):
    __tablename__ = "kd_topic_edges"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    from_topic_id: Mapped[int] = mapped_column(ForeignKey("kd_topics.id", ondelete="CASCADE"), index=True)
    to_topic_id: Mapped[int] = mapped_column(ForeignKey("kd_topics.id", ondelete="CASCADE"), index=True)
    # prerequisite（from 是 to 的前置）| related
    relation: Mapped[str] = mapped_column(String(20), default="prerequisite")
    note: Mapped[str] = mapped_column(String(500), default="")


class StudyTask(Base, TimestampMixin):
    __tablename__ = "kd_study_tasks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    topic_id: Mapped[int] = mapped_column(ForeignKey("kd_topics.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(300))
    question_text: Mapped[str] = mapped_column(Text, default="")
    my_answer: Mapped[str] = mapped_column(Text, default="")
    # 普通任务 = open/closed；验证任务额外有 verification_status
    status: Mapped[str] = mapped_column(String(20), default="open")
    is_verification: Mapped[bool] = mapped_column(Boolean, default=False)
    source_suggestion_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    verification_status: Mapped[str | None] = mapped_column(String(20), nullable=True)


class Attempt(Base, TimestampMixin):
    __tablename__ = "kd_attempts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("kd_study_tasks.id", ondelete="CASCADE"), index=True)
    topic_id: Mapped[int] = mapped_column(Integer, index=True)  # 冗余存储，便于按知识点聚合
    correct: Mapped[bool] = mapped_column(Boolean)
    # none | concept_gap | retrieval_failure | method_selection | execution_error | transfer_failure | other
    error_category: Mapped[str] = mapped_column(String(40), default="none")
    independent: Mapped[bool] = mapped_column(Boolean, default=False)  # 是否独立完成
    duration_minutes: Mapped[float | None] = mapped_column(Float, nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    occurred_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Diagnosis(Base, TimestampMixin):
    __tablename__ = "kd_diagnoses"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    topic_id: Mapped[int] = mapped_column(ForeignKey("kd_topics.id", ondelete="CASCADE"), index=True)
    # concept_gap | retrieval_failure | method_selection | execution_error | transfer_failure | other | insufficient_data
    category: Mapped[str] = mapped_column(String(40))
    confidence: Mapped[float] = mapped_column(Float, default=0.0)  # 0~1
    rationale: Mapped[str] = mapped_column(Text, default="")
    evidence_attempts: Mapped[list] = mapped_column(JSON, default=list)  # 引用的 attempt id 列表
    alternatives: Mapped[list] = mapped_column(JSON, default=list)  # [{category, likelihood, reason}]
    basis_attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    # rule | ai | user
    source: Mapped[str] = mapped_column(String(20), default="rule")
    # provisional | user_confirmed | rejected
    status: Mapped[str] = mapped_column(String(20), default="provisional")
    corrected_category: Mapped[str | None] = mapped_column(String(40), nullable=True)
    correction_note: Mapped[str | None] = mapped_column(Text, nullable=True)


class Suggestion(Base, TimestampMixin):
    __tablename__ = "kd_suggestions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    diagnosis_id: Mapped[int] = mapped_column(ForeignKey("kd_diagnoses.id", ondelete="CASCADE"), index=True)
    content: Mapped[str] = mapped_column(Text)
    verification_task_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # open | testing | effective | ineffective
    status: Mapped[str] = mapped_column(String(20), default="open")
    effectiveness_note: Mapped[str] = mapped_column(Text, default="")
