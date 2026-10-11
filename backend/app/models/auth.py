"""认证模型：登录会话（密码本身存于 settings 表的 auth_config，bcrypt 哈希）。"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, utcnow


class AuthSession(Base):
    """一次登录对应一条会话。Cookie 中保存随机 token，库内只存其 SHA-256。"""

    __tablename__ = "auth_sessions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime, index=True)
