"use client";
/**
 * 国际化接口：中文为默认完整语言；英文覆盖导航与常用操作，作为未来国际化的预留接口。
 * 用法：const t = useT();  t("nav.dashboard")
 */
import { createContext, useCallback, useContext, useEffect, useState } from "react";

export type Locale = "zh" | "en";

export const zh: Record<string, string> = {
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
  "login.hint": "本地单用户模式，无需登录",
};

export const en: Record<string, string> = {
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
  "login.hint": "Local single-user mode, no login required",
};

const dicts: Record<Locale, Record<string, string>> = { zh, en };

interface I18nContextValue {
  locale: Locale;
  setLocale: (l: Locale) => void;
  t: (key: string) => string;
}

const I18nContext = createContext<I18nContextValue | null>(null);

export function I18nProvider({ children }: { children: React.ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>("zh");

  useEffect(() => {
    const saved = window.localStorage.getItem("causalab.locale") as Locale | null;
    if (saved === "en" || saved === "zh") setLocaleState(saved);
  }, []);

  const setLocale = useCallback((l: Locale) => {
    setLocaleState(l);
    window.localStorage.setItem("causalab.locale", l);
  }, []);

  const t = useCallback((key: string) => dicts[locale][key] ?? dicts.zh[key] ?? key, [locale]);

  return <I18nContext.Provider value={{ locale, setLocale, t }}>{children}</I18nContext.Provider>;
}

export function useT(): (key: string) => string {
  const ctx = useContext(I18nContext);
  return ctx ? ctx.t : (key) => dicts.zh[key] ?? key;
}

/** 通用领域词典（模块内文案），保证 zh 完整。 */
export const L = {
  kdErrorCategory: {
    none: "未标注",
    concept_gap: "概念不理解",
    retrieval_failure: "知识提取失败",
    method_selection: "方法选择困难",
    execution_error: "推理执行困难",
    transfer_failure: "知识迁移困难",
    other: "其他",
    insufficient_data: "样本不足",
  } as Record<string, string>,
  kdDiagCategory: {
    concept_gap: "概念不理解",
    retrieval_failure: "知识提取失败",
    method_selection: "方法选择困难",
    execution_error: "推理执行困难",
    transfer_failure: "知识迁移困难",
    other: "其他",
    insufficient_data: "样本不足，暂不下结论",
  } as Record<string, string>,
  module: {
    kd: "知识债务",
    ml: "记忆实验室",
    dtm: "决策时间机",
    ta: "任务复盘",
    hyp: "假设实验室",
    loop: "改进循环",
    sys: "系统",
  } as Record<string, string>,
  taskStatus: {
    todo: "待开始",
    doing: "进行中",
    blocked: "已阻塞",
    done: "已完成",
    cancelled: "已取消",
  } as Record<string, string>,
  taEventType: {
    blocked: "阻塞",
    resumed: "恢复",
    rework: "返工",
    interrupted: "中断",
    requirement_change: "需求变化",
    note: "备注",
    status_change: "状态变更",
  } as Record<string, string>,
  loopStage: {
    observe: "发现问题",
    hypothesize: "提出假设",
    intervene: "设计干预",
    measure: "执行与收集数据",
    review: "复盘",
    adjust: "修改策略",
  } as Record<string, string>,
  evidenceKind: {
    fact: "事实",
    speculation: "推测",
    missing_evidence: "缺失证据",
    ai_analysis: "AI 分析",
    user_correction: "用户纠正",
    user_input: "用户输入",
  } as Record<string, string>,
};
