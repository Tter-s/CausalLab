# CausaLab API 文档

运行中的完整交互式文档：后端 `http://127.0.0.1:8000/docs`（Swagger UI，由 FastAPI 自动生成，90+ 端点）。

本文档列出核心端点与语义约定。所有路径前缀 `/api`；请求/响应均为 JSON；时间字段为 ISO 8601（UTC，`Z` 后缀）。

## 约定

- 错误体：`{"detail": <字符串 或 {code, message, ...>}`
- AI 专属错误码：
  - `428 ai_confirm_required` — 隐私闸门：响应含 `payload_preview`（将要发送的内容），前端确认后带 `confirm_send=true` 重试
  - `409 ai_not_configured` — AI 未配置
  - `402 ai_budget_exceeded` — 月度预算用尽
  - `502 ai_upstream_error / ai_response_invalid` — 云端失败/输出不合法（诊断类端点会自动回退规则分析）

## 元信息

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/health` | 健康检查 |
| GET | `/api/dashboard` | 仪表盘：统计、待复盘、最近事件、14 天活动图、demo 标识 |
| GET | `/api/search?q=` | 全局搜索（跨 9 类实体 + 事件） |

## Knowledge Debt（知识债务）

| 方法 | 路径 | 说明 |
|---|---|---|
| GET/POST | `/kd/subjects` | 学科列表/创建 |
| DELETE | `/kd/subjects/{id}` | 删除学科（级联） |
| GET/POST | `/kd/topics` | 知识点（可按 subject_id 过滤） |
| PATCH/DELETE | `/kd/topics/{id}` | 更新（如标记 weak）/删除 |
| GET | `/kd/graph?subject_id=` | 图谱：nodes + edges + subjects |
| POST/DELETE | `/kd/edges` | 依赖关系（拒绝自依赖） |
| GET/POST | `/kd/tasks` | 学习任务（可按 topic_id/status 过滤） |
| PATCH/DELETE | `/kd/tasks/{id}` | 更新/删除 |
| POST | `/kd/tasks/{id}/attempts` | **记录答题**：`{correct, error_category, independent, notes, occurred_at?}` |
| GET | `/kd/topics/{id}/attempts` | 该知识点全部答题记录 |
| POST | `/kd/topics/{id}/diagnose` | **规则诊断**（保守：样本不足 → insufficient_data） |
| GET | `/kd/diagnoses?topic_id=` | 诊断列表 |
| PATCH | `/kd/diagnoses/{id}` | **用户纠正**：`{corrected_category, correction_note}` → status=user_confirmed + 证据 |
| GET/POST | `/kd/suggestions` | 学习建议 |
| POST | `/kd/suggestions/{id}/verification-task` | 为建议生成验证任务（is_verification=true） |
| POST | `/kd/suggestions/{id}/verification-result` | **提交验证结论** `{success, note}` → effective/ineffective |

## Memory Laboratory（记忆实验室）

| 方法 | 路径 | 说明 |
|---|---|---|
| GET/POST | `/ml/decks` | 卡组 |
| GET/POST | `/ml/cards` | 卡片（创建即入复习队列） |
| PATCH/DELETE | `/ml/cards/{id}` | 更新（可 suspend）/删除 |
| GET | `/ml/due?limit=&deck_id=` | 到期队列（含 FSRS 状态与可提取性） |
| GET | `/ml/cards/{id}/preview` | 四种评分的间隔预览（复习按钮文案） |
| POST | `/ml/reviews` | **提交复习** `{card_id, rating(1-4), duration_ms}` → 新状态 + 间隔文案；若卡片在实验组自动记录 group_tag |
| GET | `/ml/cards/{id}/logs` | 复习日志 |
| GET | `/ml/stats` | 统计：每日复习数、间隔分布、成熟度、7 天回忆率/遗忘率 |
| GET | `/ml/forgetting-curve?days=` | 未来 N 天到期数（复习负担预测） |
| GET/POST | `/ml/experiments` | 对照实验 |
| PATCH | `/ml/experiments/{id}` | 状态流转（running 时自动记 started_at/ends_at） |
| POST | `/ml/experiments/{id}/assign` | **随机分组** `{card_ids: [...]}`（服务端 shuffle 均分 A/B） |
| GET | `/ml/experiments/{id}/results` | 分组结果 + 差异说明 + **免责声明** |
| POST | `/ml/experiments/{id}/link-diagnosis/{diagnosis_id}` | 与 KD 诊断建立跨模块链接 |

## Decision Time Machine（决策时间机）

| 方法 | 路径 | 说明 |
|---|---|---|
| GET/POST | `/dtm/decisions` | 列表/创建（创建即生成第一个**不可覆盖快照**） |
| GET | `/dtm/decisions/{id}` | 详情聚合：predictions/updates/reviews/counterfactuals/snapshots |
| PATCH | `/dtm/decisions/{id}` | 修改（**追加新快照**，旧快照不变） |
| DELETE | `/dtm/decisions/{id}` | 删除 |
| GET | `/dtm/decisions/{id}/snapshots` | 快照历史（只读） |
| POST | `/dtm/decisions/{id}/predictions` | 添加概率预测 `{statement, probability(0-1), option_key?}` |
| PATCH | `/dtm/predictions/{id}` | **揭晓** `{resolved, actual_note}` |
| POST | `/dtm/decisions/{id}/updates` | 新信息 `{content, source, significance}` |
| POST | `/dtm/decisions/{id}/reviews` | 手动复盘 `{summary, process_score(1-5), lessons, bias_flags}`（过程质量 ≠ 结果好坏） |
| GET | `/dtm/due-reviews` | 已到复盘时间未复盘的决策 |
| GET | `/dtm/calibration` | 校准：Brier 分数 + 5 桶对比 + 免责说明 |
| POST | `/dtm/decisions/{id}/counterfactuals` | 反事实（`is_hypothetical` 恒 True） |

## Task Autopsy（任务复盘）

| 方法 | 路径 | 说明 |
|---|---|---|
| GET/POST | `/ta/projects` | 项目 |
| GET/POST | `/ta/projects/{id}/tasks` | 任务（支持 parent_id 子任务、depends_on 依赖） |
| PATCH | `/ta/tasks/{id}` | 状态流转（done 自动算 actual_hours；blocked/resumed 事件联动） |
| POST | `/ta/tasks/{id}/events` | **过程事件**：blocked/resumed/rework/interrupted/requirement_change/note（含时长） |
| GET | `/ta/projects/{id}/stats` | 统计：预估 vs 实际、平均超支比、阻塞分钟、返工/中断/需求变化计数、逐任务明细 |
| POST | `/ta/projects/{id}/rule-review` | **规则复盘**（无需 AI）：严格分区 事实/推测/缺失证据/改进建议 |
| GET/POST | `/ta/projects/{id}/reviews` | 复盘报告列表/手动报告 |
| GET/POST/PATCH | `/ta/improvements` | 改进措施追踪（proposed→trying→adopted/discarded + effect） |

## 跨模块（时间线 / 证据 / 链接 / 假设 / 循环）

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/timeline?module=&q=&days=&limit=&offset=` | 统一事件流（分页） |
| GET | `/timeline/entity?module=&ref_type=&ref_id=` | 实体的全部事件 |
| GET/POST | `/evidence?module=&ref_type=&ref_id=` | 证据（kind: fact/speculation/missing_evidence/…） |
| GET/POST | `/links?module=&ref_type=&ref_id=` | 跨模块实体链接 |
| GET/POST/PATCH | `/hypotheses` | 假设实验室（statement/design/criteria/status） |
| GET/POST | `/hypotheses/{id}/observations` | 观察值（含分组上下文 context） |
| GET | `/hypotheses/{id}/analysis?group_key=` | 分组对比统计 + **固定局限性说明**（相关≠因果） |
| GET/POST/PATCH | `/loops` | 改进循环 |
| GET/POST | `/loops/{id}/stages` | 阶段推进（observe→hypothesize→intervene→measure→review→adjust） |
| PATCH | `/loops/{id}` | 关闭（verdict: effective/ineffective/uncertain） |

## 设置 / AI / 数据管理

| 方法 | 路径 | 说明 |
|---|---|---|
| GET/PUT | `/settings/ai` | AI 配置（Key 只回传掩码 `sk-x****xxxx`；PUT 不传 Key 保持原值） |
| GET | `/settings/ai/status` | 模式提示（无 AI / 演示 / 云端） |
| POST | `/settings/ai/test` | 连通性测试（不发送私人资料） |
| GET | `/settings/ai/usage?month=` | 用量明细与合计 |
| GET | `/settings/budget` | 预算余量 |
| GET | `/data/export` | 全量 JSON 导出 |
| POST | `/data/import` | 全量替换导入（校验 app 标识；settings 保留本地） |
| GET | `/data/export/kd-attempts.csv`、`/data/export/ml-reviews.csv` | CSV 导出 |
| POST | `/data/demo` | 载入演示数据（先清空业务数据；界面显示 Demo 标识） |
| DELETE | `/data/all` | 清空业务数据（保留设置） |

## AI 分析端点（均支持 `confirm_send` 隐私闸门；provider=none 时 409）

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/ai/kd/diagnose?topic_id=&confirm_send=` | AI 诊断（结构化校验、引用校验、失败回退规则） |
| POST | `/ai/kd/diagnoses/{id}/suggestions` | AI 学习建议 + 验证任务 |
| POST | `/ai/kd/diagnoses/{id}/spawn-experiment?question=&strategy_a=&strategy_b=` | **一键派生记忆实验**（跨模块联动） |
| POST | `/ai/ta/projects/{id}/review` | AI 项目复盘（事实/推测/缺失证据） |
| POST | `/ai/dtm/decisions/{id}/review` | AI 决策复盘（过程质量分） |
| POST | `/ai/dtm/decisions/{id}/counterfactual?scenario=` | AI 反事实推演（恒为假设） |
| POST | `/ai/hypotheses/{id}/design` | AI 帮设计记录实验 |
| POST | `/ai/loops/{id}/review` | AI 循环复盘（证据不足必须 uncertain） |
