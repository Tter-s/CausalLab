"""跨模块 API：统一事件时间线 / 证据 / 实体链接 / 假设实验室 / 改进循环 / 搜索 / 仪表盘。"""
from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models import (
    Card,
    Decision,
    Deck,
    EventLog,
    Hypothesis,
    HypothesisObservation,
    ImprovementLoop,
    LoopStage,
    Project,
    ReviewState,
    Setting,
    StudyTask,
    Task,
    Topic,
)
from app.schemas.cross import (
    DashboardOut,
    DayCount,
    EventOut,
    EventPage,
    EvidenceIn,
    EvidenceOut,
    GroupComparison,
    HypothesisAnalysisOut,
    HypothesisIn,
    HypothesisOut,
    HypothesisUpdateIn,
    LinkIn,
    LinkOut,
    LoopIn,
    LoopOut,
    LoopStageIn,
    LoopStageOut,
    LoopUpdateIn,
    ObservationIn,
    ObservationOut,
    SearchHit,
    SearchOut,
)
from app.services import calibration as calib
from app.services.base import utcnow
from app.services.events import count_events, events_for, record_event
from app.services.links import add_evidence, create_link, evidence_for, links_for

router = APIRouter(tags=["cross"])

STAGE_LABELS = {
    "observe": "发现问题",
    "hypothesize": "提出假设",
    "intervene": "设计干预",
    "measure": "执行与收集数据",
    "review": "复盘",
    "adjust": "修改策略",
}


# ================= 事件时间线 =================
@router.get("/timeline", response_model=EventPage)
def timeline(
    module: str | None = None,
    q: str | None = None,
    days: int | None = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    stmt = select(EventLog).order_by(EventLog.occurred_at.desc(), EventLog.id.desc())
    if module:
        stmt = stmt.where(EventLog.module == module)
    if days:
        stmt = stmt.where(EventLog.occurred_at >= utcnow() - timedelta(days=days))
    if q:
        stmt = stmt.where(EventLog.title.like(f"%{q}%"))
    total = int(db.scalar(select(func.count()).select_from(stmt.subquery())) or 0)
    items = list(db.scalars(stmt.limit(limit).offset(offset)))
    return EventPage(items=[EventOut.model_validate(e, from_attributes=True) for e in items], total=total)


@router.get("/timeline/entity", response_model=list[EventOut])
def entity_events(module: str, ref_type: str, ref_id: int, db: Session = Depends(get_db)):
    return list(events_for(db, module, ref_type, ref_id))


# ================= 证据 =================
@router.get("/evidence")
def get_evidence(module: str, ref_type: str, ref_id: int, db: Session = Depends(get_db)):
    return list(evidence_for(db, module, ref_type, ref_id))


@router.post("/evidence", response_model=EvidenceOut, status_code=201)
def create_evidence(payload: EvidenceIn, db: Session = Depends(get_db)):
    rec = add_evidence(
        db, module=payload.module, ref_type=payload.ref_type, ref_id=payload.ref_id,
        kind=payload.kind, content=payload.content, source=payload.source, confidence=payload.confidence,
    )
    db.commit()
    db.refresh(rec)
    return EvidenceOut.model_validate(rec, from_attributes=True)


# ================= 链接 =================
@router.get("/links")
def get_links(module: str, ref_type: str, ref_id: int, db: Session = Depends(get_db)):
    return list(links_for(db, module, ref_type, ref_id))


@router.post("/links", response_model=LinkOut, status_code=201)
def create_link_api(payload: LinkIn, db: Session = Depends(get_db)):
    link = create_link(
        db, from_module=payload.from_module, from_ref_type=payload.from_ref_type,
        from_ref_id=payload.from_ref_id, to_module=payload.to_module,
        to_ref_type=payload.to_ref_type, to_ref_id=payload.to_ref_id,
        relation=payload.relation, note=payload.note,
    )
    record_event(db, module="sys", event_type="cross.link", ref_type=payload.from_ref_type,
                 ref_id=payload.from_ref_id,
                 title=f"建立关联：{payload.from_module}:{payload.from_ref_type}#{payload.from_ref_id} → "
                       f"{payload.to_module}:{payload.to_ref_type}#{payload.to_ref_id}",
                 importance=1)
    db.commit()
    db.refresh(link)
    return LinkOut.model_validate(link, from_attributes=True)


# ================= 假设实验室 =================
@router.get("/hypotheses", response_model=list[HypothesisOut])
def list_hypotheses(db: Session = Depends(get_db)):
    return list(db.scalars(select(Hypothesis).order_by(Hypothesis.id.desc())))


@router.post("/hypotheses", response_model=HypothesisOut, status_code=201)
def create_hypothesis(payload: HypothesisIn, db: Session = Depends(get_db)):
    h = Hypothesis(**payload.model_dump())
    db.add(h)
    db.flush()
    record_event(db, module="hyp", event_type="hypothesis.created", ref_type="hypothesis", ref_id=h.id,
                 title=f"创建假设：{payload.statement[:60]}", importance=2)
    db.commit()
    db.refresh(h)
    return h


@router.get("/hypotheses/{hypothesis_id}", response_model=HypothesisOut)
def get_hypothesis(hypothesis_id: int, db: Session = Depends(get_db)):
    h = db.get(Hypothesis, hypothesis_id)
    if h is None:
        raise HTTPException(status_code=404, detail="假设不存在")
    return h


@router.patch("/hypotheses/{hypothesis_id}", response_model=HypothesisOut)
def update_hypothesis(hypothesis_id: int, payload: HypothesisUpdateIn, db: Session = Depends(get_db)):
    h = db.get(Hypothesis, hypothesis_id)
    if h is None:
        raise HTTPException(status_code=404, detail="假设不存在")
    data = payload.model_dump(exclude_unset=True)
    for field in ("statement", "rationale", "design", "criteria", "status"):
        if field in data and data[field] is not None:
            setattr(h, field, data[field])
    db.flush()
    if data.get("status"):
        record_event(db, module="hyp", event_type="hypothesis.status", ref_type="hypothesis", ref_id=h.id,
                     title=f"假设状态更新为 {data['status']}", importance=2,
                     detail={"statement": h.statement[:80]})
    db.commit()
    db.refresh(h)
    return h


@router.get("/hypotheses/{hypothesis_id}/observations", response_model=list[ObservationOut])
def list_observations(hypothesis_id: int, db: Session = Depends(get_db)):
    h = db.get(Hypothesis, hypothesis_id)
    if h is None:
        raise HTTPException(status_code=404, detail="假设不存在")
    return list(
        db.scalars(
            select(HypothesisObservation)
            .where(HypothesisObservation.hypothesis_id == hypothesis_id)
            .order_by(HypothesisObservation.observed_at)
        )
    )


@router.post("/hypotheses/{hypothesis_id}/observations", response_model=ObservationOut, status_code=201)
def add_observation(hypothesis_id: int, payload: ObservationIn, db: Session = Depends(get_db)):
    h = db.get(Hypothesis, hypothesis_id)
    if h is None:
        raise HTTPException(status_code=404, detail="假设不存在")
    o = HypothesisObservation(
        hypothesis_id=hypothesis_id,
        value=payload.value,
        context=payload.context,
        note=payload.note,
        observed_at=payload.observed_at or utcnow(),
    )
    db.add(o)
    db.flush()
    record_event(db, module="hyp", event_type="observation.added", ref_type="hypothesis", ref_id=hypothesis_id,
                 title=f"记录观察值 {payload.value}", importance=1)
    db.commit()
    db.refresh(o)
    return o


@router.get("/hypotheses/{hypothesis_id}/analysis", response_model=HypothesisAnalysisOut)
def analyze_hypothesis(hypothesis_id: int, group_key: str | None = None, db: Session = Depends(get_db)):
    """描述性统计：整体均值 + 可选分组对比。永远附带局限性说明（相关≠因果）。"""
    h = db.get(Hypothesis, hypothesis_id)
    if h is None:
        raise HTTPException(status_code=404, detail="假设不存在")
    obs = list(
        db.scalars(
            select(HypothesisObservation)
            .where(HypothesisObservation.hypothesis_id == hypothesis_id)
            .order_by(HypothesisObservation.observed_at)
        )
    )
    values = [o.value for o in obs]
    overall_mean, overall_std = calib.mean_std(values)

    groups: list[GroupComparison] = []
    if group_key:
        buckets: dict[str, list[float]] = {}
        for o in obs:
            key = str((o.context or {}).get(group_key, "未标注"))
            buckets.setdefault(key, []).append(o.value)
        for label, vals in sorted(buckets.items()):
            m, s = calib.mean_std(vals)
            groups.append(
                GroupComparison(
                    label=label,
                    n=len(vals),
                    mean=round(m, 4) if m is not None else 0.0,
                    std=round(s, 4) if s is not None else None,
                )
            )

    verdict_hint = "数据不足，无法给出倾向。"
    if overall_mean is not None and len(values) >= 5:
        if len(groups) >= 2:
            best = max(groups, key=lambda g: g.mean)
            verdict_hint = (
                f"分组「{best.label}」均值最高（{best.mean}），可能支持假设方向；"
                "但这是相关性描述，不能证明因果，请继续积累数据。"
            )
        else:
            verdict_hint = (
                f"已有 {len(values)} 条观察，整体均值 {overall_mean:.2f}。"
                "请设置分组字段（group_key）对比不同条件下的差异。"
            )

    return HypothesisAnalysisOut(
        hypothesis_id=hypothesis_id,
        n_observations=len(values),
        overall_mean=round(overall_mean, 4) if overall_mean is not None else None,
        overall_std=round(overall_std, 4) if overall_std is not None else None,
        groups=groups,
        limitations=calib.HYP_LIMITATIONS,
        verdict_hint=verdict_hint,
    )


# ================= 改进循环 =================
@router.get("/loops", response_model=list[LoopOut])
def list_loops(status: str | None = None, db: Session = Depends(get_db)):
    stmt = select(ImprovementLoop).order_by(ImprovementLoop.id.desc())
    if status:
        stmt = stmt.where(ImprovementLoop.status == status)
    return list(db.scalars(stmt))


@router.post("/loops", response_model=LoopOut, status_code=201)
def create_loop(payload: LoopIn, db: Session = Depends(get_db)):
    loop = ImprovementLoop(title=payload.title, problem=payload.problem)
    db.add(loop)
    db.flush()
    db.add(LoopStage(loop_id=loop.id, stage="observe", content={"problem": payload.problem}))
    record_event(db, module="loop", event_type="loop.created", ref_type="loop", ref_id=loop.id,
                 title=f"开启改进循环：{payload.title}", importance=2)
    db.commit()
    db.refresh(loop)
    return loop


@router.get("/loops/{loop_id}", response_model=LoopOut)
def get_loop(loop_id: int, db: Session = Depends(get_db)):
    loop = db.get(ImprovementLoop, loop_id)
    if loop is None:
        raise HTTPException(status_code=404, detail="改进循环不存在")
    return loop


@router.patch("/loops/{loop_id}", response_model=LoopOut)
def update_loop(loop_id: int, payload: LoopUpdateIn, db: Session = Depends(get_db)):
    loop = db.get(ImprovementLoop, loop_id)
    if loop is None:
        raise HTTPException(status_code=404, detail="改进循环不存在")
    data = payload.model_dump(exclude_unset=True)
    for field in ("title", "problem", "current_stage", "intervention", "outcome_note",
                  "hypothesis_id", "status", "verdict"):
        if field in data and data[field] is not None:
            setattr(loop, field, data[field])
    if data.get("status") == "closed" and loop.verdict:
        record_event(db, module="loop", event_type="loop.closed", ref_type="loop", ref_id=loop.id,
                     title=f"改进循环关闭（结论：{loop.verdict}）：{loop.title}", importance=3)
    db.commit()
    db.refresh(loop)
    return loop


@router.get("/loops/{loop_id}/stages", response_model=list[LoopStageOut])
def loop_stages(loop_id: int, db: Session = Depends(get_db)):
    loop = db.get(ImprovementLoop, loop_id)
    if loop is None:
        raise HTTPException(status_code=404, detail="改进循环不存在")
    return list(db.scalars(select(LoopStage).where(LoopStage.loop_id == loop_id).order_by(LoopStage.id)))


@router.post("/loops/{loop_id}/stages", response_model=LoopStageOut, status_code=201)
def advance_loop(loop_id: int, payload: LoopStageIn, db: Session = Depends(get_db)):
    """推进循环阶段：发现问题 → 提出假设 → 设计干预 → 执行 → 复盘 → 调整。"""
    loop = db.get(ImprovementLoop, loop_id)
    if loop is None:
        raise HTTPException(status_code=404, detail="改进循环不存在")
    stage = LoopStage(loop_id=loop_id, stage=payload.stage, content=payload.content)
    db.add(stage)
    loop.current_stage = payload.stage
    if payload.stage == "intervene" and isinstance(payload.content.get("intervention"), str):
        loop.intervention = payload.content["intervention"]
    if payload.stage == "hypothesize" and payload.content.get("hypothesis_id"):
        loop.hypothesis_id = int(payload.content["hypothesis_id"])
    db.flush()
    record_event(db, module="loop", event_type=f"loop.stage.{payload.stage}", ref_type="loop", ref_id=loop_id,
                 title=f"改进循环推进到「{STAGE_LABELS.get(payload.stage, payload.stage)}」", importance=2)
    db.commit()
    db.refresh(stage)
    return stage


# ================= 搜索 =================
@router.get("/search", response_model=SearchOut)
def search(q: str, db: Session = Depends(get_db)):
    like = f"%{q}%"
    groups: dict[str, list[SearchHit]] = {}
    total = 0

    def add(group: str, module: str, ref_type: str, ref_id: int, title: str, snippet: str = "") -> None:
        nonlocal total
        groups.setdefault(group, []).append(
            SearchHit(module=module, ref_type=ref_type, ref_id=ref_id, title=title, snippet=snippet[:120])  # type: ignore[arg-type]
        )
        total += 1

    for t in db.scalars(select(Topic).where(or_(Topic.name.like(like), Topic.description.like(like))).limit(5)):
        add("知识点", "kd", "topic", t.id, t.name, t.description)
    for st in db.scalars(
        select(StudyTask).where(or_(StudyTask.title.like(like), StudyTask.question_text.like(like))).limit(5)
    ):
        add("学习任务", "kd", "study_task", st.id, st.title)
    for dk in db.scalars(select(Deck).where(or_(Deck.name.like(like), Deck.description.like(like))).limit(5)):
        add("卡组", "ml", "deck", dk.id, dk.name, dk.description)
    for cd in db.scalars(select(Card).where(or_(Card.front.like(like), Card.back.like(like))).limit(5)):
        add("卡片", "ml", "card", cd.id, cd.front[:60])
    for dec in db.scalars(
        select(Decision).where(or_(Decision.title.like(like), Decision.context.like(like))).limit(5)
    ):
        add("决策", "dtm", "decision", dec.id, dec.title, dec.context)
    for p in db.scalars(
        select(Project).where(or_(Project.name.like(like), Project.description.like(like))).limit(5)
    ):
        add("项目", "ta", "project", p.id, p.name, p.description)
    for tk in db.scalars(select(Task).where(or_(Task.title.like(like), Task.description.like(like))).limit(5)):
        add("任务", "ta", "task", tk.id, tk.title)
    for h in db.scalars(select(Hypothesis).where(Hypothesis.statement.like(like)).limit(5)):
        add("假设", "hyp", "hypothesis", h.id, h.statement[:80])
    for loop in db.scalars(
        select(ImprovementLoop)
        .where(or_(ImprovementLoop.title.like(like), ImprovementLoop.problem.like(like)))
        .limit(5)
    ):
        add("改进循环", "loop", "loop", loop.id, loop.title, loop.problem)
    for e in (
        db.scalars(select(EventLog).where(EventLog.title.like(like)).order_by(EventLog.occurred_at.desc()).limit(5))
    ):
        add("事件", e.module, e.ref_type, e.ref_id, e.title)  # type: ignore[arg-type]  # noqa: E501
    return SearchOut(query=q, groups=groups, total=total)


# ================= 仪表盘 =================
@router.get("/dashboard", response_model=DashboardOut)
def dashboard(db: Session = Depends(get_db)):
    now = utcnow()
    week_ago = now - timedelta(days=7)

    stats: dict[str, int] = {
        "decisions_open": int(db.scalar(select(func.count(Decision.id)).where(Decision.status == "open")) or 0),
        "decisions_due": int(
            db.scalar(
                select(func.count(Decision.id)).where(
                    Decision.status == "open", Decision.review_at.is_not(None), Decision.review_at <= now
                )
            )
            or 0
        ),
        "cards_due": int(db.scalar(select(func.count(ReviewState.id)).where(ReviewState.due_at <= now)) or 0),
        "tasks_blocked": int(db.scalar(select(func.count(Task.id)).where(Task.status == "blocked")) or 0),
        "tasks_doing": int(db.scalar(select(func.count(Task.id)).where(Task.status == "doing")) or 0),
        "projects_active": int(db.scalar(select(func.count(Project.id)).where(Project.status == "active")) or 0),
        "topics_weak": int(db.scalar(select(func.count(Topic.id)).where(Topic.status == "weak")) or 0),
        "hypotheses_testing": int(
            db.scalar(select(func.count(Hypothesis.id)).where(Hypothesis.status == "testing")) or 0
        ),
        "loops_active": int(
            db.scalar(select(func.count(ImprovementLoop.id)).where(ImprovementLoop.status == "active")) or 0
        ),
        "events_7d": count_events(db, week_ago),
    }

    due_decisions = list(
        db.scalars(
            select(Decision)
            .where(Decision.status == "open", Decision.review_at.is_not(None), Decision.review_at <= now)
            .order_by(Decision.review_at)
            .limit(5)
        )
    )
    due_events = [
        EventOut(
            id=-d.id,
            module="dtm",
            event_type="decision.review_due",
            ref_type="decision",
            ref_id=d.id,
            title=f"决策待复盘：{d.title}",
            detail={"review_at": d.review_at.isoformat() if d.review_at else None},
            importance=3,
            occurred_at=d.review_at,
        )
        for d in due_decisions
    ]

    recent = list(db.scalars(select(EventLog).order_by(EventLog.occurred_at.desc(), EventLog.id.desc()).limit(12)))
    recent_out = [EventOut.model_validate(e, from_attributes=True) for e in recent]

    days = [(now - timedelta(days=i)).date().isoformat() for i in range(13, -1, -1)]
    charts: dict[str, list[DayCount]] = {}
    for mod, label in (("kd", "学习"), ("ml", "复习"), ("ta", "任务"), ("dtm", "决策")):
        counts = dict.fromkeys(days, 0)
        rows = db.scalars(
            select(EventLog).where(EventLog.module == mod, EventLog.occurred_at >= now - timedelta(days=14))
        )
        for e in rows:
            key = e.occurred_at.date().isoformat()
            if key in counts:
                counts[key] += 1
        charts[label] = [DayCount(date=k, count=v) for k, v in counts.items()]

    demo_row = db.get(Setting, "demo_mode")
    return DashboardOut(
        today=now.date(),
        stats=stats,
        due_decision_reviews=due_events,
        recent_events=recent_out,
        charts=charts,
        demo_mode=bool(demo_row and demo_row.value.get("enabled")),
    )
