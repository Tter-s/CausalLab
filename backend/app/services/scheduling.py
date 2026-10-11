"""FSRS 官方库（open-spaced-repetition/py-fsrs，MIT）适配层。

数据库中只存 Card.to_dict() 的 JSON；本模块负责在官方 Card 对象与存储格式之间转换。
若官方库不可用（理论上不会，纯 Python 包），抛出明确错误而不是静默退化。
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fsrs import Card as FSRSCard
from fsrs import Rating as FSRSRating
from fsrs import Scheduler
from fsrs import State as FSRSState

RATING_MAP = {1: FSRSRating.Again, 2: FSRSRating.Hard, 3: FSRSRating.Good, 4: FSRSRating.Easy}
STATE_NAMES = {FSRSState.Learning: "learning", FSRSState.Review: "review", FSRSState.Relearning: "relearning"}

_scheduler = Scheduler(enable_fuzzing=False)  # 关闭随机扰动，保证调度可复现、可测试


def _aware(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


def new_card_dict(now: datetime) -> dict:
    return dict(FSRSCard().to_dict())


def load_card(state: dict | None) -> FSRSCard:
    if not state:
        return FSRSCard()
    return FSRSCard.from_dict(state)  # type: ignore[arg-type]


def review(state: dict | None, rating: int, now: datetime, duration_ms: int = 0) -> dict:
    """执行一次复习，返回新的可序列化状态。rating: 1 again / 2 hard / 3 good / 4 easy。"""
    card = load_card(state)
    new_card, _log = _scheduler.review_card(card, RATING_MAP[int(rating)], _aware(now), duration_ms)
    return dict(new_card.to_dict())


def summary_from(state: dict | None, now: datetime) -> dict:
    """从序列化状态提取展示字段。"""
    card = load_card(state)
    due = card.due.astimezone(UTC).replace(tzinfo=None) if card.due else None
    last = card.last_review.astimezone(UTC).replace(tzinfo=None) if card.last_review else None
    retrievability: float | None = None
    if card.last_review is not None:
        retrievability = round(_scheduler.get_card_retrievability(card, _aware(now)), 4)
    return {
        "card_id": 0,  # 由调用方填充真实 card_id
        "stability": round(card.stability or 0.0, 4),
        "difficulty": round(card.difficulty or 0.0, 4),
        "due_at": due,
        "last_review_at": last,
        "reps": 0,  # 由调用方按 ReviewLog 计数填充
        "lapses": 0,
        # 从未复习过的卡（内部 state=Learning 但尚无任何记录）对外统一为 "new"
        "state_str": "new" if card.last_review is None else STATE_NAMES.get(card.state, "new"),
        "retrievability": retrievability,
        # 学习/重学步骤细分：step 为 0 起始索引；steps_minutes 为该状态下全部步骤时长（分钟）
        "step": (card.step if card.last_review else None),
        "steps_minutes": _steps_minutes_for(card),
    }


def _steps_minutes_for(card) -> list[float] | None:
    """返回卡片当前状态对应的步骤时长列表（分钟）；Review 状态或新卡返回 None。"""
    if card.last_review is None:
        return None
    if card.state == FSRSState.Learning:
        return [round(s.total_seconds() / 60, 2) for s in _scheduler.learning_steps]
    if card.state == FSRSState.Relearning:
        return [round(s.total_seconds() / 60, 2) for s in _scheduler.relearning_steps]
    return None


def learning_steps_minutes() -> list[float]:
    return [round(s.total_seconds() / 60, 2) for s in _scheduler.learning_steps]


def relearning_steps_minutes() -> list[float]:
    return [round(s.total_seconds() / 60, 2) for s in _scheduler.relearning_steps]


def preview_intervals(state: dict | None, now: datetime) -> dict[int, str]:
    """预览四种评分后的间隔文案（不真正写入）。"""
    card = load_card(state)
    out: dict[int, str] = {}
    for r in (1, 2, 3, 4):
        preview_card, _ = _scheduler.review_card(card, RATING_MAP[r], _aware(now))
        days = (preview_card.due - _aware(now)).total_seconds() / 86400
        out[r] = format_interval(days)
    return out


def format_interval(days: float) -> str:
    minutes = days * 1440
    if minutes < 1:
        return "<1 分钟"
    if minutes < 60:
        return f"{int(round(minutes))} 分钟"
    if minutes < 1440:
        return f"{int(round(minutes / 60))} 小时"
    if days < 31:
        return f"{int(round(days))} 天"
    if days < 365:
        return f"{days / 30.44:.1f} 个月"
    return f"{days / 365.25:.1f} 年"


def retrievability_now(state: dict | None, now: datetime) -> float | None:
    card = load_card(state)
    if card.last_review is None:
        return None
    return round(_scheduler.get_card_retrievability(card, _aware(now)), 4)


def default_desired_retention() -> float:
    return _scheduler.desired_retention


__all__ = [
    "RATING_MAP",
    "default_desired_retention",
    "format_interval",
    "load_card",
    "new_card_dict",
    "preview_intervals",
    "review",
    "retrievability_now",
    "summary_from",
    "timedelta",
]
