"use client";
/** Decision Time Machine 列表页 + 全局校准分析。 */
import * as React from "react";
import Link from "next/link";
import { toast } from "sonner";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip as ChartTooltip,
  XAxis,
  YAxis,
} from "recharts";
import { CalendarClock, Plus } from "lucide-react";
import { PageHeader, EmptyState, LoadingBlock, ErrorState, AIBanner } from "@/components/layout/shared";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input, Label, Textarea } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { post } from "@/lib/api";
import { useApi } from "@/lib/useApi";
import { fmtDateTime, fromLocalInput } from "@/lib/format";
import type { Calibration, Decision } from "@/lib/types";

export default function DTMPage() {
  const decisions = useApi<Decision[]>("/dtm/decisions");
  const calibration = useApi<Calibration>("/dtm/calibration");
  const [createOpen, setCreateOpen] = React.useState(false);
  const [form, setForm] = React.useState({
    title: "", context: "", goals: "", basis: "", risks: "",
    optionA: "", optionB: "", review_at: "",
  });

  const create = async () => {
    if (!form.title.trim()) return toast.error("请填写决策标题");
    const options = [form.optionA, form.optionB]
      .map((s, i) => ({ key: String.fromCharCode(65 + i), label: s.trim(), description: "" }))
      .filter((o) => o.label);
    await post("/dtm/decisions", {
      title: form.title,
      context: form.context,
      goals: form.goals,
      options,
      basis: form.basis,
      risks: form.risks,
      review_at: fromLocalInput(form.review_at),
    });
    setCreateOpen(false);
    setForm({ title: "", context: "", goals: "", basis: "", risks: "", optionA: "", optionB: "", review_at: "" });
    toast.success("决策已记录，首个快照已保存（不可修改）");
    void decisions.refresh();
  };

  if (decisions.loading && !decisions.data) return <LoadingBlock rows={4} />;
  if (decisions.error) return <ErrorState error={decisions.error} onRetry={decisions.refresh} />;
  const list = decisions.data ?? [];

  return (
    <div>
      <AIBanner />
      <PageHeader
        title="决策时间机"
        description="记录决策时的真实想法与概率预测；结果不能简单判定当初的对错，复盘评价的是决策过程。"
        actions={<Button onClick={() => setCreateOpen(true)}><Plus /> 记录决策</Button>}
      />

      <Tabs defaultValue="list">
        <TabsList>
          <TabsTrigger value="list">决策列表</TabsTrigger>
          <TabsTrigger value="calibration">预测校准</TabsTrigger>
        </TabsList>

        <TabsContent value="list">
          {list.length === 0 ? (
            <EmptyState
              icon={CalendarClock}
              title="还没有决策记录"
              hint="记录下决策发生时的背景、备选方案与概率预测，未来回看时你会感谢现在的自己。"
              action={<Button onClick={() => setCreateOpen(true)}><Plus /> 记录第一个决策</Button>}
            />
          ) : (
            <div className="grid gap-3 md:grid-cols-2">
              {list.map((d) => {
                const due = d.status === "open" && d.review_at && new Date(d.review_at) <= new Date();
                return (
                  <Link key={d.id} href={`/dtm/${d.id}`}>
                    <Card className="h-full transition-shadow hover:shadow-md">
                      <CardHeader className="pb-2">
                        <div className="flex items-start justify-between gap-2">
                          <CardTitle className="text-base leading-snug">{d.title}</CardTitle>
                          <Badge variant={d.status === "reviewed" ? "success" : due ? "warning" : "muted"}>
                            {d.status === "reviewed" ? "已复盘" : due ? "待复盘" : "进行中"}
                          </Badge>
                        </div>
                        <CardDescription className="line-clamp-2">{d.context || "（未填写背景）"}</CardDescription>
                      </CardHeader>
                      <CardContent className="text-xs text-muted-foreground">
                        {d.options.length > 0 && <p>备选：{d.options.map((o) => o.label).join(" / ")}</p>}
                        <p className="mt-1">创建于 {fmtDateTime(d.created_at)}{d.review_at && ` · 计划复盘 ${fmtDateTime(d.review_at)}`}</p>
                      </CardContent>
                    </Card>
                  </Link>
                );
              })}
            </div>
          )}
        </TabsContent>

        <TabsContent value="calibration">
          <CalibrationPanel cal={calibration} />
        </TabsContent>
      </Tabs>

      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent wide>
          <DialogHeader>
            <DialogTitle>记录决策</DialogTitle>
          </DialogHeader>
          <div className="max-h-[60vh] space-y-3 overflow-y-auto pr-1">
            <div><Label>标题 *</Label><Input value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} placeholder="如：考研还是就业" /></div>
            <div><Label>背景</Label><Textarea value={form.context} onChange={(e) => setForm({ ...form, context: e.target.value })} placeholder="当时的环境与约束" /></div>
            <div><Label>目标</Label><Input value={form.goals} onChange={(e) => setForm({ ...form, goals: e.target.value })} placeholder="希望达成什么" /></div>
            <div className="grid grid-cols-2 gap-3">
              <div><Label>备选 A</Label><Input value={form.optionA} onChange={(e) => setForm({ ...form, optionA: e.target.value })} /></div>
              <div><Label>备选 B（可选）</Label><Input value={form.optionB} onChange={(e) => setForm({ ...form, optionB: e.target.value })} /></div>
            </div>
            <div><Label>当时依据</Label><Textarea value={form.basis} onChange={(e) => setForm({ ...form, basis: e.target.value })} placeholder="你依据哪些信息做出的判断" /></div>
            <div><Label>已知风险</Label><Textarea value={form.risks} onChange={(e) => setForm({ ...form, risks: e.target.value })} /></div>
            <div><Label>计划复盘时间（可选）</Label><Input type="datetime-local" value={form.review_at} onChange={(e) => setForm({ ...form, review_at: e.target.value })} /></div>
            <p className="text-xs text-muted-foreground">创建后可进入详情页添加量化预测（如“过线概率 60%”），系统会生成第一个不可修改的快照。</p>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCreateOpen(false)}>取消</Button>
            <Button onClick={() => void create()}>保存</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function CalibrationPanel({ cal }: { cal: { data: Calibration | null; loading: boolean; error: Error | null; refresh: () => Promise<void> } }) {
  if (cal.loading && !cal.data) return <LoadingBlock rows={2} />;
  if (cal.error) return <ErrorState error={cal.error} onRetry={cal.refresh} />;
  const c = cal.data;
  if (!c) return null;
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">预测校准</CardTitle>
        <CardDescription>
          共 {c.n_predictions} 条已揭晓的预测 · Brier 分数 {c.brier_score}（越接近 0 越好，随机猜测约 0.25）
        </CardDescription>
      </CardHeader>
      <CardContent>
        {c.n_predictions === 0 ? (
          <EmptyState title="还没有已揭晓的预测" hint="在决策详情中添加概率预测，揭晓后这里会显示你的校准曲线。" />
        ) : (
          <>
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={c.bins} margin={{ top: 8, right: 8, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-border" vertical={false} />
                  <XAxis dataKey="label" tick={{ fontSize: 11 }} tickLine={false} axisLine={false} />
                  <YAxis domain={[0, 1]} tick={{ fontSize: 11 }} tickLine={false} axisLine={false} tickFormatter={(v: number) => `${Math.round(v * 100)}%`} />
                  <ChartTooltip contentStyle={{ background: "var(--card)", border: "1px solid var(--border)", borderRadius: 8, fontSize: 12 }} />
                  <Bar dataKey="avg_predicted" name="你的平均预测" fill="var(--chart-1)" radius={[3, 3, 0, 0]} />
                  <Bar dataKey="actual_rate" name="实际发生率" fill="var(--chart-3)" radius={[3, 3, 0, 0]} />
                  <ReferenceLine y={0.5} className="stroke-border" />
                </BarChart>
              </ResponsiveContainer>
            </div>
            <p className="mt-3 rounded bg-muted/50 px-3 py-2 text-xs leading-relaxed text-muted-foreground">{c.caveat}</p>
          </>
        )}
      </CardContent>
    </Card>
  );
}
