"""Knowledge Debt API：学科 / 知识点 / 依赖图 / 学习任务 / 答题 / 诊断 / 建议与验证。

护栏：诊断永远可由用户纠正；样本不足时输出 insufficient_data；备选解释永远存在。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models import Attempt, Diagnosis, StudyTask, Subject, Suggestion, Topic, TopicEdge
from app.schemas.kd import (
    AlternativeOut,
    AttemptIn,
    AttemptOut,
    DiagnosisCorrectionIn,
    DiagnosisOut,
    GraphOut,
    StudyTaskIn,
    StudyTaskOut,
    SubjectIn,
    SubjectOut,
    SuggestionIn,
    SuggestionOut,
    TopicEdgeIn,
    TopicEdgeOut,
    TopicIn,
    TopicOut,
    TopicUpdate,
    VerificationResultIn,
)
from app.services.base import utcnow
from app.services.events import record_event
from app.services.kd_rules import CATEGORY_LABELS, AttemptFact, rule_diagnose
from app.services.links import add_evidence, links_for

router = APIRouter(prefix="/kd", tags=["kd"])


# ---------- 学科 ----------
@router.get("/subjects", response_model=list[SubjectOut])
def list_subjects(db: Session = Depends(get_db)):
    return list(db.scalars(select(Subject).order_by(Subject.id)))


@router.post("/subjects", response_model=SubjectOut, status_code=201)
def create_subject(payload: SubjectIn, db: Session = Depends(get_db)):
    s = Subject(**payload.model_dump())
    db.add(s)
    db.flush()
    record_event(db, module="kd", event_type="subject.created", ref_type="subject", ref_id=s.id,
                 title=f"创建学科：{s.name}", importance=1)
    db.commit()
    db.refresh(s)
    return s


@router.delete("/subjects/{subject_id}", status_code=204)
def delete_subject(subject_id: int, db: Session = Depends(get_db)):
    s = db.get(Subject, subject_id)
    if s is None:
        raise HTTPException(status_code=404, detail="学科不存在")
    db.delete(s)
    db.commit()


# ---------- 知识点 ----------
@router.get("/topics", response_model=list[TopicOut])
def list_topics(subject_id: int | None = None, db: Session = Depends(get_db)):
    stmt = select(Topic).order_by(Topic.id)
    if subject_id is not None:
        stmt = stmt.where(Topic.subject_id == subject_id)
    return list(db.scalars(stmt))


@router.post("/topics", response_model=TopicOut, status_code=201)
def create_topic(payload: TopicIn, db: Session = Depends(get_db)):
    if db.get(Subject, payload.subject_id) is None:
        raise HTTPException(status_code=404, detail="学科不存在")
    t = Topic(**payload.model_dump())
    db.add(t)
    db.flush()
    record_event(db, module="kd", event_type="topic.created", ref_type="topic", ref_id=t.id,
                 title=f"新增知识点：{t.name}")
    db.commit()
    db.refresh(t)
    return t


@router.patch("/topics/{topic_id}", response_model=TopicOut)
def update_topic(topic_id: int, payload: TopicUpdate, db: Session = Depends(get_db)):
    t = db.get(Topic, topic_id)
    if t is None:
        raise HTTPException(status_code=404, detail="知识点不存在")
    data = payload.model_dump(exclude_unset=True)
    for field in ("name", "description", "status"):
        if data.get(field) is not None:
            setattr(t, field, data[field])
    db.flush()
    db.commit()
    db.refresh(t)
    return t


@router.delete("/topics/{topic_id}", status_code=204)
def delete_topic(topic_id: int, db: Session = Depends(get_db)):
    t = db.get(Topic, topic_id)
    if t is None:
        raise HTTPException(status_code=404, detail="知识点不存在")
    db.delete(t)
    db.commit()


# ---------- 依赖图 ----------
@router.get("/graph", response_model=GraphOut)
def get_graph(subject_id: int | None = None, db: Session = Depends(get_db)):
    topics = list(db.scalars(select(Topic).order_by(Topic.id)))
    if subject_id is not None:
        topics = [t for t in topics if t.subject_id == subject_id]
    ids = {t.id for t in topics}
    edges = [e for e in db.scalars(select(TopicEdge)) if e.from_topic_id in ids and e.to_topic_id in ids]
    subjects = list(db.scalars(select(Subject).order_by(Subject.id)))
    return GraphOut(
        nodes=[TopicOut.model_validate(t, from_attributes=True) for t in topics],
        edges=[TopicEdgeOut.model_validate(e, from_attributes=True) for e in edges],
        subjects=[SubjectOut.model_validate(s, from_attributes=True) for s in subjects],
    )


@router.post("/edges", response_model=TopicEdgeOut, status_code=201)
def create_edge(payload: TopicEdgeIn, db: Session = Depends(get_db)):
    if payload.from_topic_id == payload.to_topic_id:
        raise HTTPException(status_code=422, detail="不能创建自依赖")
    for tid in (payload.from_topic_id, payload.to_topic_id):
        if db.get(Topic, tid) is None:
            raise HTTPException(status_code=404, detail=f"知识点 {tid} 不存在")
    e = TopicEdge(**payload.model_dump())
    db.add(e)
    db.commit()
    db.refresh(e)
    return e


@router.delete("/edges/{edge_id}", status_code=204)
def delete_edge(edge_id: int, db: Session = Depends(get_db)):
    e = db.get(TopicEdge, edge_id)
    if e is None:
        raise HTTPException(status_code=404, detail="依赖关系不存在")
    db.delete(e)
    db.commit()


# ---------- 学习任务 ----------
@router.get("/tasks", response_model=list[StudyTaskOut])
def list_tasks(topic_id: int | None = None, status: str | None = None, db: Session = Depends(get_db)):
    stmt = select(StudyTask).order_by(StudyTask.id.desc())
    if topic_id is not None:
        stmt = stmt.where(StudyTask.topic_id == topic_id)
    if status:
        stmt = stmt.where(StudyTask.status == status)
    return list(db.scalars(stmt))


@router.post("/tasks", response_model=StudyTaskOut, status_code=201)
def create_task(payload: StudyTaskIn, db: Session = Depends(get_db)):
    if db.get(Topic, payload.topic_id) is None:
        raise HTTPException(status_code=404, detail="知识点不存在")
    t = StudyTask(**payload.model_dump())
    db.add(t)
    db.flush()
    record_event(db, module="kd", event_type="task.created", ref_type="study_task", ref_id=t.id,
                 title=f"新建学习任务：{t.title}")
    db.commit()
    db.refresh(t)
    return t


@router.patch("/tasks/{task_id}", response_model=StudyTaskOut)
def update_task(task_id: int, payload: dict, db: Session = Depends(get_db)):
    t = db.get(StudyTask, task_id)
    if t is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    for field in ("title", "question_text", "my_answer", "status"):
        if field in payload and payload[field] is not None:
            setattr(t, field, payload[field])
    db.flush()
    db.commit()
    db.refresh(t)
    return t


@router.delete("/tasks/{task_id}", status_code=204)
def delete_task(task_id: int, db: Session = Depends(get_db)):
    t = db.get(StudyTask, task_id)
    if t is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    db.delete(t)
    db.commit()


# ---------- 答题记录 ----------
@router.get("/tasks/{task_id}/attempts", response_model=list[AttemptOut])
def list_attempts(task_id: int, db: Session = Depends(get_db)):
    if db.get(StudyTask, task_id) is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    return list(db.scalars(select(Attempt).where(Attempt.task_id == task_id).order_by(Attempt.occurred_at)))


@router.get("/topics/{topic_id}/attempts", response_model=list[AttemptOut])
def list_topic_attempts(topic_id: int, db: Session = Depends(get_db)):
    return list(db.scalars(select(Attempt).where(Attempt.topic_id == topic_id).order_by(Attempt.occurred_at)))


@router.post("/tasks/{task_id}/attempts", response_model=AttemptOut, status_code=201)
def record_attempt(task_id: int, payload: AttemptIn, db: Session = Depends(get_db)):
    task = db.get(StudyTask, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    a = Attempt(
        task_id=task_id,
        topic_id=task.topic_id,
        correct=payload.correct,
        error_category=payload.error_category if not payload.correct else "none",
        independent=payload.independent,
        duration_minutes=payload.duration_minutes,
        notes=payload.notes,
        occurred_at=payload.occurred_at or utcnow(),
    )
    db.add(a)
    db.flush()
    record_event(
        db, module="kd", event_type="attempt.recorded", ref_type="topic", ref_id=task.topic_id,
        title=f"记录答题（{'正确' if a.correct else '错误'}，{'独立' if a.independent else '非独立'}）",
        detail={"attempt_id": a.id, "task": task.title,
                "error_category": a.error_category if not a.correct else None},
    )
    db.commit()
    db.refresh(a)
    return a


# ---------- 诊断 ----------
def _run_rule_diagnosis(db: Session, topic_id: int) -> Diagnosis:
    attempts = list(db.scalars(select(Attempt).where(Attempt.topic_id == topic_id).order_by(Attempt.occurred_at)))
    facts = [AttemptFact(id=a.id, correct=a.correct, error_category=a.error_category,
                         independent=a.independent, notes=a.notes) for a in attempts]
    result = rule_diagnose(facts)
    diag = Diagnosis(
        topic_id=topic_id,
        category=result["category"],
        confidence=result["confidence"],
        rationale=result["rationale"],
        evidence_attempts=result["evidence_attempt_ids"],
        alternatives=result["alternatives"],
        basis_attempt_count=result["basis_attempt_count"],
        source="rule",
        status="provisional",
    )
    db.add(diag)
    db.flush()
    label = CATEGORY_LABELS.get(result["category"], result["category"])
    record_event(db, module="kd", event_type="diagnosis.created", ref_type="topic", ref_id=topic_id,
                 title=f"规则诊断：{label}（置信度 {result['confidence']:.0%}）",
                 importance=2, detail={"diagnosis_id": diag.id})
    add_evidence(
        db, module="kd", ref_type="diagnosis", ref_id=diag.id, kind="fact",
        content=f"规则诊断依据 {result['basis_attempt_count']} 条答题记录：{result['rationale']}",
        source="规则诊断引擎", confidence=result["confidence"],
    )
    return diag


@router.post("/topics/{topic_id}/diagnose", response_model=DiagnosisOut, status_code=201)
def diagnose_topic(topic_id: int, db: Session = Depends(get_db)):
    """规则诊断（无 AI / 未配置 AI 时使用）。AI 版见 /api/ai/kd/diagnose。"""
    if db.get(Topic, topic_id) is None:
        raise HTTPException(status_code=404, detail="知识点不存在")
    diag = _run_rule_diagnosis(db, topic_id)
    db.commit()
    db.refresh(diag)
    return _diag_out(db, diag)


def _diag_out(db: Session, diag: Diagnosis) -> DiagnosisOut:
    return DiagnosisOut(
        id=diag.id,
        topic_id=diag.topic_id,
        category=diag.category,  # type: ignore[arg-type]
        confidence=diag.confidence,
        rationale=diag.rationale,
        evidence_attempts=diag.evidence_attempts or [],
        alternatives=[AlternativeOut(**a) for a in (diag.alternatives or [])],
        basis_attempt_count=diag.basis_attempt_count,
        source=diag.source,  # type: ignore[arg-type]
        status=diag.status,  # type: ignore[arg-type]
        corrected_category=diag.corrected_category,
        correction_note=diag.correction_note,
        created_at=diag.created_at,
        updated_at=diag.updated_at,
    )


@router.get("/diagnoses", response_model=list[DiagnosisOut])
def list_diagnoses(topic_id: int | None = None, db: Session = Depends(get_db)):
    stmt = select(Diagnosis).order_by(Diagnosis.id.desc())
    if topic_id is not None:
        stmt = stmt.where(Diagnosis.topic_id == topic_id)
    return [_diag_out(db, d) for d in db.scalars(stmt)]


@router.patch("/diagnoses/{diagnosis_id}", response_model=DiagnosisOut)
def correct_diagnosis(diagnosis_id: int, payload: DiagnosisCorrectionIn, db: Session = Depends(get_db)):
    """用户纠正 AI/规则诊断：记录为 user_confirmed 状态与 user_correction 证据。"""
    diag = db.get(Diagnosis, diagnosis_id)
    if diag is None:
        raise HTTPException(status_code=404, detail="诊断不存在")
    diag.corrected_category = payload.corrected_category
    diag.correction_note = payload.correction_note
    diag.status = "user_confirmed"
    db.flush()
    record_event(db, module="kd", event_type="diagnosis.corrected", ref_type="topic", ref_id=diag.topic_id,
                 title=f"用户纠正诊断为「{CATEGORY_LABELS.get(payload.corrected_category, payload.corrected_category)}」",
                 importance=2, detail={"diagnosis_id": diag.id, "note": payload.correction_note})
    add_evidence(
        db, module="kd", ref_type="diagnosis", ref_id=diag.id, kind="user_correction",
        content=f"用户把诊断从「{CATEGORY_LABELS.get(diag.category, diag.category)}」改为"
                f"「{CATEGORY_LABELS.get(payload.corrected_category, payload.corrected_category)}」。"
                f"备注：{payload.correction_note or '无'}",
        source="用户",
    )
    db.commit()
    db.refresh(diag)
    return _diag_out(db, diag)


# ---------- 建议与验证闭环 ----------
@router.get("/suggestions", response_model=list[SuggestionOut])
def list_suggestions(diagnosis_id: int | None = None, db: Session = Depends(get_db)):
    stmt = select(Suggestion).order_by(Suggestion.id.desc())
    if diagnosis_id is not None:
        stmt = stmt.where(Suggestion.diagnosis_id == diagnosis_id)
    return list(db.scalars(stmt))


@router.post("/suggestions", response_model=SuggestionOut, status_code=201)
def create_suggestion(payload: SuggestionIn, db: Session = Depends(get_db)):
    if db.get(Diagnosis, payload.diagnosis_id) is None:
        raise HTTPException(status_code=404, detail="诊断不存在")
    s = Suggestion(diagnosis_id=payload.diagnosis_id, content=payload.content)
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


@router.post("/suggestions/{suggestion_id}/verification-task", response_model=StudyTaskOut, status_code=201)
def create_verification_task(suggestion_id: int, payload: dict, db: Session = Depends(get_db)):
    """为建议生成验证任务（关联该诊断对应的知识点）。"""
    s = db.get(Suggestion, suggestion_id)
    if s is None:
        raise HTTPException(status_code=404, detail="建议不存在")
    diag = db.get(Diagnosis, s.diagnosis_id)
    if diag is None:
        raise HTTPException(status_code=404, detail="诊断不存在")
    title = str(payload.get("title") or "验证任务：独立完成一道同类题").strip()
    task = StudyTask(
        topic_id=diag.topic_id,
        title=title[:300],
        question_text=str(payload.get("question_text") or ""),
        is_verification=True,
        source_suggestion_id=s.id,
        verification_status="pending",
    )
    db.add(task)
    s.status = "testing"
    db.flush()
    record_event(db, module="kd", event_type="verification_task.created", ref_type="topic", ref_id=diag.topic_id,
                 title=f"生成验证任务：{task.title}", importance=2,
                 detail={"suggestion_id": s.id, "study_task_id": task.id})
    db.commit()
    db.refresh(task)
    return task


@router.post("/suggestions/{suggestion_id}/verification-result", response_model=SuggestionOut)
def record_verification_result(suggestion_id: int, payload: VerificationResultIn, db: Session = Depends(get_db)):
    """提交验证任务结果：判断建议是否有效，形成“建议→验证→结论”闭环。"""
    s = db.get(Suggestion, suggestion_id)
    if s is None:
        raise HTTPException(status_code=404, detail="建议不存在")
    s.status = "effective" if payload.success else "ineffective"
    s.effectiveness_note = payload.note
    diag = db.get(Diagnosis, s.diagnosis_id)
    if diag:
        for t in db.scalars(select(StudyTask).where(StudyTask.source_suggestion_id == s.id)):
            t.verification_status = "success" if payload.success else "failure"
        record_event(db, module="kd", event_type="suggestion.verified", ref_type="topic", ref_id=diag.topic_id,
                     title=f"验证结论：建议{'有效' if payload.success else '未生效'}", importance=2,
                     detail={"suggestion_id": s.id, "note": payload.note})
        add_evidence(db, module="kd", ref_type="diagnosis", ref_id=diag.id,
                     kind="fact" if payload.success else "speculation",
                     content=f"验证任务结果：{'独立完成成功，建议有效' if payload.success else '未通过独立验证，建议需要调整'}。"
                             f"{payload.note}",
                     source="验证任务", confidence=0.7 if payload.success else 0.4)
    db.commit()
    db.refresh(s)
    return s


@router.get("/topics/{topic_id}/links")
def topic_links(topic_id: int, db: Session = Depends(get_db)):
    return list(links_for(db, "kd", "topic", topic_id))
