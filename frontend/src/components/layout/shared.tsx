"use client";
import * as React from "react";
import { Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useApi } from "@/lib/useApi";
import { useL, useT } from "@/lib/i18n";
import type { AIStatus } from "@/lib/types";
import { cn } from "@/lib/utils";

export function PageHeader({
  title,
  description,
  actions,
}: {
  title: string;
  description?: string;
  actions?: React.ReactNode;
}) {
  return (
    <div className="mb-6 flex flex-wrap items-start justify-between gap-3">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">{title}</h1>
        {description && <p className="mt-1 text-sm text-muted-foreground">{description}</p>}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </div>
  );
}

export function EmptyState({
  icon: Icon,
  title,
  hint,
  action,
}: {
  icon?: React.ComponentType<{ className?: string }>;
  title: string;
  hint?: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center rounded-xl border border-dashed px-6 py-14 text-center">
      {Icon && <Icon className="mb-3 h-10 w-10 text-muted-foreground/50" />}
      <p className="font-medium">{title}</p>
      {hint && <p className="mt-1 max-w-md text-sm text-muted-foreground">{hint}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

export function ErrorState({ error, onRetry }: { error: Error; onRetry?: () => void }) {
  const t = useT();
  const unreachable = error.message.includes("无法连接后端") || error.message.includes("backend API");
  return (
    <div className={`flex flex-col items-center justify-center rounded-xl border px-6 py-10 text-center ${unreachable ? "border-warning/40 bg-warning/5" : "border-destructive/30 bg-destructive/5"}`}>
      <p className={`whitespace-pre-line font-medium ${unreachable ? "text-warning" : "text-destructive"}`}>
        {error.message || t("state.error")}
      </p>
      {onRetry && (
        <Button variant="outline" size="sm" className="mt-3" onClick={onRetry}>
          {t("重试")}
        </Button>
      )}
    </div>
  );
}

export function LoadingBlock({ rows = 3 }: { rows?: number }) {
  return (
    <div className="space-y-3">
      {Array.from({ length: rows }).map((_, i) => (
        <Skeleton key={i} className="h-16 w-full" />
      ))}
    </div>
  );
}

/** 统计卡片 */
export function StatCard({
  label,
  value,
  hint,
  tone = "default",
  icon: Icon,
}: {
  label: string;
  value: React.ReactNode;
  hint?: string;
  tone?: "default" | "warning" | "success" | "destructive";
  icon?: React.ComponentType<{ className?: string }>;
}) {
  const toneClass = {
    default: "text-foreground",
    warning: "text-warning",
    success: "text-success",
    destructive: "text-destructive",
  }[tone];
  return (
    <Card>
      <CardContent className="p-5">
        <div className="flex items-center justify-between">
          <p className="text-sm text-muted-foreground">{label}</p>
          {Icon && <Icon className="h-4 w-4 text-muted-foreground/70" />}
        </div>
        <p className={cn("mt-1.5 text-2xl font-bold tabular-nums", toneClass)}>{value}</p>
        {hint && <p className="mt-1 text-xs text-muted-foreground">{hint}</p>}
      </CardContent>
    </Card>
  );
}

/** 确认对话框（重要操作） */
export function ConfirmDialog({
  open,
  onOpenChange,
  title,
  description,
  confirmText,
  destructive = false,
  onConfirm,
}: {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  title: string;
  description?: string;
  confirmText?: string;
  destructive?: boolean;
  onConfirm: () => Promise<void> | void;
}) {
  const t = useT();
  const ctext = confirmText ?? t("action.confirm");
  const [busy, setBusy] = React.useState(false);
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          {description && <DialogDescription>{description}</DialogDescription>}
        </DialogHeader>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            {t("action.cancel")}
          </Button>
          <Button
            variant={destructive ? "destructive" : "default"}
            disabled={busy}
            onClick={async () => {
              setBusy(true);
              try {
                await onConfirm();
                onOpenChange(false);
              } finally {
                setBusy(false);
              }
            }}
          >
            {busy && <Loader2 className="animate-spin" />}
            {ctext}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

/** AI 状态横幅：明确告知当前处于无 AI / 演示 / 云端模式。 */
export function AIBanner() {
  const { data } = useApi<AIStatus>("/settings/ai/status");
  const [dismissed, setDismissed] = React.useState(false);
  const t = useT();
  if (!data || dismissed) return null;
  const tone =
    data.provider === "none"
      ? "bg-secondary text-secondary-foreground border"
      : data.provider === "mock"
        ? "bg-warning/10 text-warning border border-warning/30"
        : "bg-primary/10 text-primary border border-primary/20";
  const message = data.provider === "none"
    ? t("当前为无 AI 模式：核心记录、统计、实验与可视化功能完整可用；诊断与复盘使用内置规则分析。")
    : data.provider === "mock"
      ? t("当前为演示模式：AI 输出为固定模拟数据，仅用于预览交互流程。")
      : data.configured
        ? t("已连接云端模型。所有请求经本服务端代理，API Key 不会返回给前端；发送前需要你确认内容。")
        : t("AI 配置不完整（缺少 Base URL、模型名或 API Key），分析将回退到规则模式。");
  return (
    <div className={cn("mb-5 flex items-start justify-between gap-3 rounded-lg px-4 py-2.5 text-sm", tone)}>
      <span>{message}</span>
      <button className="shrink-0 text-xs opacity-70 hover:opacity-100 cursor-pointer" onClick={() => setDismissed(true)}>
        {t("知道了")}
      </button>
    </div>
  );
}

/** 演示数据标识横幅 */
export function DemoBanner({ show }: { show: boolean }) {
  const t = useT();
  if (!show) return null;
  return (
    <div className="mb-5 flex items-center justify-between rounded-lg border border-warning/40 bg-warning/10 px-4 py-2.5 text-sm text-warning">
      <span>
        {t("当前展示的是")}
        <strong>{t("演示数据")}</strong>
        {t("（非真实记录），可在「设置 → 数据管理」中清除或导出。")}
      </span>
      <Badge variant="warning">Demo</Badge>
    </div>
  );
}

/** 证据徽章：事实/推测/缺失 */
export function EvidenceBadge({ kind }: { kind: string }) {
  const L = useL();
  const map: Record<string, { label: string; variant: "success" | "warning" | "destructive" | "muted" }> = {
    fact: { label: L.evidenceKind.fact, variant: "success" },
    speculation: { label: L.evidenceKind.speculation, variant: "warning" },
    missing_evidence: { label: L.evidenceKind.missing_evidence, variant: "destructive" },
    ai_analysis: { label: L.evidenceKind.ai_analysis, variant: "muted" },
    user_correction: { label: L.evidenceKind.user_correction, variant: "muted" },
    user_input: { label: L.evidenceKind.user_input, variant: "muted" },
  };
  const item = map[kind] ?? { label: kind, variant: "muted" as const };
  return <Badge variant={item.variant}>{item.label}</Badge>;
}
