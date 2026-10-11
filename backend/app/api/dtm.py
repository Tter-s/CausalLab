"""Decision Time Machine API。

关键设计：
- 快照只追加（append-only），任何 API 都不提供修改/删除快照的能力；
- 修改决策 = 生成新快照，历史可完整回放；
- 结果不能简单判定决策对错：复盘单列“决策过程质量分”，校准分析只对概率预测本身。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models import (
    Counterfactual,
    Decision,
    DecisionReview,
    DecisionSnapshot,
    DecisionUpdate,
    Prediction,
)
from app.schemas.cross import EventOut
from app.schemas.dtm import (
    CalibrationBin,
    CalibrationOut,
    CounterfactualIn,
    CounterfactualOut,
    DecisionDetailOut,
    DecisionIn,
    DecisionOut,
    DecisionReviewIn,
    DecisionReviewOut,
    DecisionUpdateIn,
    DecisionUpdateOut,
    DecisionUpdateRecordIn,
    PredictionIn,
    PredictionOut,
    PredictionResolveIn,
    SnapshotOut,
)
from app.services.base import utcnow
from app.services.calibration import CAVEAT, brier_score, calibration_bins
from app.services.events import events_for, record_event
from app.services.links import links_for

router = APIRouter(prefix="/dtm", tags=["dtm"])


def _serialize_decision(d: Decision) -> DecisionOut:
    return DecisionOut(
        id=d.id,
        title=d.title,
        context=d.context,
        goals=d.goals,
        options=d.options or [],
        basis=d.basis,
        risks=d.risks,
        status=d.status,  # type: ignore[arg-type]
        review_at=d.review_at,
        reviewed_at=d.reviewed_at,
        created_at=d.created_at,
        updated_at=d.updated_at,
    )


def _snapshot(db: Session, decision: Decision, reason: str) -> DecisionSnapshot:
    snap = DecisionSnapshot(
        decision_id=decision.id,
        reason=reason,
        payload={
            "title": decision.title,
            "context": decision.context,
            "goals": decision.goals,
            "options": decision.options,
            "basis": decision.basis,
            "risks": decision.risks,
            "review_at": decision.review_at.isoformat() if decision.review_at else None,
            "status": decision.status,
        },
        snapshot_at=utcnow(),
    )
    db.add(snap)
    db.flush()
    return snap


def _get_decision(db: Session, decision_id: int) -> Decision:
    d = db.get(Decision, decision_id)
    if d is None:
        raise HTTPException(status_code=404, detail="决策不存在")
    return d


@router.get("/decisions", response_model=list[DecisionOut])
def list_decisions(status: str | None = None, db: Session = Depends(get_db)):
    stmt = select(Decision).order_by(Decision.updated_at.desc())
    if status:
        stmt = stmt.where(Decision.status == status)
    return [_serialize_decision(d) for d in db.scalars(stmt)]


@router.post("/decisions", response_model=DecisionOut, status_code=201)
def create_decision(payload: DecisionIn, db: Session = Depends(get_db)):
    now = utcnow()
    d = Decision(
        title=payload.title,
        context=payload.context,
        goals=payload.goals,
        options=[o.model_dump() for o in payload.options],
        basis=payload.basis,
        risks=payload.risks,
        review_at=payload.review_at,
        created_at=now,
        updated_at=now,
    )
    db.add(d)
    db.flush()
    _snapshot(db, d, "created")
    record_event(
        db,
        module="dtm",
        event_type="decision.created",
        ref_type="decision",
        ref_id=d.id,
        title=f"创建决策：{d.title}",
        importance=2,
        detail={"options": [o.get("label") for o in d.options]},
    )
    db.commit()
    db.refresh(d)
    return _serialize_decision(d)


@router.get("/decisions/{decision_id}", response_model=DecisionDetailOut)
def get_decision(decision_id: int, db: Session = Depends(get_db)):
    d = _get_decision(db, decision_id)
    detail = DecisionDetailOut(**_serialize_decision(d).model_dump())
    detail.predictions = [
        PredictionOut.model_validate(p, from_attributes=True)
        for p in db.scalars(select(Prediction).where(Prediction.decision_id == d.id).order_by(Prediction.id))
    ]
    detail.updates = [
        DecisionUpdateOut.model_validate(u, from_attributes=True)
        for u in db.scalars(
            select(DecisionUpdate).where(DecisionUpdate.decision_id == d.id).order_by(DecisionUpdate.occurred_at)
        )
    ]
    detail.reviews = [
        DecisionReviewOut.model_validate(r, from_attributes=True)
        for r in db.scalars(
            select(DecisionReview).where(DecisionReview.decision_id == d.id).order_by(DecisionReview.reviewed_at)
        )
    ]
    detail.counterfactuals = [
        CounterfactualOut.model_validate(c, from_attributes=True)
        for c in db.scalars(select(Counterfactual).where(Counterfactual.decision_id == d.id))
    ]
    detail.snapshots = [
        SnapshotOut.model_validate(s, from_attributes=True)
        for s in db.scalars(
            select(DecisionSnapshot).where(DecisionSnapshot.decision_id == d.id).order_by(DecisionSnapshot.id)
        )
    ]
    return detail


@router.patch("/decisions/{decision_id}", response_model=DecisionOut)
def update_decision(decision_id: int, payload: DecisionUpdateIn, db: Session = Depends(get_db)):
    d = _get_decision(db, decision_id)
    changed = []
    data = payload.model_dump(exclude_unset=True)
    # 快照里的可变字段
    for field in ("title", "context", "goals", "basis", "risks"):
        if data.get(field) is not None and getattr(d, field) != data[field]:
            setattr(d, field, data[field])
            changed.append(field)
    if data.get("options") is not None:
        d.options = [o.model_dump() if hasattr(o, "model_dump") else o for o in payload.options or []]  # type: ignore[union-attr]
        changed.append("options")
    if "review_at" in data and data["review_at"] is not None:
        d.review_at = payload.review_at
        changed.append("review_at")
    if data.get("status") is not None:
        d.status = data["status"]
        changed.append("status")
    if changed:
        d.updated_at = utcnow()
        _snapshot(db, d, "updated")
        record_event(
            db,
            module="dtm",
            event_type="decision.updated",
            ref_type="decision",
            ref_id=d.id,
            title=f"更新决策：{d.title}",
            detail={"fields": changed},
            importance=1,
        )
        db.commit()
        db.refresh(d)
    return _serialize_decision(d)


@router.delete("/decisions/{decision_id}", status_code=204)
def delete_decision(decision_id: int, db: Session = Depends(get_db)):
    d = _get_decision(db, decision_id)
    db.delete(d)
    record_event(db, module="sys", event_type="decision.deleted", ref_type="decision", ref_id=decision_id,
                 title=f"删除决策 #{decision_id}（其快照一并删除）")
    db.commit()


@router.get("/decisions/{decision_id}/snapshots", response_model=list[SnapshotOut])
def list_snapshots(decision_id: int, db: Session = Depends(get_db)):
    _get_decision(db, decision_id)
    return list(
        db.scalars(
            select(DecisionSnapshot)
            .where(DecisionSnapshot.decision_id == decision_id)
            .order_by(DecisionSnapshot.id)
        )
    )


# ---------- 预测 ----------
@router.post("/decisions/{decision_id}/predictions", response_model=PredictionOut, status_code=201)
def add_prediction(decision_id: int, payload: PredictionIn, db: Session = Depends(get_db)):
    d = _get_decision(db, decision_id)
    p = Prediction(decision_id=d.id, statement=payload.statement, option_key=payload.option_key,
                   probability=payload.probability)
    db.add(p)
    db.flush()
    record_event(db, module="dtm", event_type="prediction.added", ref_type="decision", ref_id=d.id,
                 title=f"记录预测（{payload.probability:.0%}）：{payload.statement[:60]}", importance=1)
    db.commit()
    db.refresh(p)
    return p


@router.patch("/predictions/{prediction_id}", response_model=PredictionOut)
def resolve_prediction(prediction_id: int, payload: PredictionResolveIn, db: Session = Depends(get_db)):
    p = db.get(Prediction, prediction_id)
    if p is None:
        raise HTTPException(status_code=404, detail="预测不存在")
    p.resolved = payload.resolved
    p.actual_note = payload.actual_note
    p.resolved_at = utcnow()
    db.flush()
    record_event(db, module="dtm", event_type="prediction.resolved", ref_type="decision", ref_id=p.decision_id,
                 title=f"预测揭晓（{'命中' if payload.resolved else '未命中'}，当初 {p.probability:.0%}）",
                 importance=2, detail={"prediction_id": p.id})
    db.commit()
    db.refresh(p)
    return p


# ---------- 决策时间线（新信息） ----------
@router.post("/decisions/{decision_id}/updates", response_model=DecisionUpdateOut, status_code=201)
def add_update(decision_id: int, payload: DecisionUpdateRecordIn, db: Session = Depends(get_db)):
    d = _get_decision(db, decision_id)
    u = DecisionUpdate(
        decision_id=d.id,
        content=payload.content,
        source=payload.source,
        significance=payload.significance,
        occurred_at=payload.occurred_at or utcnow(),
    )
    db.add(u)
    db.flush()
    record_event(db, module="dtm", event_type="decision.update_added", ref_type="decision", ref_id=d.id,
                 title=f"新信息（{payload.significance}）：{payload.content[:60]}", importance=2)
    db.commit()
    db.refresh(u)
    return u


# ---------- 复盘 ----------
@router.post("/decisions/{decision_id}/reviews", response_model=DecisionReviewOut, status_code=201)
def review_decision(decision_id: int, payload: DecisionReviewIn, db: Session = Depends(get_db)):
    d = _get_decision(db, decision_id)
    r = DecisionReview(
        decision_id=d.id,
        summary=payload.summary,
        process_score=payload.process_score,
        lessons=payload.lessons,
        bias_flags=payload.bias_flags,
        source="manual",
        reviewed_at=utcnow(),
    )
    db.add(r)
    d.status = "reviewed"
    d.reviewed_at = utcnow()
    d.updated_at = utcnow()
    db.flush()
    record_event(db, module="dtm", event_type="decision.reviewed", ref_type="decision", ref_id=d.id,
                 title=f"决策复盘：{d.title}", importance=3,
                 detail={"process_score": payload.process_score})
    db.commit()
    db.refresh(r)
    return r


@router.get("/due-reviews", response_model=list[DecisionOut])
def due_reviews(db: Session = Depends(get_db)):
    """已到复盘时间但尚未复盘的决策。"""
    now = utcnow()
    rows = list(
        db.scalars(
            select(Decision)
            .where(Decision.status == "open", Decision.review_at.is_not(None), Decision.review_at <= now)
            .order_by(Decision.review_at)
        )
    )
    return [_serialize_decision(d) for d in rows]


# ---------- 校准 ----------
@router.get("/calibration", response_model=CalibrationOut)
def calibration(db: Session = Depends(get_db)):
    preds = list(db.scalars(select(Prediction).where(Prediction.resolved.is_not(None))))
    data = [(p.probability, bool(p.resolved)) for p in preds]
    bins = [CalibrationBin(**b) for b in calibration_bins(data)]
    return CalibrationOut(
        n_predictions=len(data),
        brier_score=round(brier_score(data), 4) if data else 0.0,
        bins=bins,
        caveat=CAVEAT,
    )


# ---------- 反事实 ----------
@router.post("/decisions/{decision_id}/counterfactuals", response_model=CounterfactualOut, status_code=201)
def add_counterfactual(decision_id: int, payload: CounterfactualIn, db: Session = Depends(get_db)):
    d = _get_decision(db, decision_id)
    c = Counterfactual(
        decision_id=d.id,
        scenario=payload.scenario,
        analysis=payload.analysis,
        is_hypothetical=True,  # 恒为假设推演
        source="manual",
    )
    db.add(c)
    db.flush()
    record_event(db, module="dtm", event_type="decision.counterfactual", ref_type="decision", ref_id=d.id,
                 title=f"反事实推演（假设）：{payload.scenario[:60]}", importance=1,
                 detail={"is_hypothetical": True})
    db.commit()
    db.refresh(c)
    return c


@router.get("/decisions/{decision_id}/events", response_model=list[EventOut])
def decision_events(decision_id: int, db: Session = Depends(get_db)):
    _get_decision(db, decision_id)
    return list(events_for(db, "dtm", "decision", decision_id))


@router.get("/decisions/{decision_id}/links")
def decision_links(decision_id: int, db: Session = Depends(get_db)):
    _get_decision(db, decision_id)
    return list(links_for(db, "dtm", "decision", decision_id))
