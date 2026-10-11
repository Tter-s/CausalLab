"""跨模块测试：时间线、证据、链接、假设分析、改进循环、搜索、仪表盘、AI 闸门与联动。"""
from __future__ import annotations


def test_timeline_and_evidence_and_links(client):
    did = client.post("/api/dtm/decisions", json={"title": "时间线测试决策"}).json()["id"]
    tl = client.get("/api/timeline", params={"module": "dtm"}).json()
    assert tl["total"] >= 1
    assert any("时间线测试决策" in e["title"] for e in tl["items"])

    # 证据
    ev = client.post("/api/evidence", json={
        "module": "dtm", "ref_type": "decision", "ref_id": did,
        "kind": "speculation", "content": "推测：导师更支持 A 方案",
    })
    assert ev.status_code == 201

    # 链接：决策 → 任务
    pid = client.post("/api/ta/projects", json={"name": "联动项目"}).json()["id"]
    task = client.post(f"/api/ta/projects/{pid}/tasks", json={"title": "执行决策的任务"}).json()
    link = client.post("/api/links", json={
        "from_module": "dtm", "from_ref_type": "decision", "from_ref_id": did,
        "to_module": "ta", "to_ref_type": "task", "to_ref_id": task["id"],
        "relation": "spawned_from", "note": "由决策派生的执行任务",
    })
    assert link.status_code == 201
    links = client.get("/api/links", params={"module": "dtm", "ref_type": "decision", "ref_id": did}).json()
    assert len(links) == 1
    assert links[0]["relation"] == "spawned_from"

    # 实体事件
    entity_events = client.get("/api/timeline/entity", params={
        "module": "dtm", "ref_type": "decision", "ref_id": did,
    }).json()
    assert entity_events


def test_hypothesis_laboratory(client):
    h = client.post("/api/hypotheses", json={
        "statement": "我在上午学习时独立完成率更高",
        "rationale": "最近几次上午做题比较顺",
        "criteria": {"support_if": "上午均值高 15%+", "refute_if": "差异 < 5%"},
    }).json()
    assert h["status"] == "draft"

    # 手动观察值（分上午/晚上两组）
    for i in range(6):
        client.post(f"/api/hypotheses/{h['id']}/observations", json={
            "value": 0.8 if i % 2 == 0 else 0.5,
            "context": {"时段": "上午" if i % 2 == 0 else "晚上"},
        })
    analysis = client.get(f"/api/hypotheses/{h['id']}/analysis", params={"group_key": "时段"}).json()
    assert analysis["n_observations"] == 6
    assert len(analysis["groups"]) == 2
    am = next(g for g in analysis["groups"] if g["label"] == "上午")
    pm = next(g for g in analysis["groups"] if g["label"] == "晚上")
    assert am["mean"] > pm["mean"]
    assert any("相关" in lim or "因果" in lim for lim in analysis["limitations"])

    # 状态更新
    upd = client.patch(f"/api/hypotheses/{h['id']}", json={"status": "testing"})
    assert upd.json()["status"] == "testing"


def test_improvement_loop_flow(client):
    loop = client.post("/api/loops", json={"title": "减少刷题分心", "problem": "做题总想看手机"}).json()
    assert loop["current_stage"] == "observe"

    stages = client.get(f"/api/loops/{loop['id']}/stages").json()
    assert stages[0]["stage"] == "observe"

    # 推进：假设 → 干预 → 复盘 → 调整
    r1 = client.post(f"/api/loops/{loop['id']}/stages", json={
        "stage": "hypothesize", "content": {"hypothesis": "分心来自手机在身边"},
    })
    assert r1.status_code == 201
    r2 = client.post(f"/api/loops/{loop['id']}/stages", json={
        "stage": "intervene", "content": {"intervention": "番茄钟 + 手机放客厅"},
    })
    assert r2.status_code == 201
    cur = client.get(f"/api/loops/{loop['id']}").json()
    assert cur["current_stage"] == "intervene"
    assert "番茄钟" in cur["intervention"]

    client.post(f"/api/loops/{loop['id']}/stages", json={"stage": "review", "content": {"data": "分心次数 5→1"}})
    closed = client.patch(f"/api/loops/{loop['id']}", json={"status": "closed", "verdict": "effective"})
    assert closed.json()["verdict"] == "effective"


def test_search_across_modules(client):
    client.post("/api/dtm/decisions", json={"title": "搜索测试：实习选择"})
    client.post("/api/ta/projects", json={"name": "搜索测试：秋招准备"})
    out = client.get("/api/search", params={"q": "搜索测试"}).json()
    assert out["total"] >= 2
    assert "决策" in out["groups"] and "项目" in out["groups"]


def test_dashboard(client):
    d = client.get("/api/dashboard").json()
    assert "stats" in d and "cards_due" in d["stats"]
    assert "recent_events" in d
    assert set(d["charts"].keys()) == {"学习", "复习", "任务", "决策"}
    assert d["demo_mode"] is False


def test_ai_confirm_gate_428(client):
    """隐私闸门：未确认时必须 428 并返回发送内容预览。"""
    s = client.post("/api/kd/subjects", json={"name": "AI 闸门学科"}).json()
    t = client.post("/api/kd/topics", json={"subject_id": s["id"], "name": "AI 闸门知识点"}).json()
    task = client.post("/api/kd/tasks", json={"topic_id": t["id"], "title": "题"}).json()
    for _ in range(3):
        client.post(f"/api/kd/tasks/{task['id']}/attempts", json={
            "correct": False, "error_category": "concept_gap", "independent": True,
        })

    # provider=none → 409
    r_none = client.post("/api/ai/kd/diagnose", params={"topic_id": t["id"], "confirm_send": True})
    assert r_none.status_code == 409

    # 配置 mock provider
    client.put("/api/settings/ai", json={"provider": "mock", "model_id": "mock-1", "monthly_budget": 0})

    # 不确认 → 428 + 预览
    r428 = client.post("/api/ai/kd/diagnose", params={"topic_id": t["id"], "confirm_send": False})
    assert r428.status_code == 428
    body = r428.json()
    assert body["code"] == "ai_confirm_required"
    assert "payload_preview" in body

    # 确认 → mock 诊断成功
    ok = client.post("/api/ai/kd/diagnose", params={"topic_id": t["id"], "confirm_send": True})
    assert ok.status_code == 201, ok.text
    data = ok.json()
    assert data["ai_mock"] is True
    assert data["source"] == "ai"
    assert data["category"] in ("concept_gap", "retrieval_failure", "method_selection",
                                "execution_error", "transfer_failure", "other", "insufficient_data")
    assert len(data["alternatives"]) >= 1


def test_ai_auto_confirm_and_usage_log(client):
    client.put("/api/settings/ai", json={
        "provider": "mock", "model_id": "mock-1", "monthly_budget": 0, "auto_confirm_send": True,
    })
    s = client.post("/api/kd/subjects", json={"name": "自动确认学科"}).json()
    t = client.post("/api/kd/topics", json={"subject_id": s["id"], "name": "自动确认知识点"}).json()
    task = client.post("/api/kd/tasks", json={"topic_id": t["id"], "title": "题"}).json()
    for _ in range(3):
        client.post(f"/api/kd/tasks/{task['id']}/attempts", json={
            "correct": False, "error_category": "method_selection", "independent": True,
        })
    r = client.post("/api/ai/kd/diagnose", params={"topic_id": t["id"], "confirm_send": False})
    assert r.status_code == 201  # auto_confirm 开启后不再要求确认

    usage = client.get("/api/settings/ai/usage").json()
    assert usage["total_calls"] >= 1
    assert usage["rows"][0]["ok"] is True
    status = client.get("/api/settings/ai/status").json()
    assert status["provider"] == "mock"
    assert "模拟" in status["notice"]


def test_ai_mock_suggestion_and_ta_review(client):
    client.put("/api/settings/ai", json={
        "provider": "mock", "model_id": "mock-1", "monthly_budget": 0, "auto_confirm_send": True,
    })
    # KD 建议
    s = client.post("/api/kd/subjects", json={"name": "建议学科"}).json()
    t = client.post("/api/kd/topics", json={"subject_id": s["id"], "name": "建议知识点"}).json()
    task = client.post("/api/kd/tasks", json={"topic_id": t["id"], "title": "题"}).json()
    for _ in range(3):
        client.post(f"/api/kd/tasks/{task['id']}/attempts", json={
            "correct": False, "error_category": "concept_gap", "independent": True,
        })
    diag = client.post("/api/ai/kd/diagnose", params={"topic_id": t["id"], "confirm_send": True}).json()
    sugg = client.post(f"/api/ai/kd/diagnoses/{diag['id']}/suggestions", params={"confirm_send": True})
    assert sugg.status_code == 201
    assert len(sugg.json()["verification_tasks"]) >= 1

    # TA 复盘
    pid = client.post("/api/ta/projects", json={"name": "AI 复盘项目"}).json()["id"]
    client.post(f"/api/ta/projects/{pid}/tasks", json={"title": "任务1", "estimated_hours": 2})
    review = client.post(f"/api/ai/ta/projects/{pid}/review", params={"confirm_send": True})
    assert review.status_code == 201
    body = review.json()
    assert isinstance(body["facts"], list) and isinstance(body["speculations"], list)
    assert body["mock"] is True


def test_ai_fallback_to_rule_on_upstream_error(client):
    """配置一个指向不可达地址的 provider → AI 失败必须回退规则诊断而不是 500。"""
    client.put("/api/settings/ai", json={
        "provider": "openai-compat", "base_url": "http://127.0.0.1:9/v1", "api_key": "sk-test",
        "model_id": "whatever", "timeout_seconds": 5, "monthly_budget": 0, "auto_confirm_send": True,
    })
    s = client.post("/api/kd/subjects", json={"name": "回退学科"}).json()
    t = client.post("/api/kd/topics", json={"subject_id": s["id"], "name": "回退知识点"}).json()
    task = client.post("/api/kd/tasks", json={"topic_id": t["id"], "title": "题"}).json()
    for _ in range(3):
        client.post(f"/api/kd/tasks/{task['id']}/attempts", json={
            "correct": False, "error_category": "method_selection", "independent": True,
        })
    r = client.post("/api/ai/kd/diagnose", params={"topic_id": t["id"], "confirm_send": True})
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["source"] == "rule"
    assert "AI 调用失败" in data["rationale"] or "回退" in data["rationale"]


def test_cross_module_spawn_experiment(client):
    """四模块联动：KD 诊断 → 一键创建 ML 实验并建立链接。"""
    s = client.post("/api/kd/subjects", json={"name": "联动学科"}).json()
    t = client.post("/api/kd/topics", json={"subject_id": s["id"], "name": "联动知识点"}).json()
    task = client.post("/api/kd/tasks", json={"topic_id": t["id"], "title": "题"}).json()
    for _ in range(3):
        client.post(f"/api/kd/tasks/{task['id']}/attempts", json={
            "correct": False, "error_category": "retrieval_failure", "independent": True,
        })
    diag = client.post(f"/api/kd/topics/{t['id']}/diagnose").json()
    r = client.post(f"/api/ai/kd/diagnoses/{diag['id']}/spawn-experiment", params={
        "question": "间隔复习能否改善提取失败？",
        "strategy_a": "间隔复习", "strategy_b": "集中背诵",
    })
    assert r.status_code == 201
    exp_id = r.json()["experiment_id"]
    links = client.get("/api/links", params={"module": "kd", "ref_type": "diagnosis", "ref_id": diag["id"]}).json()
    assert any(lnk["to_ref_id"] == exp_id and lnk["relation"] == "spawned_from" for lnk in links)


def test_timeline_cursor_pagination(client):
    """游标分页：页间不重叠、顺序稳定、has_more 正确，且不受新增事件影响。"""
    for i in range(5):
        client.post("/api/dtm/decisions", json={"title": f"游标测试 {i}", "options": []})

    base = {"q": "游标测试", "limit": 2}
    p1 = client.get("/api/timeline", params=base).json()
    assert p1["total"] == 5
    assert len(p1["items"]) == 2
    assert p1["has_more"] is True
    assert p1["next_before_at"] and p1["next_before_id"]

    def fetch(params):
        return client.get("/api/timeline", params=params).json()

    p2 = fetch({**base, "before_at": p1["next_before_at"], "before_id": p1["next_before_id"]})
    p3 = fetch({**base, "before_at": p2["next_before_at"], "before_id": p2["next_before_id"]})

    seen1 = {e["ref_id"] for e in p1["items"]}
    seen2 = {e["ref_id"] for e in p2["items"]}
    seen3 = {e["ref_id"] for e in p3["items"]}
    assert not (seen1 & seen2) and not (seen2 & seen3) and not (seen1 & seen3)
    # 5 条事件全部覆盖且第三页到底
    assert p2["has_more"] is True
    assert p3["has_more"] is False and p3["next_before_at"] is None
    assert len(p1["items"]) + len(p2["items"]) + len(p3["items"]) == 5
    # 排序稳定：每页内部按 occurred_at DESC
    for page in (p1, p2):
        times = [e["occurred_at"] for e in page["items"]]
        assert times == sorted(times, reverse=True)

    # 游标翻页不受新增事件影响：新增一条后，用旧游标取下一页仍是原集合
    client.post("/api/dtm/decisions", json={"title": "游标测试 新增", "options": []})
    p2b = fetch({**base, "before_at": p1["next_before_at"], "before_id": p1["next_before_id"]})
    assert {e["ref_id"] for e in p2b["items"]} == seen2
