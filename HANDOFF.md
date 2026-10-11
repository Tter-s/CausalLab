# CausaLab 交接文档（HANDOFF）

> 用途：在新对话/新会话中快速恢复对 CausaLab 项目的完整上下文。读完本文件即可继续开发，细节再查 `docs/` 与 `README.md`。
> 最后更新：2026-10-11（第八次迭代后）

---

## 1. 项目是什么

**CausaLab** —— 个人学习、决策与行动实验室。四个核心模块（知识债务 KD / 记忆实验室 ML / 决策时间机 DTM / 任务复盘 TA）+ 三个跨模块能力（证据时间线 / 假设实验室 / 改进循环），共享统一的事件/证据/链接模型。完全无 AI 模式是一等公民（规则诊断/规则复盘完整可用），云端 AI（DeepSeek/MiMo/Moonshot/任意 OpenAI 兼容）是可选增强。

- 仓库：`D:\code\CausalLab`（git 已初始化，main 分支，全部工作已提交）
- 定位：本地单人 Web 应用；可选密码保护（设置 → 安全，默认关闭）

## 2. 技术栈

| 层 | 技术 |
|---|---|
| 后端 | Python 3.14（锁死，见 §5）+ FastAPI + SQLAlchemy 2.1 + Alembic + SQLite（可切 PG）+ py-fsrs v6（官方库，MIT）+ bcrypt + cryptography(Fernet) |
| 前端 | Next.js 16（App Router，纯客户端取数）+ React 19 + Tailwind v4 + Radix（shadcn 风格手写组件）+ Recharts + @xyflow/react + next-themes + sonner |
| 测试 | pytest（后端 60 用例）/ Vitest（前端 19）/ Playwright（E2E 8，复用系统 Edge） |
| 取数模式 | 前端统一相对路径 `/api/*`，由 Next rewrites 代理到 FastAPI `127.0.0.1:8000`（免 CORS） |

## 3. 目录速览

```
CausalLab/
├── 启动CausaLab.bat          # 双击启动前后端（自动清端口+等就绪+开浏览器）
├── README.md / LICENSE / docker-compose.yml
├── docs/  ARCHITECTURE.md / API.md / PROGRESS.md（进度+遗留+迭代记录）
├── backend/
│   ├── app/api/        # kd / ml / dtm / ta / cross(时间线等) / ai / auth / settings / data
│   ├── app/models/     # 37 张表（base=Base+utcnow；auth=会话表）
│   ├── app/services/   # events/links(事件证据链接)、scheduling(FSRS 适配)、
│   │   │               # kd_rules(规则诊断)、calibration、demo、crypto(Fernet)、auth(认证)
│   │   └── ai/         # Provider 抽象：none/mock/openai_compat + config(隐私闸门/预算/结构化校验)
│   ├── alembic/        # 4 个迁移（初始 schema / auth_sessions / events 索引 / recall_ms）
│   ├── scripts/smoke_no_ai.py   # 无 AI 全链路冒烟（24 项，对运行中的 8000 端口执行）
│   └── tests/          # 60 用例
└── frontend/
    ├── src/app/        # 12 路由：/ /kd /ml /dtm /dtm/[id] /ta /ta/[id] /timeline
    │                   #        /hypotheses /loops /settings /login
    ├── src/components/ # layout/(app-shell+shared) ui/(手写 shadcn 风格组件) brand-mark
    ├── src/lib/        # api.ts(含428/401处理) useApi.ts i18n.tsx(双语) i18n-page-strings.ts
    │                   # ai-client.tsx(428确认流) format.ts(日期语言) types.ts
    ├── e2e/flows.spec.ts   # 8 个场景（含认证流程）
    └── tests/          # Vitest 19（含 i18n 覆盖扫描防退化测试）
```

## 4. 启动 / 测试（Windows，Git Bash）

```bash
# 服务：双击  启动CausaLab.bat  或手动：
cd backend  && uv run uvicorn app.main:app --port 8000   # 启动时自动 Alembic 迁移
cd frontend && npm run dev                                # http://localhost:3000

# 回归全套（改动后必跑）：
cd backend  && uv run pytest -q && uv run ruff check app tests && uv run mypy app
cd frontend && npx vitest run && npx tsc --noEmit && npm run build
cd frontend && npx playwright test        # E2E，自动拉起隔离前后端（msedge channel）
cd backend  && uv run python scripts/smoke_no_ai.py   # 无 AI 冒烟（需 8000 在运行）
```

当前基线：**pytest 60/60 · Vitest 19/19 · E2E 8/8 · 冒烟 24/24 · ruff/mypy/eslint 全绿 · build 12 路由成功**。
服务当前在 8000/3000 运行中；重启可用 bat 或先 `npx kill-port 8000 3000`。

## 5. 机器硬约束（务必遵守，详见原任务书第十一节）

- **Python 锁定 3.14.7**，uv 禁止下载解释器；依赖必须有 cp314 wheel（禁 passlib，bcrypt>=5）
- **无 Docker / 无 PostgreSQL 服务端**（compose 与 PG 代码已交付但标注“未在本机验证”）
- npm 已指向 npmmirror；pip/uv 走阿里云镜像；缓存都在 D 盘
- **Playwright 复用系统 Edge**（`channel: "msedge"`），绝对不要 `npx playwright install`
- 不要动：`D:\code\qenc-main`、全局 npm prefix、`D:\flutter` 等 QENC 工具链
- 命令行传中文参数会被 GBK 拆坏：中文内容写文件（如 `git commit -F`），脚本用 Write 工具写临时 .py 再执行（heredoc 会碎）
- `docs/API.md` 等文档与代码同步更新是惯例；git 提交用中文（`git commit -F <file>` 或 heredoc）

## 6. 架构核心概念（改动前必读）

1. **统一事件/证据/链接**：所有模块关键动作写 `events` 表；判断依据写 `evidence`（fact/speculation/missing_evidence/ai_analysis/user_correction）；跨模块关联走 `entity_links`。时间线/搜索/仪表盘都建在其上。
2. **DTM 快照只追加**：创建/修改决策自动生成快照，无任何修改/删除快照的端点。
3. **KD 诊断护栏**：答题 <3 或失败 <2 → 强制 `insufficient_data` 且置信度 ≤0.25；备选解释永远 ≥1；用户纠正写入 user_correction 证据。
4. **AI 永不直接写库**：`run_structured()` = 隐私确认(428)→预算(402)→调用→用量记录→JSON 剥壳→Pydantic 校验→失败重试→仍失败回退规则分析。MockProvider 用于测试与无 Key 演示。
5. **认证**：可选密码保护，默认关。启用后中间件拦 `/api/*`（白名单见 `AUTH_PUBLIC_PATHS`）；会话 HttpOnly Cookie 30 天；中间件**先关自身 DB 会话再放行**（避免 SQLite 锁冲突）。
6. **i18n 约定**：`t("中文原文")` 源文键模式——zh 回退键本身，en 查 `i18n-page-strings.ts`（新增文案先在 `scripts/_i18n_strings_all.py` 登记再重建）。**Vitest 有覆盖扫描：任何 t("中文…") 缺英文翻译会挂测试**。
7. **数据获取模式**：页面全用自研 `useApi` hook；`ai-client.tsx` 的 `useAICall` 处理 428→预览→确认重发。刻意整页跳转（登出/演示/清空后）有 eslint 豁免注释——不要改成软导航。

## 7. 遗留问题现状

- ~~学习步骤细分~~ ✅（第八轮前）~~国际化~~ ✅ ~~品牌图标~~ ✅ ~~时间线游标分页~~ ✅ ~~认证~~ ✅ ~~回忆时长~~ ✅ ~~依赖传播~~ ✅ ~~死代码清理~~ ✅
- **仅剩 1 条**：AI 真实冒烟未做（等用户提供 DeepSeek/Moonshot Key；填入设置页点“测试连接”即可，代码已就绪）
- 另有 6 条“未在本机验证项”（Docker/PG/OpenAI 官方/CI 真跑等，环境限制，见 PROGRESS 表格）

## 8. 踩过的坑（避免重蹈）

- **Next 16**：`allowedDevOrigins` 必须含 127.0.0.1（否则 dev 资源被拦→hydration 失败卡骨架屏）；预渲染期禁直接 `Date.now()`；动态路由页需 Suspense 包裹；rewrites 改后要重启 dev
- **eslint-config-next 2025**：`set-state-in-effect` 新规则对取数 effect 误报（已降 warn）；`no-location-assign` 对刻意整页跳转需豁免注释
- **SQLite 并发**：中间件/长事务内不要在 `call_next` 期间持有连接；auth 中间件已按“先关会话再放行”实现
- **fsrs 官方库**：要求 UTC aware datetime；`Card.to_dict()` 存 JSON、`from_dict` 重建（见 scheduling.py 适配层）
- **Alembic**：alembic.ini 不能写中文注释（GBK 解码崩）；SQLite 迁移用 `render_as_batch`
- **测试隔离**：pytest 共享一个临时库（conftest 设 `CAUSALAB_DATA_DIR`）；写测试注意跨用例状态污染（AI 配置、限流器、会话 cookie 都有前车之鉴）；E2E beforeEach 会先关认证+清业务数据

## 9. 给新对话的建议开场

1. 先看 `docs/PROGRESS.md`（已完成/遗留/迭代记录）与 `docs/ARCHITECTURE.md`（设计决策）。
2. 改后端 → 跑 pytest+ruff+mypy；改前端 → tsc+eslint+vitest+build；涉及流程 → 跑 E2E。
3. 新增 i18n 文案记得登记词条（§6.6），否则 Vitest 覆盖测试会失败——这是故意的防退化设计。
4. 提交信息用中文、一次迭代一个 commit（历史示例见 `git log`）。
