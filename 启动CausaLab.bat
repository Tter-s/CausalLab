@echo off
chcp 65001 >nul
title CausaLab Launcher

echo ============================================
echo   CausaLab - starting backend + frontend
echo ============================================

REM Start backend (FastAPI, port 8000) in its own window
start "CausaLab backend (8000)" cmd /k "cd /d %~dp0backend && .venv\Scripts\python.exe -m uvicorn app.main:app --port 8000"

REM Start frontend (Next.js, port 3000) in its own window
start "CausaLab frontend (3000)" cmd /k "cd /d %~dp0frontend && npm run dev"

echo Waiting for services to come up (about 12s)...
timeout /t 12 /nobreak >nul

echo Opening http://localhost:3000 ...
start http://localhost:3000

echo.
echo 两个服务窗口保持打开即可使用；关闭窗口 = 停止服务。
echo 数据保存在 backend\data\causalab.db
echo.
pause
