# CausaLab 交接文档（HANDOFF）

> **用途**：在新对话/新会话中快速恢复对 CausaLab 的完整上下文。读完本文件即可继续开发；
> 细节查 `docs/ARCHITECTURE.md`（设计决策）、`docs/API.md`（接口）、`docs/PROGRESS.md`（进度与遗留）、`README.md`（功能与用法）、`HANDOFF-BUILD.md`（三大分发形态构建与交付）。
> **最后更新：2026-10-14（第十二次迭代后）**

---

## 1. 项目是什么

**CausaLab** —— 个人学习、决策与行动实验室。四个核心模块（知识债务 KD / 记忆实验室 ML / 决策时间机 DTM / 任务复盘 TA）+ 三个跨模块能力（证据时间线 / 假设实验室 / 改进循环），共享统一的事件/证据/链接/附件模型。

- **完全无 AI 模式是一等公民**（规则诊断/规则复盘完整可用），云端 AI（DeepSeek/MiMo/Moonshot/任意 OpenAI 兼容）是可选增强。**不做本地模型部署**（无 Ollama）。
- 仓库：GitHub `Tter-s/CausalLab`（`main` 分支；本地克隆到任意目录即可）
- 定位：本地单人 Web 应用；可选密码保护（设置 → 安全，默认关闭）

## 2. 当前状态快照（开工前先读这一节）

| 项 | 值 |
|---|---|
| 本文件描述的状态 | 写作时刚完成「桌面应用 + 安卓 APK」迭代（见 §10），三大分发形态齐备。**实际当前值请用** `git log -1 --oneline` / `git status` 查（文档不追实时状态） |
| 远端 | `https://github.com/Tter-s/CausalLab`（推送后 `origin/main` 与本地同步） |
| **推送状态** | 本地领先远端、**待推送**（由维护者执行 `git push`；差多少见 `git log --oneline origin/main..main`） |
| 工作区 | 干净；构建计划参考 `docs/PLAN-STATIC-DESKTOP.md` 保持未跟踪（不随提交） |
| 服务 | 不随仓库启动，需手动拉起（见 §5）。是否在跑用 `Get-NetTCPConnection -LocalPort 8000,3000 -State Listen` 查 |
| 实测基线 | pytest **79/79** · Vitest **26/26** · E2E **10/10** · 无 AI 冒烟 **24/24** · ruff/mypy/tsc 全绿 · eslint **0 error**（11 warning，均为已声明的 `set-state-in-effect`） · `next build` 12 条业务路由 · **`npm run build:static` 静态导出成功** · **桌面版 PyInstaller 打包成功（68 MB，dev/frozen 双冒烟 + 窗口启动通过）** · **安卓 APK release 构建成功（45.7 MB）** |
| 数据库 | 37 张业务表（+ `alembic_version`），迁移 head = `b69c58233d86` |
| API | 99 条路径 / 134 个操作；`docs/API.md` 与之 **134/134 精确对齐** |
| AI 配置 | provider=deepseek（真实 Key 已配置；Key 加密存本机，不进仓库/文档），`auto_confirm_send=false`（隐私闸门开启，推荐值） |

## 3. 技术栈与版本

| 层 | 技术 |
|---|---|
| 后端 | Python **3.14.7**（锁死，见 §6）+ FastAPI 0.143 + SQLAlchemy 2.1.4 + Alembic 1.20 + SQLite（可切 PG）+ py-fsrs 6.3.2（官方库，MIT）+ bcrypt 5 + cryptography 50（Fernet）+ psycopg 3.3.6（PG 驱动） |
| 前端 | Next.js **16.4.0**（App Router，纯客户端取数）+ React 19.3 + Tailwind v4 + Radix（shadcn 风格手写组件）+ Recharts + @xyflow/react + next-themes + sonner |
| 测试 | pytest（后端 79）/ Vitest（前端 26）/ Playwright（E2E 10，复用系统 Edge，不下载浏览器） |
| 桌面/移动 | 桌面：pywebview 6.2.1 + pythonnet 3.2.1 + PyInstaller 6.22.3（可选依赖组 `desktop`）；安卓：Flutter 3.44.9（`mobile/`，WebView 客户端）· JDK 17 · Android SDK |
| 工具 | uv 0.12.13 · Node v24.21.0 · npm 11.19 · git 2.56.0 |
| 取数模式 | 开发态：前端统一相对路径 `/api/*`，由 Next rewrites 代理到 FastAPI `127.0.0.1:8000`（免 CORS）。静态态：`apiUrl()` 基址解析（`window.__CAUSALAB_API_BASE__` → `NEXT_PUBLIC_API_BASE` → 相对路径），同源托管时行为不变（见 §7.10） |

## 4. 目录速览

```
CausalLab/
├── 启动CausaLab.bat          # 双击启动前后端（自动清端口+等就绪+开浏览器）
├── README.md / LICENSE / docker-compose.yml
├── HANDOFF.md                # 本文件
├── .github/workflows/ci.yml  # CI（本机无法真跑，见 §8）
├── docs/  ARCHITECTURE.md / API.md / PROGRESS.md
├── backend/
│   ├── .dockerignore / Dockerfile          # 均未在本机验证
│   ├── app/api/        # kd / ml / dtm / ta / cross(时间线等) / ai / auth / settings / data / uploads
│   ├── app/models/     # 37 张表（base=Base+utcnow；auth=会话表；cross 内含 attachments）
│   ├── app/services/   # events/links(事件证据链接)、uploads(附件存储)、scheduling(FSRS 适配)、
│   │   │               # kd_rules(规则诊断)、calibration、demo、crypto(Fernet)、auth(认证)
│   │   └── ai/         # Provider 抽象：none/mock/openai_compat + config(隐私闸门/预算/结构化校验)
│   ├── alembic/        # 5 个迁移（初始 schema / auth_sessions / events 索引 / recall_ms / attachments）
│   ├── alembic.ini     # 必须保持纯 ASCII（见 §9 Alembic 条）
│   ├── scripts/smoke_no_ai.py   # 无 AI 全链路冒烟（24 项；默认对 8000，可用 CAUSALAB_SMOKE_BASE 换端口）
│   └── tests/          # 79 用例（含 test_uploads.py 14 个附件用例 + test_static.py 3 个静态托管用例）
├── frontend/
│   ├── .dockerignore / Dockerfile          # 均未在本机验证
│   ├── AGENTS.md         # Next 自动生成并重写（被跟踪，见 §9）
│   ├── src/app/          # 12 路由：/ /kd /ml /dtm /dtm/detail /ta /ta/detail /timeline
│   │                     #        /hypotheses /loops /settings /login
│   │                     # 详情页为查询参数路由（/dtm/detail?id=N、/ta/detail?id=N），兼容静态导出
│   ├── src/components/   # layout/(app-shell+shared) ui/(手写 shadcn 风格组件) brand-mark
│   │                     # dev-tools-zh（仅 dev：汉化+拖拽 Next Dev Tools）
│   ├── src/lib/          # api.ts(428/401 处理 + postForm + apiUrl 基址 + isDesktopShell/openExternal) useApi.ts
│   │                     # i18n.tsx(双语) i18n-page-strings.ts ai-client.tsx(428 确认流) format.ts types.ts
│   ├── scripts/build-static.mjs  # 静态导出（npm run build:static，跨平台，产物 out/）
│   ├── e2e/flows.spec.ts # 10 个场景（含认证、附件上传、按任务模型保存）
│   └── tests/            # Vitest 26（含 i18n 覆盖扫描 + 基址解析 + 桌面桥接用例）
├── desktop/              # 桌面应用（Windows）：shell.py（pywebview 壳）+ CausaLab.spec + build.ps1
└── mobile/               # 安卓 APK：Flutter WebView 客户端（lib/main.dart + android/…）
```

## 5. 启动 / 测试（Windows）

```powershell
# 服务（PowerShell 5.1 亦可；中文参数不要放进命令行，见 §6）
cd backend  ; uv run uvicorn app.main:app --port 8000    # 启动时自动 Alembic 迁移
cd frontend ; npm run dev                                 # http://localhost:3000
# 或直接双击仓库根目录的「启动CausaLab.bat」（自动清端口 + 等就绪 + 开浏览器）

# 静态网页形态（不依赖 Docker 的分发路线，见 §7.10）
cd frontend ; npm run build:static                        # 静态导出 → frontend/out/（纯静态文件）
cd backend  ; uv run uvicorn app.main:app --port 8000     # 同源托管：http://127.0.0.1:8000/ 即完整应用
#   （后端在所有 API 路由后自动挂载 frontend/out/；CAUSALAB_STATIC_DIR 可指向别处的静态目录）

# 桌面版（§7.11）：打包与自检
powershell -ExecutionPolicy Bypass -File desktop\build.ps1   # 产物 desktop\dist\CausaLab\CausaLab.exe（68 MB）
desktop\dist\CausaLab\CausaLab.exe --smoke                   # 打包版自检（退出码 0 = 通过）

# 安卓 APK（§7.11）：构建（需 JDK 17 + Android SDK + Flutter；尖括号处替换为实际安装路径）
$env:JAVA_HOME="<JDK 17 安装目录>"; $env:ANDROID_HOME="<Android SDK 目录>"; $env:GRADLE_USER_HOME="<Gradle 用户目录>"
$env:PUB_CACHE="<Pub 缓存目录>"; $env:PUB_HOSTED_URL="https://pub.flutter-io.cn"
cd mobile ; flutter build apk --release                      # 产物 ...\flutter-apk\app-release.apk（45.7 MB）

# 回归全套（改动后必跑）——后端
cd backend  ; uv run pytest -q ; uv run ruff check app tests ; uv run mypy app
# 回归全套——前端（注意顺序：build 前先关掉 dev server，二者共用 .next）
cd frontend ; npx vitest run ; npx tsc --noEmit ; npm run lint ; npm run build
cd frontend ; npx playwright test        # E2E：自动拉起隔离前后端（:8010 + :3100，msedge）
cd backend  ; uv run python scripts/smoke_no_ai.py       # 无 AI 冒烟（需 8000 在运行）
#   若 8000 被占用：另起隔离实例并用它与脚本对接——
#   $env:CAUSALAB_DATA_DIR = Join-Path $env:TEMP ("causalab-smoke-" + (Get-Random))
#   uv run uvicorn app.main:app --port 8031               # 另开终端
#   $env:CAUSALAB_SMOKE_BASE = "http://127.0.0.1:8031" ; uv run python scripts/smoke_no_ai.py
```

**排障与注意事项**

- **E2E 前必须先关 :3000 的 dev server**——Next 16 同项目只允许一个 dev server，否则 :3100 直接启动失败。
- **`:3000` 在跑时不要执行 `npm run build`**——`next dev` 与 `next build` 共用 `.next`，会互相干扰。
- **冒烟脚本与真实 AI 冲突**：脚本第 0/1 组按「无 AI 前提」断言。若 `backend/data` 里已配置真实 AI（当前就是），
  直接跑会报 2 项失败——**这属预期**。要拿到干净的 24/24，用隔离数据目录另起一个后端：
  ```powershell
  $env:CAUSALAB_DATA_DIR = Join-Path $env:TEMP ("causalab-smoke-" + (Get-Random))
  uv run uvicorn app.main:app --port 8000     # 另开一个终端
  uv run python scripts/smoke_no_ai.py
  ```
- **冒烟脚本曾因 GBK 崩溃**：Windows 下输出被重定向时 Python 的 stdout 编码是 GBK，打印 `✓` 会抛
  `UnicodeEncodeError`。脚本内已显式 `sys.stdout.reconfigure(encoding="utf-8")`，不要再删掉。
- 端口清理：`npx kill-port 8000 3000`。

## 6. 机器硬约束（务必遵守，详见原任务书第十一节）

- **Python 锁定 3.14.7**，uv 禁止下载解释器；依赖必须有 cp314 wheel（**禁 passlib**，bcrypt>=5）。
- **依赖下限不能放松**（任务书 §11.8）：`cryptography>=50`、`pydantic>=2.14`（pydantic-core>=2.50）、`sqlalchemy>=2.1.4`、`bcrypt>=5`。钉到老版本会找不到 wheel → 回退源码编译 → Windows 上基本必然失败。
- **无 Docker / 无 PostgreSQL 服务端**（详见 §8）。
- npm 已指向 npmmirror；pip/uv 走阿里云镜像（缓存位置可自行配置）。
- **Playwright 复用系统 Edge**（`channel: "msedge"`），**绝对不要** `npx playwright install`。
- 不要动本机其他工具链：其他项目的 checkout 目录、全局 npm prefix（其中可能有正在运行的工具）、本机 SDK 安装目录等。
- **命令行传中文参数会被 GBK 拆坏**：中文内容写文件（如 `git commit -F <file>`），或用 Write 工具写临时 `.py` 再执行（heredoc 会碎）。
  同理，PowerShell 读 UTF-8 中文文件别用默认 `Get-Content`（会乱码并吞字符），用脚本的 `read_text(encoding="utf-8")`。
- 提交信息用中文、一次迭代一个 commit。

## 7. 架构核心概念（改动前必读）

1. **统一事件/证据/链接/附件**：所有模块关键动作写 `events` 表；判断依据写 `evidence`（fact/speculation/missing_evidence/ai_analysis/user_correction）；跨模块关联走 `entity_links`；上传的题目/解答走 `attachments`。四者都按 `(module, ref_type, ref_id)` 挂到任意实体——**时间线/搜索/仪表盘都建在其上**。
2. **DTM 快照只追加**：创建/修改决策自动生成快照，无任何修改/删除快照的端点。
3. **KD 诊断护栏**：答题 <3 或失败 <2 → 强制 `insufficient_data` 且置信度 ≤0.25；备选解释永远 ≥1；用户纠正写入 user_correction 证据。
4. **AI 永不直接写库**：`run_structured()` = 隐私确认(428)→预算(402)→调用→用量记录→JSON 剥壳→Pydantic 校验→失败重试→仍失败回退规则分析。MockProvider 用于测试与无 Key 演示。
5. **认证**：可选密码保护，默认关。启用后中间件拦 `/api/*`（白名单见 `AUTH_PUBLIC_PATHS`）；会话 HttpOnly Cookie 30 天；中间件**先关自身 DB 会话再放行**（避免 SQLite 锁冲突）。
6. **i18n 约定**：`t("中文原文")` 源文键模式——zh 回退键本身，en 查 `i18n-page-strings.ts`。**Vitest 有覆盖扫描：任何 t 调用里的中文键缺英文翻译会挂测试**（新增文案直接在该文件补一条英文即可；早期文档提到的 `scripts/_i18n_strings_all.py` 生成脚本**已不存在**）。
7. **附件上传**：文件本体在 `data_dir/uploads/`，磁盘名由 uuid 生成，用户文件名只存库展示（响应也不回传 `stored_name`）。端点 `GET/POST /api/uploads`、`GET /api/uploads/{id}/content`、`DELETE /api/uploads/{id}`。前端必须用 `api.ts` 的 `postForm()`——它刻意清空 headers，否则 `api()` 默认的 `application/json` 会让后端无法解析 multipart。**附件不参与 JSON 导出**，但「清空业务数据」「载入演示数据」会一并删除记录与磁盘文件（见 `_wipe_business_data`）。
8. **数据获取模式**：页面全用自研 `useApi` hook；`ai-client.tsx` 的 `useAICall` 处理 428→预览→确认重发。刻意整页跳转（登出/演示/清空后）有 eslint 豁免注释——不要改成软导航。
9. **AI 配置的 None 语义**：`AIConfigIn` 中 `api_key` 与 `task_models` 都是「None/省略 = 保持原值」。**不要写成无条件覆盖**，否则任何只提交部分字段的客户端都会清空用户已存的配置（这个 bug 真出现过）。
10. **静态分发形态（第十一次迭代新增）**：`npm run build:static` 产出 `frontend/out/`（`STATIC_EXPORT=1` → `output: "export"` + `trailingSlash: true`，该模式下**不注册 rewrites**）；FastAPI 在所有 API 路由**之后**挂 `StaticFiles(html=True)` 同源托管（默认 `frontend/out/`，`CAUSALAB_STATIC_DIR` 可覆盖，目录/index.html 缺失则跳过并记日志）。API 基址解析在 `api.ts`：`window.__CAUSALAB_API_BASE__`（运行期）→ `NEXT_PUBLIC_API_BASE`（构建期）→ 相对路径（默认）。**所有新代码访问 API 必须走 `api()` / `apiUrl()`，不要裸写 `/api/...`**，否则异地托管（静态页与后端不同源）场景断链。详情页一律查询参数路由（`/dtm/detail?id=N`、`/ta/detail?id=N`）。
11. **三大分发形态（第十二次迭代齐备）**：① 静态网页（浏览器 / 静态托管）；② **桌面应用**（`desktop/shell.py`：内嵌 uvicorn 随机端口 + pywebview/WebView2 窗口；打包态数据在 exe 同级 `data/`、开发态 `desktop/.data/`；PyInstaller onedir 把静态前端打进 `_internal/web`、alembic 打进 `_internal/alembic`——`BASE_DIR` 在 frozen 下即 `_internal`，所以这两个目录名**不能改**）；③ **安卓 APK**（`mobile/` Flutter WebView 客户端：**页面由电脑端后端提供**，手机只负责渲染，所以页面形态（静态托管/开发服务）都在电脑端控制；客户端只保存一个服务器地址）。桌面壳内的外链/下载统一走前端 `openExternal()`（检测 `window.pywebview`）→ 系统浏览器；后端 `/api/data/export?download=1` 提供 `Content-Disposition` 文件名。**手机访问必须以 `uvicorn --host 0.0.0.0` 启动后端并放行防火墙入站。**

## 8. 未在本机验证的项（**严禁写成"通过"**，任务书 §11.6）

本机为 Windows 11，无 Docker（且 `registry-1.docker.io` 不可达）、无 PostgreSQL 服务端、`api.openai.com` 不可达：

| 项 | 状态 | 本机为何做不到 |
|---|---|---|
| `docker compose up` | ⚠️ 未验证 | `docker`/`docker-compose`/`podman` 全部未安装、Docker 服务不存在、**Docker Hub 不可达**（拉不到基础镜像，装上也白搭） |
| PostgreSQL 真实集成 | ⚠️ 未验证 | 无 `psql`、5432 无监听、无 PG 服务。驱动 `psycopg[binary]` 已装、`db.py` 分支已写对，但**没有可连的服务端** |
| OpenAI 官方 API 连通 | ⚠️ 未验证 | 网络不可达（适配代码已写） |
| GitHub Actions CI 真跑 | ⚠️ 未验证 | `act` 需要 Docker |
| CI 的 Playwright Chromium 路径 | ⚠️ 未验证 | 本机只有 Edge，E2E 走 `msedge` |
| Firefox / WebKit | ⚠️ 未验证 | 本机未安装对应浏览器 |
| HuggingFace 下载 | ➖ 不涉及 | 产品明确不做本地模型部署 |
| 安卓 APK 真机安装与局域网连调 | ⚠️ 未验证 | 本机无 Android 设备/模拟器；APK 构建与包体校验（aapt2）已通过 |
| 桌面版窗口内的完整手工点选流程 | ⚠️ 部分验证 | 窗口启动、页面加载、双冒烟（含迁移链）已验证；完整交互建议按 `desktop/README.md` 手动过一遍 |

**注意**：这是**部署形态**的缺口，不是**产品功能**的缺口——应用在 SQLite 上功能完整、全部测试通过。
`README.md` 与 `docs/PROGRESS.md` 里有一份对应的用户可读版本，改完必须同步。

## 9. 踩过的坑（避免重蹈）

- **Alembic：`alembic.ini` 必须保持纯 ASCII**——Alembic 以 `encoding="locale"`（本机 GBK）读它，任何非 ASCII 字节都会抛 `UnicodeDecodeError`，而 `app.main._run_migrations()` 会**静默回退** `Base.metadata.create_all()`：应用照常可用、pytest 也照常通过，但迁移链路其实已失效。排查方法：直接调用 `app.main._run_migrations()` 并打开 INFO 日志，看打印的是 "Alembic migration finished." 还是 "failed, falling back"。SQLite 迁移用 `render_as_batch`。
- **i18n 覆盖测试会把注释也算进去**：`tests/i18n.test.ts` 用正则扫全 src 找 `t("…")`，所以**不要在注释里写 `t("中文…")` 这种字面示例**，否则被判成"缺翻译的键"。写说明时把引号去掉。
- **前端 Dockerfile 的 `COPY . .` 必须有 `.dockerignore` 兜底**：否则宿主的 Windows `node_modules` 会覆盖容器内 `npm ci` 装好的 Linux 依赖（`@next/swc-win32-x64-msvc`、`lightningcss-win32-x64-msvc`、`@img/sharp-win32-x64` 等原生二进制），构建失败或产出坏镜像；构建上下文也会从 ~1 MB 涨到 ~1.37 GB。
- **CI 的 Playwright project 名是 `edge`，不是 `chromium`**：`playwright.config.ts` 里只有一个名为 `edge` 的 project，浏览器通道由环境变量 **`PLAYWRIGHT_CHANNEL`** 控制（默认 `msedge`）。写 CI 时别用 `--project=chromium`，也不存在 `PLAYWRIGHT_CHROMIUM` 这个变量名。
- **Windows 上 pytest 的临时目录**：`conftest.py` 的 `pytest_sessionfinish` 必须**先 `engine.dispose()`** 再 `rmtree`，否则 SQLite 句柄未释放导致删除失败，而 `ignore_errors=True` 会吞掉失败——症状是临时目录里持续累积只剩一个 `causalab.db` 的 `causalab_test_*` 目录（曾累积 74 个）。
- **不要把失败的"消失"当成成功**：曾以「pytest 警告从 2 条降到 1 条」当作修复生效的证据，实际是 Alembic 整个没跑起来。验证迁移要看迁移本身（`alembic current` / `_run_migrations()` 的日志），不是看警告数量。
- **Next 16**：`allowedDevOrigins` 必须含 127.0.0.1（否则 dev 资源被拦 → hydration 失败卡骨架屏）；预渲染期禁直接 `Date.now()`；动态路由页需 Suspense 包裹；rewrites 改后要重启 dev；**同项目只允许一个 dev server**。
- **`frontend/AGENTS.md` 由 `next dev` 自动重写**且被 git 跟踪，跑 dev 后可能出现非预期 diff（Next 官方设计如此，不必惊慌）。
- **eslint-config-next 2025**：`set-state-in-effect` 新规则对取数 effect 误报（已降 warn，全局 11 条）；`no-location-assign` 对刻意整页跳转需豁免注释。
- **SQLite 并发**：中间件/长事务内不要在 `call_next` 期间持有连接；auth 中间件已按「先关会话再放行」实现。
- **fsrs 官方库**：要求 UTC aware datetime；`Card.to_dict()` 存 JSON、`from_dict` 重建（见 `scheduling.py` 适配层）。
- **`run_structured` 提示词必须带 JSON Schema**：只写"符合字段结构"而不给 schema，Mock 测不出、真实模型必然校验失败回退规则；schema 以 `model_json_schema()` 附在系统提示词。
- **AI 配置填错的表现**：base_url 误填 `/anthropic`（Anthropic 协议端点）或 model_id 误填 `deepseek`（合法名是 `deepseek-chat`/`deepseek-reasoner`）都会"测试连接"失败；错误详情被包装，诊断可直连 API 看状态码。
- **Next Dev Tools（nextjs-portal）**：open shadow DOM；菜单开关绑定在 click（非 pointerdown）；N 按钮容器是 `.nextjs-toast`（fixed），菜单卡片 `[role="menu"]` 自身就是 fixed 元素。`dev-tools-zh.tsx` 基于这些结构做汉化+拖拽，Next 大版本升级若失效会静默退化为无增强（不影响应用）。该 N 按钮在 dev 下会压住侧边栏底部文案，`app-shell.tsx` 已用 `NODE_ENV === "development"` 追加内边距让开。
- **`.next/dev` 缓存会持续增长**：跑 `next dev`/E2E 后可涨到数百 MB（曾测得 ~750 MB），而纯 `npm run build` 的 `.next` 仅约 75 MB。属 Turbopack 行为，可定期清理。
- **测试隔离**：pytest 共享一个临时库（conftest 设 `CAUSALAB_DATA_DIR`）；写测试注意跨用例状态污染（AI 配置、限流器、会话 cookie 都有前车之鉴）；E2E `beforeEach` 会先关认证 + 清业务数据。
- **静态导出的三个坑**（第十一次迭代踩过）：① `output: "export"` 与 `rewrites` 不兼容——静态模式直接不注册代理（见 `next.config.ts` 的 `STATIC_EXPORT` 分支）；② 动态段路由（`[id]`）无法在构建期枚举运行期 id，静态导出必然失败——详情页改查询参数即解；③ `useSearchParams` 必须包 Suspense（两详情页已包，预渲染输出为骨架屏，数据客户端加载）。另：Starlette `StaticFiles(html=True)` 对**不带尾斜杠**的目录路径返回 307 跳到带斜杠版本，**查询参数原样保留**，浏览器与 curl -L 均无感。
- **静态托管验证别忘同源性**：改动 `api.ts` 基址逻辑后，跑 `npm run build:static` + uvicorn（挂载 `out/`）在浏览器实际点一遍；只跑 dev/E2E 验证不到静态链路（dev 走的是 Next 代理）。
- **gradle wrapper 官方下载链不可达**（第十二次迭代踩过）：`distributionUrl` 官方地址会 302 到 `github.com/gradle/gradle-distributions` 的 release 资产，本机网络不稳 → 首次 `flutter build apk` 直接失败。已改用**华为云镜像**（`mobile/android/gradle/wrapper/gradle-wrapper.properties`，文件内附注释）。排查技巧：wrapper 缓存目录 `%GRADLE_USER_HOME%\wrapper\dists\<版本>\<hash>` 的 **hash = Base36(MD5(完整 URL 字符串))**——换 URL 会换 hash，可用 Python 反推某个缓存目录对应的是哪个 URL。
- **PyInstaller 冻结桌面版的三个要点**：① 无控制台（`console=False`）→ 一切诊断写 `<数据目录>/desktop.log`，`--smoke` 用**退出码**反映结果；② `alembic/` 与 `alembic.ini` 必须以 datas 打进 `_internal` 根（`BASE_DIR` 解析即 `_internal`），否则迁移静默回退 create_all；③ uvicorn 的动态导入（`loops.auto` / `protocols.*.auto` / `lifespan.on`）要写进 hiddenimports，webview/pythonnet/clr_loader 用 `collect_all` 连同 JS 资源一起收。
- **手机（APK）连不上电脑**的三个常见原因：后端仍绑在 127.0.0.1（要 `--host 0.0.0.0`）、Windows 防火墙未放行 8000 入站、手机与电脑不在同一局域网。另注意：后端暴露到局域网后建议启用密码保护。

## 10. 最近一次迭代（第十二次）改了什么

**桌面应用 + 安卓 APK**——在「静态网页」之外补齐另外两大分发形态（使用者视角的三种启动方式：静态网页 / 桌面应用 / 安卓 APK）：

- **桌面应用（`desktop/`）**：`shell.py` 内嵌 uvicorn（127.0.0.1 随机端口）+ WebView2 窗口；数据便携化（exe 同级 `data/`）；`--smoke` 自检；前端新增桌面桥接 `isDesktopShell()/openExternal()`（附件打开、JSON/CSV 导出改走系统浏览器）；后端 `?download=1` 导出头；`build.ps1` 一键 PyInstaller onedir 打包（68 MB）；依赖组 `desktop`（pywebview/pythonnet/pyinstaller）
- **安卓 APK（`mobile/`）**：Flutter 3.44.9 WebView 客户端——服务器地址配置页 + 全屏 WebView（刷新/改地址/返回键处理/错误重试）；INTERNET + 明文 HTTP；release 构建 45.7 MB（debug 签名可侧载）
- **构建修复**：gradle wrapper 改华为云镜像（官方链重定向到 GitHub 资产不可达）
- **本机验证**：pytest **79**、Vitest **26**、E2E **10**、冒烟 **24/24**、ruff/mypy/tsc/eslint 全绿；桌面版开发态/打包版冒烟 + 真实窗口启动均通过；APK aapt2 校验通过
- **未验证**：APK 真机安装与连调（本机无设备/模拟器，见 §8）

完整的逐条记录见 `docs/PROGRESS.md` §5「迭代记录」。

## 11. 给新对话的建议开场

1. 先读本文件 §2（当前状态）→ `docs/ARCHITECTURE.md`（设计决策）→ `docs/PROGRESS.md`（进度与遗留）。
2. 改后端 → 跑 `pytest + ruff + mypy`；改前端 → `tsc + eslint + vitest + build`；涉及流程 → 跑 E2E；涉及数据清空/导入导出 → 跑无 AI 冒烟。
3. 新增 i18n 文案记得在 `i18n-page-strings.ts` 补英文（§7.6），否则 Vitest 覆盖测试会失败——这是**刻意的防退化设计**，别去绕过它。
4. **新增任何"用户数据"类功能时，检查三处联动**：统一事件流是否写了事件、数据导出/导入是否要带上、`_wipe_business_data` 清空时是否要一并清理（附件那次就漏了第三处）。
5. 提交信息用中文、一次迭代一个 commit；本机做不到的事**如实标注"未在本机验证"**，不要写成"通过"。
