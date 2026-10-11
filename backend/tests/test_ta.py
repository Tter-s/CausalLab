"""任务复盘 API 集成测试：状态流转、过程事件、统计与规则复盘。"""
from __future__ import annotations


def _make_project(client) -> int:
    return client.post("/api/ta/projects", json={"name": "测试项目", "description": "用于测试"}).json()["id"]


def test_task_lifecycle_and_stats(client):
    pid = _make_project(client)

    t1 = client.post(f"/api/ta/projects/{pid}/tasks", json={
        "title": "写爬虫", "estimated_hours": 5, "depends_on": [],
    }).json()
    t2 = client.post(f"/api/ta/projects/{pid}/tasks", json={
        "title": "写报告", "estimated_hours": 3, "depends_on": [t1["id"]],
    }).json()
    assert t2["id"] != t1["id"]

    # 依赖
    deps = client.get(f"/api/tasks_{t2['id']}/deps") if False else client.get(f"/api/ta/tasks/{t2['id']}/deps").json()
    assert len(deps) == 1
    assert deps[0]["depends_on_task_id"] == t1["id"]

    # 状态流转：doing → blocked（事件联动）→ doing → done
    client.patch(f"/api/ta/tasks/{t1['id']}", json={"status": "doing"})
    client.post(f"/api/ta/tasks/{t1['id']}/events", json={
        "type": "blocked", "description": "目标网站改版", "duration_minutes": 120,
    })
    t1_now = client.get(f"/api/ta/tasks/{t1['id']}").json()
    assert t1_now["status"] == "blocked"
    client.post(f"/api/ta/tasks/{t1['id']}/events", json={"type": "resumed", "description": "修复完成"})
    assert client.get(f"/api/ta/tasks/{t1['id']}").json()["status"] == "doing"
    client.patch(f"/api/ta/tasks/{t1['id']}", json={"status": "done", "actual_hours": 7.5})

    # 过程事件
    client.post(f"/api/ta/tasks/{t1['id']}/events", json={"type": "rework", "description": "反爬策略重写"})
    events = client.get(f"/api/ta/tasks/{t1['id']}/events").json()
    types = [e["type"] for e in events]
    assert "status_change" in types and "blocked" in types and "rework" in types

    # 统计
    stats = client.get(f"/api/ta/projects/{pid}/stats").json()
    assert stats["tasks_total"] == 2
    assert stats["tasks_done"] == 1
    assert stats["rework_count"] == 1
    assert stats["blocked_minutes_total"] == 120
    assert stats["avg_overrun_ratio"] == round(7.5 / 5, 2)
    row = next(r for r in stats["per_task"] if r["task_id"] == t1["id"])
    assert row["overrun_ratio"] == 1.5

    # 规则复盘：必须区分事实/推测/缺失证据
    review = client.post(f"/api/ta/projects/{pid}/rule-review").json()
    assert review["source"] == "rule"
    assert any("实际" in f or "任务" in f for f in review["facts"])
    assert isinstance(review["speculations"], list)
    assert isinstance(review["missing_evidence"], list)
    assert len(review["improvements"]) >= 1


def test_self_dependency_rejected(client):
    pid = _make_project(client)
    t = client.post(f"/api/ta/projects/{pid}/tasks", json={"title": "自依赖"}).json()
    r = client.post(f"/api/ta/tasks/{t['id']}/deps", json={"depends_on_task_id": t["id"]})
    assert r.status_code == 422


def test_improvement_tracking(client):
    pid = _make_project(client)
    a = client.post("/api/ta/improvements", json={
        "action": "预估时乘 1.5 系数", "project_id": pid, "status": "proposed",
    }).json()
    assert a["status"] == "proposed"
    upd = client.patch(f"/api/ta/improvements/{a['id']}", json={
        "status": "trying",
        "effect": {"note": "第一个任务偏差 1.3，比之前好"},
    })
    assert upd.status_code == 200
    assert upd.json()["status"] == "trying"


def test_project_reviews_listed(client):
    pid = _make_project(client)
    client.post(f"/api/ta/projects/{pid}/reviews", json={
        "summary": "手动复盘", "facts": ["事实1"], "speculations": [], "missing_evidence": [], "improvements": [],
    })
    reviews = client.get(f"/api/ta/projects/{pid}/reviews").json()
    assert len(reviews) == 1 and reviews[0]["source"] == "manual"
