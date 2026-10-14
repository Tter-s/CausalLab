"use client";
/** 决策详情：不可覆盖快照、概率预测、新信息时间线、复盘（AI/手动）、反事实（假设推演）。
 *  路由为查询参数形式（/dtm/detail?id=27），兼容静态导出（动态段 [id] 无法在构建期枚举）。 */
import * as React from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { toast } from "sonner";
import { ArrowLeft, Camera, Lightbulb, Plus, ShieldAlert, Sparkles } from "lucide-react";
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
import { useT } from "@/lib/i18n";
import { fmtDateTime } from "@/lib/format";
import type { DecisionDetail, Prediction } from "@/lib/types";

function DecisionDetailPageInner() {
  const t = useT();
  const searchParams = useSearchParams();
  const id = searchParams.get("id") ?? "";
  const detail = useApi<DecisionDetail>(id ? `/dtm/decisions/${id}` : null);
  const ai = useAICall();
  const [predForm, setPredForm] = React.useState({ statement: "", probability: 50 });
  const [updateForm, setUpdateForm] = React.useState({ content: "", source: "", significance: "minor" });
  const [reviewForm, setReviewForm] = React.useState({ summary: "", process_score: "3" });
  const [cfOpen, setCfOpen] = React.useState(false);
  const [cfScenario, setCfScenario] = React.useState("");

  if (!id) return <ErrorState error={new Error(t("链接缺少 id 参数：请从决策列表进入详情页。"))} />;
  if (detail.loading && !detail.data) return <LoadingBlock rows={5} />;
  if (detail.error) return <ErrorState error={detail.error} onRetry={detail.refresh} />;
  const d = detail.data;
  if (!d) return null;

  const addPrediction = async () => {
    if (!predForm.statement.trim()) return toast.error(t("请填写预测陈述（要可判定）"));
    await post(`/dtm/decisions/${id}/predictions`, {
      statement: predForm.statement,
      probability: predForm.probability / 100,
    });
    setPredForm({ statement: "", probability: 50 });
    toast.success(t("预测已记录"));
    void detail.refresh();
  };

  const resolvePrediction = async (p: Prediction, resolved: boolean) => {
    const note = window.prompt(resolved ? t("实际结果如何？（可留空）") : t("为什么没有发生？（可留空）")) ?? "";
    await patch(`/dtm/predictions/${p.id}`, { resolved, actual_note: note });
    toast.success(t("预测已揭晓"));
    void detail.refresh();
  };

  const addUpdate = async () => {
    if (!updateForm.content.trim()) return toast.error(t("请填写新信息内容"));
    await post(`/dtm/decisions/${id}/updates`, updateForm);
    setUpdateForm({ content: "", source: "", significance: "minor" });
    toast.success(t("新信息已加入决策时间线"));
    void detail.refresh();
  };

  const submitReview = async () => {
    if (!reviewForm.summary.trim()) return toast.error(t("请填写复盘内容"));
    await post(`/dtm/decisions/${id}/reviews`, {
      summary: reviewForm.summary,
      process_score: reviewForm.process_score ? Number(reviewForm.process_score) : null,
      lessons: [],
      bias_flags: [],
    });
    toast.success(t("复盘已保存"));
    void detail.refresh();
  };

  const aiReview = async () => {
    await ai.call({
      path: `/ai/dtm/decisions/${id}/review`,
      successMessage: t("AI 复盘已生成"),
      onDone: () => void detail.refresh(),
    });
  };

  const addCounterfactual = async () => {
    if (!cfScenario.trim()) return toast.error(t("请描述反事实情景"));
    await ai.call({
      path: `/ai/dtm/decisions/${id}/counterfactual`,
      params: { scenario: cfScenario },
      successMessage: t("反事实推演已生成（假设推演）"),
      onDone: () => { setCfOpen(false); setCfScenario(""); void detail.refresh(); },
    });
  };

  return (
    <div>
      <AIBanner />
      <Link href="/dtm" className="mb-4 inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
        <ArrowLeft className="h-4 w-4" /> {t("返回决策列表")}
      </Link>

      <div className="mb-6 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="flex items-center gap-2 text-2xl font-bold tracking-tight">
            {d.title}
            <Badge variant={d.status === "reviewed" ? "success" : "muted"}>
              {d.status === "reviewed" ? t("已复盘") : d.status === "archived" ? t("已归档") : t("进行中")}
            </Badge>
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">{t("创建于 {x}", { x: fmtDateTime(d.created_at) })}</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => setCfOpen(true)}>
            <Lightbulb /> {t("反事实推演")}
          </Button>
        </div>
      </div>

      <Tabs defaultValue="record">
        <TabsList>
          <TabsTrigger value="record">{t("决策记录")}</TabsTrigger>
          <TabsTrigger value="predictions">{t("预测与校准")}</TabsTrigger>
          <TabsTrigger value="timeline">{t("新信息时间线")}</TabsTrigger>
          <TabsTrigger value="review">{t("复盘")}</TabsTrigger>
          <TabsTrigger value="snapshots">{t("快照历史")}</TabsTrigger>
        </TabsList>

        <TabsContent value="record" className="grid gap-4 md:grid-cols-2">
          <Card>
            <CardHeader><CardTitle className="text-base">{t("背景与目标")}</CardTitle></CardHeader>
            <CardContent className="space-y-3 text-sm">
              <div><p className="text-xs font-medium text-muted-foreground">{t("背景")}</p><p className="whitespace-pre-wrap">{d.context || "—"}</p></div>
              <div><p className="text-xs font-medium text-muted-foreground">{t("目标")}</p><p className="whitespace-pre-wrap">{d.goals || "—"}</p></div>
              <div><p className="text-xs font-medium text-muted-foreground">{t("当时依据")}</p><p className="whitespace-pre-wrap">{d.basis || "—"}</p></div>
              <div><p className="text-xs font-medium text-muted-foreground">{t("已知风险")}</p><p className="whitespace-pre-wrap">{d.risks || "—"}</p></div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader><CardTitle className="text-base">{t("备选方案")}</CardTitle></CardHeader>
            <CardContent className="space-y-2 text-sm">
              {d.options.length === 0 && <p className="text-muted-foreground">{t("未记录备选方案")}</p>}
              {d.options.map((o) => (
                <div key={o.key} className="rounded-lg border p-3">
                  <p className="font-medium"><span className="mr-1.5 rounded bg-primary/10 px-1.5 py-0.5 text-xs text-primary">{o.key}</span>{o.label}</p>
                  {o.description && <p className="mt-1 text-muted-foreground">{o.description}</p>}
                </div>
              ))}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="predictions" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">{t("添加预测")}</CardTitle>
              <CardDescription>{t("写下可判定的陈述与你的主观概率，揭晓后进入校准统计。")}</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <Input placeholder={t("如：如果选 A，初试过线的概率")} value={predForm.statement} onChange={(e) => setPredForm({ ...predForm, statement: e.target.value })} />
              <div className="flex items-center gap-3">
                <input type="range" min={0} max={100} value={predForm.probability} onChange={(e) => setPredForm({ ...predForm, probability: Number(e.target.value) })} className="h-2 flex-1 cursor-pointer appearance-none rounded-full bg-muted accent-[var(--primary)]" />
                <span className="w-14 text-right text-sm font-semibold tabular-nums">{predForm.probability}%</span>
              </div>
              <Button size="sm" onClick={() => void addPrediction()}><Plus /> {t("记录预测")}</Button>
            </CardContent>
          </Card>
          {d.predictions.map((p) => (
            <Card key={p.id}>
              <CardContent className="flex flex-wrap items-center gap-3 p-4">
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium">{p.statement}</p>
                  <p className="mt-0.5 text-xs text-muted-foreground">{t("记录于 {x}", { x: fmtDateTime(p.created_at) })}</p>
                </div>
                <span className="text-lg font-bold tabular-nums">{Math.round(p.probability * 100)}%</span>
                {p.resolved === null || p.resolved === undefined ? (
                  <div className="flex gap-1.5">
                    <Button size="sm" variant="outline" onClick={() => void resolvePrediction(p, true)}>{t("命中")}</Button>
                    <Button size="sm" variant="outline" onClick={() => void resolvePrediction(p, false)}>{t("未命中")}</Button>
                  </div>
                ) : (
                  <Badge variant={p.resolved ? "success" : "destructive"}>{p.resolved ? t("命中") : t("未命中")}</Badge>
                )}
                {p.actual_note && <p className="w-full text-xs text-muted-foreground">{t("实际：")}{p.actual_note}</p>}
              </CardContent>
            </Card>
          ))}
          {d.predictions.length === 0 && <p className="rounded-lg border border-dashed px-4 py-8 text-center text-sm text-muted-foreground">{t("还没有预测。量化预测是复盘时最有价值的证据。")}</p>}
        </TabsContent>

        <TabsContent value="timeline" className="space-y-4">
          <Card>
            <CardHeader><CardTitle className="text-base">{t("记录新信息")}</CardTitle></CardHeader>
            <CardContent className="space-y-3">
              <Textarea placeholder={t("决策之后出现了什么新信息？（缩招、新 offer、身体状态变化…）")} value={updateForm.content} onChange={(e) => setUpdateForm({ ...updateForm, content: e.target.value })} />
              <div className="grid grid-cols-2 gap-3">
                <Input placeholder={t("信息来源（可选）")} value={updateForm.source} onChange={(e) => setUpdateForm({ ...updateForm, source: e.target.value })} />
                <Select value={updateForm.significance} onChange={(e) => setUpdateForm({ ...updateForm, significance: e.target.value })}>
                  <option value="minor">{t("一般信息")}</option>
                  <option value="major">{t("重大信息")}</option>
                </Select>
              </div>
              <Button size="sm" onClick={() => void addUpdate()}><Plus /> {t("加入时间线")}</Button>
            </CardContent>
          </Card>
          <ol className="relative ml-3 space-y-4 border-l pl-5">
            {d.updates.map((u) => (
              <li key={u.id}>
                <span className={`absolute -left-1.5 mt-1.5 h-3 w-3 rounded-full border-2 border-background ${u.significance === "major" ? "bg-destructive" : "bg-primary"}`} />
                <Card>
                  <CardContent className="p-4">
                    <div className="flex items-center gap-2">
                      {u.significance === "major" && <Badge variant="destructive">{t("重大")}</Badge>}
                      <span className="text-xs text-muted-foreground">{fmtDateTime(u.occurred_at)}{u.source && ` · ${t("来源：")}${u.source}`}</span>
                    </div>
                    <p className="mt-1.5 text-sm">{u.content}</p>
                  </CardContent>
                </Card>
              </li>
            ))}
            {d.updates.length === 0 && <p className="text-sm text-muted-foreground">{t("还没有后续信息")}</p>}
          </ol>
        </TabsContent>

        <TabsContent value="review" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">{t("复盘决策")}</CardTitle>
              <CardDescription>{t("复盘评价的是决策过程质量（信息、备选、判断依据），不是结果好坏。")}</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <Textarea placeholder={t("回顾当时的信息与判断，哪里做得好、哪里是运气？")} value={reviewForm.summary} onChange={(e) => setReviewForm({ ...reviewForm, summary: e.target.value })} />
              <div className="flex items-center gap-3">
                <Label>{t("过程质量分")}</Label>
                <Select className="w-40" value={reviewForm.process_score} onChange={(e) => setReviewForm({ ...reviewForm, process_score: e.target.value })}>
                  {[1, 2, 3, 4, 5].map((n) => <option key={n} value={n}>{n} {t("分")}</option>)}
                </Select>
              </div>
              <div className="flex gap-2">
                <Button size="sm" onClick={() => void submitReview()}>{t("保存手动复盘")}</Button>
                <Button size="sm" variant="outline" disabled={ai.pending} onClick={() => void aiReview()}>
                  <Sparkles /> {t("AI 复盘报告")}{ai.pending ? "…" : ""}
                </Button>
              </div>
            </CardContent>
          </Card>
          {d.reviews.map((r) => (
            <Card key={r.id}>
              <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-base">{r.source === "ai" ? t("AI 复盘报告") : t("手动复盘")}</CardTitle>
                  <span className="text-xs text-muted-foreground">{fmtDateTime(r.reviewed_at)}</span>
                </div>
                {r.process_score !== null && (
                  <CardDescription>{t("决策过程质量：{s}/5（与结果好坏无关）", { s: r.process_score })}</CardDescription>
                )}
              </CardHeader>
              <CardContent className="space-y-2 text-sm">
                <p className="whitespace-pre-wrap">{r.summary}</p>
                {r.lessons.length > 0 && (
                  <div><p className="text-xs font-semibold text-muted-foreground">{t("经验")}</p>
                    <ul className="list-disc pl-5">{r.lessons.map((l, i) => <li key={i}>{l}</li>)}</ul>
                  </div>
                )}
                {r.bias_flags.length > 0 && (
                  <div className="flex flex-wrap items-center gap-1.5">
                    <span className="text-xs font-semibold text-muted-foreground">{t("可能的偏差：")}</span>
                    {r.bias_flags.map((b, i) => <Badge key={i} variant="warning">{b}</Badge>)}
                  </div>
                )}
              </CardContent>
            </Card>
          ))}
        </TabsContent>

        <TabsContent value="snapshots" className="space-y-3">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base"><Camera className="h-4 w-4" /> {t("不可覆盖快照")}</CardTitle>
              <CardDescription>{t("创建与每次修改都会生成新快照；快照只能查看，永远不能修改或删除。")}</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {d.snapshots.map((s, i) => (
                <div key={s.id} className="rounded-lg border p-3">
                  <div className="flex items-center justify-between text-xs text-muted-foreground">
                    <span>#{i + 1} · {s.reason === "created" ? t("创建时") : t("修改时")}</span>
                    <span>{fmtDateTime(s.snapshot_at)}</span>
                  </div>
                  <pre className="mt-2 max-h-40 overflow-y-auto whitespace-pre-wrap rounded bg-muted/40 p-2.5 text-xs leading-relaxed">
                    {JSON.stringify(s.payload, null, 2)}
                  </pre>
                </div>
              ))}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {d.counterfactuals.length > 0 && (
        <Card className="mt-4 border-dashed">
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-base"><ShieldAlert className="h-4 w-4 text-warning" /> {t("反事实推演（假设，非事实）")}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {d.counterfactuals.map((c) => (
              <div key={c.id} className="rounded-lg border border-warning/30 bg-warning/5 p-3 text-sm">
                <p className="font-medium">{t("情景：")}{c.scenario}</p>
                <p className="mt-1.5 whitespace-pre-wrap text-muted-foreground">{c.analysis}</p>
                <p className="mt-2 text-xs text-warning">{t("假设推演")} · {fmtDateTime(c.created_at)} · {t("不能用推演结果评判当初的决策")}</p>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      <Dialog open={cfOpen} onOpenChange={setCfOpen}>
        <DialogContent wide>
          <DialogHeader>
            <DialogTitle>{t("反事实推演")}</DialogTitle>
            <DialogDescription>
              {t("描述一个如果当初……的情景，AI 会基于已记录的依据推演可能的结果。推演结果永远标记为假设，不作为事实使用。")}
            </DialogDescription>
          </DialogHeader>
          <Textarea rows={4} placeholder={t("如：如果当初选择方案 B，且照常执行会怎样？")} value={cfScenario} onChange={(e) => setCfScenario(e.target.value)} />
          <DialogFooter>
            <Button variant="outline" onClick={() => setCfOpen(false)}>取消</Button>
            <Button disabled={ai.pending} onClick={() => void addCounterfactual()}>
              <Sparkles /> {t("生成推演")}{ai.pending ? "…" : ""}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
      {ai.dialog}
    </div>
  );
}

export default function DecisionDetailPage() {
  return (
    <React.Suspense fallback={<LoadingBlock rows={5} />}>
      <DecisionDetailPageInner />
    </React.Suspense>
  );
}
