# CausaLab 桌面版（pywebview + PyInstaller）

双击 `CausaLab.exe` 即用：自动在 `127.0.0.1` 起一个内置后端（FastAPI，同源托管静态前端），
再用系统 WebView2 打开窗口。用户不需要安装 Python / Node / Docker 任何前置环境。

## 构建（Windows）

```powershell
# 仓库根目录执行（需要 Node ≥20、uv、Python 3.12+；首次自动安装 desktop 依赖组）
powershell -ExecutionPolicy Bypass -File desktop\build.ps1

# 产物：desktop\dist\CausaLab\CausaLab.exe
# （整个 desktop\dist\CausaLab 文件夹即绿色便携版，可整体拷贝到任意位置运行）
```

## 开发态运行

```powershell
cd backend
uv run --group desktop python ..\desktop\shell.py
```

## 说明

- **数据目录**：打包版存放在 **exe 同级的 `data\`**（SQLite / 附件 / 密钥，便携式随文件夹迁移）；
  开发态在 `desktop\.data\`。都可用 `CAUSALAB_DATA_DIR` 覆盖。
- **运行日志**：`<数据目录>/desktop.log`（打包版无控制台窗口，排查问题看这里）。
- **自检**：`CausaLab.exe --smoke` 无窗口启动自检（退出码 0 = 通过）。
- **外链与下载**：附件、JSON/CSV 导出会交给系统默认浏览器处理（webview 内不可靠）。
