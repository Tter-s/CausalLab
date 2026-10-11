"""统一事件记录服务：所有模块的关键动作都经过这里写入 events 表。"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import EventLog
from app.models.base import utcnow


def record_event(
    db: Session,
    *,
    module: str,
    event_type: str,
    ref_type: str,
    ref_id: int,
    title: str,
    detail: dict | None = None,
    importance: int = 1,
    occurred_at: datetime | None = None,
) -> EventLog:
    ev = EventLog(
        module=module,
        event_type=event_type,
        ref_type=ref_type,
        ref_id=ref_id,
        title=title,
        detail=detail or {},
        importance=importance,
        occurred_at=occurred_at or utcnow(),
    )
    db.add(ev)
    db.flush()
    return ev


def events_for(db: Session, module: str, ref_type: str, ref_id: int) -> list[EventLog]:
    return list(
        db.scalars(
            select(EventLog)
            .where(EventLog.module == module, EventLog.ref_type == ref_type, EventLog.ref_id == ref_id)
            .order_by(EventLog.occurred_at.desc(), EventLog.id.desc())
        )
    )


def count_events(db: Session, since: datetime) -> int:
    return int(db.scalar(select(func.count(EventLog.id)).where(EventLog.occurred_at >= since)) or 0)
