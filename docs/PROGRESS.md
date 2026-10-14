# CausaLab 开发进度与未解决问题

> 最后更新：2026-10-14
> 本文件是任务书 §九 要求的「开发进度与未解决问题清单」。
> **本文件中的所有数字均为本机实测结果**；任何无法在本机验证的项都逐条标注「未在本机验证」，绝不写成"通过"（任务书 §11.6）。

---

## 1. 当前基线（全部为实测值）

| 项目 | 结果 | 实测方式 |
|---|---|---|
| 后端单元/集成测试 | **79 passed** | `cd backend && uv run pytest -q` |
| 前端单元测试 | **26 passed** | `cd frontend && npx vitest run` |
| E2E（Playwright + 系统 Edge） | **10 passed** | `cd frontend && npx playwright test` |
| 无 AI 全链路冒烟 | **24 通过 / 0 失败** | `cd backend && uv run python scripts/smoke_no_ai.py` |
| ruff | All checks passed | `uv run ruff check app tests` |
| mypy | no issues（49 个源文件） | `uv run mypy app` |
| tsc | 无错误 | `npx tsc --noEmit` |
| eslint | **0 error**（11 warning，均为已声明的 `set-state-in-effect`） | `npx eslint .` |
| next build | 成功，**12 条业务路由** | `npm run build` |
| **静态导出构建** | **成功，产物 `frontend/out/`（2.5 MB，全部路由目录化）** | `npm run build:static` |
| **静态页同源托管浏览器实测** | **通过**（uvicorn + Edge：首页/建决策/详情/深链/TA 全流程 8 项） | 见 §2.5 |
| **桌面版打包（PyInstaller onedir）** | **成功，68 MB**；开发态/打包版双冒烟通过、真实窗口启动验证通过（关窗无残留进程） | `desktop\build.ps1` → `CausaLab.exe --smoke` |
| **安卓 APK（Flutter release）** | **构建成功，45.7 MB**（aapt2 校验：`com.causalab.causalab` v0.1.0 / INTERNET / arm64+armv7+x86_64） | `flutter build apk --release` |
| 数据模型 | **37 张业务表**（+ `alembic_version`） | `len(Base.metadata.tables)` |
| 数据库迁移 | head = `b69c58233d86`（共 5 个迁移） | `uv run alembic current` |
| API 规模 | **99 条路径 / 134 个操作** | `app.openapi()` |

> 运行时：Python 3.14.7 · Node v24.21.0 · Next.js 16.4.0 · FastAPI 0.143.0 · SQLAlchemy 2.1.4 · py-fsrs 6.3.2

---

## 2. 已完成

### 2.1 四个核心模块

| 模块 | 状态 | 要点 |
|---|---|---|
| **Knowledge Debt (KD)** | 完成 | 学科/知识点/依赖图（React Flow）、学习任务与答题记录（正确/错误类别/是否独立）、五类障碍诊断、诊断依据+置信度+备选解释、用户纠正、建议→验证→结论闭环；护栏：答题 <3 或失败 <2 强制 `insufficient_data` 且置信度 ≤0.25 |
| **Memory Laboratory (ML)** | 完成 | 卡组/卡片、FSRS v6 官方库调度、主动回忆复习、复习与回忆耗时、遗忘曲线与统计、A/B 对照实验（随机分组、结果含免责声明） |
| **Decision Time Machine (DTM)** | 完成 | 决策记录与背景、概率预测、**不可覆盖快照**（无修改/删除端点）、新信息时间线、到期复盘提醒、校准分析（Brier + 分桶）、过程质量与结果解耦、反事实（恒标记为假设） |
| **Task Autopsy (TA)** | 完成 | 项目/任务/子任务/依赖、预估 vs 实际耗时、7 类过程事件（阻塞/恢复/返工/中断/需求变化/备注/依赖解除）、统计、规则复盘（严格区分事实/推测/缺失证据）、改进措施追踪 |

### 2.2 三个跨模块能力
- **Evidence Timeline**：统一 `events` 事件流 + 游标分页（`before_at`+`before_id`）
- **Hypothesis Laboratory**：假设、观察值（含分组上下文）、分组对比 + 固定局限性说明（相关≠因果）
- **Improvement Loop**：observe→hypothesize→intervene→measure→review→adjust 六阶段推进与结论

四模块联动通过 `events` / `evidence` / `entity_links` 三张共享表实现（如 KD 诊断一键派生 ML 实验、TA 任务完成后反馈到 DTM）。

### 2.3 AI 接入
- 四种模式：`none`（默认，一等公民）/ `mock`（演示与自动化测试）/ `openai-compat`（DeepSeek / MiMo / Moonshot / 任意兼容）/ 真实云端
- **不做本地模型部署**（无 Ollama）
- 设置项齐全：Provider、Base URL、API Key、模型 ID（不硬编码）、Temperature、最大输出 Token、请求超时、每月预算、价格与费用估算、自动确认发送、**按任务类型覆盖模型**
- 隐私闸门（428 预览确认）、预算闸门（402）、结构化输出经 Pydantic 校验、失败回退规则引擎、用量与费用统计、限流与重试

### 2.4 题目 / 解答附件上传（本轮新增）
- 新表 `attachments`（`module` / `ref_type` / `ref_id` / `kind` / `original_name` / `stored_name` / `content_type` / `size_bytes` / `note`），沿用 `evidence`/`entity_links` 的挂载模式，可扩展到任意模块实体
- 端点：`GET/POST /api/uploads`、`GET /api/uploads/{id}/content`、`DELETE /api/uploads/{id}`
- 安全设计：扩展名白名单（png/jpg/jpeg/webp/gif/pdf/txt/md）、`content_type` 由扩展名推导（不信任客户端）、单文件 10 MB 上限且超限立即清理半截文件、磁盘文件名由 `uuid4` 生成（杜绝路径穿越与覆盖）、响应**不回传** `stored_name`、写入统一事件流、受可选密码保护中间件约束
- 与数据管理的联动：**「清空业务数据」与「载入演示数据」都会同时删除附件记录与磁盘文件**（附件是二进制，不参与 JSON 导出，但绝不能留孤儿记录）
- 前端：KD「学习任务与诊断」标签页内新增「题目与解答附件」卡片（类型选择 / 选择文件 / 上传 / 列表 / 打开 / 删除），**与文本记录并存**（文本记要点，附件存原始题目与手写解答）
- 测试：后端 **14** 个用例（扩展名/大小/空文件/非法 scope/路径穿越/越权/下载一致性/清空联动）+ 前端 `postForm` 1 个单元用例 + E2E **2** 个场景（真实文件上传与删除、按任务模型保存并回读校验）

### 2.5 静态网页分发（本轮新增）

依托「不依赖 Docker」的分发路线，新增第三种运行形态：**纯静态网页 + 后端托管**。

- **解除 API 通道对 Next 代理的硬依赖**（原 Bug 1）：`api.ts` 新增基址解析，优先级 `window.__CAUSALAB_API_BASE__`（运行期注入，部署后不改包即可换后端地址）→ `NEXT_PUBLIC_API_BASE`（构建期）→ `""`（相对路径，开发/同源场景零行为变化）；`api()` / `postForm()` 与 4 处裸 `fetch/跳转`（登录、CSV 导出、任务事件轮询、附件打开）统一走 `apiUrl()`。
- **详情页改为查询参数路由**（原 Bug 2）：`/dtm/[id]`→`/dtm/detail?id=N`、`/ta/[id]`→`/ta/detail?id=N`；动态段无法在构建期枚举全部运行期 id，静态导出必然失败，改为查询参数后彻底解除。9 处链接构造同步更新，空 `id` 有明确报错态（含英文翻译）。
- **静态导出构建**：`npm run build:static`（`scripts/build-static.mjs`，跨平台、零新依赖；`STATIC_EXPORT=1` → `output: "export"` + `trailingSlash`，该模式不注册 rewrites）。
- **后端同源托管**：`app/main.py` 在所有 API 路由之后挂载 `StaticFiles(html=True)`，默认目录 `frontend/out/`（`CAUSALAB_STATIC_DIR` 可覆盖）；目录或 index.html 缺失时跳过并记日志（pytest / 纯 API 场景不受影响）。同源托管无 CORS、无代理；页面公开、`/api/*` 仍受可选密码保护约束。
- **异地托管（可选场景）**：任意静态服务器 + 后端设 `CAUSALAB_CORS_ORIGINS`（JSON 数组）+ 页面放一个 `config.js` 注入 `window.__CAUSALAB_API_BASE__`（文档见 `config.py` 顶部注释）。
- **测试**：后端新增 `tests/test_static.py` 3 个用例（根页面与深链目录、`/api` 优先级、目录缺失不挂载）；前端新增 4 个基址解析单元用例。
- **本机实测**（Edge，经 uvicorn 同源托管 `http://127.0.0.1:8031/`）：首页加载、UI 建决策、点卡片进详情（查询参数路由）、详情内加预测、直接深链（无尾斜杠，StaticFiles 307 跳转保留 `?id=`）、TA 项目详情、刷新持久性——**8 项全部通过**。

### 2.6 桌面应用与安卓 APK（本轮新增，三大分发形态齐备）

**桌面应用（`desktop/`）——Windows 双击即用，使用者无需 Python / Node / Docker**：

- `desktop/shell.py`：内嵌 uvicorn（127.0.0.1 随机空闲端口，同源托管静态前端）+ WebView2 窗口（pywebview 6.2.1 + pythonnet 3.2.1）；
  数据目录便携化（打包态 = exe 同级 `data/`，开发态 = `desktop/.data/`）；`--smoke` 无窗口自检；日志写 `<数据目录>/desktop.log`（打包版无控制台）；
- **桌面桥接（前端）**：`isDesktopShell()` / `openExternal()`——附件打开与 JSON/CSV 导出改走系统浏览器（webview 内 `window.open` / blob 下载不可靠）；后端 `GET /api/data/export?download=1` 附 `Content-Disposition`；
- **打包**：`desktop/build.ps1` 一键（PyInstaller onedir；spec 捆绑静态前端 `web/`、`alembic/` 迁移脚本与配置、webview / pythonnet / clr_loader 资源；uvicorn / sqlalchemy 隐藏导入）；产物 **68 MB**；
- 依赖组：`backend/pyproject.toml` 新增可选 `desktop` 组（pywebview / pythonnet / pyinstaller；默认安装与 CI 不受影响，uv.lock 已同步）；
- **验证（本机）**：开发态冒烟 ✅ → PyInstaller 打包 ✅ → 打包版 `--smoke` ✅（含完整 Alembic 迁移链）→ 真实窗口启动 ✅（WebView2 加载、关窗无残留进程）。

**安卓 APK（`mobile/`）——Flutter WebView 客户端（手机连接电脑端的 CausaLab，同一局域网）**：

- 首次填写电脑地址（`http://<电脑IP>:8000`）并保存，之后自动直连；右上角可刷新 / 改地址；连接失败有明确提示与重试入口；
- 允许明文 HTTP（局域网 http://）+ INTERNET 权限；应用名 CausaLab；release 采用 Flutter 模板默认 debug 签名（可直接侧载）；
- **构建**：`flutter build apk --release`（JDK 17 + Android SDK + Flutter 3.44.9）；**gradle 发行版改用华为云镜像**（官方下载链重定向到 github.com 资产，本机网络不可达；文件内附注释可换回官方源）；
- 产物：`mobile/build/app/outputs/flutter-apk/app-release.apk`（**45.7 MB**，aapt2 校验：包名 `com.causalab.causalab` v0.1.0 / INTERNET / arm64-v8a+armeabi-v7a+x86_64）；
- **手机访问前置**：电脑端需 `uvicorn --host 0.0.0.0` + 防火墙放行 8000（README / mobile/README 已写明）；暴露到局域网**建议启用密码保护**；
- 未验证：**真机安装与局域网连调**（本机无 Android 设备/模拟器，见 §3）。

---

## 3. 未在本机验证的项（**严禁当作"通过"**）

本机为 Windows 11，无 Docker、Docker Hub 不可达、无 PostgreSQL 服务端、`api.openai.com` 不可达，因此以下内容**已交付但无法在本机验证**：

| 项 | 状态 | 说明 |
|---|---|---|
| `docker compose up` | ⚠️ **未在本机验证** | 本机无 Docker；已交付 `docker-compose.yml` + 前后端 Dockerfile + `.dockerignore` |
| PostgreSQL 真实集成 | ⚠️ **未在本机验证** | 无 PG 服务端。驱动 `psycopg[binary]` 已加入依赖，`app/db.py` 的分支逻辑已按标准写法实现，但**从未连接过真实 PG** |
| OpenAI 官方 API | ⚠️ **未在本机验证** | 适配代码已写（OpenAICompatProvider），本机网络不可达 |
| GitHub Actions CI 真跑 | ⚠️ **未在本机验证** | `act` 需要 Docker。workflow 已按官方语法编写并修正过 3 处错误配置，但**从未在 CI 上真跑** |
| CI 的 Playwright Chromium 路径 | ⚠️ **未在本机验证** | 本机使用系统 Edge（`channel: msedge`）验证通过；CI 的 Chromium 路径未实跑 |
| Firefox / WebKit | ⚠️ **未在本机验证** | 本机只有 Edge，E2E 仅覆盖 Edge |
| HuggingFace 下载 | ➖ 不涉及 | 本产品明确不做本地模型部署 |
| 安卓 APK 真机安装与局域网连调 | ⚠️ **未在本机验证** | 本机无 Android 设备/模拟器；APK 构建与包体校验（aapt2）已通过，安装与连接流程需真机验证 |
| 桌面版窗口内的完整手工点选流程 | ⚠️ 部分验证 | 窗口启动、页面加载、双冒烟（含迁移链）已验证；完整交互（建决策/附件/导出）建议按 `desktop/README.md` 手动过一遍 |

**已在本机充分验证**：pytest 79、Vitest 26、`next build`、`npm run build:static`（静态产物 `frontend/out/`）、uvicorn 同源托管静态页的浏览器全流程（Edge，8 项）、**桌面版**（PyInstaller 打包成功、开发态/打包版双冒烟、真实窗口启动）、**安卓 APK**（release 构建成功、aapt2 包体校验）、Playwright E2E（Edge，10 场景）、Alembic 迁移（SQLite）、ruff、mypy、tsc、eslint、无 AI 全链路冒烟 24/24、附件上传端到端（经 Next 代理的真实链路 + 浏览器内真实文件选择与删除）。

---

## 4. 已知问题与取舍（如实记录）

1. **Next 调试按钮遮挡侧边栏文案**：dev 模式下 Next 的「N」固定按钮会压住侧边栏底部文案。已在 `app-shell.tsx` 用 `NODE_ENV === "development"` 条件追加底部内边距规避；生产构建界面不受影响。
2. **演示数据时间戳集中**：一键载入的演示数据几乎同一时刻生成，导致首页「近 14 天活动」只有一天有柱子，图表观感偏极端（数据本身真实，非 bug）。
3. **`.next/dev` 开发缓存会持续增长**：跑 `next dev`/E2E 后该目录可涨到数百 MB（曾测得约 750 MB），而纯 `npm run build` 的 `.next` 仅约 75 MB。属 Next/Turbopack 行为；日常可用 `npm run build && npm start` 减轻，或定期清理。
4. **`frontend/AGENTS.md` 由 `next dev` 自动重写**且被 git 跟踪，跑 dev 后可能出现非预期 diff（Next 官方设计如此）。
5. **`.zcodeignore`** 是 ZCode 编辑器的个人工具配置，随仓库分发；对项目本身无作用。
6. **`vitest.config.ts` 的 ESM/CommonJS 警告**：Vite 未来大版本将改变 config 加载方式，届时需改为 `.mts` 或设置 `"type": "module"`。当前仅为警告。
7. **学术诚实边界**（刻意设计，非缺陷）：
   - 单人 A/B 实验**不能**证明某种记忆方法对所有人最优 → 实验结果固定附免责声明；
   - 相关性**不等于**因果 → 假设分析固定附局限性说明；
   - **不**用最终结果判断当初决策的对错 → 过程质量分独立于结果；
   - **不**凭一次失败断言能力缺陷 → 规则诊断护栏强制 `insufficient_data`。
8. **SQLite 并发**：认证中间件按「先关闭自身 DB 会话再放行」实现以避免写锁争用；高并发场景应改用 PostgreSQL（见第 3 节，本机无法验证）。
9. **隐私闸门默认为开启预览**（`auto_confirm_send = false`）。若曾改为直接发送，建议确认后改回，以免私人资料在无确认的情况下发往第三方模型。
10. **`frontend/scripts/_i18n_strings_all.py` 已不存在**：早期文档提到用它生成 `i18n-page-strings.ts`，该脚本在某次死代码清理中被移除。现在新增文案直接编辑 `i18n-page-strings.ts` 即可，`tests/i18n.test.ts` 会强制校验覆盖率。

---

## 5. 迭代记录

| # | 提交 | 内容 |
|---|---|---|
| 1 | `49a8e3a` | FastAPI 后端完整实现（模型/迁移/服务/路由） |
| 2 | `a4766c8` | Next.js 16 前端完整实现 |
| 3 | `2f65329` | Playwright Edge E2E 核心流程（7/7） |
| 4 | `810788b` | README / ARCHITECTURE / API 文档 / Docker / CI |
| 5 | `afcd41f` | Windows 一键启动脚本 |
| 6 | `160aca0` | 后端不可达友好指引 + 启动脚本端口清理与就绪等待 |
| 7 | `8a07078` | 全站英文翻译 + zh/en 切换 |
| 8 | `e669165` | FSRS 学习/重学步骤细分展示 |
| 9 | `1c47503` | 可选密码保护（bcrypt + 会话 Cookie + 限流） |
| 10 | `d46d17c` | 品牌图标 + 时间线游标分页与索引 |
| 11 | `10446ff` | 回忆用时指标 + TA 依赖传播自动化 |
| 12 | `00678be` | 死代码清理 + 无 AI 全链路冒烟 24/24 |
| 13 | `ff19b91` | HANDOFF.md 交接文档 |
| 14 | `b8734f1` | AI 真实冒烟打通 + Dev Tools 汉化与拖拽 |
| 15 | `fb6e68c` | 设置页 DeepSeek 参考价提示 |
| 16 | `93b4b1b` | AI 用量记录可清空 |
| 17 | `90b9bf1` | 清理已移除文档的残留引用 |
| 18 | `d512aca` | 修正 CI E2E job 的 project 名与环境变量名 |
| 19 | `ea175bf` | 新增前后端 `.dockerignore`（修 `COPY . .` 覆盖容器依赖的隐患） |
| 20 | `f20309b` | 校正文档计数漂移 + 补全 API 文档（与 OpenAPI 对齐） |
| 21 | `c0f2fcb` | 补上 PostgreSQL 驱动 `psycopg` + 移除未使用依赖 |
| 22 | `4dea440` | 消除弃用告警、lint 告警与冒烟脚本 GBK 编码崩溃 |
| 23 | `f2d1cae` | 恢复 `alembic.ini` 纯 ASCII，修复启动迁移静默降级 |
| 24 | *（本轮）* | 题目/解答附件上传（表+迁移+端点+前端+测试）；按任务类型选模型的前端入口；修 `task_models` 被清空的数据丢失、pytest 临时目录泄漏、依赖下限、调试按钮遮挡；本文件重建 |
| 25 | *（静态分发轮）* | 静态网页分发：解除 API 通道对 Next 代理的硬依赖（基址注入 + `apiUrl()` 统一）；详情页改查询参数路由；`npm run build:static` 静态导出；FastAPI 同源托管 `out/`；新增 test_static.py 3 例 + 基址解析 4 例；冒烟脚本支持 `CAUSALAB_SMOKE_BASE` 端口覆盖 |
| 26 | *（本轮）* | **桌面应用**（pywebview 壳 + 前端桌面桥接 + PyInstaller 打包，68 MB）+ **安卓 APK**（Flutter WebView 客户端，45.7 MB）；gradle wrapper 改华为云镜像；README 升级为三大分发形态；pytest 79 / Vitest 26 |

---

## 6. 下一步建议

1. **安卓 APK 真机验证**：把 `mobile/build/app/outputs/flutter-apk/app-release.apk` 安装到手机，按 README「安卓 APK」一节连接电脑后端并走一遍核心流程（本机无 Android 设备/模拟器，未能代验）。
2. **桌面版打磨（可选）**：自定义应用图标、正式代码签名（当前为未签名 exe，首次运行 SmartScreen 会提示「仍要运行」即可）、开机自启等。
3. **在具备 Docker 的机器上真跑一次** `docker compose up --build`，验证 Dockerfile 与 `.dockerignore`（本机永远做不到）。
4. **在具备 PostgreSQL 的机器上**验证 `CAUSALAB_DB_URL=postgresql+psycopg://...` 的建表与迁移兼容性。
5. **让 CI 真跑一次**（当前仅本地校验过语法与配置项名称）；可考虑在 CI 增加桌面打包与 APK 构建任务（本机已证明两者均可构建）。
6. 若要暴露到公网：启用密码保护，并考虑在反向代理层再加一道登录限流（进程内限流重启即清零）。
7. 附件上传目前仅接在 KD 知识点上；由于表结构是通用的 `(module, ref_type, ref_id)`，可按需扩展到 ML 卡片、DTM 决策、TA 任务等。
