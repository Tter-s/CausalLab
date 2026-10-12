"""附件 API：上传题目 / 我的解答，以及列表、下载、删除。

文件本体存 `data_dir/uploads/`，库中只存元数据（见 services/uploads.py）。
全部挂在 /api 下，因此自动受「可选密码保护」中间件约束（启用认证后需登录）。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.cross import AttachmentOut
from app.services.events import record_event
from app.services.uploads import (
    attachments_for,
    delete_attachment,
    get_attachment,
    resolve_stored_path,
    save_upload,
)

router = APIRouter(tags=["uploads"])

_KIND_LABEL = {"question": "题目", "solution": "我的解答", "other": "附件"}


@router.get("/uploads", response_model=list[AttachmentOut])
def list_uploads(module: str, ref_type: str, ref_id: int, db: Session = Depends(get_db)):
    """列出挂在某个实体上的全部附件。"""
    return list(attachments_for(db, module, ref_type, ref_id))


@router.post("/uploads", response_model=AttachmentOut, status_code=201)
async def create_upload(
    module: str = Form(...),
    ref_type: str = Form(...),
    ref_id: int = Form(...),
    kind: str = Form("other"),
    note: str = Form(""),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """上传题目或我的解答（multipart/form-data）。"""
    att = await save_upload(
        db, file, module=module, ref_type=ref_type, ref_id=ref_id, kind=kind, note=note
    )
    record_event(
        db,
        module=module,
        event_type="attachment.uploaded",
        ref_type=ref_type,
        ref_id=ref_id,
        title=f"上传{_KIND_LABEL.get(att.kind, '附件')}：{att.original_name}",
        detail={"attachment_id": att.id, "kind": att.kind, "size_bytes": att.size_bytes},
    )
    db.commit()
    db.refresh(att)
    return AttachmentOut.model_validate(att, from_attributes=True)


@router.get("/uploads/{attachment_id}/content")
def download_upload(attachment_id: int, db: Session = Depends(get_db)):
    """下载/预览附件本体。"""
    att = get_attachment(db, attachment_id)
    path = resolve_stored_path(att.stored_name)
    if not path.exists():
        raise HTTPException(status_code=404, detail="附件文件已丢失")
    return FileResponse(path, media_type=att.content_type, filename=att.original_name)


@router.delete("/uploads/{attachment_id}", status_code=204)
def remove_upload(attachment_id: int, db: Session = Depends(get_db)):
    """删除附件（同时删除磁盘文件）。"""
    att = get_attachment(db, attachment_id)
    ref = (att.module, att.ref_type, att.ref_id, att.kind, att.original_name)
    delete_attachment(db, att)
    record_event(
        db,
        module=ref[0],
        event_type="attachment.deleted",
        ref_type=ref[1],
        ref_id=ref[2],
        title=f"删除{_KIND_LABEL.get(ref[3], '附件')}：{ref[4]}",
    )
    db.commit()
