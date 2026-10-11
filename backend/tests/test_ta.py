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


def test_dependency_propagation_and_auto_resume(client):
    """任务完成 → 下游“依赖解除”事件；全部前置完成后 blocked 的下游自动恢复；环被拒绝。"""
    pid = _make_project(client)
    t1 = client.post(f"/api/ta/projects/{pid}/tasks", json={"title": "上游任务", "estimated_hours": 2}).json()
    t2 = client.post(f"/api/ta/projects/{pid}/tasks", json={"title": "下游任务", "depends_on": [t1["id"]]}).json()
    t3 = client.post(f"/api/ta/projects/{pid}/tasks", json={"title": "多前置任务", "depends_on": [t1["id"], t2["id"]]}).json()

    # 环检测：让 t1 依赖 t3 会形成 t1→t3→t1 的环
    r = client.post(f"/api/ta/tasks/{t1['id']}/deps", json={"depends_on_task_id": t3["id"]})
    assert r.status_code == 422
    assert "循环" in r.json()["detail"]

    # t2 阻塞；t1 完成 → t2 全部前置完成 → 自动恢复 doing；t3 只解除部分依赖（t2 未完成）
    client.patch(f"/api/ta/tasks/{t2['id']}", json={"status": "blocked"})
    client.patch(f"/api/ta/tasks/{t1['id']}", json={"status": "done"})

    t2_now = client.get(f"/api/ta/tasks/{t2['id']}").json()
    assert t2_now["status"] == "doing"
    ev2 = [e["type"] for e in client.get(f"/api/ta/tasks/{t2['id']}/events").json()]
    assert "dependency_cleared" in ev2 and "status_change" in ev2

    t3_now = client.get(f"/api/ta/tasks/{t3['id']}").json()
    assert t3_now["status"] == "todo"  # 仍有未完成前置：不自动开始
    ev3 = [e["type"] for e in client.get(f"/api/ta/tasks/{t3['id']}/events").json()]
    assert "dependency_cleared" in ev3

    # t3 阻塞后 t2 完成 → t3 全部前置完成 → 自动恢复
    client.patch(f"/api/ta/tasks/{t3['id']}", json={"status": "blocked"})
    client.patch(f"/api/ta/tasks/{t2['id']}", json={"status": "done"})
    assert client.get(f"/api/ta/tasks/{t3['id']}").json()["status"] == "doing"

    # 统计事件计数包含新类型
    stats = client.get(f"/api/ta/projects/{pid}/stats").json()
    assert stats["event_type_counts"].get("dependency_cleared", 0) >= 3


def test_create_task_cycle_rejected(client):
    """创建任务时通过 depends_on 构环同样被拒绝。"""
    pid = _make_project(client)
    a = client.post(f"/api/ta/projects/{pid}/tasks", json={"title": "A"}).json()
    b = client.post(f"/api/ta/projects/{pid}/tasks", json={"title": "B", "depends_on": [a["id"]]}).json()
    # 再让 A 依赖 B → 环
    r = client.post(f"/api/ta/tasks/{a['id']}/deps", json={"depends_on_task_id": b["id"]})
    assert r.status_code == 422
