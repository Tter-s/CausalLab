"""知识债务 API 集成测试：图谱、答题、诊断护栏、用户纠正、建议验证闭环。"""
from __future__ import annotations


def _setup_topic(client) -> dict:
    s = client.post("/api/kd/subjects", json={"name": "机器学习"}).json()
    t = client.post("/api/kd/topics", json={"subject_id": s["id"], "name": "梯度下降"}).json()
    t2 = client.post("/api/kd/topics", json={"subject_id": s["id"], "name": "反向传播"}).json()
    return {"subject": s, "topic": t, "topic2": t2}


def test_graph(client):
    data = _setup_topic(client)
    s, t1, t2 = data["subject"], data["topic"], data["topic2"]
    client.post("/api/kd/edges", json={"from_topic_id": t1["id"], "to_topic_id": t2["id"], "relation": "prerequisite"})
    graph = client.get("/api/kd/graph", params={"subject_id": s["id"]}).json()
    assert len(graph["nodes"]) == 2
    assert len(graph["edges"]) == 1
    assert graph["edges"][0]["relation"] == "prerequisite"


def test_self_edge_rejected(client):
    data = _setup_topic(client)
    r = client.post("/api/kd/edges", json={"from_topic_id": data["topic"]["id"], "to_topic_id": data["topic"]["id"]})
    assert r.status_code == 422


def test_attempts_and_rule_diagnosis_guardrail(client):
    data = _setup_topic(client)
    topic_id = data["topic"]["id"]
    task = client.post("/api/kd/tasks", json={"topic_id": topic_id, "title": "手推梯度下降更新公式"}).json()

    # 只有一次失败 → 必须给 insufficient_data
    client.post(f"/api/kd/tasks/{task['id']}/attempts", json={
        "correct": False, "error_category": "method_selection", "independent": True,
    })
    diag = client.post(f"/api/kd/topics/{topic_id}/diagnose").json()
    assert diag["category"] == "insufficient_data"
    assert diag["confidence"] <= 0.25

    # 补足样本后可以下结论
    for _ in range(3):
        client.post(f"/api/kd/tasks/{task['id']}/attempts", json={
            "correct": False, "error_category": "method_selection", "independent": False,
        })
    diag2 = client.post(f"/api/kd/topics/{topic_id}/diagnose").json()
    assert diag2["category"] in ("method_selection", "transfer_failure")
    assert diag2["confidence"] > 0.5
    assert len(diag2["alternatives"]) >= 1


def test_user_correction_flow(client):
    data = _setup_topic(client)
    topic_id = data["topic"]["id"]
    task = client.post("/api/kd/tasks", json={"topic_id": topic_id, "title": "题目"}).json()
    for _ in range(3):
        client.post(f"/api/kd/tasks/{task['id']}/attempts", json={
            "correct": False, "error_category": "concept_gap", "independent": True,
        })
    diag = client.post(f"/api/kd/topics/{topic_id}/diagnose").json()
    corrected = client.patch(f"/api/kd/diagnoses/{diag['id']}", json={
        "corrected_category": "retrieval_failure", "correction_note": "看答案就懂，是提取失败",
    }).json()
    assert corrected["status"] == "user_confirmed"
    assert corrected["corrected_category"] == "retrieval_failure"

    # 证据里应有 user_correction 记录
    ev = client.get("/api/evidence", params={"module": "kd", "ref_type": "diagnosis", "ref_id": diag["id"]}).json()
    assert any(e["kind"] == "user_correction" for e in ev)


def test_suggestion_verification_loop(client):
    data = _setup_topic(client)
    topic_id = data["topic"]["id"]
    task = client.post("/api/kd/tasks", json={"topic_id": topic_id, "title": "题目"}).json()
    for _ in range(3):
        client.post(f"/api/kd/tasks/{task['id']}/attempts", json={
            "correct": False, "error_category": "retrieval_failure", "independent": True,
        })
    diag = client.post(f"/api/kd/topics/{topic_id}/diagnose").json()

    sugg = client.post("/api/kd/suggestions", json={
        "diagnosis_id": diag["id"], "content": "先回忆再看答案",
    }).json()
    # 生成验证任务
    vt = client.post(f"/api/kd/suggestions/{sugg['id']}/verification-task", json={
        "title": "验证：48 小时后独立完成一道新题",
    }).json()
    assert vt["is_verification"] is True
    assert vt["verification_status"] == "pending"
    assert sugg["status"] == "testing" or client.get("/api/kd/suggestions", params={"diagnosis_id": diag["id"]}).json()[0]["status"] == "testing"

    # 提交验证结果 → 建议闭环
    result = client.post(f"/api/kd/suggestions/{sugg['id']}/verification-result", json={
        "success": True, "note": "独立完成成功",
    }).json()
    assert result["status"] == "effective"
    v_tasks = [t for t in client.get("/api/kd/tasks", params={"topic_id": topic_id}).json() if t["is_verification"]]
    assert v_tasks and v_tasks[0]["verification_status"] == "success"


def test_topic_attempts_listing(client):
    data = _setup_topic(client)
    topic_id = data["topic"]["id"]
    task = client.post("/api/kd/tasks", json={"topic_id": topic_id, "title": "题目"}).json()
    client.post(f"/api/kd/tasks/{task['id']}/attempts", json={"correct": True, "independent": True})
    attempts = client.get(f"/api/kd/topics/{topic_id}/attempts").json()
    assert len(attempts) == 1
    assert attempts[0]["correct"] is True
