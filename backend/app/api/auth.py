"""认证 API：状态 / 启用（设置密码）/ 登录 / 登出 / 禁用 / 修改密码。

默认（未启用）时本机无需登录；启用后除公开端点外全部要求会话 Cookie。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.services import auth as auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


class PasswordIn(BaseModel):
    password: str = Field(min_length=6, max_length=128)


class ChangePasswordIn(BaseModel):
    old_password: str = Field(min_length=6, max_length=128)
    new_password: str = Field(min_length=6, max_length=128)


def _client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for")
    return fwd.split(",")[0].strip() if fwd else (request.client.host if request.client else "?")


def _set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=auth_service.SESSION_COOKIE,
        value=token,
        httponly=True,
        samesite="lax",
        max_age=auth_service.SESSION_TTL_DAYS * 86400,
        path="/",
    )


@router.get("/status")
def auth_status(request: Request, db: Session = Depends(get_db)):
    enabled = auth_service.is_enabled(db)
    return {
        "enabled": enabled,
        "authed": auth_service.validate_session(db, request.cookies.get(auth_service.SESSION_COOKIE)) if enabled else True,
    }


@router.post("/setup", status_code=201)
def setup(payload: PasswordIn, db: Session = Depends(get_db)):
    """首次启用密码保护（仅在未启用时可用）。"""
    if auth_service.is_enabled(db):
        raise HTTPException(status_code=409, detail={"code": "auth_already_enabled", "message": "密码保护已启用，请先在设置中禁用后再重新设置。"})
    auth_service.set_password(db, payload.password)
    db.commit()
    return {"ok": True, "enabled": True}


@router.post("/login")
def login(payload: PasswordIn, request: Request, response: Response, db: Session = Depends(get_db)):
    if auth_service.login_rate_limited(_client_ip(request)):
        raise HTTPException(status_code=429, detail={"code": "rate_limited", "message": "尝试过于频繁，请一分钟后再试。"})
    if not auth_service.is_enabled(db):
        raise HTTPException(status_code=409, detail={"code": "auth_not_enabled", "message": "当前未启用密码保护。"})
    if not auth_service.verify_password(db, payload.password):
        raise HTTPException(status_code=401, detail={"code": "bad_credentials", "message": "密码错误。"})
    token, _expires = auth_service.create_session(db)
    db.commit()
    _set_session_cookie(response, token)
    return {"ok": True}


@router.post("/logout", status_code=204)
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    auth_service.delete_session(db, request.cookies.get(auth_service.SESSION_COOKIE))
    db.commit()
    response.delete_cookie(key=auth_service.SESSION_COOKIE, path="/")
    return Response(status_code=204)


@router.post("/disable", status_code=200)
def disable(payload: PasswordIn, db: Session = Depends(get_db)):
    """关闭密码保护（需当前密码验证——这是忘记会话时的恢复路径）。"""
    if not auth_service.is_enabled(db):
        return {"ok": True, "enabled": False}
    if not auth_service.verify_password(db, payload.password):
        raise HTTPException(status_code=401, detail={"code": "bad_credentials", "message": "密码错误。"})
    auth_service.disable(db)
    db.commit()
    return {"ok": True, "enabled": False}


@router.post("/change-password")
def change_password(payload: ChangePasswordIn, request: Request, db: Session = Depends(get_db)):
    """修改密码（需要有效会话；由中间件保证）。"""
    if not auth_service.is_enabled(db):
        raise HTTPException(status_code=409, detail={"code": "auth_not_enabled", "message": "当前未启用密码保护。"})
    if not auth_service.verify_password(db, payload.old_password):
        raise HTTPException(status_code=401, detail={"code": "bad_credentials", "message": "当前密码错误。"})
    auth_service.set_password(db, payload.new_password)
    db.commit()
    return {"ok": True}
