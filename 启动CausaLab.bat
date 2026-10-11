@echo off
chcp 65001 >nul
title CausaLab Launcher

echo ============================================
echo   CausaLab - starting backend + frontend
echo ============================================

echo [1/3] Cleaning up any stale processes on ports 8000 / 3000 ...
powershell -NoProfile -Command "Get-NetTCPConnection -LocalPort 8000,3000 -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique | ForEach-Object { try { Stop-Process -Id $_ -Force -ErrorAction Stop; Write-Host ('    stopped stale PID ' + $_) } catch {} }"
timeout /t 1 /nobreak >nul

echo [2/3] Starting backend (FastAPI :8000) ...
start "CausaLab backend (8000)" cmd /k "cd /d %~dp0backend && .venv\Scripts\python.exe -m uvicorn app.main:app --port 8000"

echo [3/3] Starting frontend (Next.js :3000) ...
start "CausaLab frontend (3000)" cmd /k "cd /d %~dp0frontend && npm run dev"

echo Waiting for both services to become ready (first start may take ~30s) ...
powershell -NoProfile -Command "$readyB=$false; $readyF=$false; foreach($i in 1..60){ if(-not $readyB){ try { if((Invoke-WebRequest -Uri 'http://127.0.0.1:8000/api/health' -UseBasicParsing -TimeoutSec 2).StatusCode -eq 200){$readyB=$true; Write-Host '    backend: ready'} } catch {} } if(-not $readyF){ try { if((Invoke-WebRequest -Uri 'http://127.0.0.1:3000' -UseBasicParsing -TimeoutSec 5).StatusCode -eq 200){$readyF=$true; Write-Host '    frontend: ready'} } catch {} } if($readyB -and $readyF){ break } Start-Sleep -Milliseconds 500 }; if($readyB -and $readyF){ Write-Host 'ALL READY' } else { if(-not $readyB){ Write-Host 'WARN: backend NOT ready - check the backend window for errors' } if(-not $readyF){ Write-Host 'WARN: frontend NOT ready - check the frontend window for errors' } }"

start http://localhost:3000

echo.
echo ==================================================
echo   服务已启动（两个窗口保持打开即可使用）。
echo   - 界面地址:  http://localhost:3000
echo   - 后端文档:  http://127.0.0.1:8000/docs
echo   - 数据文件:  backend\data\causalab.db
echo   关闭对应窗口 = 停止该服务。
echo   若页面提示“无法连接后端 API”，请查看 backend
echo   窗口中的红色报错信息，并确认 8000 端口未被其他
echo   程序占用（本脚本启动前会自动清理旧进程）。
echo ==================================================
echo.
pause
