# -*- coding: utf-8 -*-
"""无 AI（provider=none）全链路冒烟：验证核心功能在完全不接云端 AI 时可用。

对运行中的 127.0.0.1:8000 执行；创建的实体以「冒烟」前缀命名，结束后逐一清理。
"""
import sys

import httpx

BASE = "http://127.0.0.1:8000/api"
c = httpx.Client(base_url=BASE, timeout=30)
ok_count = 0
failures = []


def check(name: str, cond: bool, extra: str = ""):
    global ok_count
    if cond:
        ok_count += 1
        print(f"  ✓ {name}")
    else:
        failures.append(name)
        print(f"  ✗ {name} {extra}")


print("== 0. AI 状态：确认无 AI 模式 ==")
st = c.get("/settings/ai/status").json()
check("provider=none", st["provider"] == "none", st)

print("== 1. KD：答题→规则诊断护栏→纠正→建议→验证闭环 ==")
s = c.post("/kd/subjects", json={"name": "冒烟-学科"}).json()
t1 = c.post("/kd/topics", json={"subject_id": s["id"], "name": "冒烟-知识点"}).json()
task = c.post("/kd/tasks", json={"topic_id": t1["id"], "title": "冒烟-题目"}).json()
c.post(f"/kd/tasks/{task['id']}/attempts", json={"correct": False, "error_category": "method_selection", "independent": True})
diag = c.post(f"/kd/topics/{t1['id']}/diagnose").json()
check("一次失败 → insufficient_data（不下结论护栏）", diag["category"] == "insufficient_data" and diag["confidence"] <= 0.25)
for _ in range(3):
    c.post(f"/kd/tasks/{task['id']}/attempts", json={"correct": False, "error_category": "method_selection", "independent": False})
diag2 = c.post(f"/kd/topics/{t1['id']}/diagnose").json()
check("补足样本 → 给出类别+备选解释", diag2["category"] == "method_selection" and len(diag2["alternatives"]) >= 1)
fixed = c.patch(f"/kd/diagnoses/{diag2['id']}", json={"corrected_category": "concept_gap", "correction_note": "冒烟纠正"}).json()
check("用户纠正生效", fixed["status"] == "user_confirmed")
# AI 分析端点在无 AI 时应明确拒绝（409），而不是假装工作
r_ai = c.post("/ai/kd/diagnose", params={"topic_id": t1["id"], "confirm_send": True})
check("AI 诊断在无 AI 时 409", r_ai.status_code == 409, f"got {r_ai.status_code}")
sugg = c.post("/kd/suggestions", json={"diagnosis_id": diag2["id"], "content": "冒烟-建议"}).json()
vt = c.post(f"/kd/suggestions/{sugg['id']}/verification-task", json={"title": "冒烟-验证任务"}).json()
res = c.post(f"/kd/suggestions/{sugg['id']}/verification-result", json={"success": True, "note": "通过"}).json()
check("建议→验证→有效 闭环", res["status"] == "effective")

print("== 2. ML：卡片→复习→学习步骤→统计 ==")
deck = c.post("/ml/decks", json={"name": "冒烟-卡组"}).json()
card = c.post("/ml/cards", json={"deck_id": deck["id"], "front": "冒烟-正面", "back": "背面"}).json()
r = c.post("/ml/reviews", json={"card_id": card["id"], "rating": 3, "duration_ms": 5000, "recall_ms": 2100}).json()
check("复习进入学习步骤 2/2（10 分钟）", r["state"]["state_str"] == "learning" and r["state"]["step"] == 1)
stats = c.get("/ml/stats").json()
check("统计含步骤细分", any(b["state"] == "learning" for b in stats["step_breakdown"]))

print("== 3. DTM：快照→预测→揭晓→复盘→校准 ==")
d = c.post("/dtm/decisions", json={"title": "冒烟-决策", "options": [{"key": "A", "label": "甲"}], "review_at": "2027-01-01T00:00:00Z"}).json()
snaps = c.get(f"/dtm/decisions/{d['id']}/snapshots").json()
check("创建即有不可覆盖快照", len(snaps) == 1)
p = c.post(f"/dtm/decisions/{d['id']}/predictions", json={"statement": "冒烟-预测", "probability": 0.7}).json()
c.patch(f"/dtm/predictions/{p['id']}", json={"resolved": True, "actual_note": "命中"})
c.post(f"/dtm/decisions/{d['id']}/reviews", json={"summary": "冒烟复盘", "process_score": 4})
cal = c.get("/dtm/calibration").json()
check("校准统计可用", cal["n_predictions"] >= 1)

print("== 4. TA：依赖完成→自动恢复（#3 新功能） ==")
pj = c.post("/ta/projects", json={"name": "冒烟-项目"}).json()
ta_ = c.post(f"/ta/projects/{pj['id']}/tasks", json={"title": "冒烟-上游"}).json()
tb = c.post(f"/ta/projects/{pj['id']}/tasks", json={"title": "冒烟-下游", "depends_on": [ta_["id"]]}).json()
c.patch(f"/ta/tasks/{tb['id']}", json={"status": "blocked"})
c.patch(f"/ta/tasks/{ta_['id']}", json={"status": "done"})
tb_now = c.get(f"/ta/tasks/{tb['id']}").json()
check("上游完成 → 下游自动恢复 doing", tb_now["status"] == "doing")
evs = c.get(f"/ta/tasks/{tb['id']}/events").json()
check("下游有 dependency_cleared 事件", any(e["type"] == "dependency_cleared" for e in evs))
rr = c.post(f"/ta/projects/{pj['id']}/rule-review")
check("规则复盘（无 AI）可用", rr.status_code == 201 and rr.json()["source"] == "rule")

print("== 5. 跨模块：时间线游标→证据→搜索→仪表盘 ==")
tl = c.get("/timeline", params={"limit": 2}).json()
check("时间线游标字段就绪", tl["has_more"] is True and tl["next_before_id"] is not None)
tl2 = c.get("/timeline", params={"limit": 2, "before_at": tl["next_before_at"], "before_id": tl["next_before_id"]}).json()
check("游标翻页页间不重叠", not ({e["id"] for e in tl["items"]} & {e["id"] for e in tl2["items"]}))
ev = c.post("/evidence", json={"module": "dtm", "ref_type": "decision", "ref_id": d["id"], "kind": "speculation", "content": "冒烟-推测"}).json()
check("证据记录", ev["kind"] == "speculation")
sr = c.get("/search", params={"q": "冒烟"}).json()
check("全局搜索", sr["total"] >= 3)
dash = c.get("/dashboard").json()
check("仪表盘统计", "cards_due" in dash["stats"])

print("== 6. 认证：启用→401→登录→放行→关闭 ==")
c.post("/auth/setup", json={"password": "smoke-pass-1"})
check("启用后业务 API 401", c.get("/dashboard").status_code == 401)
c.post("/auth/login", json={"password": "smoke-pass-1"})
check("登录后放行", c.get("/dashboard").status_code == 200)
c.post("/auth/disable", json={"password": "smoke-pass-1"})
check("关闭后恢复免登录", c.get("/dashboard").status_code == 200)

print("== 7. 数据导出/导入 ==")
exp = c.get("/data/export").json()
check("导出包含各业务表", "kd_topics" in exp["tables"] and "dtm_decisions" in exp["tables"])
imp = c.post("/data/import", json=exp)
check("导入往返", imp.status_code == 200 and imp.json()["ok"] is True)

print("== 8. 清理冒烟实体 ==")
for path in [
    f"/ta/projects/{pj['id']}", f"/dtm/decisions/{d['id']}",
    f"/ml/decks/{deck['id']}", f"/kd/subjects/{s['id']}",
]:
    r = c.delete(path)
    if r.status_code != 204:
        print(f"  ⚠ DELETE {path} -> {r.status_code} {r.text[:80]}")
sr2 = c.get("/search", params={"q": "冒烟-"}).json()
# 业务实体（知识点/卡组/决策/项目）应已删除；事件标题保留属审计设计
biz_left = [g for g in sr2["groups"] if g in ("知识点", "学习任务", "卡组", "卡片", "决策", "项目")]
check("冒烟业务实体已清理（事件日志按设计保留）", not biz_left, f"残留分组: {biz_left}")

print(f"\n结果：{ok_count} 通过，{len(failures)} 失败")
if failures:
    print("失败项：", failures)
    sys.exit(1)
print("无 AI（provider=none）全链路冒烟：全部通过 ✓")
