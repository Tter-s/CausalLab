"""Memory Laboratory 模块模型：卡组 / 卡片 / 复习状态（FSRS）/ 复习日志 / 对照实验。"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, utcnow


class Deck(Base, TimestampMixin):
    __tablename__ = "ml_decks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")


class Card(Base, TimestampMixin):
    __tablename__ = "ml_cards"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    deck_id: Mapped[int] = mapped_column(ForeignKey("ml_decks.id", ondelete="CASCADE"), index=True)
    front: Mapped[str] = mapped_column(Text)
    back: Mapped[str] = mapped_column(Text, default="")
    tags: Mapped[list] = mapped_column(JSON, default=list)
    suspended: Mapped[bool] = mapped_column(Boolean, default=False)


class ReviewState(Base, TimestampMixin):
    """每张卡片一条 FSRS 记忆状态。fsrs_card 存官方 fsrs 库 Card.to_dict() 的完整序列化。"""

    __tablename__ = "ml_review_states"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    card_id: Mapped[int] = mapped_column(ForeignKey("ml_cards.id", ondelete="CASCADE"), unique=True, index=True)
    fsrs_card: Mapped[dict] = mapped_column(JSON, default=dict)
    stability: Mapped[float] = mapped_column(Float, default=0.0)
    difficulty: Mapped[float] = mapped_column(Float, default=0.0)
    due_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_review_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    reps: Mapped[int] = mapped_column(Integer, default=0)
    lapses: Mapped[int] = mapped_column(Integer, default=0)
    # learning | review | relearning
    state_str: Mapped[str] = mapped_column(String(20), default="new")
    # 实验分组标签（参与实验时写入）
    experiment_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    group_tag: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)


class ReviewLog(Base, TimestampMixin):
    __tablename__ = "ml_review_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    card_id: Mapped[int] = mapped_column(ForeignKey("ml_cards.id", ondelete="CASCADE"), index=True)
    rating: Mapped[int] = mapped_column(Integer)  # 1 again | 2 hard | 3 good | 4 easy
    reviewed_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    scheduled_days: Mapped[float | None] = mapped_column(Float, nullable=True)
    elapsed_days: Mapped[float | None] = mapped_column(Float, nullable=True)
    experiment_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    group_tag: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)


class MemExperiment(Base, TimestampMixin):
    __tablename__ = "ml_experiments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    question: Mapped[str] = mapped_column(Text)
    strategy_a: Mapped[str] = mapped_column(String(300))
    strategy_b: Mapped[str] = mapped_column(String(300))
    # retention | recall_speed | delayed_test
    metric: Mapped[str] = mapped_column(String(30), default="retention")
    # setup | running | completed
    status: Mapped[str] = mapped_column(String(20), default="setup")
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    delayed_test_days: Mapped[int] = mapped_column(Integer, default=7)
    notes: Mapped[str] = mapped_column(Text, default="")


class ExpGroup(Base, TimestampMixin):
    __tablename__ = "ml_experiment_groups"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    experiment_id: Mapped[int] = mapped_column(ForeignKey("ml_experiments.id", ondelete="CASCADE"), index=True)
    # A | B
    name: Mapped[str] = mapped_column(String(10))
    strategy: Mapped[str] = mapped_column(String(300), default="")


class ExpAssignment(Base, TimestampMixin):
    __tablename__ = "ml_experiment_assignments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    experiment_id: Mapped[int] = mapped_column(ForeignKey("ml_experiments.id", ondelete="CASCADE"), index=True)
    card_id: Mapped[int] = mapped_column(ForeignKey("ml_cards.id", ondelete="CASCADE"), index=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("ml_experiment_groups.id", ondelete="CASCADE"), index=True)
