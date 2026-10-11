"""记忆实验室 API 集成测试：FSRS 复习调度、统计、实验分组与免责声明。"""
from __future__ import annotations


def _make_deck_and_cards(client, n: int = 4) -> tuple[int, list[int]]:
    deck = client.post("/api/ml/decks", json={"name": "测试卡组"}).json()
    ids = []
    for i in range(n):
        c = client.post("/api/ml/cards", json={"deck_id": deck["id"], "front": f"词{i}", "back": f"义{i}"}).json()
        ids.append(c["id"])
    return deck["id"], ids


def test_review_moves_due_forward(client):
    _, cards = _make_deck_and_cards(client, 1)
    card_id = cards[0]
    # 复习队列初始应包含新卡
    due = client.get("/api/ml/due").json()
    assert due["total_due"] >= 1

    r = client.post("/api/ml/reviews", json={"card_id": card_id, "rating": 3, "duration_ms": 3500})
    assert r.status_code == 201, r.text
    result = r.json()
    assert result["due_at"] is not None
    assert result["state"]["reps"] == 1
    assert result["interval_display"]

    # 日志
    logs = client.get(f"/api/ml/cards/{card_id}/logs").json()
    assert len(logs) == 1
    assert logs[0]["rating"] == 3

    # again 评分会更快到期
    r2 = client.post("/api/ml/reviews", json={"card_id": card_id, "rating": 1, "duration_ms": 5000})
    assert r2.json()["state"]["lapses"] == 1


def test_stats_and_forgetting_curve(client):
    _, cards = _make_deck_and_cards(client, 2)
    for cid in cards:
        client.post("/api/ml/reviews", json={"card_id": cid, "rating": 4, "duration_ms": 2000})
    stats = client.get("/api/ml/stats").json()
    assert stats["total_cards"] >= 2
    assert stats["reviews_last_7d"] >= 2
    assert stats["retention_7d"] is not None
    assert len(stats["reviews_per_day"]) == 14
    assert sum(b["count"] for b in stats["interval_distribution"]) >= 2
    fc = client.get("/api/ml/forgetting-curve").json()
    assert len(fc) == 30


def test_experiment_random_split_and_disclaimer(client):
    deck_id, cards = _make_deck_and_cards(client, 6)
    exp = client.post("/api/ml/experiments", json={
        "question": "间隔 vs 集中复习哪个保持率高？",
        "strategy_a": "间隔复习", "strategy_b": "集中复习", "metric": "retention",
    }).json()
    assert exp["status"] == "setup"

    r = client.post(f"/api/ml/experiments/{exp['id']}/assign", json={"card_ids": cards})
    assert r.status_code == 201
    data = r.json()
    assert data["assigned"]["A"] + data["assigned"]["B"] == 6
    assert abs(data["assigned"]["A"] - data["assigned"]["B"]) <= 1

    results = client.get(f"/api/ml/experiments/{exp['id']}/results").json()
    assert len(results["groups"]) == 2
    assert results["groups"][0]["n_cards"] == 3
    assert "不能证明" in results["disclaimer"]

    # 分组后复习应带上实验标签
    first = client.get("/api/ml/cards").json()
    target = next(c for c in first if c["id"] == cards[0])
    client.post("/api/ml/reviews", json={"card_id": target["id"], "rating": 2, "duration_ms": 1000})
    logs = client.get(f"/api/ml/cards/{target['id']}/logs").json()
    assert logs[-1]["experiment_id"] == exp["id"]
    assert logs[-1]["group_tag"] in ("A", "B")


def test_card_suspension_excludes_from_due(client):
    deck_id, cards = _make_deck_and_cards(client, 1)
    client.patch(f"/api/ml/cards/{cards[0]}", json={"suspended": True})
    # 新卡（due 立即到期）被挂起后不应出现在队列
    due = client.get("/api/ml/due").json()
    assert all(c["id"] != cards[0] for c in due["cards"])
