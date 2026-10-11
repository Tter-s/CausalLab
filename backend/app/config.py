"""CausaLab 应用配置。

所有配置支持通过环境变量覆盖（前缀 CAUSALAB_），例如：
    CAUSALAB_DATA_DIR=D:/causalab-data
    CAUSALAB_DB_URL=postgresql+psycopg://user:pass@host/db   # 生产可切换 PostgreSQL（本机未验证）
"""
from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class AppConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CAUSALAB_", env_file=".env", extra="ignore")

    app_name: str = "CausaLab"
    app_version: str = "0.1.0"
    # 数据目录：SQLite 数据库、Fernet 密钥文件、上传附件都放在这里（已加入 .gitignore）
    data_dir: Path = BASE_DIR / "data"
    # 留空则使用 SQLite；生产可指向 PostgreSQL（本机未验证，见 README）
    db_url: str = ""
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]
    # 默认每月 AI 预算（人民币）；0 表示不设限
    default_monthly_budget: float = 20.0

    @property
    def database_url(self) -> str:
        if self.db_url:
            return self.db_url
        self.data_dir.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{(self.data_dir / 'causalab.db').as_posix()}"

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")


settings = AppConfig()
