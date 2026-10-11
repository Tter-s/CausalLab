"""证据与实体链接服务。"""
from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models import EntityLink, EvidenceRecord


def add_evidence(
    db: Session,
    *,
    module: str,
    ref_type: str,
    ref_id: int,
    kind: str,
    content: str,
    source: str = "",
    confidence: float | None = None,
    event_id: int | None = None,
) -> EvidenceRecord:
    rec = EvidenceRecord(
        module=module,
        ref_type=ref_type,
        ref_id=ref_id,
        kind=kind,
        content=content,
        source=source,
        confidence=confidence,
        event_id=event_id,
    )
    db.add(rec)
    db.flush()
    return rec


def evidence_for(db: Session, module: str, ref_type: str, ref_id: int) -> list[EvidenceRecord]:
    return list(
        db.scalars(
            select(EvidenceRecord)
            .where(EvidenceRecord.module == module, EvidenceRecord.ref_type == ref_type, EvidenceRecord.ref_id == ref_id)
            .order_by(EvidenceRecord.created_at.asc(), EvidenceRecord.id.asc())
        )
    )


def create_link(
    db: Session,
    *,
    from_module: str,
    from_ref_type: str,
    from_ref_id: int,
    to_module: str,
    to_ref_type: str,
    to_ref_id: int,
    relation: str = "associated_with",
    note: str = "",
) -> EntityLink:
    link = EntityLink(
        from_module=from_module,
        from_ref_type=from_ref_type,
        from_ref_id=from_ref_id,
        to_module=to_module,
        to_ref_type=to_ref_type,
        to_ref_id=to_ref_id,
        relation=relation,
        note=note,
    )
    db.add(link)
    db.flush()
    return link


def links_for(db: Session, module: str, ref_type: str, ref_id: int) -> list[EntityLink]:
    return list(
        db.scalars(
            select(EntityLink).where(
                or_(
                    (EntityLink.from_module == module)
                    & (EntityLink.from_ref_type == ref_type)
                    & (EntityLink.from_ref_id == ref_id),
                    (EntityLink.to_module == module)
                    & (EntityLink.to_ref_type == ref_type)
                    & (EntityLink.to_ref_id == ref_id),
                )
            )
        )
    )
