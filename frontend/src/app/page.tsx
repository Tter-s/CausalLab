"use client";
import * as React from "react";
import Link from "next/link";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip as ChartTooltip,
  XAxis,
  YAxis,
} from "recharts";
import { AlertTriangle, ArrowRight, BrainCircuit, CalendarClock, FlaskConical, GraduationCap, Layers, RefreshCcw } from "lucide-react";
import { PageHeader, StatCard, LoadingBlock, ErrorState, DemoBanner } from "@/components/layout/shared";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useApi } from "@/lib/useApi";
import type { Dashboard } from "@/lib/types";
import { useL, useT } from "@/lib/i18n";
import { fmtRelative } from "@/lib/format";
import { cn } from "@/lib/utils";

const MODULE_COLORS: Record<string, string> = {
  kd: "bg-chart-3",
  ml: "bg-chart-1",
  dtm: "bg-chart-2",
  ta: "bg-chart-4",
  hyp: "bg-chart-5",
  loop: "bg-chart-4",
  sys: "bg-muted-foreground",
};

function eventHref(module: string, refType: string, refId: number): string {
  if (module === "dtm") return `/dtm/detail?id=${refId}`;
  if (module === "kd") return `/kd?topic=${refId}`;
  if (module === "ta") return refType === "project" ? `/ta/detail?id=${refId}` : "/ta";
  if (module === "ml") return "/ml";
  if (module === "hyp") return "/hypotheses";
  if (module === "loop") return "/loops";
  return "/timeline";
}

export default function DashboardPage() {
  const { data, error, loading, refresh } = useApi<Dashboard>("/dashboard");
  const t = useT();
  const L = useL();

  const chartData = React.useMemo(() => {
    const dates = data?.charts["学习"]?.map((d) => d.date) ?? [];
    return dates.map((date) => ({
      date: date.slice(5),
      学习: data?.charts["学习"]?.find((x) => x.date === date)?.count ?? 0,
      复习: data?.charts["复习"]?.find((x) => x.date === date)?.count ?? 0,
      任务: data?.charts["任务"]?.find((x) => x.date === date)?.count ?? 0,
      决策: data?.charts["决策"]?.find((x) => x.date === date)?.count ?? 0,
    }));
  }, [data]);

  if (loading) return <LoadingBlock rows={5} />;
  if (error) return <ErrorState error={error} onRetry={refresh} />;
  if (!data) return null;

  const s = data.stats;

  return (
    <div>
      <PageHeader
        title={t("概览")}
        description={t("你的学习、决策与行动数据都在这里汇合。")}
        actions={
          <Button variant="outline" size="sm" onClick={() => void refresh()}>
            <RefreshCcw /> {t("action.refresh")}
          </Button>
        }
      />
      <DemoBanner show={data.demo_mode} />

      <div className="grid grid-cols-2 gap-4 md:grid-cols-3 xl:grid-cols-6">
        <StatCard label={t("待复盘决策")} value={s.decisions_due} tone={s.decisions_due > 0 ? "warning" : "default"} hint={t("共 {n} 个进行中", { n: s.decisions_open })} icon={CalendarClock} />
        <StatCard label={t("到期卡片")} value={s.cards_due} tone={s.cards_due > 0 ? "default" : "success"} hint={t("记忆实验室待复习")} icon={BrainCircuit} />
        <StatCard label={t("阻塞任务")} value={s.tasks_blocked} tone={s.tasks_blocked > 0 ? "destructive" : "success"} hint={t("{n} 个进行中", { n: s.tasks_doing })} icon={AlertTriangle} />
        <StatCard label={t("薄弱知识点")} value={s.topics_weak} tone={s.topics_weak > 0 ? "warning" : "success"} hint={t("知识债务标记")} icon={GraduationCap} />
        <StatCard label={t("实验中假设")} value={s.hypotheses_testing} hint={t("{n} 个改进循环进行中", { n: s.loops_active })} icon={FlaskConical} />
        <StatCard label={t("近 7 天事件")} value={s.events_7d} hint={t("全部模块活动")} icon={Layers} />
      </div>

      <div className="mt-6 grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="text-base">{t("近 14 天活动")}</CardTitle>
            <CardDescription>{t("按模块统计的事件数量")}</CardDescription>
          </CardHeader>
          <CardContent className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" className="stroke-border" vertical={false} />
                <XAxis dataKey="date" tick={{ fontSize: 11 }} className="text-muted-foreground" tickLine={false} axisLine={false} />
                <YAxis tick={{ fontSize: 11 }} className="text-muted-foreground" tickLine={false} axisLine={false} allowDecimals={false} />
                <ChartTooltip
                  contentStyle={{ background: "var(--card)", border: "1px solid var(--border)", borderRadius: 8, fontSize: 12 }}
                  cursor={{ fill: "var(--accent)", opacity: 0.4 }}
                />
                <Bar dataKey="学习" name={L.module.kd} stackId="a" fill="var(--chart-3)" radius={[0, 0, 0, 0]} />
                <Bar dataKey="复习" name={L.module.ml} stackId="a" fill="var(--chart-1)" />
                <Bar dataKey="任务" name={L.module.ta} stackId="a" fill="var(--chart-4)" />
                <Bar dataKey="决策" name={L.module.dtm} stackId="a" fill="var(--chart-2)" radius={[3, 3, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">{t("待办提醒")}</CardTitle>
            <CardDescription>{t("到期的决策复盘")}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2">
            {data.due_decision_reviews.length === 0 && (
              <p className="rounded-lg bg-muted/50 px-3 py-6 text-center text-sm text-muted-foreground">
                {t("没有待复盘的决策。")}
              </p>
            )}
            {data.due_decision_reviews.map((e) => (
              <Link
                key={e.id}
                href={`/dtm/detail?id=${e.ref_id}`}
                className="flex items-center gap-2 rounded-lg border border-warning/30 bg-warning/5 px-3 py-2 text-sm hover:bg-warning/10"
              >
                <AlertTriangle className="h-4 w-4 shrink-0 text-warning" />
                <span className="min-w-0 flex-1 truncate">{e.title.replace("决策待复盘：", t("决策待复盘："))}</span>
                <ArrowRight className="h-3.5 w-3.5 shrink-0" />
              </Link>
            ))}
          </CardContent>
        </Card>
      </div>

      <Card className="mt-6">
        <CardHeader>
          <CardTitle className="text-base">{t("最近活动")}</CardTitle>
          <CardDescription>{t("跨模块统一事件流")}</CardDescription>
        </CardHeader>
        <CardContent>
          {data.recent_events.length === 0 ? (
            <p className="py-8 text-center text-sm text-muted-foreground">{t("还没有任何记录。从上面的模块开始创建第一条数据吧。")}</p>
          ) : (
            <ul className="divide-y">
              {data.recent_events.map((e) => (
                <li key={e.id} className="flex items-center gap-3 py-2.5 text-sm">
                  <span className={cn("h-2 w-2 shrink-0 rounded-full", MODULE_COLORS[e.module] ?? "bg-muted-foreground")} />
                  <Link href={eventHref(e.module, e.ref_type, e.ref_id)} className="min-w-0 flex-1 truncate hover:underline">
                    {e.title}
                  </Link>
                  <Badge variant="muted" className="hidden shrink-0 sm:inline-flex">
                    {L.module[e.module] ?? e.module}
                  </Badge>
                  <span className="w-24 shrink-0 text-right text-xs text-muted-foreground">{fmtRelative(e.occurred_at)}</span>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
