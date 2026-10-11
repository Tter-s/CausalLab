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


def test_learning_step_breakdown(client):
    """学习/重学步骤细分：step 索引、每步时长、毕业状态与统计细分。"""
    deck = client.post("/api/ml/decks", json={"name": "步骤卡组"}).json()
    c_good = client.post("/api/ml/cards", json={"deck_id": deck["id"], "front": "步骤A", "back": "B"}).json()
    c_easy = client.post("/api/ml/cards", json={"deck_id": deck["id"], "front": "步骤B", "back": "B"}).json()

    # 新卡 Good → 进入学习步骤 2/2（10 分钟后到期）
    r = client.post("/api/ml/reviews", json={"card_id": c_good["id"], "rating": 3, "duration_ms": 1000}).json()
    assert r["state"]["state_str"] == "learning"
    assert r["state"]["step"] == 1
    assert r["state"]["steps_minutes"] == [1.0, 10.0]

    # 学习步骤内 Again → 回到步骤 1/2（1 分钟）
    r2 = client.post("/api/ml/reviews", json={"card_id": c_good["id"], "rating": 1, "duration_ms": 1000}).json()
    assert r2["state"]["state_str"] == "learning"
    assert r2["state"]["step"] == 0

    # 新卡 Easy → 直接毕业进入复习循环（无步骤）
    r3 = client.post("/api/ml/reviews", json={"card_id": c_easy["id"], "rating": 4, "duration_ms": 1000}).json()
    assert r3["state"]["state_str"] == "review"
    assert r3["state"]["step"] is None
    assert r3["state"]["steps_minutes"] is None

    # 统计：maturity 含 relearning；step_breakdown 含学习步骤细分
    stats = client.get("/api/ml/stats").json()
    assert "relearning" in stats["maturity"]
    step1 = [b for b in stats["step_breakdown"] if b["state"] == "learning" and b["step"] == 1]
    assert step1 and step1[0]["minutes"] == 1.0 and step1[0]["count"] >= 1  # 步骤A 在 1 分钟步骤上
    # 存在处于 10 分钟步骤的卡片时，其 minutes 必须正确
    step2 = [b for b in stats["step_breakdown"] if b["state"] == "learning" and b["step"] == 2]
    if step2:
        assert step2[0]["minutes"] == 10.0

    # 到期队列：学习步骤未到期的卡片不应出现（1 分钟后才会到期）
    due = client.get("/api/ml/due").json()
    assert all(c["id"] != c_good["id"] for c in due["cards"])


def test_recall_ms_and_median(client):
    """recall_ms 存储 + 实验结果用“纯回忆用时中位数”，异常值（>5min）被剔除。"""
    deck = client.post("/api/ml/decks", json={"name": "回忆用时卡组"}).json()
    c0 = client.post("/api/ml/cards", json={"deck_id": deck["id"], "front": "卡0", "back": "B"}).json()
    c1 = client.post("/api/ml/cards", json={"deck_id": deck["id"], "front": "卡1", "back": "B"}).json()
    exp = client.post("/api/ml/experiments", json={
        "question": "回忆用时对比", "strategy_a": "A 策略", "strategy_b": "B 策略", "metric": "recall_speed",
    }).json()
    client.post(f"/api/ml/experiments/{exp['id']}/assign", json={"card_ids": [c0["id"], c1["id"]]})

    # 各组 1 张卡（随机分组）；c0 正常回忆用时 1200ms，c1 为 15 分钟（>5min 异常值）
    client.post("/api/ml/reviews", json={"card_id": c0["id"], "rating": 3, "duration_ms": 30_000, "recall_ms": 1200})
    client.post("/api/ml/reviews", json={"card_id": c1["id"], "rating": 3, "duration_ms": 900_000, "recall_ms": 900_000})

    logs0 = client.get(f"/api/ml/cards/{c0['id']}/logs").json()
    assert logs0[0]["recall_ms"] == 1200
    group0 = logs0[0]["group_tag"]

    results = client.get(f"/api/ml/experiments/{exp['id']}/results").json()
    g0 = next(g for g in results["groups"] if g["name"] == group0)
    other = next(g for g in results["groups"] if g["name"] != group0)
    assert g0["median_recall_ms"] == 1200.0 and g0["recall_samples"] == 1
    assert other["median_recall_ms"] is None and other["recall_samples"] == 0  # 全部被异常值过滤
    # 普通复习不带 recall_ms → 落库为 None
    c2 = client.post("/api/ml/cards", json={"deck_id": deck["id"], "front": "卡2", "back": "B"}).json()
    r2 = client.post("/api/ml/reviews", json={"card_id": c2["id"], "rating": 3, "duration_ms": 4000}).json()
    assert r2["state"]["reps"] == 1
    logs2 = client.get(f"/api/ml/cards/{c2['id']}/logs").json()
    assert logs2[0]["recall_ms"] is None
