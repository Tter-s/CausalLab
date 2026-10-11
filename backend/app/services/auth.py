"""认证服务：可选密码保护（默认关闭）、bcrypt 哈希、数据库会话、登录限流。

设计定位（对应遗留问题 #6）：个人本机部署默认无需登录；一旦启用，
所有 /api/*（除 health/auth 公开端点）都需要有效会话（30 天，HttpOnly Cookie）。
"""
from __future__ import annotations

import hashlib
import secrets
import time
from datetime import datetime, timedelta

import bcrypt
from sqlalchemy import delete as sa_delete
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AuthSession, Setting
from app.services.base import utcnow

AUTH_CONFIG_KEY = "auth_config"
SESSION_COOKIE = "causalab_session"
SESSION_TTL_DAYS = 30

AUTH_PUBLIC_PATHS = {
    "/api/health",
    "/api/auth/status",
    "/api/auth/login",
    "/api/auth/setup",
    "/api/auth/disable",
    "/api/auth/logout",
}


def get_auth_config(db: Session) -> dict:
    row = db.get(Setting, AUTH_CONFIG_KEY)
    data = {"enabled": False, "password_hash": ""}
    if row and isinstance(row.value, dict):
        data.update(row.value)
    return data


def is_enabled(db: Session) -> bool:
    return bool(get_auth_config(db).get("enabled"))


def set_password(db: Session, password: str) -> None:
    """启用保护或修改密码（调用方负责先验证旧密码）。"""
    cfg = get_auth_config(db)
    cfg["enabled"] = True
    cfg["password_hash"] = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    row = db.get(Setting, AUTH_CONFIG_KEY)
    if row is None:
        row = Setting(key=AUTH_CONFIG_KEY, value=cfg)
        db.add(row)
    else:
        row.value = cfg
    db.flush()


def verify_password(db: Session, password: str) -> bool:
    cfg = get_auth_config(db)
    h = cfg.get("password_hash") or ""
    if not h:
        return False
    try:
        return bcrypt.checkpw(password.encode("utf-8"), h.encode("utf-8"))
    except ValueError:
        return False


def disable(db: Session) -> None:
    cfg = get_auth_config(db)
    cfg["enabled"] = False
    cfg["password_hash"] = ""
    row = db.get(Setting, AUTH_CONFIG_KEY)
    if row is not None:
        row.value = cfg
    delete_all_sessions(db)
    db.flush()


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_session(db: Session) -> tuple[str, datetime]:
    cleanup_expired(db)
    token = secrets.token_urlsafe(32)
    expires = utcnow() + timedelta(days=SESSION_TTL_DAYS)
    db.add(AuthSession(token_hash=_hash_token(token), expires_at=expires))
    db.flush()
    return token, expires


def validate_session(db: Session, token: str | None) -> bool:
    """只读校验（可在中间件中使用，不持有写锁）。过期清理见 cleanup_expired。"""
    if not token:
        return False
    now = utcnow()
    row = db.scalar(select(AuthSession).where(AuthSession.token_hash == _hash_token(token)))
    return row is not None and row.expires_at > now


def cleanup_expired(db: Session) -> None:
    """删除过期会话（写操作，仅在登录/启用等写路径中调用并随后 commit）。"""
    db.execute(sa_delete(AuthSession).where(AuthSession.expires_at < utcnow()))
    db.flush()


def delete_session(db: Session, token: str | None) -> None:
    if token:
        db.execute(sa_delete(AuthSession).where(AuthSession.token_hash == _hash_token(token)))
        db.flush()


def delete_all_sessions(db: Session) -> None:
    db.execute(sa_delete(AuthSession))
    db.flush()


# ---------- 登录限流（内存实现，按 IP 每分钟 10 次；进程重启即清零） ----------
_LOGIN_LIMIT = 10
_LOGIN_WINDOW_SECONDS = 60
_login_attempts: dict[str, tuple[float, int]] = {}


def login_rate_limited(ip: str) -> bool:
    now = time.monotonic()
    window_start, count = _login_attempts.get(ip, (now, 0))
    if now - window_start > _LOGIN_WINDOW_SECONDS:
        _login_attempts[ip] = (now, 1)
        return False
    count += 1
    _login_attempts[ip] = (window_start, count)
    return count > _LOGIN_LIMIT
