"""数据管理 API：JSON 全量导出/导入、CSV 导出、演示数据、清空数据。"""
from __future__ import annotations

import contextlib
import csv
import io
from datetime import date, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models import (
    AIUsageLog,
    Attachment,
    Attempt,
    Card,
    Counterfactual,
    Decision,
    DecisionReview,
    DecisionSnapshot,
    DecisionUpdate,
    Deck,
    Diagnosis,
    EntityLink,
    EventLog,
    EvidenceRecord,
    ExpAssignment,
    ExpGroup,
    Hypothesis,
    HypothesisObservation,
    ImprovementAction,
    ImprovementLoop,
    LoopStage,
    MemExperiment,
    Prediction,
    Project,
    ProjectReview,
    ReviewLog,
    ReviewState,
    Setting,
    StudyTask,
    Subject,
    Suggestion,
    Task,
    TaskDep,
    TaskEvent,
    Topic,
    TopicEdge,
)
from app.services.base import utcnow
from app.services.demo import seed_demo
from app.services.events import record_event
from app.services.uploads import resolve_stored_path

router = APIRouter(prefix="/data", tags=["data"])

# 导出顺序即导入顺序（依赖表在后）
EXPORT_ORDER: list[tuple[str, Any]] = [
    ("kd_subjects", Subject),
    ("kd_topics", Topic),
    ("kd_topic_edges", TopicEdge),
    ("kd_study_tasks", StudyTask),
    ("kd_attempts", Attempt),
    ("kd_diagnoses", Diagnosis),
    ("kd_suggestions", Suggestion),
    ("ml_decks", Deck),
    ("ml_cards", Card),
    ("ml_review_states", ReviewState),
    ("ml_review_logs", ReviewLog),
    ("ml_experiments", MemExperiment),
    ("ml_experiment_groups", ExpGroup),
    ("ml_experiment_assignments", ExpAssignment),
    ("dtm_decisions", Decision),
    ("dtm_decision_snapshots", DecisionSnapshot),
    ("dtm_predictions", Prediction),
    ("dtm_decision_updates", DecisionUpdate),
    ("dtm_decision_reviews", DecisionReview),
    ("dtm_counterfactuals", Counterfactual),
    ("ta_projects", Project),
    ("ta_tasks", Task),
    ("ta_task_deps", TaskDep),
    ("ta_task_events", TaskEvent),
    ("ta_project_reviews", ProjectReview),
    ("ta_improvement_actions", ImprovementAction),
    ("events", EventLog),
    ("evidence", EvidenceRecord),
    ("entity_links", EntityLink),
    ("hyp_hypotheses", Hypothesis),
    ("hyp_observations", HypothesisObservation),
    ("loop_loops", ImprovementLoop),
    ("loop_stages", LoopStage),
    ("settings", Setting),
    ("ai_usage_logs", AIUsageLog),
]


def _row_to_dict(obj: Any) -> dict:
    out = {}
    for c in obj.__table__.columns:  # type: ignore[attr-defined]
        v = getattr(obj, c.name)
        if isinstance(v, (datetime, date)):
            v = v.isoformat()
        out[c.name] = v
    return out


@router.get("/export")
def export_all(db: Session = Depends(get_db)):
    data = {
        "schema_version": 1,
        "exported_at": utcnow().isoformat(),
        "app": "CausaLab",
        "tables": {},
    }
    tables_out: dict[str, list[dict]] = {}
    for name, model in EXPORT_ORDER:
        rows: list[Any] = list(db.scalars(select(model)))
        tables_out[name] = [_row_to_dict(r) for r in rows]
    data["tables"] = tables_out
    return data


def _coerce(value, column):
    """把 JSON 里的 ISO 字符串还原为 DateTime 列需要的 datetime 对象。"""
    from sqlalchemy import DateTime as SADateTime

    if value is None or isinstance(value, datetime) or not isinstance(column.type, SADateTime):
        return value
    try:
        return datetime.fromisoformat(str(value))
    except ValueError:
        return None


def _wipe_attachments(db: Session) -> None:
    """清空附件：既删库记录，也删磁盘文件。

    附件不参与 JSON 导出（二进制文件无法随 JSON 走），但必须随「清空业务数据」一起清理，
    否则会留下指向已不存在文件的孤儿记录。
    """
    for att in db.scalars(select(Attachment)):
        # 单个文件删除失败（如权限问题）不应中断整体清空
        with contextlib.suppress(Exception):
            resolve_stored_path(att.stored_name).unlink(missing_ok=True)
    db.query(Attachment).delete(synchronize_session=False)
    db.flush()


def _wipe_business_data(db: Session, tables: dict | None = None) -> None:
    """按依赖逆序物理删除业务数据。tables=None 表示全部（settings 除外）。"""
    if tables is None:
        # 全量清空（清空数据 / 载入演示）时才动附件；按表导入时保留既有附件
        _wipe_attachments(db)
    for name, model in reversed(EXPORT_ORDER):
        if name == "settings":
            continue
        if tables is not None and name not in tables:
            continue
        db.query(model).delete(synchronize_session=False)
    db.flush()


@router.post("/import")
def import_all(payload: dict, db: Session = Depends(get_db)):
    """全量替换导入。要求文件由本应用导出（校验 schema_version 与 app 标识）。"""
    if payload.get("app") != "CausaLab" or "tables" not in payload:
        raise HTTPException(status_code=422, detail="不是有效的 CausaLab 导出文件")
    tables = payload["tables"]
    # 第一阶段：清空并立即提交，避免同一事务内删除/插入排序引发外键冲突
    _wipe_business_data(db, tables)
    db.commit()
    db.expunge_all()

    # 第二阶段：按依赖顺序逐表插入（settings 保留本地当前值，不导入）
    inserted = {}
    for name, model in EXPORT_ORDER:
        if name == "settings":
            inserted[name] = 0
            continue
        rows = tables.get(name, [])
        cols = {c.name: c for c in model.__table__.columns}
        objs = []
        for rd in rows:
            clean = {k: _coerce(v, cols[k]) for k, v in rd.items() if k in cols}
            objs.append(model(**clean))
        db.add_all(objs)
        db.flush()
        inserted[name] = len(objs)
    record_event(db, module="sys", event_type="data.imported", ref_type="system", ref_id=0,
                 title=f"导入数据完成（{sum(inserted.values())} 行）", importance=2)
    db.commit()
    return {"ok": True, "inserted": inserted}


@router.get("/export/kd-attempts.csv")
def export_attempts_csv(db: Session = Depends(get_db)):
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["attempt_id", "task_id", "topic_id", "correct", "error_category",
                     "independent", "duration_minutes", "notes", "occurred_at"])
    for a in db.scalars(select(Attempt).order_by(Attempt.occurred_at)):
        writer.writerow([a.id, a.task_id, a.topic_id, a.correct, a.error_category,
                         a.independent, a.duration_minutes, a.notes, a.occurred_at])
    return Response(
        content=buf.getvalue(), media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=causalab_attempts.csv"},
    )


@router.get("/export/ml-reviews.csv")
def export_reviews_csv(db: Session = Depends(get_db)):
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["review_id", "card_id", "rating", "reviewed_at", "duration_ms",
                     "scheduled_days", "elapsed_days", "experiment_id", "group_tag"])
    for r in db.scalars(select(ReviewLog).order_by(ReviewLog.reviewed_at)):
        writer.writerow([r.id, r.card_id, r.rating, r.reviewed_at, r.duration_ms,
                         r.scheduled_days, r.elapsed_days, r.experiment_id, r.group_tag])
    return Response(
        content=buf.getvalue(), media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=causalab_reviews.csv"},
    )


@router.post("/demo")
def load_demo(db: Session = Depends(get_db)):
    """载入演示数据（会先清空现有业务数据）。演示数据在界面上有明确标识。"""
    _wipe_business_data(db)
    db.commit()
    db.expunge_all()
    seed_demo(db)
    row = db.get(Setting, "demo_mode")
    if row is None:
        row = Setting(key="demo_mode", value={"enabled": True})
        db.add(row)
    else:
        row.value = {"enabled": True}
    record_event(db, module="sys", event_type="data.demo_loaded", ref_type="system", ref_id=0,
                 title="载入演示数据（非真实记录）", importance=3)
    db.commit()
    return {"ok": True, "notice": "演示数据已载入，界面将显示“演示数据”标识；可在设置中一键清除。"}


@router.delete("/all")
def delete_all(db: Session = Depends(get_db)):
    """清空所有业务数据（保留设置）。危险操作，前端需二次确认。"""
    _wipe_business_data(db)
    db.flush()
    row = db.get(Setting, "demo_mode")
    if row:
        row.value = {"enabled": False}
    record_event(db, module="sys", event_type="data.cleared", ref_type="system", ref_id=0,
                 title="清空全部业务数据", importance=3)
    db.commit()
    return {"ok": True}
