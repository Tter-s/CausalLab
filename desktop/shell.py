# -*- coding: utf-8 -*-
"""CausaLab 桌面壳（pywebview + 内嵌后端）。

双击即用：在本机起一个 FastAPI 服务（127.0.0.1 空闲端口，同源托管静态前端），
用原生窗口（WebView2）打开页面——用户不需要 Python / Node / Docker 任何前置环境。

运行形态：
    开发态（仓库内）：cd backend && uv run --group desktop python ..\\desktop\\shell.py
    打包态（交付版）：desktop/build.ps1 生成的 CausaLab.exe（PyInstaller onedir）

数据目录（SQLite 数据库 / 加密密钥 / 上传附件）：
    打包态：<exe 所在目录>/data（便携式——整个文件夹可拷到任意位置）
    开发态：<仓库>/desktop/.data
    两者都可用环境变量 CAUSALAB_DATA_DIR 显式覆盖。

自检 / 诊断：
    --smoke   无窗口冒烟：起服务 → 校验 /api/health 与首页 → 校验 pywebview 可导入 → 退出（0=通过）
    运行日志写入 <数据目录>/desktop.log（打包后无控制台，排查问题看这里）。
"""
from __future__ import annotations

import argparse
import logging
import os
import socket
import sys
import threading
import time
import urllib.request
import webbrowser
from pathlib import Path

APP_TITLE = "CausaLab"
FROZEN = bool(getattr(sys, "frozen", False))


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _bundle_root() -> Path:
    """打包态 = PyInstaller 的 _MEIPASS（onedir 下即 _internal）；开发态 = 仓库根。"""
    if FROZEN:
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
    return _repo_root()


def _setup_env() -> tuple[Path, Path]:
    """解析路径并设置 CAUSALAB_* 环境变量（必须早于任何 `import app`）。返回 (data_dir, web_dir)。"""
    bundle = _bundle_root()
    if FROZEN:
        web_dir = bundle / "web"
        data_dir = Path(sys.executable).resolve().parent / "data"
        sys.path.insert(0, str(bundle))  # 打包态：app 包就在 _internal 下
    else:
        web_dir = _repo_root() / "frontend" / "out"
        data_dir = Path(__file__).resolve().parent / ".data"
        sys.path.insert(0, str(_repo_root() / "backend"))  # 开发态：从 backend/ 导入 app
    os.environ.setdefault("CAUSALAB_DATA_DIR", str(data_dir))
    os.environ.setdefault("CAUSALAB_STATIC_DIR", str(web_dir))
    return Path(os.environ["CAUSALAB_DATA_DIR"]), Path(os.environ["CAUSALAB_STATIC_DIR"])


def _pick_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def _setup_logging(log_file: Path) -> None:
    handlers: list[logging.Handler] = [logging.FileHandler(log_file, encoding="utf-8")]
    if sys.stdout is not None:  # --windowed 打包后没有控制台
        handlers.append(logging.StreamHandler(sys.stdout))
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=handlers,
        force=True,
    )


def _start_server(port: int):
    """在主线程之外启动 uvicorn（daemon 线程，随进程退出而退出）。"""
    import uvicorn

    from app.main import create_app

    config = uvicorn.Config(
        create_app(),
        host="127.0.0.1",
        port=port,
        log_level="info",
        log_config=None,  # 不覆盖我们的文件日志配置
        access_log=False,
    )
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, name="causalab-uvicorn", daemon=True)
    thread.start()
    return server


def _wait_ready(port: int, timeout: float = 30.0) -> bool:
    url = f"http://127.0.0.1:{port}/api/health"
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as resp:
                if resp.status == 200:
                    return True
        except Exception:  # noqa: BLE001 — 服务尚未就绪，继续轮询
            time.sleep(0.2)
    return False


class JsBridge:
    """暴露给页面的原生能力（前端检测 window.pywebview 后调用）。"""

    def open_external(self, url: str) -> bool:
        """在系统默认浏览器打开链接 / 触发下载（附件、导出等）。"""
        if isinstance(url, str) and url.startswith(("http://", "https://")):
            webbrowser.open(url)
            return True
        return False


def _run_smoke(port: int, log: logging.Logger) -> int:
    ok = _wait_ready(port, timeout=40.0)
    log.info("smoke: backend ready=%s port=%s", ok, port)
    if ok:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=10) as resp:
                body = resp.read(8192).decode("utf-8", "ignore")
            ok = resp.status == 200 and "<!DOCTYPE html>" in body
            log.info("smoke: index status=%s contains_html=%s", resp.status, ok)
        except Exception:  # noqa: BLE001
            log.exception("smoke: 首页请求失败")
            ok = False
    try:
        import webview  # noqa: F401 — 打包完整性检查（pythonnet/WebView2 依赖是否随包）

        log.info("smoke: pywebview import OK")
    except Exception:  # noqa: BLE001
        log.exception("smoke: pywebview 导入失败")
        ok = False
    log.info("SMOKE %s", "OK" if ok else "FAIL")
    return 0 if ok else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="CausaLab 桌面版（内嵌后端 + WebView2 窗口）")
    parser.add_argument("--smoke", action="store_true", help="无窗口自检后退出（打包产物验证用）")
    args = parser.parse_args(argv)

    data_dir, web_dir = _setup_env()
    data_dir.mkdir(parents=True, exist_ok=True)
    _setup_logging(data_dir / "desktop.log")
    log = logging.getLogger("causalab.desktop")
    log.info("desktop starting (frozen=%s, data=%s, web=%s)", FROZEN, data_dir, web_dir)
    if not (web_dir / "index.html").is_file():
        log.warning("静态前端缺失：%s（页面将不可用；请先运行 npm run build:static）", web_dir)

    port = _pick_free_port()
    server = _start_server(port)
    log.info("uvicorn starting on 127.0.0.1:%s", port)

    if args.smoke:
        code = _run_smoke(port, log)
        server.should_exit = True
        return code

    if not _wait_ready(port):
        log.error("后端在 30 秒内未就绪，仍尝试打开窗口（请查看 desktop.log 与 <数据目录>/desktop.log）")

    import webview

    # WebView2 内 window.open / blob 下载不可靠：外链走系统浏览器、允许原生下载
    for key, value in (("ALLOW_DOWNLOADS", True), ("OPEN_EXTERNAL_LINKS_IN_BROWSER", True)):
        try:
            webview.settings[key] = value
        except Exception:  # noqa: BLE001 — 不同版本设置项可能有差异，缺失时忽略
            log.warning("pywebview 不支持设置项 %s", key)

    window = webview.create_window(
        APP_TITLE,
        f"http://127.0.0.1:{port}/",
        width=1280,
        height=860,
        min_size=(1000, 640),
        js_api=JsBridge(),
    )
    log.info("window created: %s", window.title if hasattr(window, "title") else APP_TITLE)
    webview.start()  # 阻塞至窗口关闭

    # 关窗 → 停 uvicorn，确保进程无残留
    log.info("window closed, shutting down")
    server.should_exit = True
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
