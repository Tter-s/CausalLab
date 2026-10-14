"""CausaLab 应用配置。

所有配置支持通过环境变量覆盖（前缀 CAUSALAB_），例如：
    CAUSALAB_DATA_DIR=C:/CausaLabData                        # 数据目录（示例，建议放仓库外）
    CAUSALAB_DB_URL=postgresql+psycopg://user:pass@host/db   # 生产可切换 PostgreSQL（本机未验证）
    CAUSALAB_STATIC_DIR=C:/CausaLabStatic                    # 静态前端目录（默认 frontend/out）
    CAUSALAB_CORS_ORIGINS='["http://192.0.2.10:8080"]'       # 页面来源示例（RFC 5737 文档地址；替换为实际来源）

CORS 说明（异地静态托管场景）：页面与 API 不同源时（例如页面由另一台机器上的静态服务器提供，
后端在本机 8000），需要把页面来源写进 CAUSALAB_CORS_ORIGINS（JSON 数组格式），并在页面的
config.js 里注入 window.__CAUSALAB_API_BASE__ = "http://<后端地址>:8000"。
同源托管（FastAPI 同时服务页面与 API）无需任何 CORS 配置。
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
    # 静态前端目录（npm run build:static 的产物）。目录不存在时后端跳过挂载、只提供 API。
    static_dir: Path = BASE_DIR.parent / "frontend" / "out"
    # 跨源白名单：仅当静态页与后端异源部署时才需要扩充（如局域网另一台机器打开页面）
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
