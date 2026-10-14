# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 打包配置（onedir）——由 desktop/build.ps1 调用，也可手动执行：

    cd backend
    uv run --group desktop pyinstaller ..\\desktop\\CausaLab.spec --noconfirm

产物：<repo>/desktop/dist/CausaLab/CausaLab.exe（连同整个 CausaLab 文件夹一起分发）。
"""
import os

from PyInstaller.utils.hooks import collect_all, collect_submodules

ROOT = os.path.dirname(SPECPATH)  # 仓库根（本文件在 desktop/ 下）
BACKEND = os.path.join(ROOT, "backend")
WEB = os.path.join(ROOT, "frontend", "out")

if not os.path.isfile(os.path.join(WEB, "index.html")):
    raise SystemExit("缺少静态前端产物：请先运行 `npm run build:static`（frontend/out 不存在或为空）")

datas = [
    (WEB, "web"),  # 静态前端 → _internal/web（shell.py 通过 CAUSALAB_STATIC_DIR 指给后端）
    (os.path.join(BACKEND, "alembic"), "alembic"),  # 迁移脚本 → _internal/alembic（BASE_DIR 即 _internal）
    (os.path.join(BACKEND, "alembic.ini"), "."),  # 迁移配置 → _internal/alembic.ini
]
binaries = []
hiddenimports = [
    # uvicorn 的运行期动态导入
    "uvicorn.logging",
    "uvicorn.loops.auto",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan.on",
    # SQLAlchemy 方言动态导入（SQLite）
    "sqlalchemy.dialects.sqlite.pysqlite",
]
for pkg in ("webview", "pythonnet", "clr_loader"):
    pkg_datas, pkg_binaries, pkg_hidden = collect_all(pkg)
    datas += pkg_datas
    binaries += pkg_binaries
    hiddenimports += pkg_hidden
hiddenimports += collect_submodules("app")

a = Analysis(
    [os.path.join(SPECPATH, "shell.py")],
    pathex=[BACKEND],  # 让分析器能静态发现 app 包
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter", "pytest", "ruff", "mypy"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="CausaLab",
    debug=False,
    strip=False,
    upx=False,
    console=False,  # 无控制台窗口（排查问题看 <数据目录>/desktop.log）
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="CausaLab",
)
