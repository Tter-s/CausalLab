"""跨模块共享模型：统一事件时间线 / 证据 / 实体链接 / 假设实验室 / 改进循环。"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, utcnow


class EventLog(Base):
    """统一事件时间线。所有模块的关键动作都写一条事件，支撑 Evidence Timeline 与全局活动流。"""

    __tablename__ = "events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    # kd | ml | dtm | ta | hyp | loop | sys
    module: Mapped[str] = mapped_column(String(10), index=True)
    event_type: Mapped[str] = mapped_column(String(50))  # 如 decision.created / ml.review
    ref_type: Mapped[str] = mapped_column(String(40))  # 如 decision / topic / task
    ref_id: Mapped[int] = mapped_column(Integer, index=True)
    title: Mapped[str] = mapped_column(String(400))
    detail: Mapped[dict] = mapped_column(JSON, default=dict)
    importance: Mapped[int] = mapped_column(Integer, default=1)  # 1 普通 2 重要 3 关键
    occurred_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)


class EvidenceRecord(Base, TimestampMixin):
    """证据记录：区分事实 / 推测 / 缺失证据 / AI 分析 / 用户纠正。"""

    __tablename__ = "evidence"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    module: Mapped[str] = mapped_column(String(10), index=True)
    ref_type: Mapped[str] = mapped_column(String(40), index=True)
    ref_id: Mapped[int] = mapped_column(Integer, index=True)
    event_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # fact | speculation | missing_evidence | ai_analysis | user_correction | user_input
    kind: Mapped[str] = mapped_column(String(30), index=True)
    content: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(200), default="")
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)


class EntityLink(Base, TimestampMixin):
    """跨模块实体链接：四模块联动与改进循环的骨架。"""

    __tablename__ = "entity_links"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    from_module: Mapped[str] = mapped_column(String(10), index=True)
    from_ref_type: Mapped[str] = mapped_column(String(40))
    from_ref_id: Mapped[int] = mapped_column(Integer, index=True)
    to_module: Mapped[str] = mapped_column(String(10), index=True)
    to_ref_type: Mapped[str] = mapped_column(String(40))
    to_ref_id: Mapped[int] = mapped_column(Integer, index=True)
    # spawned_from（由此派生）| associated_with（关联）| validates（验证）| feedback_to（反馈）
    relation: Mapped[str] = mapped_column(String(30), default="associated_with")
    note: Mapped[str] = mapped_column(String(500), default="")


class Hypothesis(Base, TimestampMixin):
    __tablename__ = "hyp_hypotheses"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    statement: Mapped[str] = mapped_column(Text)  # 可检验的陈述
    rationale: Mapped[str] = mapped_column(Text, default="")
    design: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    criteria: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # {support_if, refute_if}
    # draft | testing | supported | rejected | uncertain
    status: Mapped[str] = mapped_column(String(20), default="draft")


class HypothesisObservation(Base, TimestampMixin):
    __tablename__ = "hyp_observations"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    hypothesis_id: Mapped[int] = mapped_column(ForeignKey("hyp_hypotheses.id", ondelete="CASCADE"), index=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    value: Mapped[float] = mapped_column(Float)
    context: Mapped[dict] = mapped_column(JSON, default=dict)  # 分组上下文，如 {"时段": "上午"}
    note: Mapped[str] = mapped_column(Text, default="")
    # manual | auto
    source: Mapped[str] = mapped_column(String(20), default="manual")


class ImprovementLoop(Base, TimestampMixin):
    """改进循环：发现问题 → 提出假设 → 设计干预 → 执行 → 收集数据 → 复盘 → 修改策略。"""

    __tablename__ = "loop_loops"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(300))
    problem: Mapped[str] = mapped_column(Text, default="")
    # active | closed
    status: Mapped[str] = mapped_column(String(20), default="active", index=True)
    # observe | hypothesize | intervene | measure | review | adjust
    current_stage: Mapped[str] = mapped_column(String(20), default="observe")
    hypothesis_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    intervention: Mapped[str] = mapped_column(Text, default="")
    outcome_note: Mapped[str] = mapped_column(Text, default="")
    verdict: Mapped[str | None] = mapped_column(String(20), nullable=True)  # effective | ineffective | uncertain


class LoopStage(Base):
    __tablename__ = "loop_stages"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    loop_id: Mapped[int] = mapped_column(ForeignKey("loop_loops.id", ondelete="CASCADE"), index=True)
    stage: Mapped[str] = mapped_column(String(20))
    content: Mapped[dict] = mapped_column(JSON, default=dict)
    entered_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
