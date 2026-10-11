"""Decision Time Machine 模块模型：决策 / 不可覆盖快照 / 概率预测 / 新信息 / 复盘 / 反事实。"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, utcnow


class Decision(Base, TimestampMixin):
    __tablename__ = "dtm_decisions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(300))
    context: Mapped[str] = mapped_column(Text, default="")  # 决策背景
    goals: Mapped[str] = mapped_column(Text, default="")  # 目标
    options: Mapped[list] = mapped_column(JSON, default=list)  # [{key,label,description}]
    basis: Mapped[str] = mapped_column(Text, default="")  # 当时的依据
    risks: Mapped[str] = mapped_column(Text, default="")  # 已知风险
    # open | reviewed | archived
    status: Mapped[str] = mapped_column(String(20), default="open")
    review_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class DecisionSnapshot(Base):
    """只追加、不可修改、不可删除的决策快照。创建与每次修改都会生成新快照。"""

    __tablename__ = "dtm_decision_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    decision_id: Mapped[int] = mapped_column(ForeignKey("dtm_decisions.id", ondelete="CASCADE"), index=True)
    # created | updated
    reason: Mapped[str] = mapped_column(String(30), default="created")
    payload: Mapped[dict] = mapped_column(JSON)
    snapshot_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Prediction(Base, TimestampMixin):
    __tablename__ = "dtm_predictions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    decision_id: Mapped[int] = mapped_column(ForeignKey("dtm_decisions.id", ondelete="CASCADE"), index=True)
    statement: Mapped[str] = mapped_column(Text)  # 可判定的预测陈述
    option_key: Mapped[str | None] = mapped_column(String(100), nullable=True)
    probability: Mapped[float] = mapped_column(Float)  # 0~1
    resolved: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    actual_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class DecisionUpdate(Base, TimestampMixin):
    """决策后的新信息，构成决策时间线。"""

    __tablename__ = "dtm_decision_updates"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    decision_id: Mapped[int] = mapped_column(ForeignKey("dtm_decisions.id", ondelete="CASCADE"), index=True)
    content: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(200), default="")
    # minor | major
    significance: Mapped[str] = mapped_column(String(20), default="minor")
    occurred_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class DecisionReview(Base, TimestampMixin):
    __tablename__ = "dtm_decision_reviews"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    decision_id: Mapped[int] = mapped_column(ForeignKey("dtm_decisions.id", ondelete="CASCADE"), index=True)
    summary: Mapped[str] = mapped_column(Text)
    # 评价“决策过程质量”（1~5），刻意与结果好坏分开
    process_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    lessons: Mapped[list] = mapped_column(JSON, default=list)
    bias_flags: Mapped[list] = mapped_column(JSON, default=list)
    # manual | ai
    source: Mapped[str] = mapped_column(String(20), default="manual")
    reviewed_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Counterfactual(Base, TimestampMixin):
    """反事实情景。is_hypothetical 恒为 True，仅作假设推演，永远不作为事实使用。"""

    __tablename__ = "dtm_counterfactuals"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    decision_id: Mapped[int] = mapped_column(ForeignKey("dtm_decisions.id", ondelete="CASCADE"), index=True)
    scenario: Mapped[str] = mapped_column(Text)
    analysis: Mapped[str] = mapped_column(Text, default="")
    is_hypothetical: Mapped[bool] = mapped_column(Boolean, default=True)
    # manual | ai
    source: Mapped[str] = mapped_column(String(20), default="manual")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
