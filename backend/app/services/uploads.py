"""附件（题目 / 我的解答）存储服务。

安全要点：
1. **磁盘文件名一律由服务端生成**（uuid4 + 白名单扩展名），用户提供的文件名只存库用于展示，
   因此不存在路径穿越、覆盖既有文件的问题；
2. **只接受白名单扩展名**，`content_type` 由扩展名推导，不信任客户端声明；
3. **分块读取 + 超限立即中止**，避免把超大文件整个读进内存；
4. 读取时**再次校验**目标路径确实落在 uploads 目录内（纵深防御）。
"""
from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Attachment

# 允许的扩展名 -> MIME。同时作为 content_type 的唯一来源（不信任客户端）。
ALLOWED_TYPES: dict[str, str] = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
    ".pdf": "application/pdf",
    ".txt": "text/plain",
    ".md": "text/markdown",
}

MAX_SIZE_BYTES = 10 * 1024 * 1024  # 单文件上限 10 MB
_CHUNK = 1024 * 1024

KINDS = {"question", "solution", "other"}
MODULES = {"kd", "ml", "dtm", "ta", "hyp", "loop", "sys"}
REF_TYPES = {"topic", "task", "attempt", "subject", "suggestion", "decision", "project", "card", "hypothesis", "loop", "other"}


def uploads_dir() -> Path:
    """附件目录（位于数据目录下，已在 .gitignore 的 backend/data/ 覆盖范围内）。"""
    d = settings.data_dir / "uploads"
    d.mkdir(parents=True, exist_ok=True)
    return d


def resolve_stored_path(stored_name: str) -> Path:
    """把库中的 stored_name 解析为磁盘路径，并确认它没有逃出 uploads 目录。"""
    base = uploads_dir().resolve()
    target = (base / stored_name).resolve()
    if base != target.parent:
        raise HTTPException(status_code=400, detail="附件路径非法")
    return target


def _checked_ext(original_name: str) -> str:
    ext = Path(original_name).suffix.lower()
    if ext not in ALLOWED_TYPES:
        allowed = "、".join(sorted(ALLOWED_TYPES))
        raise HTTPException(
            status_code=422,
            detail=f"不支持的文件类型 {ext or '(无扩展名)'}；允许：{allowed}",
        )
    return ext


def _validate_ref(module: str, ref_type: str, kind: str) -> None:
    if module not in MODULES:
        raise HTTPException(status_code=422, detail=f"不支持的 module：{module}")
    if ref_type not in REF_TYPES:
        raise HTTPException(status_code=422, detail=f"不支持的 ref_type：{ref_type}")
    if kind not in KINDS:
        raise HTTPException(status_code=422, detail=f"不支持的 kind：{kind}（可用：question / solution / other）")


async def save_upload(
    db: Session,
    file: UploadFile,
    *,
    module: str,
    ref_type: str,
    ref_id: int,
    kind: str = "other",
    note: str = "",
) -> Attachment:
    """校验并落盘一个上传文件，返回附件元数据（调用方负责 commit）。"""
    _validate_ref(module, ref_type, kind)

    original = (file.filename or "").strip()
    if not original:
        raise HTTPException(status_code=422, detail="缺少文件名")
    ext = _checked_ext(original)

    stored_name = f"{uuid.uuid4().hex}{ext}"
    dest = uploads_dir() / stored_name
    size = 0
    try:
        with dest.open("wb") as fh:
            while True:
                chunk = await file.read(_CHUNK)
                if not chunk:
                    break
                size += len(chunk)
                if size > MAX_SIZE_BYTES:
                    raise HTTPException(
                        status_code=413,
                        detail=f"文件超过上限 {MAX_SIZE_BYTES // (1024 * 1024)} MB",
                    )
                fh.write(chunk)
    except HTTPException:
        dest.unlink(missing_ok=True)
        raise
    except OSError as exc:  # 磁盘写失败
        dest.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail="附件写入失败") from exc

    if size == 0:
        dest.unlink(missing_ok=True)
        raise HTTPException(status_code=422, detail="文件内容为空")

    att = Attachment(
        module=module,
        ref_type=ref_type,
        ref_id=ref_id,
        kind=kind,
        original_name=original[:300],
        stored_name=stored_name,
        content_type=ALLOWED_TYPES[ext],
        size_bytes=size,
        note=note[:500],
    )
    db.add(att)
    db.flush()
    return att


def attachments_for(db: Session, module: str, ref_type: str, ref_id: int) -> list[Attachment]:
    return list(
        db.scalars(
            select(Attachment)
            .where(
                Attachment.module == module,
                Attachment.ref_type == ref_type,
                Attachment.ref_id == ref_id,
            )
            .order_by(Attachment.created_at.asc(), Attachment.id.asc())
        )
    )


def get_attachment(db: Session, attachment_id: int) -> Attachment:
    att = db.get(Attachment, attachment_id)
    if att is None:
        raise HTTPException(status_code=404, detail="附件不存在")
    return att


def delete_attachment(db: Session, att: Attachment) -> None:
    """先删磁盘文件再删库记录；文件缺失不报错（保持一致可恢复）。"""
    resolve_stored_path(att.stored_name).unlink(missing_ok=True)
    db.delete(att)
    db.flush()
