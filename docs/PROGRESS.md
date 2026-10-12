# CausaLab 开发进度与未解决问题

> 最后更新：2026-10-12
> 本文件是任务书 §九 要求的「开发进度与未解决问题清单」。
> **本文件中的所有数字均为本机实测结果**；任何无法在本机验证的项都逐条标注「未在本机验证」，绝不写成"通过"（任务书 §11.6）。

---

## 1. 当前基线（全部为实测值）

| 项目 | 结果 | 实测方式 |
|---|---|---|
| 后端单元/集成测试 | **75 passed** | `cd backend && uv run pytest -q` |
| 前端单元测试 | **20 passed** | `cd frontend && npx vitest run` |
| E2E（Playwright + 系统 Edge） | **10 passed** | `cd frontend && npx playwright test` |
| 无 AI 全链路冒烟 | **24 通过 / 0 失败** | `cd backend && uv run python scripts/smoke_no_ai.py` |
| ruff | All checks passed | `uv run ruff check app tests` |
| mypy | no issues（49 个源文件） | `uv run mypy app` |
| tsc | 无错误 | `npx tsc --noEmit` |
| eslint | **0 error**（11 warning，均为已声明的 `set-state-in-effect`） | `npx eslint .` |
| next build | 成功，**12 条业务路由** | `npm run build` |
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

**已在本机充分验证**：pytest 75、Vitest 20、`next build`、uvicorn 冒烟、Playwright E2E（Edge，10 场景）、Alembic 迁移（SQLite）、ruff、mypy、tsc、eslint、无 AI 全链路冒烟 24/24、附件上传端到端（经 Next 代理的真实链路 + 浏览器内真实文件选择与删除）。

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

---

## 6. 下一步建议

1. **在具备 Docker 的机器上真跑一次** `docker compose up --build`，验证 Dockerfile 与 `.dockerignore`（本机永远做不到）。
2. **在具备 PostgreSQL 的机器上**验证 `CAUSALAB_DB_URL=postgresql+psycopg://...` 的建表与迁移兼容性。
3. **让 CI 真跑一次**（当前仅本地校验过语法与配置项名称）。
4. 若要暴露到公网：启用密码保护，并考虑在反向代理层再加一道登录限流（进程内限流重启即清零）。
5. 附件上传目前仅接在 KD 知识点上；由于表结构是通用的 `(module, ref_type, ref_id)`，可按需扩展到 ML 卡片、DTM 决策、TA 任务等。
