# CausaLab 架构

## 1. 总体结构

```
浏览器（Next.js 16 App Router, 中文 UI, 深/浅主题）
   │  相对路径 /api/*（Next rewrites 反向代理，免 CORS）
   ▼
FastAPI（90+ REST 端点，Pydantic v2 校验）
   │
   ├── SQLAlchemy 2.x ── SQLite（默认）/ PostgreSQL（CAUSALAB_DB_URL，未在本机验证）
   ├── Alembic（启动时自动 upgrade head；SQLite 用 render_as_batch）
   ├── AI Provider 抽象（none / mock / openai-compat）
   └── Fernet（API Key 静态加密，密钥文件在数据目录）
```

Monorepo：`backend/`（Python 包管理用 uv）+ `frontend/`（npm）。接口契约以 FastAPI Pydantic Schema 为唯一权威，前端 `src/lib/types.ts` 与之手工对齐。

## 2. 数据模型（统一事件与证据模型是核心）

四模块各自的业务表之外，存在一组**跨模块共享表**，它们是实现联动的骨架：

```
events（事件日志）        所有模块的关键动作都写一条：module + event_type + ref_type/ref_id + title + importance
evidence（证据记录）      kind: fact | speculation | missing_evidence | ai_analysis | user_correction
entity_links（实体链接）  from(module,ref) → to(module,ref)，relation: spawned_from | validates | feedback_to | associated_with
```

产品级约束如何在模型层落实：

- **决策快照不可覆盖**：`dtm_decision_snapshots` 只在 create/update 时追加，API 层不存在修改/删除快照的端点；
- **诊断不下绝对结论**：`kd_diagnoses.alternatives` 永远非空、`insufficient_data` 类别 + 置信度上限；用户纠正写入 `user_correction` 证据；
- **反事实恒为假设**：`dtm_counterfactuals.is_hypothetical` 恒 True，UI 强制黄色标注；
- **复盘与结果解耦**：`dtm_decision_reviews.process_score` 单独评价决策过程质量；
- **实验不夸大**：ML 实验结果固定附带免责声明字符串（单人实验不能证明普适最优）。

## 3. 关键服务层

### 3.1 FSRS 适配（services/scheduling.py）

直接依赖官方 [`py-fsrs`](https://github.com/open-spaced-repetition/py-fsrs)（MIT）v6，不做自研算法：
- 数据库只存 `Card.to_dict()` JSON（`ml_review_states.fsrs_card`），适配层负责重建对象；
- 关闭 fuzzing 保证调度可复现、可测试；
- `summary_from()` 提取 due/stability/difficulty/retrievability 供 API 输出；
- 间隔文案（分钟→小时→天→月→年）由 `format_interval` 统一。

### 3.2 规则诊断引擎（services/kd_rules.py）

无 AI 时的默认诊断路径，也是 AI 失败的回退路径：
- 输入为答题事实（correct / error_category / independent）；
- **护栏**：答题 < 3 条或失败 < 2 次 → 输出 `insufficient_data` 且置信度 ≤ 0.25；
- 置信度 = f(失败数, 类别一致性)，封顶 0.85；「辅助下正确、独立时失败」的模式会提升"迁移困难"作为备选解释；
- 备选解释永远 ≥ 1 条。

### 3.3 AI Provider 抽象（services/ai/）

```
AIProvider(ABC) ── complete(AIRequest) -> AIResponse
   ├── OpenAICompatProvider   # DeepSeek/MiMo/Moonshot/任意兼容：httpx 异步，3 次指数退避重试，
   │                          # 超时/429/5xx 重试，Key 仅在服务端；URL 启发式拼接（/v1/chat/completions）
   ├── MockProvider           # 确定性结构化输出：自动化测试 + 无 Key 演示（绝不打真实 API）
   └── (provider="none")      # AINotConfigured → 前端明确提示规则分析可用

run_structured():  统一管道 = 隐私确认(428) → 预算检查(402) → 调用 → 用量/费用记录
                   → JSON 剥壳 → Pydantic 校验 → 失败一次修复重试 → 仍失败 AIResponseInvalid
```

- **隐私闸门**：`confirm_send=False` 且未开启自动确认时抛 `AIConfirmRequired`（携带 payload 预览），映射为 HTTP 428，前端弹「发送内容预览」确认框；
- **预算**：`ai_usage_logs` 按月累计估算费用（可配单价），超限 HTTP 402；mock 不计费；
- **失败回退**：诊断类端点捕获瞬时错误（上游不可达/输出不合法）后回退规则引擎；配置类错误（未配置/超预算）则明确返回给用户；
- **写库边界**：AI 输出校验后由**服务层函数**创建实体，AI 永不直接操作数据库。

## 4. 前端架构

- **App Router + 全 client 页面**：11 个路由；数据获取用自研 SWR 风格 `useApi` hook（不引入 React Query，保持轻量）；
- **API 客户端**（lib/api.ts）：统一错误结构；428 响应转成 `AIConfirmRequiredError`，`useAICall` hook 自动处理「预览 → 确认 → 重发」流程；
- **UI 组件库**：shadcn 风格手写（Tailwind v4 + Radix primitives + CVA），主题 token 用 OKLCH CSS 变量，深/浅色由 next-themes 驱动；
- **视觉规范**：侧边栏布局、卡片化信息结构、空态/加载骨架/错误态全覆盖、重要操作二次确认、sonner 全局 toast；
- **国际化接口**：zh 字典完整、en 覆盖导航与通用操作（任务书要求"预留接口"），`useT()` + localStorage；
- **Next 16 适配**：动态路由页用 Suspense 边界（PPR 流式渲染）；`allowedDevOrigins` 允许 127.0.0.1 访问 dev 资源；预渲染期间禁止直接读时钟（计时状态在 effect 中初始化）。

## 4.5 可选认证层（services/auth.py）

个人本机默认无需登录；设置页启用后，FastAPI 中间件对 `/api/*` 做会话检查（公开端点白名单在 `AUTH_PUBLIC_PATHS`）：
- 密码 bcrypt 哈希存于 settings 表（key=auth_config）；会话令牌随机 32 字节，库存 SHA-256，TTL 30 天，登录时顺带清理过期行；
- 中间件**先关闭自身 DB 会话再放行路由**，避免与路由写事务争 SQLite 锁；
- 登录限流为进程内存实现（10 次/分/IP），重启即清零——公网部署建议再加反向代理级限流；
- 前端 `api.ts` 对 401/auth_required 统一跳转 `/login`（登录页独立布局，AppShell 对 /login 不渲染侧边栏）。

## 5. 测试策略

| 层 | 工具 | 覆盖重点 |
|---|---|---|
| 后端单元 | pytest | FSRS 调度数学性质、规则诊断护栏（一次失败不下结论）、Fernet 往返、校准分桶 |
| 后端集成 | pytest + TestClient | 四模块全流程、AI 闸门 428/预算 402/回退、导入导出往返、跨模块链接 |
| 前端单元 | Vitest | 格式化工具（UTC↔本地）、API 客户端错误映射、i18n 字典一致性 |
| E2E | Playwright（系统 Edge，channel=msedge） | 真实 UI 黑盒：仪表盘、决策全流程、任务阻塞、复习调度、诊断护栏在 UI 层的呈现、时间线、设置 |

E2E 使用独立数据目录（`backend/data-e2e`），`beforeEach` 清空业务数据保证幂等；webServer 自动拉起前后端。

## 6. 技术选型偏差说明

- **shadcn/ui 采用"手写等效组件"**而非 CLI 生成：组件代码结构与 shadcn 一致（Radix + CVA + tailwind-merge），避免交互式 CLI 在自动化环境的脆弱性，且便于随 Tailwind v4 token 定制；
- **FSRS 用官方库**而非复刻算法：正确性与可维护性优先；
- **无 AI 优先**：所有分析端点都有规则实现，AI 是增强而非依赖（任务书硬要求）；
- **不引入 React Query/Zustand**：需求规模下自研 60 行 hooks 足够，降低依赖面。
