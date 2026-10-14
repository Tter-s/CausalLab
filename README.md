# CausaLab — 个人学习、决策与行动实验室

> 帮助你理解自己为什么反复遇到同类问题，并通过**记录、分析、实验和复盘**，寻找真正有效的改进方法。

CausaLab 不是错题本、记忆卡片、日记或待办工具，而是一个把「学习障碍诊断、记忆策略实验、决策复盘、任务失败分析」连成一体的实验室：四个核心模块共享统一的事件时间线、证据记录与 AI 分析接口，用数据回答「我为什么会这样」和「什么改进真的有效」。

> **全程本机运行（非线上环境）**：数据默认只存本机（SQLite 单文件 + 本地附件目录），不需要任何在线服务、账号或云数据库；
> 云端 AI 完全可选、默认关闭——**无 AI 模式即完整可用**。
>
> **三种使用形态**：① **静态网页**（浏览器直接开）· ② **桌面应用**（Windows 双击即用，内嵌后端与页面，无需任何环境）· ③ **安卓 APK**（手机上连接电脑使用）。

## 功能总览

### 四个核心模块

| 模块 | 解决什么 | 关键能力 |
|---|---|---|
| **知识债务 (KD)** | 学习障碍诊断而非正确率统计 | 知识依赖图谱（React Flow）、答题记录、**题目/解答附件上传（图片、PDF）**、五类障碍分类（概念/提取/方法/执行/迁移）、可纠正的 AI/规则诊断、建议→验证→结论闭环 |
| **记忆实验室 (ML)** | 用自己的数据检验记忆策略 | FSRS-6 官方算法调度、主动回忆复习、遗忘/复习统计图、随机分组 A/B 对照实验（附科学性免责声明） |
| **决策时间机 (DTM)** | 记录决策当时的真实想法 | 不可覆盖快照（只追加）、概率预测与校准分析（Brier 分数）、新信息时间线、过程质量复盘（与结果好坏解耦）、反事实推演（恒为假设标记） |
| **任务复盘 (TA)** | 用过程数据解释延期与返工 | 任务/子任务/依赖、阻塞/返工/中断/需求变化事件、预估-实际统计、规则/AI 复盘报告（严格区分事实/推测/缺失证据）、改进措施追踪 |

### 三个跨模块能力

- **证据时间线 (Evidence Timeline)**：一切判断可追溯——什么时候形成、依据什么、后来出现了什么新证据、为什么变化。
- **假设实验室 (Hypothesis Laboratory)**：把「我上午学习效率更高」这类直觉变成可检验的记录实验，分组对比并强制附上局限性说明（相关≠因果）。
- **改进循环 (Improvement Loop)**：发现问题 → 提出假设 → 设计干预 → 执行 → 收集数据 → 复盘 → 修改策略，每一步都是可操作的产品流程。

### 四模块联动（不是四个孤立页面）

- 知识债务的诊断可以**一键派生**记忆实验室实验（跨模块链接自动建立）；
- 决策的执行任务落在任务复盘里，任务完成后结果**反馈**到决策时间线；
- 一切动作进入统一事件流，仪表盘、全局搜索、证据时间线跨模块呈现。

### AI 接入（可选增强）

- 支持 **DeepSeek / MiMo / Moonshot / 任意 OpenAI 兼容云端 API / Mock 演示模式 / 完全无 AI**（默认且一等公民）；
- 不做本地模型部署（无 Ollama）；
- 所有云端调用经服务端代理；API Key 加密存储（Fernet + 本机密钥文件），掩码返回，绝不进前端/日志/错误报告；
- **隐私确认闸门**：默认每次向云端发送内容前弹窗预览，用户确认后才发送（可关闭）；
- 结构化输出经 Pydantic 校验，AI 永不直接写库；调用失败自动回退规则分析，基础功能永不受影响；
- 月度预算上限、Token 用量与费用估算、超时重试与限流处理；
- 模型名由用户自行填写（不硬编码），支持按任务类型指定低成本模型。

---

## 本机安装与运行（详细指南）

> 下列步骤在 **Windows 11 + PowerShell** 上实测通过；macOS / Linux 命令基本相同（仅「一键启动脚本」为 Windows 专属）。
> 全程**不需要** Docker、不需要 PostgreSQL、不需要注册任何在线账号（云端 AI 为可选功能）。

**极简版（三步）**：装好 uv 与 Node → `backend` 里 `uv sync`、`frontend` 里 `npm ci` → 双击仓库根目录的 `启动CausaLab.bat`。

### 1. 运行环境要求

| 组件 | 要求 | 说明 |
|---|---|---|
| 操作系统 | Windows 10/11（已验证） | macOS / Linux 理论兼容（用「手动启动」，见方式 B） |
| Python | **3.12+**（开发验证版本 3.14.7） | 无需手动安装：由 uv 自动管理（项目已固定 3.14） |
| uv | 最新版（开发验证版本 0.12.13） | Python 包/环境管理器，替代 pip + venv |
| Node.js | **≥ 20**（开发验证版本 24.x） | 仅前端需要；用「静态托管形态」时也需 Node 构建一次 |
| 浏览器 | Chrome / Edge / Firefox 任意现代浏览器 | E2E 测试复用系统 Edge，不额外下载浏览器 |
| 网络 | **仅首次安装依赖需要** | 装好后可长期离线运行；依赖镜像可自配 |

- 安装 uv：`winget install astral-sh.uv`（或见 [uv 官方文档](https://docs.astral.sh/uv/) 的其他安装方式）。
- 安装 Node.js：[nodejs.org](https://nodejs.org/) LTS 版即可。
- 验证：`uv --version`、`node -v`、`npm -v` 均能输出版本号。

### 2. 获取代码

```bash
git clone https://github.com/Tter-s/CausalLab.git
cd CausalLab
```

（也可直接使用任意本地目录下的项目副本。）

### 3. 安装依赖（每台机器只需一次）

```powershell
# 后端：创建 .venv 并按 uv.lock 精确安装（含测试/lint 工具）
cd backend
uv sync

# 前端：按 package-lock.json 精确安装
cd ../frontend
npm ci
```

> 下载慢的备选：npm 可先 `npm config set registry https://registry.npmmirror.com`；uv/pip 可配置国内 PyPI 镜像（`UV_DEFAULT_INDEX=https://mirrors.aliyun.com/pypi/simple/`）。

### 4. 配置（全部可选，默认值即可直接运行）

后端所有配置都支持 `CAUSALAB_` 前缀的环境变量，或写在 `backend/.env` 文件里（`.env` 已被 .gitignore 排除，不会提交）：

| 变量 | 默认值 | 用途 |
|---|---|---|
| `CAUSALAB_DATA_DIR` | `backend/data` | 数据目录：SQLite 数据库、密钥文件、上传附件都放这里 |
| `CAUSALAB_DB_URL` | 空（SQLite） | 数据库连接串；留空用 SQLite，可切 PostgreSQL（本机未验证） |
| `CAUSALAB_STATIC_DIR` | `frontend/out` | 静态前端目录（配合「静态托管形态」使用） |
| `CAUSALAB_CORS_ORIGINS` | 本机 3000 | 跨源白名单（仅页面与后端**异源**部署时需要） |

使用方式（PowerShell 示例，只对当前窗口生效；重启终端即失效）：

```powershell
$env:CAUSALAB_DATA_DIR = "C:\CausaLabData"   # 例如把数据放到仓库之外的目录
```

或写入 `backend/.env`（持久生效）：

```
CAUSALAB_DATA_DIR=C:/CausaLabData
```

**AI 配置（可选）**：不需要环境变量——启动后在界面「设置 → AI 服务」里填写 Provider、Base URL、模型名、API Key（Key 加密后只存本机，绝不回传前端/不进日志，见下方「数据与隐私」）。
**密码保护（可选）**：界面「设置 → 安全」里开启，默认关闭（本机单人使用不需要）。

### 5. 启动（四种方式，任选其一）

#### 方式 A：一键启动（推荐，Windows）

双击仓库根目录的 **`启动CausaLab.bat`**（请先完成第 3 步安装依赖）：

- 自动清理 8000 / 3000 端口上的旧进程；
- 在独立窗口分别启动后端（FastAPI :8000）与前端（Next.js :3000）；
- 等待两个服务就绪后自动打开浏览器 `http://localhost:3000`；
- **关闭对应窗口 = 停止对应服务**。

#### 方式 B：手动启动（跨平台通用）

两个终端窗口分别执行：

```powershell
# 终端 1 —— 后端
cd backend
uv run uvicorn app.main:app --port 8000
# 启动时会自动执行数据库迁移；交互式 API 文档：http://127.0.0.1:8000/docs

# 终端 2 —— 前端（开发模式）
cd frontend
npm run dev
# 打开 http://localhost:3000（Next.js 把 /api/* 代理到 127.0.0.1:8000，无 CORS）
```

首次使用建议：进入「设置 → 数据管理 → 载入演示数据」，界面会明确显示「演示数据」标识；随时可一键清除。

#### 方式 C：静态托管形态（单端口，最接近「部署」）

前端只需构建一次静态产物，之后只跑后端一个进程：

```powershell
cd frontend
npm run build:static            # 静态导出 → frontend/out/（纯静态文件）

cd ../backend
uv run uvicorn app.main:app --port 8000
# 打开 http://127.0.0.1:8000/ —— 页面与 /api 同端口，无 CORS、无代理
```

- 后端启动时自动检测 `frontend/out/`（可用 `CAUSALAB_STATIC_DIR` 指向别处）并挂载；目录不存在则跳过、只提供 API；
- **异地托管（可选）**：把 `out/` 放到任意静态服务器/另一台机器时，给后端设 `CAUSALAB_CORS_ORIGINS`，并在静态目录放一个 `config.js`：
  ```js
  window.__CAUSALAB_API_BASE__ = "http://<后端地址>:8000";
  ```
- 静态页面公开，`/api/*` 仍受可选密码保护约束（页面可开、数据受保护）。

#### 方式 D：Docker Compose（⚠️ 本机未验证）

```powershell
docker compose up --build
# 访问 http://localhost:3000
```

> 本机无 Docker（且 Docker Hub 不可达），此方式**未实测**，仅供有 Docker 的机器参考。

### 6. 桌面应用（Windows 双击即用）

把「内置后端 + 静态前端 + 原生窗口」打包成一个绿色文件夹——**使用者不需要 Python / Node / Docker**：

```powershell
# 构建（需要 Node / uv / Python 3.12+；在仓库根目录执行）
powershell -ExecutionPolicy Bypass -File desktop\build.ps1
# 产物：desktop\dist\CausaLab\CausaLab.exe（整个 CausaLab 文件夹可整体拷到任意位置）

# 开发态直接运行（不打包）
cd backend
uv run --group desktop python ..\desktop\shell.py
```

- 双击 `CausaLab.exe`：自动在 `127.0.0.1` 起内置后端并打开窗口（关窗即退出，无残留进程）；
- **数据在 exe 同级的 `data\`**（便携式：整个文件夹拷走，数据跟着走）；日志：`data\desktop.log`；
- 附件打开与 JSON/CSV 导出交给系统默认浏览器处理（窗口内下载不可靠）；
- 自检：`CausaLab.exe --smoke`（退出码 0 = 通过）；更多见 `desktop\README.md`。

### 7. 安卓 APK（手机连接电脑使用）

手机上的 CausaLab 是一个 WebView 客户端——页面与数据来自你电脑上运行的 CausaLab，**需在同一局域网**：

```powershell
# 构建（需要 Flutter + JDK 17 + Android SDK；本机工具链环境变量示例）
$env:JAVA_HOME = "D:\jdk17"
$env:ANDROID_HOME = "D:\Android\Sdk"
$env:GRADLE_USER_HOME = "D:\gradle-home"
cd mobile
flutter build apk --release
# 产物：mobile\build\app\outputs\flutter-apk\app-release.apk（拷到手机安装即可）

# 电脑端（让手机能访问）：后端监听局域网地址
cd backend
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
# 首次可能需要在（管理员）PowerShell 放行防火墙入站：
#   New-NetFirewallRule -DisplayName "CausaLab LAN" -Direction Inbound -Protocol TCP -LocalPort 8000 -Action Allow -Profile Private
```

- 手机首次打开填写 `http://<电脑IP>:8000`（电脑 IP 用 `ipconfig` 查询）；电脑端先执行过一次 `npm run build:static`（静态页面形态），或改填开发地址 `http://<电脑IP>:3000`；
- 手机与电脑连接同一个 Wi-Fi；**建议**：把 CausaLab 暴露到局域网时启用「设置 → 安全」密码保护；
- 说明：仅含 Android 平台；release 包采用 Flutter 模板默认的 debug 签名（可直接侧载，上架商店需自配签名）；更多见 `mobile\README.md`。

### 8. 验证安装（本机自检）

```powershell
# ① 后端测试（79 个用例）
cd backend ; uv run pytest -q

# ② 前端测试（26 个用例）
cd frontend ; npx vitest run

# ③ 端到端测试（Playwright + 系统 Edge；自动拉起隔离前后端 :8010/:3100）
cd frontend ; npx playwright test

# ④ 无 AI 全链路冒烟（需后端已在 8000 运行；24 项全过即正常）
cd backend ; uv run python scripts/smoke_no_ai.py
#    若 8000 被别的程序占用，可另起隔离实例并用环境变量指向：
#    $env:CAUSALAB_SMOKE_BASE = "http://127.0.0.1:8031"

# ⑤ 静态产物构建自查
cd frontend ; npm run build:static

# ⑥ 桌面版自检（先按「6. 桌面应用」打包）
desktop\dist\CausaLab\CausaLab.exe --smoke
```

**手工验收清单（浏览器，2 分钟）**：

1. 打开首页 → 可见「概览」标题与统计卡片；
2. 设置 → 数据管理 → 「载入演示数据」→ 各模块图表出现数据；
3. 决策时间机 → 记录一条决策 → 点卡片进详情 → 添加一条预测 → 返回；
4. 设置 → 数据管理 → 导出 JSON（得到备份文件）→ 清空业务数据（可再导入还原）。

后端健康检查：访问 `http://127.0.0.1:8000/api/health`，返回 `{"status":"ok",...}` 即正常。

---

## 常见问题（FAQ）

### 启动与端口

1. **端口被占用（8000 / 3000）**：一键脚本会自动清理；手动模式可先执行 `npx kill-port 8000 3000`，或改端口启动（前端换端口后，可用 `API_PROXY_TARGET` 指定后端地址）。注意同一项目只允许一个 `next dev`。
2. **页面提示「无法连接后端 API」**：后端没起来或地址不对。先访问 `http://127.0.0.1:8000/api/health` 确认；再查看后端窗口中的报错。
3. **`npm run build` 与 `next dev` 互相干扰**：两者共用 `frontend/.next` 缓存，构建前请先关闭 dev server。

### 数据库与数据

4. **启动日志出现 `Alembic migration failed, falling back to create_all()`**：迁移没有跑起来、已静默回退建表（应用可用但迁移链失效）。常见原因是 `backend/alembic.ini` 被改成了非 ASCII 内容（该文件必须保持纯 ASCII）；确认后删掉 `backend/data/causalab.db` 重新启动即可。
5. **数据存在哪里？怎么备份？**：全部在 `backend/data/`（SQLite 数据库 + `uploads/` 附件 + `secret.key`）。整体复制该目录即完成完整备份；也可用「设置 → 数据管理」导出/导入 JSON（附件不参与 JSON 导出，请一并复制 `uploads/`）。
6. **忘记密码保护的密码怎么办**：先备份 `backend/data/`，停掉后端，然后重置（会把密码保护恢复为「关闭」状态，数据不受影响）：
   ```powershell
   cd backend
   uv run python -c "import sqlite3; c=sqlite3.connect('data/causalab.db'); c.execute('DELETE FROM settings WHERE key=char(97,117,116,104,95,99,111,110,102,105,103)'); c.commit(); print('已重置密码保护')"
   ```
   （命令中 `char(...)` 生成的就是字符串 `auth_config`，这样写是为了避免命令行引号嵌套问题，可原样复制执行。）
   若自定义过 `CAUSALAB_DATA_DIR`，把命令中的 `data/causalab.db` 换成实际路径。另一个更彻底的办法：备份后直接删除 `backend/data/causalab.db` 重建——但那会丢失全部数据，不推荐。
7. **想换 PostgreSQL**：设置 `CAUSALAB_DB_URL=postgresql+psycopg://user:pass@host:5432/db` 后重建库（迁移会自动执行）。本机无 PG 服务端，**未验证**。

### AI 配置

8. **「测试连接」失败**：常见原因有——Base URL 填成了非 OpenAI 兼容端点（如误填 `/anthropic` 后缀）；模型名不对（DeepSeek 合法值为 `deepseek-chat` / `deepseek-reasoner`，不能只写 `deepseek`）；Key 无效或余额不足；本机访问不了该域名。
9. **不想连云端**：什么都不用配，或把 Provider 设为 `none`/`mock`——规则诊断、规则复盘与全部统计功能不受影响。

### Windows / 编码

10. **命令行输出乱码或 `UnicodeEncodeError`**：Windows 控制台默认 GBK，仓库内脚本已做 UTF-8 处理；自己写小脚本打印 ✓/✗ 时同样需要对 `sys.stdout` 做 `reconfigure(encoding="utf-8")`。
11. **PowerShell 读取含中文的 UTF-8 文件乱码**：不要用默认 `Get-Content`，用 `Get-Content -Encoding utf8` 或脚本内 `read_text(encoding="utf-8")`。
12. **E2E/Playwright 相关**：只复用系统 Edge（`channel: msedge`），**不要**执行 `npx playwright install`；跑 E2E 前先关掉 3000 端口的 dev server。
13. **`frontend/.next` 越来越大**：dev 模式缓存可持续增长（数百 MB），属 Next/Turbopack 正常行为，可定期删除该目录。

### 静态托管形态

14. **静态页面能打开但数据加载失败**：
    - 同源托管（方式 C）：确认后端在运行、`frontend/out/` 存在且已重新构建；
    - 异地托管：确认页面 `config.js` 的 `window.__CAUSALAB_API_BASE__` 指向正确的后端地址，且后端 `CAUSALAB_CORS_ORIGINS` 包含页面来源。
15. **直接输入详情页链接报 404**：静态服务器需要支持「目录索引」（把 `/dtm/detail/` 映射到 `index.html`）；FastAPI 同源托管已内置该行为。

### 桌面版 / 安卓版

16. **桌面版的数据存在哪里、如何迁移**：`CausaLab.exe` 同级的 `data\` 目录（便携式：把整个 CausaLab 文件夹拷到别处，数据跟着走）；运行日志在同目录 `desktop.log`。开发态数据在 `desktop\.data\`。
17. **APK 连不上电脑**：按序检查——① 手机与电脑连接同一 Wi-Fi；② 电脑端后端用 `--host 0.0.0.0` 启动（默认只监听本机 127.0.0.1，手机访问不到）；③ Windows 防火墙放行 8000 入站（命令见「7. 安卓 APK」一节）；④ 地址格式 `http://<电脑IP>:8000`（`ipconfig` 查询 IPv4）。暴露到局域网后**建议启用密码保护**。

### 其他

18. **macOS / Linux**：不使用 `.bat` 与桌面版打包脚本（均 Windows 专属），按「方式 B」手动启动即可，其余命令相同。
19. **完全离线可用吗**：依赖安装完成后，除「云端 AI」外的全部功能离线可用；不配置 AI 即为完全离线。
20. **如何更新代码**：`git pull` 后执行 `uv sync` 与 `npm ci`；启动时数据库迁移会自动升级。

## 无 AI 模式（默认）

没有配置任何 API Key 时，CausaLab 的全部记录、统计、实验、可视化功能**完整可用**：

- 知识诊断使用内置规则引擎（样本不足时明确输出「样本不足，暂不下结论」，绝不凭一次失败断言能力缺陷）；
- 项目复盘使用规则分析（只陈述数据事实、模式推测与缺失证据）；
- 假设分析提供分组统计与局限性说明。

配置 AI 后，同一批端点自动升级为 AI 分析（失败时回退规则分析）。

## 安全（可选密码保护）

默认关闭——本机单人模式打开即用。若要把 CausaLab 暴露到局域网/公网：进入 **「设置 → 安全」** 启用密码保护：

- 启用后所有 `/api/*` 端点（除健康检查与认证端点）都需要登录会话（HttpOnly Cookie，30 天有效）；
- 密码使用 bcrypt 哈希存储；会话令牌只存 SHA-256，数据库泄露不直接泄露会话；
- 登录接口限流（每 IP 每分钟 10 次）；前端自动跳转 `/login`，支持修改密码与关闭保护（需当前密码验证）；
- Cookie 为 SameSite=Lax + HttpOnly；页面与 API 同源（开发态经 Next.js 代理 / 静态托管由 FastAPI 直接提供），无跨站风险面；
- 未启用时行为与之前完全一致（本地打开即用）。

## 数据与隐私

- 单用户本地模式，数据默认存于本机 SQLite（`backend/data/causalab.db`）；
- 支持全量 JSON 导出/导入、答题与复习记录 CSV 导出、一键清除；
- **题目/解答附件**存于 `backend/data/uploads/`（该目录随 `backend/data/` 一并被 `.gitignore` 排除），仅接受图片/PDF/文本类白名单扩展名，单文件上限 10 MB；
- API Key 用 Fernet 加密存储在 `backend/data/secret.key`（该文件与数据库均在 `.gitignore` 中）；
- AI 请求默认带「发送前预览确认」闸门；`auto_confirm_send` 默认 `false`（推荐保持）；
- 生产可切换 PostgreSQL（`CAUSALAB_DB_URL`，驱动 `psycopg[binary]` 已内置）——见下方未验证清单。

## 未在本机验证的项（如实标注）

开发环境为 Windows 11（无 Docker、Docker Hub 不可达、`api.openai.com` 不可达），以下内容**已按规范交付但未在本机运行验证过**：

| 项 | 状态 |
|---|---|
| `docker compose up`（含 backend/frontend Dockerfile） | ⚠️ 未在本机验证（本机无 Docker） |
| PostgreSQL 集成（`CAUSALAB_DB_URL=postgresql+psycopg://…`） | ⚠️ 未在本机验证（SQLite 已充分验证；Alembic 迁移对 PostgreSQL 的兼容按标准类型编写） |
| OpenAI 官方 API（`api.openai.com`）连通 | ⚠️ 适配代码已写（OpenAICompatProvider），本机网络不可达，标注「本机未验证」 |
| DeepSeek 真实调用 | ✅ **已打通**（测试连接 + 端到端诊断 `source=ai` 实测通过）；模型名与 Base URL 由用户填写，不硬编码 |
| MiMo / Moonshot 真实调用 | ⚠️ 未在本机验证（网络可达，但无可用 Key）；协议层与 DeepSeek 共用 `OpenAICompatProvider`，已由 MockProvider + 单测覆盖请求构造/重试/解析 |
| GitHub Actions CI 真跑 | ⚠️ 未在本机验证（`act` 需要 Docker）；workflow 按官方 Action 语法编写 |
| Playwright Chromium（CI） | ⚠️ 本机使用系统 Edge（channel: `msedge`）验证通过；CI 的 Chromium 路径未实跑 |

已在本机充分验证：pytest **79** 用例、Vitest **26** 用例、`next build`、`npm run build:static`（静态导出产物 + uvicorn 同源托管的浏览器全流程）、**桌面版**（PyInstaller 打包成功、开发态/打包版双冒烟、真实窗口启动）、**安卓 APK**（release 构建成功、aapt2 包体校验）、Playwright E2E（Edge，**10** 个场景）、无 AI 全链路冒烟 **24/24**、Alembic 迁移（SQLite）、附件上传端到端（含真实文件选择与删除）、ruff、mypy、tsc、eslint。

完整进度与未解决问题清单见 [PROGRESS.md](docs/PROGRESS.md)。

## 项目结构

```
CausalLab/
├── backend/                # FastAPI + SQLAlchemy 2 + Alembic + SQLite/PG
│   ├── app/
│   │   ├── api/            # kd / ml / dtm / ta / cross / ai / auth / settings / data / uploads 路由
│   │   ├── models/         # 37 张表（四模块 + 跨模块事件/证据/链接/附件 + 设置/AI 用量）
│   │   ├── schemas/        # Pydantic v2 请求/响应模型
│   │   ├── services/       # 事件/证据/链接、附件存储、FSRS 适配、规则诊断、校准、演示数据
│   │   │   └── ai/         # Provider 抽象：none / mock / openai-compat(DeepSeek/MiMo/…)
│   │   ├── config.py       # 环境变量配置（CAUSALAB_* 前缀；含静态目录与 CORS 说明）
│   │   └── main.py         # 应用工厂（启动时自动迁移；可选挂载静态前端同源托管）
│   ├── alembic/            # 迁移（5 个）
│   └── tests/              # pytest（78 用例）
├── frontend/               # Next.js 16 + React 19 + Tailwind v4 + Radix + Recharts + React Flow
│   ├── src/app/            # 12 个路由（概览/四模块/时间线/假设/循环/设置/登录 + 2 个详情页）
│   │                       # 详情页为查询参数路由（/dtm/detail?id=N），兼容静态导出
│   ├── src/components/     # shadcn 风格 UI 组件库 + 布局壳
│   ├── src/lib/            # API 客户端（含 428 确认闸门、静态托管基址解析）、hooks、i18n（zh 完整/en 预留）
│   ├── scripts/build-static.mjs  # 静态导出（npm run build:static → out/）
│   ├── e2e/                # Playwright（Edge）10 个核心场景
│   └── tests/              # Vitest 单测（26 个）
├── desktop/                # 桌面应用（Windows）：pywebview 壳 + PyInstaller 打包，双击即用
├── mobile/                 # 安卓 APK：Flutter WebView 客户端（连接电脑使用）
├── docker-compose.yml      # 未在本机验证
└── .github/workflows/ci.yml
```

更多设计细节见 [ARCHITECTURE.md](docs/ARCHITECTURE.md) 与 [API.md](docs/API.md)；开发进度与遗留问题见 [PROGRESS.md](docs/PROGRESS.md)，新会话上下文见 [HANDOFF.md](HANDOFF.md)。

## 许可证

MIT
