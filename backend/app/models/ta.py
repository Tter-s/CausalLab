"""Task Autopsy 模块模型：项目 / 任务 / 依赖 / 过程事件 / 项目复盘 / 改进措施。"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, utcnow


class Project(Base, TimestampMixin):
    __tablename__ = "ta_projects"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    # active | done | archived
    status: Mapped[str] = mapped_column(String(20), default="active")
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    deadline: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class Task(Base, TimestampMixin):
    __tablename__ = "ta_tasks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("ta_projects.id", ondelete="CASCADE"), index=True)
    parent_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)  # 子任务
    title: Mapped[str] = mapped_column(String(300))
    description: Mapped[str] = mapped_column(Text, default="")
    # todo | doing | blocked | done | cancelled
    status: Mapped[str] = mapped_column(String(20), default="todo", index=True)
    estimated_hours: Mapped[float | None] = mapped_column(Float, nullable=True)
    actual_hours: Mapped[float | None] = mapped_column(Float, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    due_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class TaskDep(Base):
    __tablename__ = "ta_task_deps"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("ta_tasks.id", ondelete="CASCADE"), index=True)
    depends_on_task_id: Mapped[int] = mapped_column(ForeignKey("ta_tasks.id", ondelete="CASCADE"), index=True)


class TaskEvent(Base, TimestampMixin):
    """任务过程事件：阻塞、返工、中断、需求变化等，是复盘的核心证据。"""

    __tablename__ = "ta_task_events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("ta_tasks.id", ondelete="CASCADE"), index=True)
    # blocked | resumed | rework | interrupted | requirement_change | note | status_change
    type: Mapped[str] = mapped_column(String(30), index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    duration_minutes: Mapped[float | None] = mapped_column(Float, nullable=True)  # 该事件耗时（如阻塞时长）
    occurred_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class ProjectReview(Base, TimestampMixin):
    __tablename__ = "ta_project_reviews"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("ta_projects.id", ondelete="CASCADE"), index=True)
    summary: Mapped[str] = mapped_column(Text)
    facts: Mapped[list] = mapped_column(JSON, default=list)
    speculations: Mapped[list] = mapped_column(JSON, default=list)
    missing_evidence: Mapped[list] = mapped_column(JSON, default=list)
    improvements: Mapped[list] = mapped_column(JSON, default=list)
    # rule | ai
    source: Mapped[str] = mapped_column(String(20), default="rule")


class ImprovementAction(Base, TimestampMixin):
    __tablename__ = "ta_improvement_actions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    review_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    action: Mapped[str] = mapped_column(Text)
    # proposed | trying | adopted | discarded
    status: Mapped[str] = mapped_column(String(20), default="proposed")
    followup_note: Mapped[str] = mapped_column(Text, default="")
    effect: Mapped[dict | None] = mapped_column(JSON, nullable=True)
