"use client";
/** 项目详情：任务管理、过程事件、计划-实际统计、复盘报告（规则/AI）。 */
import * as React from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { toast } from "sonner";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip as ChartTooltip,
  XAxis,
  YAxis,
} from "recharts";
import { ArrowLeft, CircleCheck, Clock, Plus, Sparkles, Zap } from "lucide-react";
import { LoadingBlock, ErrorState, AIBanner } from "@/components/layout/shared";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input, Label, Select, Textarea } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { patch, post } from "@/lib/api";
import { useApi } from "@/lib/useApi";
import { useAICall } from "@/lib/ai-client";
import { useL, useT } from "@/lib/i18n";
import { fmtDateTime, fmtHours, fmtMinutes } from "@/lib/format";
import type { ProjectReviewItem, ProjectStats, TaskEventItem, TaskItem } from "@/lib/types";

function ProjectDetailPageInner() {
  const t = useT();
  const L = useL();
  const params = useParams<{ id: string }>();
  const id = params.id;
  const project = useApi<{ id: number; name: string; description: string; status: string }>(`/ta/projects/${id}`);
  const tasks = useApi<TaskItem[]>(`/ta/projects/${id}/tasks`);
  const stats = useApi<ProjectStats>(`/ta/projects/${id}/stats`);
  const reviews = useApi<ProjectReviewItem[]>(`/ta/projects/${id}/reviews`);
  const ai = useAICall();

  const [taskOpen, setTaskOpen] = React.useState(false);
  const [taskForm, setTaskForm] = React.useState({ title: "", estimated_hours: "", description: "" });
  const [eventTaskId, setEventTaskId] = React.useState<number | null>(null);
  const [eventForm, setEventForm] = React.useState({ type: "blocked", description: "", duration_minutes: "" });

  const createTask = async () => {
    if (!taskForm.title.trim()) return toast.error(t("请填写任务标题"));
    await post(`/ta/projects/${id}/tasks`, {
      title: taskForm.title,
      description: taskForm.description,
      estimated_hours: taskForm.estimated_hours ? Number(taskForm.estimated_hours) : null,
      depends_on: [],
    });
    setTaskForm({ title: "", estimated_hours: "", description: "" });
    setTaskOpen(false);
    toast.success(t("任务已创建"));
    void tasks.refresh();
    void stats.refresh();
  };

  const setTaskStatus = async (tk: TaskItem, status: string) => {
    await patch(`/ta/tasks/${tk.id}`, { status, ...(status === "done" && tk.actual_hours === null ? {} : {}) });
    toast.success(t("任务「{title}」→ {status}", { title: tk.title, status: L.taskStatus[status] }));
    void tasks.refresh();
    void stats.refresh();
  };

  const addEvent = async () => {
    if (!eventTaskId) return;
    if (!eventForm.description.trim()) return toast.error(t("请描述事件经过"));
    await post(`/ta/tasks/${eventTaskId}/events`, {
      type: eventForm.type,
      description: eventForm.description,
      duration_minutes: eventForm.duration_minutes ? Number(eventForm.duration_minutes) : null,
    });
    setEventForm({ type: "blocked", description: "", duration_minutes: "" });
    setEventTaskId(null);
    toast.success(t("过程事件已记录"));
    void tasks.refresh();
    void stats.refresh();
  };

  const ruleReview = async () => {
    await post(`/ta/projects/${id}/rule-review`);
    toast.success(t("规则复盘已生成"));
    void reviews.refresh();
  };

  const aiReview = async () => {
    await ai.call({
      path: `/ai/ta/projects/${id}/review`,
      successMessage: t("AI 复盘报告已生成"),
      onDone: () => void reviews.refresh(),
    });
  };

  if (project.loading && !project.data) return <LoadingBlock rows={5} />;
  if (project.error) return <ErrorState error={project.error} onRetry={project.refresh} />;
  const p = project.data;
  if (!p) return null;
  const s = stats.data;

  return (
    <div>
      <AIBanner />
      <Link href="/ta" className="mb-4 inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
        <ArrowLeft className="h-4 w-4" /> {t("返回项目列表")}
      </Link>

      <div className="mb-6 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">{p.name}</h1>
          {p.description && <p className="mt-1 text-sm text-muted-foreground">{p.description}</p>}
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => void ruleReview()}>{t("规则复盘")}</Button>
          <Button disabled={ai.pending} onClick={() => void aiReview()}><Sparkles /> {t("AI 复盘")}</Button>
          <Button onClick={() => setTaskOpen(true)}><Plus /> {t("新建任务")}</Button>
        </div>
      </div>

      <Tabs defaultValue="tasks">
        <TabsList>
          <TabsTrigger value="tasks">{t("任务")}</TabsTrigger>
          <TabsTrigger value="stats">{t("统计")}</TabsTrigger>
          <TabsTrigger value="reviews">{t("复盘报告")}</TabsTrigger>
        </TabsList>

        <TabsContent value="tasks" className="space-y-3">
          {(tasks.data ?? []).map((tk) => (
            <Card key={tk.id}>
              <CardContent className="flex flex-wrap items-center gap-3 p-4">
                <div className="min-w-0 flex-1">
                  <p className="font-medium">{tk.title}</p>
                  <p className="mt-0.5 text-xs text-muted-foreground">
                    {t("预估 {x}", { x: fmtHours(tk.estimated_hours) })} · {t("实际 {x}", { x: fmtHours(tk.actual_hours) })}
                    {tk.started_at && ` · ${t("开始 {x}", { x: fmtDateTime(tk.started_at) })}`}
                    {tk.finished_at && ` · ${t("完成 {x}", { x: fmtDateTime(tk.finished_at) })}`}
                  </p>
                </div>
                <Badge variant={tk.status === "done" ? "success" : tk.status === "blocked" ? "destructive" : tk.status === "doing" ? "default" : "muted"}>
                  {L.taskStatus[tk.status]}
                </Badge>
                <Select
                  className="h-8 w-28 text-xs"
                  value={tk.status}
                  onChange={(e) => void setTaskStatus(tk, e.target.value)}
                >
                  <option value="todo">待开始</option>
                  <option value="doing">进行中</option>
                  <option value="blocked">已阻塞</option>
                  <option value="done">已完成</option>
                  <option value="cancelled">已取消</option>
                </Select>
                <Button size="sm" variant="outline" onClick={() => setEventTaskId(tk.id)}>
                  <Zap className="h-3.5 w-3.5" /> {t("记录事件")}
                </Button>
              </CardContent>
              <TaskEventsInline taskId={tk.id} refreshKey={tk.updated_at} />
            </Card>
          ))}
          {(tasks.data ?? []).length === 0 && (
            <p className="rounded-lg border border-dashed px-4 py-10 text-center text-sm text-muted-foreground">{t("还没有任务，点右上角「新建任务」开始。")}</p>
          )}
        </TabsContent>

        <TabsContent value="stats">
          {!s ? (
            <LoadingBlock rows={3} />
          ) : (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
                <MiniStat label={t("任务总数")} value={s.tasks_total} />
                <MiniStat label={t("已完成")} value={s.tasks_done} />
                <MiniStat label={t("阻塞中")} value={s.tasks_blocked} tone={s.tasks_blocked ? "text-destructive" : ""} />
                <MiniStat label={t("平均实际/预估")} value={s.avg_overrun_ratio ?? "—"} tone={s.avg_overrun_ratio && s.avg_overrun_ratio > 1.3 ? "text-warning" : ""} />
                <MiniStat label={t("总预估")} value={fmtHours(s.total_estimated_hours)} />
                <MiniStat label={t("总实际")} value={fmtHours(s.total_actual_hours)} />
                <MiniStat label={t("累计阻塞")} value={fmtMinutes(s.blocked_minutes_total)} />
                <MiniStat label={t("返工/中断/需求变化")} value={`${s.rework_count}/${s.interrupted_count}/${s.requirement_change_count}`} />
              </div>
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">{t("预估 vs 实际（已完成任务）")}</CardTitle>
                </CardHeader>
                <CardContent className="h-72">
                  {s.per_task.some((r) => r.estimated_hours || r.actual_hours) ? (
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={s.per_task.map((r) => ({ name: r.title.slice(0, 10), 预估: r.estimated_hours ?? 0, 实际: r.actual_hours ?? 0 }))} margin={{ top: 8, right: 8, left: -20, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" className="stroke-border" vertical={false} />
                        <XAxis dataKey="name" tick={{ fontSize: 11 }} tickLine={false} axisLine={false} />
                        <YAxis tick={{ fontSize: 11 }} tickLine={false} axisLine={false} />
                        <ChartTooltip contentStyle={{ background: "var(--card)", border: "1px solid var(--border)", borderRadius: 8, fontSize: 12 }} />
                        <Legend wrapperStyle={{ fontSize: 12 }} />
                        <Bar dataKey="预估" fill="var(--chart-2)" radius={[3, 3, 0, 0]} />
                        <Bar dataKey="实际" fill="var(--chart-5)" radius={[3, 3, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  ) : (
                    <p className="flex h-full items-center justify-center text-sm text-muted-foreground">{t("完成任务后这里会对比预估与实际耗时")}</p>
                  )}
                </CardContent>
              </Card>
            </div>
          )}
        </TabsContent>

        <TabsContent value="reviews" className="space-y-4">
          {reviews.data?.length === 0 && (
            <p className="rounded-lg border border-dashed px-4 py-10 text-center text-sm text-muted-foreground">
              {t("还没有复盘报告。点右上角「规则复盘」（无需 AI）或「AI 复盘」。")}
            </p>
          )}
          {(reviews.data ?? []).map((r) => (
            <Card key={r.id}>
              <CardHeader className="pb-2">
                <CardTitle className="text-base">{r.source === "ai" ? t("AI 复盘报告") : t("规则复盘报告")}</CardTitle>
                <CardDescription>{fmtDateTime(r.created_at)}</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3 text-sm">
                <p className="rounded bg-muted/40 px-3 py-2">{r.summary}</p>
                <ReviewSection title={t("事实（数据直接支持）")} items={r.facts} tone="success" />
                <ReviewSection title={t("推测（需要进一步验证）")} items={r.speculations} tone="warning" />
                <ReviewSection title={t("缺失证据（无法判断的部分）")} items={r.missing_evidence} tone="destructive" />
                <ReviewSection title={t("下一步可测试的改进")} items={r.improvements} tone="primary" />
              </CardContent>
            </Card>
          ))}
        </TabsContent>
      </Tabs>

      <Dialog open={taskOpen} onOpenChange={setTaskOpen}>
        <DialogContent>
          <DialogHeader><DialogTitle>{t("新建任务")}</DialogTitle></DialogHeader>
          <div className="space-y-3">
            <div><Label>{t("标题 *")}</Label><Input value={taskForm.title} onChange={(e) => setTaskForm({ ...taskForm, title: e.target.value })} /></div>
            <div><Label>{t("预估耗时（小时）")}</Label><Input type="number" min={0} step={0.5} value={taskForm.estimated_hours} onChange={(e) => setTaskForm({ ...taskForm, estimated_hours: e.target.value })} /></div>
            <div><Label>{t("描述")}</Label><Textarea value={taskForm.description} onChange={(e) => setTaskForm({ ...taskForm, description: e.target.value })} /></div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setTaskOpen(false)}>{t("action.cancel")}</Button>
            <Button onClick={() => void createTask()}>创建</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={eventTaskId !== null} onOpenChange={(v) => !v && setEventTaskId(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t("记录过程事件")}</DialogTitle>
            <DialogDescription>{t("阻塞、返工、中断、需求变化——这些是复盘时定位问题的核心证据。")}</DialogDescription>
          </DialogHeader>
          <div className="space-y-3">
            <div>
              <Label>{t("事件类型")}</Label>
              <Select value={eventForm.type} onChange={(e) => setEventForm({ ...eventForm, type: e.target.value })}>
                <option value="blocked">{t("阻塞")}</option>
                <option value="resumed">{t("恢复")}</option>
                <option value="rework">{t("返工")}</option>
                <option value="interrupted">{t("中断")}</option>
                <option value="requirement_change">{t("需求变化")}</option>
                <option value="note">{t("备注")}</option>
              </Select>
            </div>
            <div><Label>{t("经过描述 *")}</Label><Textarea value={eventForm.description} onChange={(e) => setEventForm({ ...eventForm, description: e.target.value })} placeholder={t("发生了什么、原因、影响")} /></div>
            <div><Label>{t("耗时（分钟，可选，如阻塞时长）")}</Label><Input type="number" min={0} value={eventForm.duration_minutes} onChange={(e) => setEventForm({ ...eventForm, duration_minutes: e.target.value })} /></div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setEventTaskId(null)}>{t("action.cancel")}</Button>
            <Button onClick={() => void addEvent()}>{t("记录")}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
      {ai.dialog}
    </div>
  );
}

function TaskEventsInline({ taskId, refreshKey }: { taskId: number; refreshKey: string }) {
  const L = useL();
  const [events, setEvents] = React.useState<TaskEventItem[]>([]);
  React.useEffect(() => {
    void fetch(`/api/ta/tasks/${taskId}/events`)
      .then((r) => r.json())
      .then(setEvents)
      .catch(() => setEvents([]));
  }, [taskId, refreshKey]);
  if (events.length === 0) return null;
  return (
    <div className="border-t px-4 py-2.5">
      <ul className="space-y-1 text-xs text-muted-foreground">
        {events.map((e) => (
          <li key={e.id} className="flex flex-wrap items-center gap-1.5">
            <Badge variant={e.type === "blocked" || e.type === "rework" ? "destructive" : e.type === "requirement_change" ? "warning" : "muted"} className="h-5 px-1.5 text-[10px]">
              {L.taEventType[e.type] ?? e.type}
            </Badge>
            <span className="min-w-0 flex-1 truncate">{e.description}</span>
            {e.duration_minutes ? <span className="flex items-center gap-0.5"><Clock className="h-3 w-3" />{fmtMinutes(e.duration_minutes)}</span> : null}
            <span>{fmtDateTime(e.occurred_at)}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function MiniStat({ label, value, tone = "" }: { label: string; value: React.ReactNode; tone?: string }) {
  return (
    <Card>
      <CardContent className="p-4">
        <p className="text-xs text-muted-foreground">{label}</p>
        <p className={`mt-1 text-xl font-bold tabular-nums ${tone}`}>{value}</p>
      </CardContent>
    </Card>
  );
}

function ReviewSection({ title, items, tone }: { title: string; items: string[]; tone: "success" | "warning" | "destructive" | "primary" }) {
  if (items.length === 0) return null;
  const border = { success: "border-success/40", warning: "border-warning/40", destructive: "border-destructive/40", primary: "border-primary/30" }[tone];
  const text = { success: "text-success", warning: "text-warning", destructive: "text-destructive", primary: "text-primary" }[tone];
  return (
    <div className={`rounded-lg border ${border} p-3`}>
      <p className={`mb-1.5 text-xs font-semibold ${text}`}>{title}</p>
      <ul className="list-disc space-y-1 pl-5">
        {items.map((x, i) => <li key={i}>{x}</li>)}
      </ul>
    </div>
  );
}

export default function ProjectDetailPage() {
  return (
    <React.Suspense fallback={<LoadingBlock rows={5} />}>
      <ProjectDetailPageInner />
    </React.Suspense>
  );
}
