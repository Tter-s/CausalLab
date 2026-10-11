"""AI 分析 API。所有端点共用规则：
- confirm_send=false 且未开启“自动确认”时返回 428 + 发送内容预览（隐私闸门）；
- provider=none 时返回 409；
- MockProvider 模式输出固定模拟数据并标注；
- AI 结果经 Pydantic 校验后由服务层写库，并记录 EvidenceRecord（kind=ai_analysis）。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import ai_error_to_http, get_db
from app.models import (
    Attempt,
    Counterfactual,
    Decision,
    DecisionReview,
    Diagnosis,
    ExpGroup,
    Hypothesis,
    HypothesisObservation,
    ImprovementLoop,
    MemExperiment,
    Prediction,
    Project,
    ProjectReview,
    Topic,
)
from app.services.ai import (
    AIBudgetExceeded,
    AIConfirmRequired,
    AIError,
    AINotConfigured,
    run_structured,
)
from app.services.ai import schemas as ai_s
from app.services.ai.schemas import (
    AICounterfactualOut,
    AIDiagnosisOut,
    AIDTMReviewOut,
    AIHypothesisDesignOut,
    AILoopReviewOut,
    AISuggestionOut,
    AITAReviewOut,
)
from app.services.base import utcnow
from app.services.events import record_event
from app.services.kd_rules import CATEGORY_LABELS, AttemptFact, rule_diagnose, rule_suggestions
from app.services.links import add_evidence, create_link

router = APIRouter(prefix="/ai", tags=["ai"])


def _guard(exc: AIError) -> HTTPException:
    return ai_error_to_http(exc)


# ================= KD 诊断 =================
@router.post("/kd/diagnose", status_code=201)
async def ai_diagnose(topic_id: int, confirm_send: bool = False, db: Session = Depends(get_db)):
    topic = db.get(Topic, topic_id)
    if topic is None:
        raise HTTPException(status_code=404, detail="知识点不存在")
    attempts = list(db.scalars(select(Attempt).where(Attempt.topic_id == topic_id).order_by(Attempt.occurred_at)))

    attempt_lines = [
        f"- 记录#{a.id}：{'答对' if a.correct else '答错'}，"
        f"{'独立完成' if a.independent else '未独立完成(有辅助)'}，"
        f"错误类别：{a.error_category if not a.correct else '无'}"
        + (f"，备注：{a.notes[:80]}" if a.notes else "")
        for a in attempts
    ]
    user_prompt = (
        f"知识点：{topic.name}\n描述：{topic.description or '无'}\n"
        f"答题记录（共 {len(attempts)} 条）：\n" + ("\n".join(attempt_lines) if attempt_lines else "（无记录）")
    )

    ai_used = False
    try:
        parsed, resp = await run_structured(
            db, task_type="kd_diagnosis", system=ai_s.DIAGNOSIS_SYSTEM, user=user_prompt,
            schema=AIDiagnosisOut, confirm_send=confirm_send,
        )
        ai_used = True
        category = parsed.category
        if category not in CATEGORY_LABELS:
            category = "other"
        # 校验 evidence_attempt_ids 只能引用该知识点的记录
        valid_ids = {a.id for a in attempts}
        evidence_ids = [i for i in parsed.evidence_attempt_ids if i in valid_ids]
        rationale = parsed.rationale
        alternatives = [a.model_dump() for a in parsed.alternatives]
        confidence = min(1.0, max(0.0, parsed.confidence))
        source = "ai"
        mock_note = "（MockProvider 模拟输出）" if resp.mock else ""
    except AIConfirmRequired:
        raise
    except (AINotConfigured, AIBudgetExceeded) as exc:
        # 非瞬时错误：直接返回给前端，不做规则回退（用户需要明确的配置/预算提示）
        raise _guard(exc) from exc
    except AIError as exc:
        # 瞬时错误（上游不可达/输出不合法）→ 回退规则诊断，AI 故障不导致基础功能不可用
        rule = rule_diagnose([AttemptFact(id=a.id, correct=a.correct, error_category=a.error_category,
                                          independent=a.independent, notes=a.notes) for a in attempts])
        category, confidence = rule["category"], rule["confidence"]
        rationale = f"（AI 调用失败，已回退规则诊断：{exc.user_message}）{rule['rationale']}"
        alternatives, evidence_ids, source = rule["alternatives"], rule["evidence_attempt_ids"], "rule"
        mock_note = ""

    diag = Diagnosis(
        topic_id=topic_id,
        category=category,
        confidence=confidence,
        rationale=rationale,
        evidence_attempts=evidence_ids,
        alternatives=alternatives,
        basis_attempt_count=len(attempts),
        source=source,
        status="provisional",
    )
    db.add(diag)
    db.flush()
    label = CATEGORY_LABELS.get(category, category)
    record_event(db, module="kd", event_type="diagnosis.created", ref_type="topic", ref_id=topic_id,
                 title=f"{'AI' if ai_used else '规则'}诊断：{label}（置信度 {confidence:.0%}）",
                 importance=2, detail={"diagnosis_id": diag.id, "mock": mock_note != ""})
    add_evidence(
        db, module="kd", ref_type="diagnosis", ref_id=diag.id,
        kind="ai_analysis" if ai_used else "fact",
        content=f"{'AI' if ai_used else '规则'}诊断（基于 {len(attempts)} 条答题记录）：{rationale}",
        source="AI 分析" if ai_used else "规则诊断引擎", confidence=confidence,
    )
    db.commit()
    db.refresh(diag)
    return {
        "id": diag.id, "topic_id": diag.topic_id, "category": diag.category, "confidence": diag.confidence,
        "rationale": diag.rationale, "evidence_attempts": diag.evidence_attempts,
        "alternatives": diag.alternatives, "basis_attempt_count": diag.basis_attempt_count,
        "source": diag.source, "status": diag.status, "ai_mock": mock_note != "",
    }


# ================= KD 建议 =================
@router.post("/kd/diagnoses/{diagnosis_id}/suggestions", status_code=201)
async def ai_suggestions(diagnosis_id: int, confirm_send: bool = False, db: Session = Depends(get_db)):
    diag = db.get(Diagnosis, diagnosis_id)
    if diag is None:
        raise HTTPException(status_code=404, detail="诊断不存在")
    label = CATEGORY_LABELS.get(diag.category, diag.category)
    user_prompt = (
        f"诊断类别：{label}\n置信度：{diag.confidence:.0%}\n诊断依据：{diag.rationale}\n"
        f"用户纠正：{diag.correction_note or '无'}"
    )
    try:
        parsed, resp = await run_structured(
            db, task_type="kd_suggestion", system=ai_s.SUGGESTION_SYSTEM, user=user_prompt,
            schema=AISuggestionOut, confirm_send=confirm_send,
        )
        suggestions, tasks = parsed.suggestions, parsed.verification_tasks
        mock = resp.mock
    except AIError as exc:
        if isinstance(exc, AIConfirmRequired):
            raise _guard(exc) from exc
        rule = rule_suggestions(diag.category)
        suggestions, tasks, mock = rule["suggestions"], rule["verification_tasks"], False
        suggestions = [f"（AI 不可用，规则建议）{s}" for s in suggestions]
    return {"suggestions": suggestions, "verification_tasks": tasks, "mock": mock}


# ================= TA 复盘 =================
@router.post("/ta/projects/{project_id}/review", status_code=201)
async def ai_project_review(project_id: int, confirm_send: bool = False, db: Session = Depends(get_db)):
    from app.api.ta import project_stats

    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="项目不存在")
    stats = project_stats(project_id, db).model_dump()

    user_prompt = (
        f"项目：{project.name}\n描述：{project.description or '无'}\n"
        f"过程统计：任务总数 {stats['tasks_total']}，完成 {stats['tasks_done']}，阻塞 {stats['tasks_blocked']}；"
        f"总预估 {stats['total_estimated_hours']}h，总实际 {stats['total_actual_hours']}h；"
        f"平均实际/预估比 {stats['avg_overrun_ratio']}；累计阻塞 {stats['blocked_minutes_total']} 分钟；"
        f"返工 {stats['rework_count']} 次，中断 {stats['interrupted_count']} 次，需求变化 {stats['requirement_change_count']} 次。\n"
        f"各任务明细：{[(r['title'], r['status'], r['estimated_hours'], r['actual_hours'], r['overrun_ratio']) for r in stats['per_task']]}\n"
        f"事件类型计数：{stats['event_type_counts']}"
    )
    try:
        parsed, resp = await run_structured(
            db, task_type="ta_review", system=ai_s.TA_REVIEW_SYSTEM, user=user_prompt,
            schema=AITAReviewOut, confirm_send=confirm_send,
        )
        review_data = parsed.model_dump()
        source = "ai"
        mock = resp.mock
    except (AIConfirmRequired, AINotConfigured, AIBudgetExceeded) as exc:
        raise _guard(exc) from exc
    except AIError as exc:
        raise HTTPException(status_code=502, detail=f"AI 复盘失败，可使用规则复盘端点：{exc.user_message}") from exc

    r = ProjectReview(project_id=project_id, source=source, **review_data)
    db.add(r)
    db.flush()
    record_event(db, module="ta", event_type="project.reviewed", ref_type="project", ref_id=project_id,
                 title=f"AI 复盘报告{'（模拟）' if mock else ''}", importance=3)
    add_evidence(db, module="ta", ref_type="project_review", ref_id=r.id, kind="ai_analysis",
                 content=review_data["summary"], source="AI 复盘")
    db.commit()
    db.refresh(r)
    return {"id": r.id, **review_data, "mock": mock}


# ================= DTM 复盘 =================
@router.post("/dtm/decisions/{decision_id}/review", status_code=201)
async def ai_decision_review(decision_id: int, confirm_send: bool = False, db: Session = Depends(get_db)):
    decision = db.get(Decision, decision_id)
    if decision is None:
        raise HTTPException(status_code=404, detail="决策不存在")
    preds = list(db.scalars(select(Prediction).where(Prediction.decision_id == decision_id)))
    pred_lines = [
        f"- 预测#{p.id}：{p.statement}（概率 {p.probability:.0%}，"
        f"结果：{'命中' if p.resolved else ('未命中' if p.resolved is not None else '未揭晓')}）"
        for p in preds
    ]
    user_prompt = (
        f"决策：{decision.title}\n背景：{decision.context}\n目标：{decision.goals}\n"
        f"备选方案：{decision.options}\n当时依据：{decision.basis}\n已知风险：{decision.risks}\n"
        f"预测记录：\n" + ("\n".join(pred_lines) if pred_lines else "（无量化预测）")
    )
    try:
        parsed, resp = await run_structured(
            db, task_type="dtm_review", system=ai_s.DTM_REVIEW_SYSTEM, user=user_prompt,
            schema=AIDTMReviewOut, confirm_send=confirm_send,
        )
        review_data = parsed.model_dump()
        mock = resp.mock
    except (AIConfirmRequired, AINotConfigured, AIBudgetExceeded) as exc:
        raise _guard(exc) from exc
    except AIError as exc:
        raise HTTPException(status_code=502, detail=f"AI 复盘失败：{exc.user_message}") from exc

    r = DecisionReview(
        decision_id=decision_id, source="ai", reviewed_at=utcnow(),
        summary=review_data["summary"], process_score=review_data["process_score"],
        lessons=review_data["lessons"], bias_flags=review_data["bias_flags"],
    )
    db.add(r)
    decision.status = "reviewed"
    decision.reviewed_at = utcnow()
    db.flush()
    record_event(db, module="dtm", event_type="decision.reviewed", ref_type="decision", ref_id=decision_id,
                 title=f"AI 决策复盘{'（模拟）' if mock else ''}：{decision.title}", importance=3)
    add_evidence(db, module="dtm", ref_type="decision_review", ref_id=r.id, kind="ai_analysis",
                 content=review_data["summary"], source="AI 复盘")
    db.commit()
    db.refresh(r)
    return {"id": r.id, **review_data, "mock": mock}


# ================= DTM 反事实 =================
@router.post("/dtm/decisions/{decision_id}/counterfactual", status_code=201)
async def ai_counterfactual(decision_id: int, scenario: str, confirm_send: bool = False,
                            db: Session = Depends(get_db)):
    decision = db.get(Decision, decision_id)
    if decision is None:
        raise HTTPException(status_code=404, detail="决策不存在")
    user_prompt = (
        f"决策：{decision.title}\n背景：{decision.context}\n备选方案：{decision.options}\n"
        f"当时依据：{decision.basis}\n已知风险：{decision.risks}\n\n"
        f"要推演的反事实情景：{scenario}"
    )
    try:
        parsed, resp = await run_structured(
            db, task_type="dtm_counterfactual", system=ai_s.COUNTERFACTUAL_SYSTEM, user=user_prompt,
            schema=AICounterfactualOut, confirm_send=confirm_send,
        )
        analysis = parsed.analysis + ("；注意：" + "；".join(parsed.caveats) if parsed.caveats else "")
        mock = resp.mock
    except (AIConfirmRequired, AINotConfigured, AIBudgetExceeded) as exc:
        raise _guard(exc) from exc
    except AIError as exc:
        raise HTTPException(status_code=502, detail=f"AI 推演失败：{exc.user_message}") from exc

    c = Counterfactual(decision_id=decision_id, scenario=scenario, analysis=analysis,
                       is_hypothetical=True, source="ai")
    db.add(c)
    record_event(db, module="dtm", event_type="decision.counterfactual", ref_type="decision", ref_id=decision_id,
                 title=f"AI 反事实推演（假设{'，模拟' if mock else ''}）：{scenario[:50]}", importance=1)
    db.commit()
    db.refresh(c)
    return {"id": c.id, "scenario": c.scenario, "analysis": c.analysis,
            "is_hypothetical": True, "mock": mock}


# ================= 假设设计 =================
@router.post("/hypotheses/{hypothesis_id}/design", status_code=200)
async def ai_hypothesis_design(hypothesis_id: int, confirm_send: bool = False, db: Session = Depends(get_db)):
    h = db.get(Hypothesis, hypothesis_id)
    if h is None:
        raise HTTPException(status_code=404, detail="假设不存在")
    user_prompt = f"假设：{h.statement}\n理由：{h.rationale or '无'}\n判据：{h.criteria or '未设置'}"
    try:
        parsed, resp = await run_structured(
            db, task_type="hyp_design", system=ai_s.HYP_DESIGN_SYSTEM, user=user_prompt,
            schema=AIHypothesisDesignOut, confirm_send=confirm_send,
        )
        design = parsed.model_dump()
        mock = resp.mock
    except (AIConfirmRequired, AINotConfigured, AIBudgetExceeded) as exc:
        raise _guard(exc) from exc
    except AIError as exc:
        raise HTTPException(status_code=502, detail=f"AI 设计失败：{exc.user_message}") from exc
    h.design = design
    db.commit()
    return {"design": design, "mock": mock}


# ================= 改进循环复盘 =================
@router.post("/loops/{loop_id}/review", status_code=200)
async def ai_loop_review(loop_id: int, confirm_send: bool = False, db: Session = Depends(get_db)):
    loop = db.get(ImprovementLoop, loop_id)
    if loop is None:
        raise HTTPException(status_code=404, detail="改进循环不存在")
    obs = list(db.scalars(select(HypothesisObservation)))
    obs = [o for o in obs if o.hypothesis_id == loop.hypothesis_id] if loop.hypothesis_id else []
    obs_lines = [f"- {o.observed_at.date()}：{o.value}" + (f"（{o.note}）" if o.note else "") for o in obs]
    user_prompt = (
        f"改进循环：{loop.title}\n问题：{loop.problem}\n干预措施：{loop.intervention or '未记录'}\n"
        f"收集到的数据：\n" + ("\n".join(obs_lines) if obs_lines else "（无量化数据）") +
        f"\n当前阶段：{loop.current_stage}"
    )
    try:
        parsed, resp = await run_structured(
            db, task_type="loop_review", system=ai_s.LOOP_REVIEW_SYSTEM, user=user_prompt,
            schema=AILoopReviewOut, confirm_send=confirm_send,
        )
        review = parsed.model_dump()
        mock = resp.mock
    except (AIConfirmRequired, AINotConfigured, AIBudgetExceeded) as exc:
        raise _guard(exc) from exc
    except AIError as exc:
        raise HTTPException(status_code=502, detail=f"AI 复盘失败：{exc.user_message}") from exc
    if review["verdict"] in ("effective", "ineffective", "uncertain"):
        loop.verdict = review["verdict"]
        loop.outcome_note = review["reasoning"]
    db.commit()
    return {**review, "mock": mock}


# ================= 跨模块联动 =================
@router.post("/kd/diagnoses/{diagnosis_id}/spawn-experiment", status_code=201)
def spawn_experiment_from_diagnosis(diagnosis_id: int, question: str, strategy_a: str, strategy_b: str,
                                    db: Session = Depends(get_db)):
    """KD 诊断 → 一键创建记忆实验并建立跨模块链接。"""
    diag = db.get(Diagnosis, diagnosis_id)
    if diag is None:
        raise HTTPException(status_code=404, detail="诊断不存在")
    e = MemExperiment(question=question, strategy_a=strategy_a, strategy_b=strategy_b, metric="delayed_test")
    db.add(e)
    db.flush()
    db.add(ExpGroup(experiment_id=e.id, name="A", strategy=strategy_a))
    db.add(ExpGroup(experiment_id=e.id, name="B", strategy=strategy_b))
    create_link(db, from_module="kd", from_ref_type="diagnosis", from_ref_id=diagnosis_id,
                to_module="ml", to_ref_type="experiment", to_ref_id=e.id,
                relation="spawned_from", note="由知识债务诊断派生的记忆实验")
    record_event(db, module="sys", event_type="cross.spawn_experiment", ref_type="experiment", ref_id=e.id,
                 title=f"由诊断 #{diagnosis_id} 创建记忆实验：{question[:50]}", importance=2)
    db.commit()
    db.refresh(e)
    return {"experiment_id": e.id, "question": e.question}
