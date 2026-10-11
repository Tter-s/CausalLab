"""API Key 静态加密：Fernet + 本机密钥文件（data/secret.key，不入 Git）。"""
from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken

from app.config import settings


def _fernet() -> Fernet:
    key_file = settings.data_dir / "secret.key"
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    if not key_file.exists():
        key_file.write_bytes(Fernet.generate_key())
    return Fernet(key_file.read_bytes().strip())


def encrypt_secret(plain: str) -> str:
    if not plain:
        return ""
    return _fernet().encrypt(plain.encode("utf-8")).decode("utf-8")


def decrypt_secret(token: str) -> str:
    if not token:
        return ""
    try:
        return _fernet().decrypt(token.encode("utf-8")).decode("utf-8")
    except (InvalidToken, ValueError):
        # 密钥文件丢失/更换时避免崩溃，返回空串（用户需重新填写 Key）
        return ""


def mask_secret(plain: str) -> str:
    if not plain:
        return ""
    if len(plain) <= 8:
        return "****"
    return f"{plain[:4]}****{plain[-4:]}"
