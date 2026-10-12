/** 后端 API 类型定义（与 FastAPI Pydantic Schema 对应，时间一律 ISO 字符串，UTC 以 Z 结尾）。 */

export type ModuleId = "kd" | "ml" | "dtm" | "ta" | "hyp" | "loop" | "sys";

export interface EventItem {
  id: number;
  module: ModuleId;
  event_type: string;
  ref_type: string;
  ref_id: number;
  title: string;
  detail: Record<string, unknown>;
  importance: number;
  occurred_at: string | null;
}

export interface EventPage {
  items: EventItem[];
  total: number;
  /** 游标分页：以最后一行的 (occurred_at, id) 为下一页起点 */
  has_more: boolean;
  next_before_at: string | null;
  next_before_id: number | null;
}

// ---------- KD ----------
export interface Subject {
  id: number;
  name: string;
  description: string;
  color: string;
  created_at: string;
  updated_at: string;
}

export interface Topic {
  id: number;
  subject_id: number;
  name: string;
  description: string;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface TopicEdge {
  id: number;
  from_topic_id: number;
  to_topic_id: number;
  relation: string;
  note: string;
}

export interface StudyTask {
  id: number;
  topic_id: number;
  title: string;
  question_text: string;
  my_answer: string;
  status: string;
  is_verification: boolean;
  source_suggestion_id: number | null;
  verification_status: string | null;
  created_at: string;
}

export interface Attempt {
  id: number;
  task_id: number;
  topic_id: number;
  correct: boolean;
  error_category: string;
  independent: boolean;
  duration_minutes: number | null;
  notes: string;
  occurred_at: string | null;
  created_at: string;
}

export interface Diagnosis {
  id: number;
  topic_id: number;
  category: string;
  confidence: number;
  rationale: string;
  evidence_attempts: number[];
  alternatives: { category: string; likelihood: string; reason: string }[];
  basis_attempt_count: number;
  source: string;
  status: string;
  corrected_category: string | null;
  correction_note: string | null;
  created_at: string;
  updated_at: string;
}

export interface Suggestion {
  id: number;
  diagnosis_id: number;
  content: string;
  verification_task_id: number | null;
  status: string;
  effectiveness_note: string;
  created_at: string;
}

// ---------- ML ----------
export interface Deck {
  id: number;
  name: string;
  description: string;
  created_at: string;
}

export interface CardItem {
  id: number;
  deck_id: number;
  front: string;
  back: string;
  tags: string[];
  suspended: boolean;
  created_at: string;
  state?: ReviewState | null;
}

export interface ReviewState {
  card_id: number;
  stability: number;
  difficulty: number;
  due_at: string | null;
  last_review_at: string | null;
  reps: number;
  lapses: number;
  state_str: string;
  retrievability: number | null;
  /** 学习/重学步骤细分：0 起始索引（复习循环为 null） */
  step: number | null;
  /** 该状态下全部步骤时长（分钟），如 [1, 10] */
  steps_minutes: number[] | null;
}

export interface DueQueue {
  cards: CardItem[];
  total_due: number;
}

export interface ReviewResult {
  card_id: number;
  rating: number;
  due_at: string | null;
  interval_display: string;
  state: ReviewState;
}

export interface Experiment {
  id: number;
  question: string;
  strategy_a: string;
  strategy_b: string;
  metric: string;
  status: string;
  started_at: string | null;
  ends_at: string | null;
  delayed_test_days: number;
  notes: string;
  created_at: string;
}

export interface ExperimentResults {
  experiment_id: number;
  groups: {
    name: string;
    strategy: string;
    n_cards: number;
    n_reviews: number;
    again_rate: number | null;
    mean_duration_ms: number | null;
    median_recall_ms: number | null;
    recall_samples: number;
    delayed_test_pass_rate: number | null;
  }[];
  difference_note: string | null;
  disclaimer: string;
}

export interface MLStats {
  total_cards: number;
  due_now: number;
  reviews_last_7d: number;
  retention_7d: number | null;
  again_rate_7d: number | null;
  reviews_per_day: { date: string; count: number }[];
  interval_distribution: { label: string; count: number }[];
  maturity: Record<string, number>;
  /** 学习/重学步骤细分：处于某步骤的卡片数 */
  step_breakdown: { state: string; step: number; minutes: number; count: number }[];
}

// ---------- DTM ----------
export interface DecisionOption {
  key: string;
  label: string;
  description?: string;
}

export interface Decision {
  id: number;
  title: string;
  context: string;
  goals: string;
  options: DecisionOption[];
  basis: string;
  risks: string;
  status: "open" | "reviewed" | "archived";
  review_at: string | null;
  reviewed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface DecisionDetail extends Decision {
  predictions: Prediction[];
  updates: DecisionUpdateItem[];
  reviews: DecisionReviewItem[];
  counterfactuals: Counterfactual[];
  snapshots: Snapshot[];
}

export interface Prediction {
  id: number;
  decision_id: number;
  statement: string;
  option_key: string | null;
  probability: number;
  resolved: boolean | null;
  actual_note: string | null;
  resolved_at: string | null;
  created_at: string;
}

export interface DecisionUpdateItem {
  id: number;
  decision_id: number;
  content: string;
  source: string;
  significance: "minor" | "major";
  occurred_at: string;
  created_at: string;
}

export interface DecisionReviewItem {
  id: number;
  decision_id: number;
  summary: string;
  process_score: number | null;
  lessons: string[];
  bias_flags: string[];
  source: string;
  reviewed_at: string;
}

export interface Counterfactual {
  id: number;
  decision_id: number;
  scenario: string;
  analysis: string;
  is_hypothetical: boolean;
  source: string;
  created_at: string;
}

export interface Snapshot {
  id: number;
  decision_id: number;
  reason: string;
  payload: Record<string, unknown>;
  snapshot_at: string;
}

export interface Calibration {
  n_predictions: number;
  brier_score: number;
  bins: { label: string; lower: number; upper: number; n: number; avg_predicted: number; actual_rate: number }[];
  caveat: string;
}

// ---------- TA ----------
export interface Project {
  id: number;
  name: string;
  description: string;
  status: string;
  started_at: string | null;
  deadline: string | null;
  created_at: string;
  updated_at: string;
}

export interface TaskItem {
  id: number;
  project_id: number;
  parent_id: number | null;
  title: string;
  description: string;
  status: "todo" | "doing" | "blocked" | "done" | "cancelled";
  estimated_hours: number | null;
  actual_hours: number | null;
  started_at: string | null;
  finished_at: string | null;
  due_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface TaskEventItem {
  id: number;
  task_id: number;
  type: string;
  description: string;
  duration_minutes: number | null;
  occurred_at: string;
  created_at: string;
}

export interface ProjectStats {
  project_id: number;
  tasks_total: number;
  tasks_done: number;
  tasks_blocked: number;
  tasks_cancelled: number;
  total_estimated_hours: number;
  total_actual_hours: number;
  avg_overrun_ratio: number | null;
  blocked_minutes_total: number;
  rework_count: number;
  interrupted_count: number;
  requirement_change_count: number;
  per_task: {
    task_id: number;
    title: string;
    status: string;
    estimated_hours: number | null;
    actual_hours: number | null;
    overrun_ratio: number | null;
    blocked_minutes: number;
    rework_count: number;
  }[];
  event_type_counts: Record<string, number>;
}

export interface ProjectReviewItem {
  id: number;
  project_id: number;
  summary: string;
  facts: string[];
  speculations: string[];
  missing_evidence: string[];
  improvements: string[];
  source: string;
  created_at: string;
}

export interface Improvement {
  id: number;
  project_id: number | null;
  review_id: number | null;
  action: string;
  status: string;
  followup_note: string;
  effect: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

// ---------- 跨模块 ----------
export interface Hypothesis {
  id: number;
  statement: string;
  rationale: string;
  design: Record<string, unknown> | null;
  criteria: Record<string, unknown> | null;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface Observation {
  id: number;
  hypothesis_id: number;
  observed_at: string;
  value: number;
  context: Record<string, unknown>;
  note: string;
  source: string;
}

export interface HypothesisAnalysis {
  hypothesis_id: number;
  n_observations: number;
  overall_mean: number | null;
  overall_std: number | null;
  groups: { label: string; n: number; mean: number; std: number | null }[];
  limitations: string[];
  verdict_hint: string;
}

export interface Loop {
  id: number;
  title: string;
  problem: string;
  status: string;
  current_stage: string;
  hypothesis_id: number | null;
  intervention: string;
  outcome_note: string;
  verdict: string | null;
  created_at: string;
  updated_at: string;
}

export interface LoopStageItem {
  id: number;
  loop_id: number;
  stage: string;
  content: Record<string, unknown>;
  entered_at: string;
}

export interface EntityLinkItem {
  id: number;
  from_module: ModuleId;
  from_ref_type: string;
  from_ref_id: number;
  to_module: ModuleId;
  to_ref_type: string;
  to_ref_id: number;
  relation: string;
  note: string;
  created_at: string;
}

export interface EvidenceItem {
  id: number;
  module: ModuleId;
  ref_type: string;
  ref_id: number;
  event_id: number | null;
  kind: string;
  content: string;
  source: string;
  confidence: number | null;
  created_at: string;
}

export interface SearchOut {
  query: string;
  groups: Record<string, SearchHit[]>;
  total: number;
}

export interface SearchHit {
  module: ModuleId;
  ref_type: string;
  ref_id: number;
  title: string;
  snippet: string;
}

export interface Dashboard {
  today: string;
  stats: Record<string, number>;
  due_decision_reviews: EventItem[];
  recent_events: EventItem[];
  charts: Record<string, { date: string; count: number }[]>;
  demo_mode: boolean;
}

// ---------- 认证 ----------
export interface AuthStatus {
  enabled: boolean;
  authed: boolean;
}

// ---------- 附件（题目 / 我的解答） ----------
export type AttachmentKind = "question" | "solution" | "other";

export interface Attachment {
  id: number;
  module: string;
  ref_type: string;
  ref_id: number;
  kind: AttachmentKind;
  original_name: string;
  content_type: string;
  size_bytes: number;
  note: string;
  created_at: string;
}

// ---------- 设置 / AI ----------
export interface AIConfig {
  provider: string;
  base_url: string;
  api_key_masked: string;
  model_id: string;
  temperature: number | null;
  max_tokens: number;
  timeout_seconds: number;
  monthly_budget: number;
  auto_confirm_send: boolean;
  task_models: { task_type: string; model_id: string | null; temperature: number | null }[];
  price_prompt_per_m: number;
  price_completion_per_m: number;
  configured: boolean;
}

export interface AIStatus {
  enabled: boolean;
  provider: string;
  model_id: string;
  configured: boolean;
  auto_confirm_send: boolean;
  notice: string;
}

export interface UsageSummary {
  rows: {
    id: number;
    provider: string;
    model: string;
    task_type: string;
    prompt_tokens: number;
    completion_tokens: number;
    cost_estimated: number;
    latency_ms: number;
    ok: boolean;
    error: string | null;
    created_at: string;
  }[];
  total_calls: number;
  total_prompt_tokens: number;
  total_completion_tokens: number;
  total_cost: number;
  month: string;
}

/** AI 确认闸门的 428 响应体 */
export interface AIConfirmRequiredBody {
  code: "ai_confirm_required";
  message: string;
  provider: string;
  model_id: string;
  payload_preview: string;
}
