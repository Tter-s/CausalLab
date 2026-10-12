# CausaLab 交接文档（HANDOFF）

> 用途：在新对话/新会话中快速恢复对 CausaLab 项目的完整上下文。读完本文件即可继续开发，细节再查 `docs/` 与 `README.md`。
> 最后更新：2026-10-11（第九次迭代后）

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
| 测试 | pytest（后端 75 用例）/ Vitest（前端 20）/ Playwright（E2E 10，复用系统 Edge） |
| 取数模式 | 前端统一相对路径 `/api/*`，由 Next rewrites 代理到 FastAPI `127.0.0.1:8000`（免 CORS） |

## 3. 目录速览

```
CausalLab/
├── 启动CausaLab.bat          # 双击启动前后端（自动清端口+等就绪+开浏览器）
├── README.md / LICENSE / docker-compose.yml
├── docs/  ARCHITECTURE.md / API.md / PROGRESS.md（设计决策 + 接口 + 进度与遗留）
├── backend/
│   ├── app/api/        # kd / ml / dtm / ta / cross(时间线等) / ai / auth / settings / data / uploads
│   ├── app/models/     # 37 张表（base=Base+utcnow；auth=会话表；attachments=题目/解答附件）
│   ├── app/services/   # events/links(事件证据链接)、uploads(附件存储)、scheduling(FSRS 适配)、
│   │   │               # kd_rules(规则诊断)、calibration、demo、crypto(Fernet)、auth(认证)
│   │   └── ai/         # Provider 抽象：none/mock/openai_compat + config(隐私闸门/预算/结构化校验)
│   ├── alembic/        # 5 个迁移（初始 schema / auth_sessions / events 索引 / recall_ms / attachments）
│   ├── scripts/smoke_no_ai.py   # 无 AI 全链路冒烟（24 项，对运行中的 8000 端口执行）
│   └── tests/          # 75 用例（含 test_uploads.py 14 个附件与清空联动用例）
└── frontend/
    ├── src/app/        # 12 路由：/ /kd /ml /dtm /dtm/[id] /ta /ta/[id] /timeline
    │                   #        /hypotheses /loops /settings /login
    ├── src/components/ # layout/(app-shell+shared) ui/(手写 shadcn 风格组件) brand-mark
    │                   # dev-tools-zh（仅 dev：汉化+拖拽 Next Dev Tools，见 §8 末条）
    ├── src/lib/        # api.ts(含428/401处理 + postForm 附件上传) useApi.ts i18n.tsx(双语)
    │                   # i18n-page-strings.ts ai-client.tsx(428确认流) format.ts types.ts
    ├── e2e/flows.spec.ts   # 10 个场景（含认证流程、附件上传、按任务模型保存）
    └── tests/          # Vitest 20（含 i18n 覆盖扫描防退化测试 + postForm multipart 测试）
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

当前基线：**pytest 75/75 · Vitest 20/20 · E2E 10/10 · 冒烟 24/24 · AI 测试连接 ✅ · ruff/mypy/eslint 全绿 · build 12 业务路由成功**。
服务默认未启动（启动方式见上）；如需重启，可先 `npx kill-port 8000 3000` 清理端口。
注意：E2E 需先关 :3000 dev server（Next 16 同项目不允许第二个 dev server）；
冒烟脚本若在已配置真实 AI 时运行，第 0/1 组各 1 项按"无 AI 前提"断言会报失败，属预期。

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
6. **i18n 约定**：`t("中文原文")` 源文键模式——zh 回退键本身，en 查 `i18n-page-strings.ts`。**Vitest 有覆盖扫描：任何 t 调用里的中文键缺英文翻译会挂测试**（新增文案直接在该文件补一条英文即可；早期文档提到的 `scripts/_i18n_strings_all.py` 生成脚本已不存在）。
7. **附件上传**：`attachments` 表按 `(module, ref_type, ref_id)` 挂到任意实体（同 evidence/links 模式）；文件本体在 `data_dir/uploads/`，磁盘名由 uuid 生成，用户文件名只存库展示。端点 `POST/GET /api/uploads`、`GET /api/uploads/{id}/content`、`DELETE /api/uploads/{id}`。前端用 `api.ts` 的 `postForm()`——它刻意清空 headers，否则 `api()` 默认的 `application/json` 会让后端无法解析 multipart。
8. **数据获取模式**：页面全用自研 `useApi` hook；`ai-client.tsx` 的 `useAICall` 处理 428→预览→确认重发。刻意整页跳转（登出/演示/清空后）有 eslint 豁免注释——不要改成软导航。
9. **AI 配置的 None 语义**：`AIConfigIn` 中 `api_key` 与 `task_models` 都是「None/省略 = 保持原值」。改后端时别写成无条件覆盖，否则任何只提交部分字段的客户端都会清空用户已存的配置。

## 7. 遗留问题现状

- ~~学习步骤细分~~ ✅（第八轮前）~~国际化~~ ✅ ~~品牌图标~~ ✅ ~~时间线游标分页~~ ✅ ~~认证~~ ✅ ~~回忆时长~~ ✅ ~~依赖传播~~ ✅ ~~死代码清理~~ ✅ ~~AI 真实冒烟~~ ✅（第九次迭代：DeepSeek 测试连接 577ms + 端到端诊断 source=ai 实测通过）~~题目/解答附件上传~~ ✅（本轮：表+迁移+端点+前端+12 个后端用例）
- **遗留清零**。另有 6 条"未在本机验证项"（Docker/PG/MiMo/Moonshot/OpenAI 官方/CI 真跑等，环境限制）
- 本轮同时修掉：CI E2E job 的 3 处错误配置、缺失的 `.dockerignore`、文档计数漂移与 API 文档漏登、缺 PostgreSQL 驱动、`alembic.ini` 中文注释导致迁移静默降级、pytest 临时目录泄漏、依赖下限偏低、`task_models` 被部分提交清空、Next 调试按钮遮挡侧边栏文案。详见 `docs/PROGRESS.md`。

## 8. 踩过的坑（避免重蹈）

- **Next 16**：`allowedDevOrigins` 必须含 127.0.0.1（否则 dev 资源被拦→hydration 失败卡骨架屏）；预渲染期禁直接 `Date.now()`；动态路由页需 Suspense 包裹；rewrites 改后要重启 dev
- **eslint-config-next 2025**：`set-state-in-effect` 新规则对取数 effect 误报（已降 warn）；`no-location-assign` 对刻意整页跳转需豁免注释
- **SQLite 并发**：中间件/长事务内不要在 `call_next` 期间持有连接；auth 中间件已按“先关会话再放行”实现
- **fsrs 官方库**：要求 UTC aware datetime；`Card.to_dict()` 存 JSON、`from_dict` 重建（见 scheduling.py 适配层）
- **Alembic**：`alembic.ini` 必须保持**纯 ASCII**——Alembic 以 `encoding="locale"`（本机 GBK）读它，任何非 ASCII 字节都会抛 `UnicodeDecodeError`，而 `app.main._run_migrations()` 会**静默回退** `Base.metadata.create_all()`，表面上应用照常可用、pytest 也照常通过，但迁移链路其实已经失效。SQLite 迁移用 `render_as_batch`。排查方法：直接调用 `app.main._run_migrations()` 并打开 INFO 日志，看是打印 "Alembic migration finished." 还是 "failed, falling back"。
- **i18n 覆盖测试会把注释也算进去**：`tests/i18n.test.ts` 用正则扫全 src 找 `t("…")`，所以**不要在注释或文档字符串里写 `t("中文…")` 这种字面示例**，否则会被判成"缺翻译的键"。写说明时把引号去掉（如 `t 调用中的中文键`）。
- **部分提交的配置不要无条件覆盖**：`AIConfigIn` 里 `api_key` / `task_models` 都是「None = 保持原值」。历史上前端 `save()` 没带 `task_models`，后端又无条件覆盖，导致**每次在界面保存 AI 设置都会清空按任务模型的覆盖**。新增可选字段时请沿用 None 语义。
- **Windows 上 pytest 的临时目录**：`conftest.py` 的 `pytest_sessionfinish` 必须**先 `engine.dispose()`** 再 `rmtree`，否则 SQLite 句柄未释放会导致删除失败，而 `ignore_errors=True` 会吞掉失败——症状是临时目录里持续累积只剩一个 `causalab.db` 的 `causalab_test_*` 目录。
- **测试隔离**：pytest 共享一个临时库（conftest 设 `CAUSALAB_DATA_DIR`）；写测试注意跨用例状态污染（AI 配置、限流器、会话 cookie 都有前车之鉴）；E2E beforeEach 会先关认证+清业务数据
- **run_structured 提示词必须带 JSON Schema**（第九次迭代修的真 Bug）：只写"符合字段结构"而不给 schema，Mock 测不出、真实模型必然校验失败回退规则；schema 以 `model_json_schema()` 附在系统提示词
- **Next 16 同项目只允许一个 dev server**：:3000 在跑时 E2E（:3100）直接启动失败；跑 E2E 前先关 :3000
- **AI 配置填错的表现**：base_url 误填 `/anthropic`（Anthropic 协议端点）或 model_id 误填 `deepseek`（合法名是 deepseek-chat/deepseek-reasoner）都会"测试连接"失败；错误详情被包装，诊断可直连 API 看状态码
- **Next Dev Tools（nextjs-portal）**：open shadow DOM；菜单开关绑定在 click（非 pointerdown）；N 按钮容器是 `.nextjs-toast`（fixed），菜单卡片 `[role="menu"]` 自身就是 fixed 元素（不在其祖先链上）；dev-tools-zh.tsx 基于这些结构做汉化+拖拽，Next 大版本升级若失效会静默退化为无增强（不影响应用）

## 9. 给新对话的建议开场

1. 先看 `docs/ARCHITECTURE.md`（设计决策）与 `README.md`（功能、用法、目录结构）。
2. 改后端 → 跑 pytest+ruff+mypy；改前端 → tsc+eslint+vitest+build；涉及流程 → 跑 E2E。
3. 新增 i18n 文案记得登记词条（§6.6），否则 Vitest 覆盖测试会失败——这是故意的防退化设计。
4. 提交信息用中文、一次迭代一个 commit（历史示例见 `git log`）。
