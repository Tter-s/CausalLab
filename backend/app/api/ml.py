"""Memory Laboratory API：卡组 / 卡片 / 复习（FSRS-6 官方调度）/ 统计 / 对照实验。"""
from __future__ import annotations

import random
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models import Card, Deck, ExpAssignment, ExpGroup, MemExperiment, ReviewLog, ReviewState
from app.schemas.ml import (
    AssignIn,
    CardIn,
    CardOut,
    CardUpdateIn,
    CardWithStateOut,
    DayCount,
    DeckIn,
    DeckOut,
    DueQueueOut,
    ExperimentIn,
    ExperimentOut,
    ExperimentResultsOut,
    ExperimentUpdateIn,
    GroupResult,
    IntervalBucket,
    MLStatsOut,
    ReviewIn,
    ReviewLogOut,
    ReviewResultOut,
    ReviewStateOut,
)
from app.services import scheduling
from app.services.base import utcnow
from app.services.events import record_event
from app.services.links import create_link

router = APIRouter(prefix="/ml", tags=["ml"])

EXPERIMENT_DISCLAIMER = (
    "注意：这是单人在真实生活中做的对照实验，不是严格控制的科学研究。样本小、条件无法完全控制，"
    "结果只能作为你个人的参考证据，不能证明某种方法对所有人更优，也不能排除其他因素（材料难度、当天状态等）的影响。"
)


def _state_out(db: Session, card_id: int, state_row: ReviewState | None) -> ReviewStateOut | None:
    if state_row is None:
        return None
    now = utcnow()
    s = scheduling.summary_from(state_row.fsrs_card, now)
    reps = int(db.scalar(select(func.count(ReviewLog.id)).where(ReviewLog.card_id == card_id)) or 0)
    lapses = int(db.scalar(select(func.count(ReviewLog.id)).where(ReviewLog.card_id == card_id, ReviewLog.rating == 1)) or 0)
    return ReviewStateOut(
        card_id=card_id,
        stability=s["stability"],
        difficulty=s["difficulty"],
        due_at=s["due_at"],
        last_review_at=s["last_review_at"],
        reps=reps,
        lapses=lapses,
        state_str=s["state_str"],
        retrievability=s["retrievability"],
    )


def _card_out(db: Session, card: Card, with_state: bool = False) -> CardOut | CardWithStateOut:
    base = CardOut.model_validate(card, from_attributes=True)
    if not with_state:
        return base
    state_row = db.scalar(select(ReviewState).where(ReviewState.card_id == card.id))
    out = CardWithStateOut(**base.model_dump())
    out.state = _state_out(db, card.id, state_row)
    return out


# ---------- 卡组 ----------
@router.get("/decks", response_model=list[DeckOut])
def list_decks(db: Session = Depends(get_db)):
    return list(db.scalars(select(Deck).order_by(Deck.id)))


@router.post("/decks", response_model=DeckOut, status_code=201)
def create_deck(payload: DeckIn, db: Session = Depends(get_db)):
    d = Deck(**payload.model_dump())
    db.add(d)
    db.flush()
    record_event(db, module="ml", event_type="deck.created", ref_type="deck", ref_id=d.id,
                 title=f"创建卡组：{d.name}")
    db.commit()
    db.refresh(d)
    return d


@router.delete("/decks/{deck_id}", status_code=204)
def delete_deck(deck_id: int, db: Session = Depends(get_db)):
    d = db.get(Deck, deck_id)
    if d is None:
        raise HTTPException(status_code=404, detail="卡组不存在")
    db.delete(d)
    db.commit()


# ---------- 卡片 ----------
@router.get("/cards", response_model=list[CardOut])
def list_cards(deck_id: int | None = None, db: Session = Depends(get_db)):
    stmt = select(Card).order_by(Card.id.desc())
    if deck_id is not None:
        stmt = stmt.where(Card.deck_id == deck_id)
    return list(db.scalars(stmt))


@router.post("/cards", response_model=CardOut, status_code=201)
def create_card(payload: CardIn, db: Session = Depends(get_db)):
    if db.get(Deck, payload.deck_id) is None:
        raise HTTPException(status_code=404, detail="卡组不存在")
    c = Card(**payload.model_dump())
    db.add(c)
    db.flush()
    # 新卡立即可复习
    db.add(ReviewState(card_id=c.id, fsrs_card=scheduling.new_card_dict(utcnow()), due_at=utcnow(), state_str="new"))
    db.commit()
    db.refresh(c)
    return c


@router.patch("/cards/{card_id}", response_model=CardOut)
def update_card(card_id: int, payload: CardUpdateIn, db: Session = Depends(get_db)):
    c = db.get(Card, card_id)
    if c is None:
        raise HTTPException(status_code=404, detail="卡片不存在")
    data = payload.model_dump(exclude_unset=True)
    for field in ("front", "back", "tags", "suspended"):
        if field in data and data[field] is not None:
            setattr(c, field, data[field])
    db.commit()
    db.refresh(c)
    return c


@router.delete("/cards/{card_id}", status_code=204)
def delete_card(card_id: int, db: Session = Depends(get_db)):
    c = db.get(Card, card_id)
    if c is None:
        raise HTTPException(status_code=404, detail="卡片不存在")
    db.delete(c)
    db.commit()


@router.get("/cards/{card_id}/logs", response_model=list[ReviewLogOut])
def card_logs(card_id: int, db: Session = Depends(get_db)):
    if db.get(Card, card_id) is None:
        raise HTTPException(status_code=404, detail="卡片不存在")
    return list(db.scalars(select(ReviewLog).where(ReviewLog.card_id == card_id).order_by(ReviewLog.reviewed_at)))


# ---------- 复习队列与复习 ----------
@router.get("/due", response_model=DueQueueOut)
def due_queue(limit: int = 20, deck_id: int | None = None, db: Session = Depends(get_db)):
    now = utcnow()
    stmt = (
        select(ReviewState)
        .join(Card, Card.id == ReviewState.card_id)
        .where(ReviewState.due_at <= now, Card.suspended.is_(False))
        .order_by(ReviewState.due_at)
        .limit(limit)
    )
    if deck_id is not None:
        stmt = stmt.where(Card.deck_id == deck_id)
    rows = list(db.scalars(stmt))
    total = int(
        db.scalar(
            select(func.count(ReviewState.id))
            .join(Card, Card.id == ReviewState.card_id)
            .where(ReviewState.due_at <= now, Card.suspended.is_(False))
        )
        or 0
    )
    cards: list[CardWithStateOut] = []
    for row in rows:
        card = db.get(Card, row.card_id)
        if card:
            out = _card_out(db, card, with_state=True)
            assert isinstance(out, CardWithStateOut)
            cards.append(out)
    return DueQueueOut(cards=cards, total_due=total)


@router.get("/cards/{card_id}/preview", response_model=dict)
def preview_intervals(card_id: int, db: Session = Depends(get_db)):
    """四种评分对应的间隔预览（用于复习按钮文案）。"""
    row = db.scalar(select(ReviewState).where(ReviewState.card_id == card_id))
    if db.get(Card, card_id) is None:
        raise HTTPException(status_code=404, detail="卡片不存在")
    return scheduling.preview_intervals(row.fsrs_card if row else None, utcnow())


@router.post("/reviews", response_model=ReviewResultOut, status_code=201)
def submit_review(payload: ReviewIn, db: Session = Depends(get_db)):
    now = utcnow()
    card = db.get(Card, payload.card_id)
    if card is None:
        raise HTTPException(status_code=404, detail="卡片不存在")
    state_row = db.scalar(select(ReviewState).where(ReviewState.card_id == payload.card_id))
    if state_row is None:
        state_row = ReviewState(card_id=payload.card_id, fsrs_card=scheduling.new_card_dict(now))
        db.add(state_row)
        db.flush()

    old_due = state_row.due_at
    new_state = scheduling.review(state_row.fsrs_card, payload.rating, now, payload.duration_ms)

    summary = scheduling.summary_from(new_state, now)
    # 统计历史 reps/lapses
    reps = int(db.scalar(select(func.count(ReviewLog.id)).where(ReviewLog.card_id == payload.card_id)) or 0) + 1
    lapses = int(
        db.scalar(
            select(func.count(ReviewLog.id)).where(ReviewLog.card_id == payload.card_id, ReviewLog.rating == 1)
        )
        or 0
    ) + (1 if payload.rating == 1 else 0)

    # 实验分组：若卡片被分配到实验组，记录到复习日志
    assignment = db.scalar(select(ExpAssignment).where(ExpAssignment.card_id == payload.card_id))
    experiment_id = assignment.experiment_id if assignment else None
    group_tag = None
    if assignment:
        group = db.get(ExpGroup, assignment.group_id)
        group_tag = group.name if group else None

    scheduled_days = None
    elapsed_days = None
    if old_due:
        pass
    due = summary["due_at"]
    if due:
        scheduled_days = round((due - now).total_seconds() / 86400, 4)
    if state_row.last_review_at:
        elapsed_days = round((now - state_row.last_review_at).total_seconds() / 86400, 4)

    state_row.fsrs_card = new_state
    state_row.stability = summary["stability"]
    state_row.difficulty = summary["difficulty"]
    state_row.due_at = due
    state_row.last_review_at = now
    state_row.reps = reps
    state_row.lapses = lapses
    state_row.state_str = summary["state_str"]

    log = ReviewLog(
        card_id=payload.card_id,
        rating=payload.rating,
        reviewed_at=now,
        duration_ms=payload.duration_ms,
        scheduled_days=scheduled_days,
        elapsed_days=elapsed_days,
        experiment_id=experiment_id,
        group_tag=group_tag,
    )
    db.add(log)
    db.flush()

    interval_display = scheduling.format_interval(scheduled_days or 0)
    record_event(
        db, module="ml", event_type="ml.review", ref_type="card", ref_id=card.id,
        title=f"复习卡片（评分 {payload.rating}，下次 {interval_display}）",
        detail={"experiment_id": experiment_id, "group_tag": group_tag},
    )
    db.commit()

    return ReviewResultOut(
        card_id=card.id,
        rating=payload.rating,
        due_at=due,
        interval_display=interval_display,
        state=ReviewStateOut(
            card_id=card.id,
            stability=summary["stability"],
            difficulty=summary["difficulty"],
            due_at=summary["due_at"],
            last_review_at=summary["last_review_at"],
            reps=reps,
            lapses=lapses,
            state_str=summary["state_str"],
            retrievability=scheduling.retrievability_now(new_state, utcnow()),
        ),
    )


# ---------- 统计 ----------
@router.get("/stats", response_model=MLStatsOut)
def ml_stats(db: Session = Depends(get_db)):
    now = utcnow()
    week_ago = now - timedelta(days=7)
    total_cards = int(db.scalar(select(func.count(Card.id))) or 0)
    due_now = int(
        db.scalar(
            select(func.count(ReviewState.id))
            .join(Card, Card.id == ReviewState.card_id)
            .where(ReviewState.due_at <= now, Card.suspended.is_(False))
        )
        or 0
    )
    logs_week = list(db.scalars(select(ReviewLog).where(ReviewLog.reviewed_at >= week_ago)))
    retention = None
    again_rate = None
    if logs_week:
        good = sum(1 for r in logs_week if r.rating >= 3)
        again = sum(1 for r in logs_week if r.rating == 1)
        retention = round(good / len(logs_week), 3)
        again_rate = round(again / len(logs_week), 3)

    # 近 14 天每日复习次数
    per_day: dict[str, int] = {}
    for i in range(13, -1, -1):
        day = (now - timedelta(days=i)).date().isoformat()
        per_day[day] = 0
    for r in db.scalars(select(ReviewLog).where(ReviewLog.reviewed_at >= now - timedelta(days=14))):
        key = r.reviewed_at.date().isoformat()
        if key in per_day:
            per_day[key] += 1

    # 间隔分布（当前 stability）
    buckets = [("≤1天", 0, 1), ("1-3天", 1, 3), ("3-7天", 3, 7), ("7-21天", 7, 21),
               ("21-60天", 21, 60), (">60天", 60, 1e9)]
    interval_dist = [IntervalBucket(label=lab, count=0) for lab, _, _ in buckets]
    maturity = {"new": 0, "learning": 0, "review": 0}
    for row in db.scalars(select(ReviewState).join(Card, Card.id == ReviewState.card_id).where(Card.suspended.is_(False))):
        if row.due_at is None:
            maturity["new"] += 1
            continue
        days = (row.due_at - now).total_seconds() / 86400
        st = row.state_str
        maturity[st if st in maturity else "review"] += 1
        for i, (_lab, lo, hi) in enumerate(buckets):
            if lo <= days < hi:
                interval_dist[i].count += 1
                break

    return MLStatsOut(
        total_cards=total_cards,
        due_now=due_now,
        reviews_last_7d=len(logs_week),
        retention_7d=retention,
        again_rate_7d=again_rate,
        reviews_per_day=[DayCount(date=k, count=v) for k, v in per_day.items()],
        interval_distribution=interval_dist,
        maturity=maturity,
    )


@router.get("/forgetting-curve", response_model=list[dict])
def forgetting_curve(deck_id: int | None = None, days: int = 30, db: Session = Depends(get_db)):
    """未来 N 天到期卡片数（复习负担预测）。"""
    now = utcnow()
    stmt = select(ReviewState).join(Card, Card.id == ReviewState.card_id).where(Card.suspended.is_(False))
    if deck_id:
        stmt = stmt.where(Card.deck_id == deck_id)
    out = []
    for i in range(days):
        day = now + timedelta(days=i)
        key = day.date().isoformat()
        cnt = 0
        for row in db.scalars(stmt):
            if row.due_at and row.due_at.date() == day.date():
                cnt += 1
        out.append({"date": key, "count": cnt})
    return out


# ---------- 对照实验 ----------
@router.get("/experiments", response_model=list[ExperimentOut])
def list_experiments(db: Session = Depends(get_db)):
    return list(db.scalars(select(MemExperiment).order_by(MemExperiment.id.desc())))


@router.post("/experiments", response_model=ExperimentOut, status_code=201)
def create_experiment(payload: ExperimentIn, db: Session = Depends(get_db)):
    e = MemExperiment(**payload.model_dump())
    db.add(e)
    db.flush()
    db.add(ExpGroup(experiment_id=e.id, name="A", strategy=payload.strategy_a))
    db.add(ExpGroup(experiment_id=e.id, name="B", strategy=payload.strategy_b))
    record_event(db, module="ml", event_type="experiment.created", ref_type="experiment", ref_id=e.id,
                 title=f"创建记忆实验：{payload.question[:60]}", importance=2)
    db.commit()
    db.refresh(e)
    return e


@router.patch("/experiments/{experiment_id}", response_model=ExperimentOut)
def update_experiment(experiment_id: int, payload: ExperimentUpdateIn, db: Session = Depends(get_db)):
    e = db.get(MemExperiment, experiment_id)
    if e is None:
        raise HTTPException(status_code=404, detail="实验不存在")
    data = payload.model_dump(exclude_unset=True)
    if data.get("status") == "running" and e.started_at is None:
        e.started_at = utcnow()
        e.ends_at = utcnow() + timedelta(days=e.delayed_test_days)
    for field in ("status", "notes"):
        if field in data and data[field] is not None:
            setattr(e, field, data[field])
    db.commit()
    db.refresh(e)
    return e


@router.post("/experiments/{experiment_id}/assign", response_model=dict, status_code=201)
def assign_cards(experiment_id: int, payload: AssignIn, db: Session = Depends(get_db)):
    """把选中的卡片随机等分成两组（随机分组由服务端完成）。"""
    e = db.get(MemExperiment, experiment_id)
    if e is None:
        raise HTTPException(status_code=404, detail="实验不存在")
    groups = list(db.scalars(select(ExpGroup).where(ExpGroup.experiment_id == experiment_id)))
    if len(groups) < 2:
        raise HTTPException(status_code=409, detail="实验分组缺失")
    card_ids = list(dict.fromkeys(payload.card_ids))
    for cid in card_ids:
        if db.get(Card, cid) is None:
            raise HTTPException(status_code=404, detail=f"卡片 {cid} 不存在")
    random.shuffle(card_ids)
    half = len(card_ids) // 2
    split = {"A": card_ids[:half], "B": card_ids[half:]}
    existing = {
        (a.card_id): a for a in db.scalars(select(ExpAssignment).where(ExpAssignment.experiment_id == experiment_id))
    }
    assigned = {"A": 0, "B": 0}
    for group_name, ids in split.items():
        group = next(g for g in groups if g.name == group_name)
        for cid in ids:
            if cid in existing:
                continue
            db.add(ExpAssignment(experiment_id=experiment_id, card_id=cid, group_id=group.id))
            row = db.scalar(select(ReviewState).where(ReviewState.card_id == cid))
            if row:
                row.experiment_id = experiment_id
                row.group_tag = group_name
            assigned[group_name] += 1
    if e.status == "setup":
        e.status = "running"
        if e.started_at is None:
            e.started_at = utcnow()
            e.ends_at = utcnow() + timedelta(days=e.delayed_test_days)
    record_event(db, module="ml", event_type="experiment.assigned", ref_type="experiment", ref_id=experiment_id,
                 title=f"随机分组 {assigned['A'] + assigned['B']} 张卡片（A={assigned['A']}, B={assigned['B']}）",
                 importance=2)
    db.commit()
    return {"assigned": assigned, "total": len(card_ids)}


@router.get("/experiments/{experiment_id}/results", response_model=ExperimentResultsOut)
def experiment_results(experiment_id: int, db: Session = Depends(get_db)):
    e = db.get(MemExperiment, experiment_id)
    if e is None:
        raise HTTPException(status_code=404, detail="实验不存在")
    groups = list(db.scalars(select(ExpGroup).where(ExpGroup.experiment_id == experiment_id).order_by(ExpGroup.name)))
    results: list[GroupResult] = []
    for g in groups:
        n_cards = int(db.scalar(select(func.count(ExpAssignment.id)).where(ExpAssignment.group_id == g.id)) or 0)
        logs = list(
            db.scalars(
                select(ReviewLog)
                .where(ReviewLog.experiment_id == experiment_id, ReviewLog.group_tag == g.name)
            )
        )
        again_rate = round(sum(1 for r in logs if r.rating == 1) / len(logs), 3) if logs else None
        mean_ms = round(sum(r.duration_ms for r in logs) / len(logs), 1) if logs else None
        results.append(
            GroupResult(
                name=g.name, strategy=g.strategy, n_cards=n_cards, n_reviews=len(logs),
                again_rate=again_rate, mean_duration_ms=mean_ms, delayed_test_pass_rate=None,
            )
        )
    diff_note = None
    rates = [r.again_rate for r in results if r.again_rate is not None]
    if len(rates) == 2 and all(r.n_reviews >= 5 for r in results):
        diff = round(rates[0] - rates[1], 3)
        diff_note = f"A 组遗忘率比 B 组高 {diff:+.0%}（负值表示 A 更好）。样本小，仅供参考。"
    return ExperimentResultsOut(
        experiment_id=experiment_id,
        groups=results,
        difference_note=diff_note,
        disclaimer=EXPERIMENT_DISCLAIMER,
    )


@router.post("/experiments/{experiment_id}/link-diagnosis/{diagnosis_id}", status_code=201)
def link_to_kd_diagnosis(experiment_id: int, diagnosis_id: int, db: Session = Depends(get_db)):
    """四模块联动：KD 诊断 → 创建/关联 ML 实验。"""
    e = db.get(MemExperiment, experiment_id)
    if e is None:
        raise HTTPException(status_code=404, detail="实验不存在")
    create_link(
        db, from_module="kd", from_ref_type="diagnosis", from_ref_id=diagnosis_id,
        to_module="ml", to_ref_type="experiment", to_ref_id=experiment_id,
        relation="spawned_from", note="由知识债务诊断派生的记忆实验",
    )
    record_event(db, module="sys", event_type="cross.link", ref_type="experiment", ref_id=experiment_id,
                 title=f"记忆实验 #{experiment_id} 已关联知识诊断 #{diagnosis_id}", importance=2)
    db.commit()
    return {"ok": True}
