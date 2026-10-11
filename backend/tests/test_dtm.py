"""决策时间机 API 集成测试：快照不可覆盖、预测校准、复盘流程。"""
from __future__ import annotations


def test_decision_crud_and_snapshots(client):
    # 创建
    r = client.post("/api/dtm/decisions", json={
        "title": "选择毕业设计方向",
        "context": "对 LLM 应用和传统后端都有兴趣",
        "goals": "做出能写进简历的项目",
        "options": [
            {"key": "A", "label": "LLM 应用", "description": "AI 相关"},
            {"key": "B", "label": "高并发后端", "description": "传统方向"},
        ],
        "basis": "招聘网站观察 + 学长建议",
        "risks": "LLM 方向竞争激烈",
        "review_at": "2027-06-01T00:00:00Z",
    })
    assert r.status_code == 201, r.text
    d = r.json()
    did = d["id"]

    # 创建即有 1 个快照
    snaps = client.get(f"/api/dtm/decisions/{did}/snapshots").json()
    assert len(snaps) == 1
    assert snaps[0]["reason"] == "created"
    assert snaps[0]["payload"]["title"] == "选择毕业设计方向"

    # 修改 → 新快照，旧快照原样保留（不可覆盖）
    r2 = client.patch(f"/api/dtm/decisions/{did}", json={"basis": "补充：看了更多岗位 JD"})
    assert r2.status_code == 200
    snaps2 = client.get(f"/api/dtm/decisions/{did}/snapshots").json()
    assert len(snaps2) == 2
    assert snaps2[0]["payload"]["basis"] == "招聘网站观察 + 学长建议"
    assert snaps2[1]["payload"]["basis"] == "补充：看了更多岗位 JD"

    # 预测
    p = client.post(f"/api/dtm/decisions/{did}/predictions", json={
        "statement": "选 LLM 方向能在答辩中拿高分", "option_key": "A", "probability": 0.7,
    }).json()
    assert p["resolved"] is None

    # 决策时间线（新信息）
    u = client.post(f"/api/dtm/decisions/{did}/updates", json={
        "content": "导师确认可以指导 LLM 方向", "source": "面谈", "significance": "major",
    })
    assert u.status_code == 201

    # 揭晓预测
    rp = client.patch(f"/api/dtm/predictions/{p['id']}", json={"resolved": True, "actual_note": "答辩 92 分"})
    assert rp.status_code == 200
    assert rp.json()["resolved"] is True

    # 复盘（评价过程质量）
    rv = client.post(f"/api/dtm/decisions/{did}/reviews", json={
        "summary": "决策过程基本合理，但备选方案调研不够",
        "process_score": 4,
        "lessons": ["重大决策前应再收集一轮信息"],
        "bias_flags": ["确认偏误"],
    })
    assert rv.status_code == 201
    detail = client.get(f"/api/dtm/decisions/{did}").json()
    assert detail["status"] == "reviewed"
    assert len(detail["predictions"]) == 1
    assert len(detail["updates"]) == 1
    assert len(detail["reviews"]) == 1
    assert len(detail["snapshots"]) == 2


def test_calibration_endpoint(client):
    cal = client.get("/api/dtm/calibration").json()
    assert "brier_score" in cal and "bins" in cal and len(cal["bins"]) == 5
    assert "仅供参考" in cal["caveat"]


def test_due_reviews(client):
    r = client.post("/api/dtm/decisions", json={
        "title": "过期的复盘测试", "review_at": "2020-01-01T00:00:00Z",
    })
    assert r.status_code == 201
    due = client.get("/api/dtm/due-reviews").json()
    assert any(x["title"] == "过期的复盘测试" for x in due)


def test_counterfactual_always_hypothetical(client):
    did = client.post("/api/dtm/decisions", json={"title": "反事实测试"}).json()["id"]
    cf = client.post(f"/api/dtm/decisions/{did}/counterfactuals", json={
        "scenario": "如果当初选了另一方案", "analysis": "推演内容",
    }).json()
    assert cf["is_hypothetical"] is True


def test_decision_events_and_links(client):
    did = client.post("/api/dtm/decisions", json={"title": "事件测试决策"}).json()["id"]
    events = client.get(f"/api/dtm/decisions/{did}/events").json()
    assert len(events) >= 1
    assert events[0]["event_type"] == "decision.created"


def test_delete_decision(client):
    did = client.post("/api/dtm/decisions", json={"title": "删除测试"}).json()["id"]
    assert client.delete(f"/api/dtm/decisions/{did}").status_code == 204
    assert client.get(f"/api/dtm/decisions/{did}").status_code == 404
