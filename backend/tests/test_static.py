"""静态前端同源托管（frontend/out → FastAPI）：
① 目录存在时 / 与深链目录（/dtm/detail）返回 index.html；
② /api/* 优先级高于静态兜底；
③ 目录（或 index.html）缺失时不挂载、应用照常可用。
"""
from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.config import settings
from app.main import create_app

INDEX_HTML = "<!doctype html><html><body><div id='root'>CausaLab 静态页</div></body></html>"


def _make_static_bundle(root: Path) -> Path:
    """构造一个最小静态产物：根 index.html + /dtm/detail/index.html（模拟 trailingSlash 目录结构）。"""
    static_dir = root / "out"
    (static_dir / "dtm" / "detail").mkdir(parents=True)
    (static_dir / "index.html").write_text(INDEX_HTML, encoding="utf-8")
    (static_dir / "dtm" / "detail" / "index.html").write_text(INDEX_HTML, encoding="utf-8")
    return static_dir


def test_static_bundle_served_at_root_and_deep_link(monkeypatch, tmp_path: Path) -> None:
    static_dir = _make_static_bundle(tmp_path)
    monkeypatch.setattr(settings, "static_dir", static_dir)
    with TestClient(create_app()) as client:
        root = client.get("/")
        assert root.status_code == 200
        assert "CausaLab 静态页" in root.text

        # 静态导出的详情页是目录形式（trailingSlash）：带斜杠直出 200；
        # 不带斜杠由 StaticFiles 307 跳到带斜杠版本，且查询参数保留（?id=N 不丢）
        resp = client.get("/dtm/detail/")
        assert resp.status_code == 200
        assert "CausaLab 静态页" in resp.text

        redirect = client.get("/dtm/detail?id=27", follow_redirects=False)
        assert redirect.status_code in (307, 308)
        assert redirect.headers["location"].endswith("/dtm/detail/?id=27")


def test_api_routes_take_priority_over_static_fallback(monkeypatch, tmp_path: Path) -> None:
    static_dir = _make_static_bundle(tmp_path)
    monkeypatch.setattr(settings, "static_dir", static_dir)
    with TestClient(create_app()) as client:
        resp = client.get("/api/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


def test_missing_static_dir_skips_mount_and_keeps_api_working(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(settings, "static_dir", tmp_path / "does-not-exist")
    with TestClient(create_app()) as client:
        assert client.get("/api/health").status_code == 200
        assert client.get("/").status_code == 404
