"""FSRS 调度适配器单元测试（不调用任何外部 API）。"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.services import scheduling

NOW = datetime(2026, 10, 11, 8, 0, 0, tzinfo=UTC)


def test_new_card_and_first_review():
    state = scheduling.new_card_dict(NOW)
    new_state = scheduling.review(state, 3, NOW)
    assert new_state["stability"] > 0
    assert new_state["due"] is not None


def test_good_rating_schedules_longer_than_again():
    state = scheduling.new_card_dict(NOW)
    good = scheduling.review(state, 3, NOW)
    again = scheduling.review(state, 1, NOW)
    due_good = datetime.fromisoformat(good["due"])
    due_again = datetime.fromisoformat(again["due"])
    assert due_good > due_again


def test_roundtrip_serialization():
    state = scheduling.review(scheduling.new_card_dict(NOW), 4, NOW)
    card = scheduling.load_card(state)
    assert card.to_dict() == state


def test_summary_fields():
    state = scheduling.review(scheduling.new_card_dict(NOW), 3, NOW)
    s = scheduling.summary_from(state, NOW + timedelta(days=1))
    assert s["due_at"] is not None
    assert 0 <= s["retrievability"] <= 1
    assert s["state_str"] in ("learning", "review", "relearning")


def test_preview_intervals_contains_four_ratings():
    previews = scheduling.preview_intervals(None, NOW)
    assert set(previews.keys()) == {1, 2, 3, 4}
    assert all(isinstance(v, str) for v in previews.values())


def test_format_interval():
    assert scheduling.format_interval(0.5 / 1440) == "<1 分钟"
    assert "小时" in scheduling.format_interval(2 / 24)
    assert "天" in scheduling.format_interval(5)
    assert "个月" in scheduling.format_interval(45)
    assert "年" in scheduling.format_interval(500)
