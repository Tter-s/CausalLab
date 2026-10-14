# CausaLab 三大分发形态构建与交付交接（HANDOFF-BUILD）

> **用途**：本轮「桌面应用 + 安卓 APK」构建工作的交接说明——交付了什么、怎么构建与运行、验证到什么程度、如何上传、还剩什么。
> 配套文档：`README.md`（本机安装/运行/FAQ，面向使用者）· `HANDOFF.md`（开发上下文，面向继续开发）· `docs/PROGRESS.md`（进度与遗留明细）。
> **最后更新：2026-10-14**

---

## 1. 交付了什么

在原有「开发模式」之外，项目现支持三种开箱即用的分发形态：

| 形态 | 技术 | 状态 |
|---|---|---|
| **静态网页** | Next.js 静态导出（`frontend/out/`）+ FastAPI 同源托管 | 已构建；经浏览器全流程实测（8 项） |
| **桌面应用（Windows）** | pywebview 6 + PyInstaller（onedir，内置后端与页面） | 已构建；dev/exe 双冒烟 + 真实窗口启动均通过 |
| **安卓 APK** | Flutter WebView 客户端（连接电脑端后端） | 已构建（aapt2 校验通过）；⚠️ 未做真机安装 |

**二进制交付物**（约 82 MB，**不在仓库中**，由构建机单独交付）：

| 文件 | 说明 |
|---|---|
| `CausaLab-Desktop-0.1.0.zip`（约 36 MB） | 解压即用的绿色版，双击 `CausaLab.exe`；使用者无需 Python/Node |
| `CausaLab-Android-0.1.0.apk`（约 46 MB） | 手机侧载安装，连接电脑端局域网地址使用 |
| `README.txt` | 两者的使用说明（使用者视角） |

> 二进制不建议入库（体积大）；如需公开分发，建议走 GitHub Releases 附件，仓库保持纯源码。

## 2. 三种形态的构建与运行

### 2.1 静态网页（零新增依赖）

```powershell
cd frontend ; npm run build:static        # → frontend/out/（纯静态文件）
cd backend  ; uv run uvicorn app.main:app --port 8000
# 打开 http://127.0.0.1:8000/ —— 页面与 /api 同端口（后端自动挂载 out/）
```

- 异地托管（页面与后端不同源）：`out/` 放任意静态服务器；后端设 `CAUSALAB_CORS_ORIGINS`；页面注入 `config.js`（`window.__CAUSALAB_API_BASE__`）。

### 2.2 桌面应用（Windows 绿色版）

```powershell
# 一键打包（仓库根目录执行；自动：构建静态页 → uv sync --group desktop → PyInstaller）
powershell -ExecutionPolicy Bypass -File desktop\build.ps1
# 产物：desktop\dist\CausaLab\（整个文件夹即绿色便携版）
desktop\dist\CausaLab\CausaLab.exe --smoke      # 自检：无窗口启动，退出码 0 = 通过

# 开发态运行（不打包，直接起窗口）
cd backend ; uv run --group desktop python ..\desktop\shell.py
```

- **运行要求**：Windows 10/11（含 WebView2 运行时，系统一般自带）；**使用者无需安装 Python/Node/Docker**。
- **数据位置**：exe 同级 `data\`（SQLite + 附件 + 加密密钥）——整个文件夹拷走即可迁移；日志在 `data\desktop.log`。
- **细节**：附件打开与 JSON/CSV 导出交给系统默认浏览器（webview 内下载不可靠）；关闭窗口即退出，无后台残留。

### 2.3 安卓 APK

```powershell
# 前置：Flutter + JDK 17 + Android SDK；尖括号处替换为实际安装路径
$env:JAVA_HOME = "<JDK 17 安装目录>"
$env:ANDROID_HOME = "<Android SDK 目录>"
$env:GRADLE_USER_HOME = "<Gradle 用户目录>"
cd mobile ; flutter build apk --release
# 产物：mobile\build\app\outputs\flutter-apk\app-release.apk

# 电脑端以局域网模式运行（手机才能访问）
cd backend ; uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
# 首次可能需（管理员）放行防火墙入站 8000（命令见 README「7. 安卓 APK」一节）
```

- **使用**：手机与电脑连接同一 Wi-Fi；首次打开填 `http://<电脑IP>:8000`（电脑 IP 用 `ipconfig` 查）。
- **要点**：release 包为 Flutter 默认 debug 签名（可直接侧载，上架商店需正式签名）；已允许明文 HTTP（局域网环境必需）。
- **Gradle 发行版**：`mobile/android/gradle/wrapper/gradle-wrapper.properties` 指向国内镜像（官方下载源在国内网络会重定向、不稳定）；如构建环境网络良好，可改回官方源。

## 3. 验证状态（本机实测）

| 项 | 结果 |
|---|---|
| 后端 pytest / ruff / mypy | **79/79** · 全绿 |
| 前端 Vitest / tsc / eslint | **26/26** · 全绿（0 error） |
| E2E（Playwright + Edge，10 场景） | **10/10** |
| 静态网页：导出 + 浏览器全流程（同源托管） | **8/8** |
| 桌面版：dev 冒烟 / exe 冒烟 / 真实窗口启动 | 全部通过 |
| 安卓：release 构建 + aapt2 校验（包名/权限/架构） | 通过 |
| 无 AI 全链路冒烟 | **24/24**（隔离实例） |

**未验证（如实标注，切勿写成「通过」）**：

1. ⚠️ **APK 未做真机安装**——构建机无安卓设备/模拟器；首次真机安装后建议完整走一遍核心流程（KD 记录 / DTM 决策 / 附件）。
2. ⚠️ 桌面版**各功能页建议人工点检**（自动化覆盖到「能启动 + 页面/API 可达」为止）。
3. ⚠️ Docker / PostgreSQL / CI 真跑（需其他机器；SQLite 已充分验证）。

## 4. 上传 / 推送（维护者操作）

本轮（三大形态构建 + 交接文档）的提交已推送到 GitHub（`origin/main` 与本地同步）；此后例行推送仍为：

```powershell
# 仓库目录下执行
git log --oneline origin/main..main    # 查看待推送提交
git push origin main                   # 普通推送（无历史重写）
```

- 二进制交付物不入库；要发布走 GitHub Releases 附件。
- 公开前保持：无密钥 / 无本机绝对路径 / 无真实私有 IP（本轮已扫描与脱敏）。
- `docs/PLAN-STATIC-DESKTOP.md`（构建计划参考）保持未跟踪、不随提交；如需入库可单独 `git add`。

## 5. 遗留事项（按优先级）

1. **APK 真机验证**（需一台安卓手机）：安装 → 填电脑地址 → 走一遍核心流程；
2. **桌面版人工点检**：记录 / 附件 / 导出在主流程各点一遍；
3. **Docker / PostgreSQL / CI 真跑**（需其他机器）；
4. 可选：安卓正式签名（上架商店时）；桌面版可考虑加图标与版本信息。

## 6. 快速索引

| 关注点 | 位置 |
|---|---|
| 桌面壳源码 / 打包脚本 | `desktop/shell.py` · `desktop/CausaLab.spec` · `desktop/build.ps1` · `desktop/README.md` |
| 安卓客户端源码 | `mobile/lib/main.dart` · `mobile/android/…` · `mobile/README.md` |
| 静态导出脚本 | `frontend/scripts/build-static.mjs`（`npm run build:static`） |
| 后端静态托管挂载 | `backend/app/main.py`（`CAUSALAB_STATIC_DIR` 可覆盖默认 `frontend/out/`） |
| 前端桌面桥接 | `frontend/src/lib/api.ts`（`apiUrl` / `isDesktopShell` / `openExternal`） |
| 桌面依赖组声明 | `backend/pyproject.toml`（`[dependency-groups] desktop`） |
