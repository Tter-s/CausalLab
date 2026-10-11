# CausaLab — 个人学习、决策与行动实验室

> 帮助你理解自己为什么反复遇到同类问题，并通过**记录、分析、实验和复盘**，寻找真正有效的改进方法。

CausaLab 不是错题本、记忆卡片、日记或待办工具，而是一个把「学习障碍诊断、记忆策略实验、决策复盘、任务失败分析」连成一体的实验室：四个核心模块共享统一的事件时间线、证据记录与 AI 分析接口，用数据回答「我为什么会这样」和「什么改进真的有效」。

## 功能总览

### 四个核心模块

| 模块 | 解决什么 | 关键能力 |
|---|---|---|
| **知识债务 (KD)** | 学习障碍诊断而非正确率统计 | 知识依赖图谱（React Flow）、答题记录、五类障碍分类（概念/提取/方法/执行/迁移）、可纠正的 AI/规则诊断、建议→验证→结论闭环 |
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

### AI 接入

- 支持 **DeepSeek / MiMo / Moonshot / 任意 OpenAI 兼容云端 API / Mock 演示模式 / 完全无 AI**（默认且一等公民）；
- 不做本地模型部署（无 Ollama）；
- 所有云端调用经服务端代理；API Key 加密存储（Fernet + 本机密钥文件），掩码返回，绝不进前端/日志/错误报告；
- **隐私确认闸门**：默认每次向云端发送内容前弹窗预览，用户确认后才发送（可关闭）；
- 结构化输出经 Pydantic 校验，AI 永不直接写库；调用失败自动回退规则分析，基础功能永不受影响；
- 月度预算上限、Token 用量与费用估算、超时重试与限流处理；
- 模型名由用户自行填写（不硬编码），支持按任务类型指定低成本模型。

## 快速开始

### 环境要求

- Python ≥ 3.12（本机开发用 3.14）
- Node.js ≥ 20（本机开发用 24）

### 本地启动（推荐）

```bash
# 1) 后端
cd backend
uv sync                      # 创建虚拟环境并安装依赖（自动生成 uv.lock 一致环境）
uv run alembic upgrade head  # 初始化数据库（SQLite，位于 backend/data/）
uv run uvicorn app.main:app --port 8000
# 应用启动时也会自动执行迁移；交互式 API 文档： http://127.0.0.1:8000/docs

# 2) 前端（新终端）
cd frontend
npm ci
npm run dev
# 打开 http://localhost:3000 （Next.js 把 /api/* 代理到 127.0.0.1:8000）
```

首次使用建议：进入「设置 → 数据管理 → 载入演示数据」，界面会明确显示「演示数据」标识；随时可一键清除。

### 运行测试

```bash
# 后端（49 个用例：规则诊断护栏、快照不可覆盖、FSRS 调度、AI 闸门/预算/回退、导入导出等）
cd backend && uv run pytest -q

# 前端单测（Vitest）
cd frontend && npx vitest run

# E2E（复用系统 Edge，不下载浏览器；自动拉起隔离的前后端）
cd frontend && npx playwright test
```

### Docker Compose（未在本机验证）

```bash
docker compose up --build
# 访问 http://localhost:3000
```

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
- Cookie 为 SameSite=Lax + HttpOnly；API 经同源 Next.js 代理访问，无跨站风险面；
- 未启用时行为与之前完全一致（本地打开即用）。

## 数据与隐私

- 单用户本地模式，数据默认存于本机 SQLite（`backend/data/causalab.db`）；
- 支持全量 JSON 导出/导入、答题与复习记录 CSV 导出、一键清除；
- API Key 用 Fernet 加密存储在 `backend/data/secret.key`（该文件与数据库均在 `.gitignore` 中）；
- 生产可切换 PostgreSQL（`CAUSALAB_DB_URL`）——见下方未验证清单。

## 未在本机验证的项（如实标注）

开发环境为 Windows 11（无 Docker、Docker Hub 不可达、`api.openai.com` 不可达），以下内容**已按规范交付但未在本机运行验证过**：

| 项 | 状态 |
|---|---|
| `docker compose up`（含 backend/frontend Dockerfile） | ⚠️ 未在本机验证（本机无 Docker） |
| PostgreSQL 集成（`CAUSALAB_DB_URL=postgresql+psycopg://…`） | ⚠️ 未在本机验证（SQLite 已充分验证；Alembic 迁移对 PostgreSQL 的兼容按标准类型编写） |
| OpenAI 官方 API（`api.openai.com`）连通 | ⚠️ 适配代码已写（OpenAICompatProvider），本机网络不可达，标注「本机未验证」 |
| DeepSeek / MiMo / Moonshot 真实调用 | ⚠️ 未用真实 Key 冒烟（本机网络可达 `api.deepseek.com`/`api.moonshot.cn`，但无可用 Key）；协议层已由 MockProvider + 单测覆盖请求构造/重试/解析 |
| GitHub Actions CI 真跑 | ⚠️ 未在本机验证（`act` 需要 Docker）；workflow 按官方 Action 语法编写 |
| Playwright Chromium（CI） | ⚠️ 本机使用系统 Edge（channel: `msedge`）验证通过；CI 的 Chromium 路径未实跑 |

已在本机充分验证：pytest 49 用例、Vitest 13 用例、`next build`、uvicorn 冒烟、Playwright E2E（Edge，7 个场景）、Alembic 迁移（SQLite）、ruff、mypy。

## 项目结构

```
CausalLab/
├── backend/                # FastAPI + SQLAlchemy 2 + Alembic + SQLite/PG
│   ├── app/
│   │   ├── api/            # kd / ml / dtm / ta / cross / ai / settings / data 路由
│   │   ├── models/         # 36 张表（四模块 + 跨模块事件/证据/链接 + 设置/AI 用量）
│   │   ├── schemas/        # Pydantic v2 请求/响应模型
│   │   ├── services/       # 事件/证据/链接、FSRS 适配、规则诊断、校准、演示数据
│   │   │   └── ai/         # Provider 抽象：none / mock / openai-compat(DeepSeek/MiMo/…)
│   │   ├── config.py       # 环境变量配置（CAUSALAB_* 前缀）
│   │   └── main.py         # 应用工厂（启动时自动迁移）
│   ├── alembic/            # 迁移
│   └── tests/              # pytest（49 用例）
├── frontend/               # Next.js 16 + React 19 + Tailwind v4 + Radix + Recharts + React Flow
│   ├── src/app/            # 11 个路由（概览/四模块/时间线/假设/循环/设置 + 2 个详情页）
│   ├── src/components/     # shadcn 风格 UI 组件库 + 布局壳
│   ├── src/lib/            # API 客户端（含 428 确认闸门）、hooks、i18n（zh 完整/en 预留）
│   ├── e2e/                # Playwright（Edge）7 个核心场景
│   └── tests/              # Vitest 单测
├── docker-compose.yml      # 未在本机验证
└── .github/workflows/ci.yml
```

更多设计细节见 [ARCHITECTURE.md](docs/ARCHITECTURE.md) 与 [API.md](docs/API.md)；开发进度与遗留问题见 [PROGRESS.md](docs/PROGRESS.md)。

## 许可证

MIT
