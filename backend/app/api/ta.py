"""Task Autopsy API：项目 / 任务 / 过程事件 / 统计 / 规则复盘 / 改进措施追踪。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models import ImprovementAction, Project, ProjectReview, Task, TaskDep, TaskEvent
from app.schemas.ta import (
    ImprovementIn,
    ImprovementOut,
    ImprovementUpdateIn,
    ProjectIn,
    ProjectOut,
    ProjectReviewIn,
    ProjectReviewOut,
    ProjectStatsOut,
    ProjectUpdateIn,
    TaskDepIn,
    TaskDepOut,
    TaskEventIn,
    TaskEventOut,
    TaskIn,
    TaskOut,
    TaskStatRow,
    TaskUpdateIn,
)
from app.services.base import utcnow
from app.services.events import record_event
from app.services.links import links_for

router = APIRouter(prefix="/ta", tags=["ta"])

_EVENT_LABELS = {
    "blocked": "阻塞",
    "resumed": "恢复",
    "rework": "返工",
    "interrupted": "中断",
    "requirement_change": "需求变化",
    "note": "备注",
    "status_change": "状态变更",
}


def _get_project(db: Session, project_id: int) -> Project:
    p = db.get(Project, project_id)
    if p is None:
        raise HTTPException(status_code=404, detail="项目不存在")
    return p


def _get_task(db: Session, task_id: int) -> Task:
    t = db.get(Task, task_id)
    if t is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    return t


def _creates_cycle(db: Session, task_id: int, depends_on_id: int) -> bool:
    """判断“task_id 依赖 depends_on_id”是否会构成环：
    沿 depends_on 边向上游走，若能回到 task_id 则成环。"""
    seen: set[int] = set()
    stack = [depends_on_id]
    while stack:
        cur = stack.pop()
        if cur == task_id:
            return True
        if cur in seen:
            continue
        seen.add(cur)
        stack.extend(
            r.depends_on_task_id
            for r in db.scalars(select(TaskDep).where(TaskDep.task_id == cur))
        )
    return False


def _propagate_dependency_cleared(db: Session, task: Task) -> None:
    """任务完成后的依赖传播：为每个直接下游任务记录“依赖解除”事件；
    若下游任务的全部前置均已完成且处于 blocked，则自动恢复为 doing。"""
    downstream = list(db.scalars(select(TaskDep).where(TaskDep.depends_on_task_id == task.id)))
    if not downstream:
        return
    cleared = 0
    resumed = 0
    for dep in downstream:
        d = db.get(Task, dep.task_id)
        if d is None or d.status in ("done", "cancelled"):
            continue
        now = utcnow()
        db.add(TaskEvent(task_id=d.id, type="dependency_cleared",
                         description=f"前置任务「{task.title}」已完成，依赖解除", occurred_at=now))
        cleared += 1
        upstream_ids = [r.depends_on_task_id for r in db.scalars(select(TaskDep).where(TaskDep.task_id == d.id))]
        all_done = all(
            (u := db.get(Task, uid)) is not None and u.status == "done" for uid in upstream_ids
        )
        if all_done and d.status == "blocked":
            d.status = "doing"
            db.add(TaskEvent(task_id=d.id, type="status_change",
                             description="依赖全部完成，自动恢复执行（blocked → doing）", occurred_at=now))
            record_event(db, module="ta", event_type="task.auto_resumed", ref_type="task", ref_id=d.id,
                         title=f"任务「{d.title}」依赖全部完成，自动恢复执行", importance=2)
            resumed += 1
        record_event(db, module="ta", event_type="task.dependency_cleared", ref_type="task", ref_id=d.id,
                     title=f"前置任务「{task.title}」完成，任务「{d.title}」依赖解除", importance=1)
    if cleared:
        record_event(db, module="ta", event_type="task.completed", ref_type="task", ref_id=task.id,
                     title=f"任务「{task.title}」完成：解除 {cleared} 个下游依赖（自动恢复 {resumed} 个）",
                     importance=1, detail={"cleared": cleared, "auto_resumed": resumed})


# ---------- 项目 ----------
@router.get("/projects", response_model=list[ProjectOut])
def list_projects(status: str | None = None, db: Session = Depends(get_db)):
    stmt = select(Project).order_by(Project.updated_at.desc())
    if status:
        stmt = stmt.where(Project.status == status)
    return list(db.scalars(stmt))


@router.post("/projects", response_model=ProjectOut, status_code=201)
def create_project(payload: ProjectIn, db: Session = Depends(get_db)):
    now = utcnow()
    p = Project(name=payload.name, description=payload.description, deadline=payload.deadline, started_at=now)
    db.add(p)
    db.flush()
    record_event(db, module="ta", event_type="project.created", ref_type="project", ref_id=p.id,
                 title=f"创建项目：{p.name}", importance=2)
    db.commit()
    db.refresh(p)
    return p


@router.get("/projects/{project_id}", response_model=ProjectOut)
def get_project(project_id: int, db: Session = Depends(get_db)):
    return _get_project(db, project_id)


@router.patch("/projects/{project_id}", response_model=ProjectOut)
def update_project(project_id: int, payload: ProjectUpdateIn, db: Session = Depends(get_db)):
    p = _get_project(db, project_id)
    data = payload.model_dump(exclude_unset=True)
    for field in ("name", "description", "status", "deadline"):
        if data.get(field) is not None:
            setattr(p, field, data[field])
    db.flush()
    record_event(db, module="ta", event_type="project.updated", ref_type="project", ref_id=p.id,
                 title=f"更新项目：{p.name}")
    db.commit()
    db.refresh(p)
    return p


@router.delete("/projects/{project_id}", status_code=204)
def delete_project(project_id: int, db: Session = Depends(get_db)):
    p = _get_project(db, project_id)
    db.delete(p)
    db.commit()


# ---------- 任务 ----------
@router.get("/projects/{project_id}/tasks", response_model=list[TaskOut])
def list_tasks(project_id: int, db: Session = Depends(get_db)):
    _get_project(db, project_id)
    return list(db.scalars(select(Task).where(Task.project_id == project_id).order_by(Task.id)))


@router.post("/projects/{project_id}/tasks", response_model=TaskOut, status_code=201)
def create_task(project_id: int, payload: TaskIn, db: Session = Depends(get_db)):
    _get_project(db, project_id)
    if payload.parent_id is not None:
        parent = _get_task(db, payload.parent_id)
        if parent.project_id != project_id:
            raise HTTPException(status_code=422, detail="父任务必须属于同一项目")
    t = Task(
        project_id=project_id,
        parent_id=payload.parent_id,
        title=payload.title,
        description=payload.description,
        estimated_hours=payload.estimated_hours,
        due_at=payload.due_at,
    )
    db.add(t)
    db.flush()
    for dep_id in payload.depends_on:
        if dep_id == t.id:
            raise HTTPException(status_code=422, detail="任务不能依赖自己")
        if _creates_cycle(db, t.id, dep_id):
            raise HTTPException(status_code=422, detail="该依赖会形成循环依赖")
        db.add(TaskDep(task_id=t.id, depends_on_task_id=dep_id))
    record_event(db, module="ta", event_type="task.created", ref_type="task", ref_id=t.id,
                 title=f"新建任务：{t.title}", importance=1)
    db.commit()
    db.refresh(t)
    return t


@router.get("/tasks/{task_id}", response_model=TaskOut)
def get_task(task_id: int, db: Session = Depends(get_db)):
    return _get_task(db, task_id)


@router.patch("/tasks/{task_id}", response_model=TaskOut)
def update_task(task_id: int, payload: TaskUpdateIn, db: Session = Depends(get_db)):
    t = _get_task(db, task_id)
    data = payload.model_dump(exclude_unset=True)
    old_status = t.status

    for field in ("title", "description", "estimated_hours", "actual_hours"):
        if data.get(field) is not None:
            setattr(t, field, data[field])
    if data.get("due_at") is not None:
        t.due_at = payload.due_at

    new_status = data.get("status")
    if new_status and new_status != old_status:
        now = utcnow()
        t.status = new_status
        if new_status == "doing" and t.started_at is None:
            t.started_at = now
        elif new_status == "done":
            t.finished_at = now
            # 未手动填写实际耗时时，按开始→完成的时间差自动计算（小时，含阻塞等，供参考）
            if t.actual_hours is None and t.started_at:
                t.actual_hours = round((now - t.started_at).total_seconds() / 3600, 2)
            _propagate_dependency_cleared(db, t)
        elif new_status == "todo" and old_status == "done":
            t.finished_at = None
        db.add(
            TaskEvent(task_id=t.id, type="status_change",
                      description=f"{old_status} → {new_status}", occurred_at=now)
        )
        record_event(db, module="ta", event_type="task.status_changed", ref_type="task", ref_id=t.id,
                     title=f"任务「{t.title}」状态：{old_status} → {new_status}",
                     importance=2 if new_status in ("done", "blocked") else 1)

    db.flush()
    db.commit()
    db.refresh(t)
    return t


@router.delete("/tasks/{task_id}", status_code=204)
def delete_task(task_id: int, db: Session = Depends(get_db)):
    t = _get_task(db, task_id)
    db.delete(t)
    db.commit()


@router.post("/tasks/{task_id}/deps", response_model=TaskDepOut, status_code=201)
def add_dependency(task_id: int, payload: TaskDepIn, db: Session = Depends(get_db)):
    t = _get_task(db, task_id)
    if payload.depends_on_task_id == task_id:
        raise HTTPException(status_code=422, detail="任务不能依赖自己")
    dep_target = _get_task(db, payload.depends_on_task_id)
    if dep_target.project_id != t.project_id:
        raise HTTPException(status_code=422, detail="依赖任务必须属于同一项目")
    if _creates_cycle(db, task_id, payload.depends_on_task_id):
        raise HTTPException(status_code=422, detail="该依赖会形成循环依赖")
    dep = TaskDep(task_id=task_id, depends_on_task_id=payload.depends_on_task_id)
    db.add(dep)
    db.commit()
    db.refresh(dep)
    return dep


@router.get("/tasks/{task_id}/deps", response_model=list[TaskDepOut])
def list_deps(task_id: int, db: Session = Depends(get_db)):
    _get_task(db, task_id)
    return list(db.scalars(select(TaskDep).where(TaskDep.task_id == task_id)))


# ---------- 过程事件 ----------
@router.post("/tasks/{task_id}/events", response_model=TaskEventOut, status_code=201)
def add_task_event(task_id: int, payload: TaskEventIn, db: Session = Depends(get_db)):
    t = _get_task(db, task_id)
    ev = TaskEvent(
        task_id=task_id,
        type=payload.type,
        description=payload.description,
        duration_minutes=payload.duration_minutes,
        occurred_at=payload.occurred_at or utcnow(),
    )
    db.add(ev)
    if payload.type == "blocked" and t.status != "blocked":
        t.status = "blocked"
    if payload.type == "resumed" and t.status == "blocked":
        t.status = "doing"
    db.flush()
    label = _EVENT_LABELS.get(payload.type, payload.type)
    record_event(db, module="ta", event_type=f"task.{payload.type}", ref_type="task", ref_id=task_id,
                 title=f"任务「{t.title}」记录{label}" + (f"：{payload.description[:50]}" if payload.description else ""),
                 importance=2 if payload.type in ("blocked", "rework", "requirement_change") else 1,
                 detail={"duration_minutes": payload.duration_minutes})
    db.commit()
    db.refresh(ev)
    return ev


@router.get("/tasks/{task_id}/events", response_model=list[TaskEventOut])
def list_task_events(task_id: int, db: Session = Depends(get_db)):
    _get_task(db, task_id)
    return list(db.scalars(select(TaskEvent).where(TaskEvent.task_id == task_id).order_by(TaskEvent.occurred_at)))


# ---------- 统计 ----------
@router.get("/projects/{project_id}/stats", response_model=ProjectStatsOut)
def project_stats(project_id: int, db: Session = Depends(get_db)):
    _get_project(db, project_id)
    tasks = list(db.scalars(select(Task).where(Task.project_id == project_id)))
    events = list(db.scalars(select(TaskEvent).where(TaskEvent.task_id.in_([t.id for t in tasks] or [0]))))

    per_task: list[TaskStatRow] = []
    total_est = 0.0
    total_actual = 0.0
    overruns: list[float] = []
    for t in tasks:
        t_events = [e for e in events if e.task_id == t.id]
        blocked_min = sum(e.duration_minutes or 0 for e in t_events if e.type in ("blocked", "interrupted"))
        rework_n = sum(1 for e in t_events if e.type == "rework")
        ratio = None
        if t.estimated_hours and t.actual_hours:
            ratio = round(t.actual_hours / t.estimated_hours, 2)
            overruns.append(ratio)
        if t.estimated_hours:
            total_est += t.estimated_hours
        if t.actual_hours:
            total_actual += t.actual_hours
        per_task.append(
            TaskStatRow(
                task_id=t.id, title=t.title, status=t.status,
                estimated_hours=t.estimated_hours, actual_hours=t.actual_hours,
                overrun_ratio=ratio, blocked_minutes=blocked_min, rework_count=rework_n,
            )
        )

    event_counts: dict[str, int] = {}
    for e in events:
        event_counts[e.type] = event_counts.get(e.type, 0) + 1

    return ProjectStatsOut(
        project_id=project_id,
        tasks_total=len(tasks),
        tasks_done=sum(1 for t in tasks if t.status == "done"),
        tasks_blocked=sum(1 for t in tasks if t.status == "blocked"),
        tasks_cancelled=sum(1 for t in tasks if t.status == "cancelled"),
        total_estimated_hours=round(total_est, 2),
        total_actual_hours=round(total_actual, 2),
        avg_overrun_ratio=round(sum(overruns) / len(overruns), 2) if overruns else None,
        blocked_minutes_total=float(sum(e.duration_minutes or 0 for e in events if e.type == "blocked")),
        rework_count=sum(1 for e in events if e.type == "rework"),
        interrupted_count=sum(1 for e in events if e.type == "interrupted"),
        requirement_change_count=sum(1 for e in events if e.type == "requirement_change"),
        per_task=per_task,
        event_type_counts=event_counts,
    )


# ---------- 复盘（规则版；AI 版在 /api/ai） ----------
@router.post("/projects/{project_id}/reviews", response_model=ProjectReviewOut, status_code=201)
def create_review(project_id: int, payload: ProjectReviewIn, db: Session = Depends(get_db)):
    _get_project(db, project_id)
    r = ProjectReview(
        project_id=project_id,
        summary=payload.summary,
        facts=payload.facts,
        speculations=payload.speculations,
        missing_evidence=payload.missing_evidence,
        improvements=payload.improvements,
        source="manual",
    )
    db.add(r)
    db.flush()
    record_event(db, module="ta", event_type="project.reviewed", ref_type="project", ref_id=project_id,
                 title="项目复盘报告（手动）", importance=3)
    db.commit()
    db.refresh(r)
    return r


@router.get("/projects/{project_id}/reviews", response_model=list[ProjectReviewOut])
def list_reviews(project_id: int, db: Session = Depends(get_db)):
    _get_project(db, project_id)
    return list(db.scalars(select(ProjectReview).where(ProjectReview.project_id == project_id).order_by(ProjectReview.id)))


@router.post("/projects/{project_id}/rule-review", response_model=ProjectReviewOut, status_code=201)
def rule_review(project_id: int, db: Session = Depends(get_db)):
    """无 AI 模式的规则复盘：只陈述数据事实、模式推测与缺失证据，绝不编造。"""
    _get_project(db, project_id)
    stats = project_stats(project_id, db)

    facts: list[str] = []
    if stats.tasks_total:
        facts.append(f"项目共 {stats.tasks_total} 个任务，完成 {stats.tasks_done} 个，取消 {stats.tasks_cancelled} 个。")
    if stats.total_estimated_hours and stats.total_actual_hours:
        facts.append(
            f"有实际耗时的任务合计预估 {stats.total_estimated_hours:.1f} 小时，实际 {stats.total_actual_hours:.1f} 小时。"
        )
    if stats.avg_overrun_ratio is not None:
        facts.append(f"已完成且可对比的任务平均实际/预估比为 {stats.avg_overrun_ratio}。")
    if stats.blocked_minutes_total:
        facts.append(f"累计阻塞时长 {stats.blocked_minutes_total:.0f} 分钟。")
    for label, key in (("返工", "rework_count"), ("中断", "interrupted_count"), ("需求变化", "requirement_change_count")):
        cnt = getattr(stats, key)
        if cnt:
            facts.append(f"记录到 {cnt} 次{label}。")
    if not facts:
        facts.append("项目还没有足够的过程数据（任务/事件），无法给出事实性结论。")

    speculations: list[str] = []
    if stats.avg_overrun_ratio is not None and stats.avg_overrun_ratio > 1.3:
        speculations.append(f"推测：平均实际/预估比 {stats.avg_overrun_ratio}，说明预估可能系统性偏低（推测依据：多个任务一致超出）。")
    if stats.blocked_minutes_total and stats.tasks_blocked:
        speculations.append("推测：阻塞集中出现，可能与外部依赖或环境准备不足有关——需要结合阻塞原因记录验证。")
    if stats.rework_count >= 2:
        speculations.append("推测：返工次数较多，可能是需求理解或方案评审环节有缺口（推测，需对照具体返工事件）。")

    missing: list[str] = []
    if stats.tasks_total and not any(e for e in stats.event_type_counts if e in ("blocked", "interrupted")):
        missing.append("缺少阻塞/中断事件记录：无法区分延期是执行慢还是外部等待。")
    if stats.tasks_total and stats.tasks_done < stats.tasks_total:
        missing.append("未完成任务缺少“剩余工作量”估计，无法预测完成时间。")
    if not stats.event_type_counts:
        missing.append("没有任何过程事件记录，无法定位问题发生的阶段。")

    improvements: list[str] = []
    if stats.avg_overrun_ratio is not None and stats.avg_overrun_ratio > 1.2:
        improvements.append(f"下个项目对同类任务预估乘以 {max(1.5, round(stats.avg_overrun_ratio, 1))} 的系数，并挑 1 个任务验证偏差。")
    if stats.blocked_minutes_total:
        improvements.append("阻塞发生时立即记录原因分类（等待他人/环境/自身），两周后回看哪类占比最高。")
    if stats.requirement_change_count:
        improvements.append("重大需求变化先记录变更来源与影响范围，再开工，用下个项目验证是否减少返工。")
    if not improvements:
        improvements.append("先补全过程记录（预估时长、阻塞原因），积累一个完整周期后再制定改进措施。")

    r = ProjectReview(
        project_id=project_id,
        summary=f"规则复盘：基于 {stats.tasks_total} 个任务与 "
                f"{sum(stats.event_type_counts.values())} 条过程事件生成；以下区分事实、推测与缺失证据。",
        facts=facts,
        speculations=speculations,
        missing_evidence=missing,
        improvements=improvements,
        source="rule",
    )
    db.add(r)
    db.flush()
    record_event(db, module="ta", event_type="project.reviewed", ref_type="project", ref_id=project_id,
                 title="项目复盘报告（规则分析）", importance=3)
    db.commit()
    db.refresh(r)
    return r


# ---------- 改进措施 ----------
@router.get("/improvements", response_model=list[ImprovementOut])
def list_improvements(project_id: int | None = None, db: Session = Depends(get_db)):
    stmt = select(ImprovementAction).order_by(ImprovementAction.updated_at.desc())
    if project_id is not None:
        stmt = stmt.where(ImprovementAction.project_id == project_id)
    return list(db.scalars(stmt))


@router.post("/improvements", response_model=ImprovementOut, status_code=201)
def create_improvement(payload: ImprovementIn, db: Session = Depends(get_db)):
    a = ImprovementAction(
        action=payload.action,
        project_id=payload.project_id,
        review_id=payload.review_id,
        status=payload.status,
    )
    db.add(a)
    db.flush()
    record_event(db, module="ta", event_type="improvement.created", ref_type="improvement", ref_id=a.id,
                 title=f"新增改进措施：{payload.action[:60]}", importance=2)
    db.commit()
    db.refresh(a)
    return a


@router.patch("/improvements/{improvement_id}", response_model=ImprovementOut)
def update_improvement(improvement_id: int, payload: ImprovementUpdateIn, db: Session = Depends(get_db)):
    a = db.get(ImprovementAction, improvement_id)
    if a is None:
        raise HTTPException(status_code=404, detail="改进措施不存在")
    data = payload.model_dump(exclude_unset=True)
    for field in ("status", "followup_note", "effect"):
        if field in data:
            setattr(a, field, data[field])
    db.flush()
    if data.get("status"):
        record_event(db, module="ta", event_type="improvement.status", ref_type="improvement", ref_id=a.id,
                     title=f"改进措施状态更新为 {data['status']}：{a.action[:50]}", importance=1)
    db.commit()
    db.refresh(a)
    return a


@router.get("/projects/{project_id}/links")
def project_links(project_id: int, db: Session = Depends(get_db)):
    _get_project(db, project_id)
    return list(links_for(db, "ta", "project", project_id))
