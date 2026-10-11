"use client";
/**
 * 国际化：中文为默认与回退语言；英文覆盖全部界面文案。
 * - 键式键（nav.dashboard）：导航与通用操作
 * - 源文键（"中文原文"）：页面文案，en 词典提供翻译，zh 回退到键本身
 * - t(key, params) 支持 {name} 插值
 * 用法：const t = useT();  t("知识债务") / t("nav.dashboard") / t("共 {n} 个", { n: 5 })
 */
import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { enPageStrings } from "./i18n-page-strings";
import { setDateLocale } from "./format";

export type Locale = "zh" | "en";

const zh: Record<string, string> = {
  "app.name": "CausaLab",
  "app.tagline": "个人学习、决策与行动实验室",
  "nav.dashboard": "概览",
  "nav.kd": "知识债务",
  "nav.ml": "记忆实验室",
  "nav.dtm": "决策时间机",
  "nav.ta": "任务复盘",
  "nav.timeline": "证据时间线",
  "nav.hypotheses": "假设实验室",
  "nav.loops": "改进循环",
  "nav.settings": "设置",
  "action.create": "新建",
  "action.save": "保存",
  "action.cancel": "取消",
  "action.delete": "删除",
  "action.edit": "编辑",
  "action.confirm": "确认",
  "action.search": "搜索",
  "action.refresh": "刷新",
  "state.loading": "加载中…",
  "state.empty": "暂无数据",
  "state.error": "出错了",
};

const en: Record<string, string> = {
  "app.name": "CausaLab",
  "app.tagline": "Personal learning, decision & action lab",
  "nav.dashboard": "Dashboard",
  "nav.kd": "Knowledge Debt",
  "nav.ml": "Memory Lab",
  "nav.dtm": "Decision Time Machine",
  "nav.ta": "Task Autopsy",
  "nav.timeline": "Evidence Timeline",
  "nav.hypotheses": "Hypothesis Lab",
  "nav.loops": "Improvement Loop",
  "nav.settings": "Settings",
  "action.create": "Create",
  "action.save": "Save",
  "action.cancel": "Cancel",
  "action.delete": "Delete",
  "action.edit": "Edit",
  "action.confirm": "Confirm",
  "action.search": "Search",
  "action.refresh": "Refresh",
  "state.loading": "Loading…",
  "state.empty": "No data yet",
  "state.error": "Something went wrong",
  // 通用
  "重试": "Retry",
  "知道了": "Got it",
  "本地单用户模式 · 数据存储在本机": "Local single-user mode · data stays on this machine",
  "菜单": "Menu",
  "全局搜索": "Global search",
  "全局搜索…": "Search everything…",
  "搜索知识点、决策、任务、卡片、事件…": "Search topics, decisions, tasks, cards, events…",
  "搜索中…": "Searching…",
  "没有匹配结果": "No matches",
  "关闭": "Close",
  "今天": "Today",
  "昨天": "Yesterday",
  "演示数据": "Demo",
  "当前展示的是": "You are viewing ",
  "（非真实记录），可在「设置 → 数据管理」中清除或导出。": " (not real records). Clear or export it in Settings → Data.",
  "切换主题": "Toggle theme",
  "语言": "Language",
};

function interpolate(template: string, params?: Record<string, string | number>): string {
  if (!params) return template;
  return template.replace(/\{(\w+)\}/g, (m, k) => (k in params ? String(params[k]) : m));
}

interface I18nContextValue {
  locale: Locale;
  setLocale: (l: Locale) => void;
  t: (key: string, params?: Record<string, string | number>) => string;
}

const I18nContext = createContext<I18nContextValue | null>(null);

export function I18nProvider({ children }: { children: React.ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>("zh");
  // 渲染期同步模块级日期语言，保证任何时点的 fmtRelative/dayLabel 都用当前语言
  setDateLocale(locale);

  useEffect(() => {
    const saved = window.localStorage.getItem("causalab.locale") as Locale | null;
    if (saved === "en" || saved === "zh") setLocaleState(saved);
  }, []);

  useEffect(() => {
    document.documentElement.lang = locale === "en" ? "en" : "zh-CN";
    setDateLocale(locale);
  }, [locale]);

  const setLocale = useCallback((l: Locale) => {
    setLocaleState(l);
    window.localStorage.setItem("causalab.locale", l);
  }, []);

  const t = useCallback(
    (key: string, params?: Record<string, string | number>) => {
      const raw = dicts[locale][key] ?? dicts.zh[key] ?? key;
      return interpolate(raw, params);
    },
    [locale],
  );

  return <I18nContext.Provider value={{ locale, setLocale, t }}>{children}</I18nContext.Provider>;
}

export function useI18n(): I18nContextValue {
  const ctx = useContext(I18nContext);
  if (!ctx) throw new Error("useI18n must be used within I18nProvider");
  return ctx;
}

export function useT(): (key: string, params?: Record<string, string | number>) => string {
  return useI18n().t;
}

// ---------------- 领域词典（状态/分类等业务标签，zh/en 双语） ----------------

export interface HypStatusInfo {
  label: string;
  variant: "default" | "success" | "warning" | "destructive" | "muted";
}

export interface DomainDict {
  module: Record<string, string>;
  kdErrorCategory: Record<string, string>;
  kdDiagCategory: Record<string, string>;
  taskStatus: Record<string, string>;
  taEventType: Record<string, string>;
  loopStage: Record<string, string>;
  evidenceKind: Record<string, string>;
  hypStatus: Record<string, HypStatusInfo>;
}

const DOMAIN_ZH: DomainDict = {
  module: {
    kd: "知识债务",
    ml: "记忆实验室",
    dtm: "决策时间机",
    ta: "任务复盘",
    hyp: "假设实验室",
    loop: "改进循环",
    sys: "系统",
  },
  kdErrorCategory: {
    none: "未标注",
    concept_gap: "概念不理解",
    retrieval_failure: "知识提取失败",
    method_selection: "方法选择困难",
    execution_error: "推理执行困难",
    transfer_failure: "知识迁移困难",
    other: "其他",
    insufficient_data: "样本不足",
  },
  kdDiagCategory: {
    concept_gap: "概念不理解",
    retrieval_failure: "知识提取失败",
    method_selection: "方法选择困难",
    execution_error: "推理执行困难",
    transfer_failure: "知识迁移困难",
    other: "其他",
    insufficient_data: "样本不足，暂不下结论",
  },
  taskStatus: {
    todo: "待开始",
    doing: "进行中",
    blocked: "已阻塞",
    done: "已完成",
    cancelled: "已取消",
  },
  taEventType: {
    blocked: "阻塞",
    resumed: "恢复",
    rework: "返工",
    interrupted: "中断",
    requirement_change: "需求变化",
    note: "备注",
    status_change: "状态变更",
    dependency_cleared: "依赖解除",
  },
  loopStage: {
    observe: "发现问题",
    hypothesize: "提出假设",
    intervene: "设计干预",
    measure: "执行与收集数据",
    review: "复盘",
    adjust: "修改策略",
  },
  evidenceKind: {
    fact: "事实",
    speculation: "推测",
    missing_evidence: "缺失证据",
    ai_analysis: "AI 分析",
    user_correction: "用户纠正",
    user_input: "用户输入",
  },
  hypStatus: {
    draft: { label: "草稿", variant: "muted" },
    testing: { label: "验证中", variant: "default" },
    supported: { label: "暂获支持", variant: "success" },
    rejected: { label: "被否定", variant: "destructive" },
    uncertain: { label: "不确定", variant: "warning" },
  },
};

const DOMAIN_EN: DomainDict = {
  module: {
    kd: "Knowledge Debt",
    ml: "Memory Lab",
    dtm: "Decision Time Machine",
    ta: "Task Autopsy",
    hyp: "Hypothesis Lab",
    loop: "Improvement Loop",
    sys: "System",
  },
  kdErrorCategory: {
    none: "Unlabeled",
    concept_gap: "Concept gap",
    retrieval_failure: "Retrieval failure",
    method_selection: "Method selection",
    execution_error: "Execution error",
    transfer_failure: "Transfer failure",
    other: "Other",
    insufficient_data: "Insufficient data",
  },
  kdDiagCategory: {
    concept_gap: "Concept gap",
    retrieval_failure: "Retrieval failure",
    method_selection: "Method selection",
    execution_error: "Execution error",
    transfer_failure: "Transfer failure",
    other: "Other",
    insufficient_data: "Insufficient data — no conclusion yet",
  },
  taskStatus: {
    todo: "To do",
    doing: "In progress",
    blocked: "Blocked",
    done: "Done",
    cancelled: "Cancelled",
  },
  taEventType: {
    blocked: "Blocked",
    resumed: "Resumed",
    rework: "Rework",
    interrupted: "Interrupted",
    requirement_change: "Requirement change",
    note: "Note",
    status_change: "Status change",
    dependency_cleared: "Dependency cleared",
  },
  loopStage: {
    observe: "Spot the problem",
    hypothesize: "Form hypothesis",
    intervene: "Design intervention",
    measure: "Run & collect data",
    review: "Review",
    adjust: "Adjust strategy",
  },
  evidenceKind: {
    fact: "Fact",
    speculation: "Speculation",
    missing_evidence: "Missing evidence",
    ai_analysis: "AI analysis",
    user_correction: "User correction",
    user_input: "User input",
  },
  hypStatus: {
    draft: { label: "Draft", variant: "muted" },
    testing: { label: "Testing", variant: "default" },
    supported: { label: "Provisionally supported", variant: "success" },
    rejected: { label: "Rejected", variant: "destructive" },
    uncertain: { label: "Uncertain", variant: "warning" },
  },
};

export function useL(): DomainDict {
  const { locale } = useI18n();
  return locale === "en" ? DOMAIN_EN : DOMAIN_ZH;
}

const dicts: Record<Locale, Record<string, string>> = {
  zh,
  en: { ...en, ...enPageStrings },
};
