"use client";
/** 假设实验室：创建关于自身学习/工作方式的假设，设计记录实验，积累观察值，分组对比（附局限性说明）。 */
import * as React from "react";
import { toast } from "sonner";
import { FlaskConical, Plus, Sparkles } from "lucide-react";
import { PageHeader, EmptyState, LoadingBlock, ErrorState, AIBanner } from "@/components/layout/shared";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input, Label, Select, Textarea } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { get, patch, post } from "@/lib/api";
import { useApi } from "@/lib/useApi";
import { useAICall } from "@/lib/ai-client";
import { useL, useT } from "@/lib/i18n";
import { fmtDate } from "@/lib/format";
import type { Hypothesis, HypothesisAnalysis, Observation } from "@/lib/types";

const STATUS_KEYS: Record<string, "draft" | "testing" | "supported" | "rejected" | "uncertain"> = {
  draft: "draft",
  testing: "testing",
  supported: "supported",
  rejected: "rejected",
  uncertain: "uncertain",
};

export default function HypothesesPage() {
  const t = useT();
  const L = useL();
  const list = useApi<Hypothesis[]>("/hypotheses");
  const ai = useAICall();
  const [createOpen, setCreateOpen] = React.useState(false);
  const [form, setForm] = React.useState({ statement: "", rationale: "" });
  const [selectedId, setSelectedId] = React.useState<number | null>(null);
  const [observations, setObservations] = React.useState<Observation[]>([]);
  const [analysis, setAnalysis] = React.useState<HypothesisAnalysis | null>(null);
  const [groupKey, setGroupKey] = React.useState("时段");
  const [obsForm, setObsForm] = React.useState({ value: "", context_key: "时段", context_value: "", note: "" });

  const selected = (list.data ?? []).find((h) => h.id === selectedId) ?? null;

  const loadDetail = React.useCallback(async (id: number, gk: string) => {
    const [obs, ana] = await Promise.all([
      get<Observation[]>(`/hypotheses/${id}/observations`),
      get<HypothesisAnalysis>(`/hypotheses/${id}/analysis?group_key=${encodeURIComponent(gk)}`),
    ]);
    setObservations(obs);
    setAnalysis(ana);
  }, []);

  React.useEffect(() => {
    if (selectedId) void loadDetail(selectedId, groupKey);
  }, [selectedId, groupKey, loadDetail]);

  const create = async () => {
    if (!form.statement.trim()) return toast.error(t("请写下假设陈述（要可检验）"));
    const h = await post<Hypothesis>("/hypotheses", form);
    setCreateOpen(false);
    setForm({ statement: "", rationale: "" });
    toast.success(t("假设已创建"));
    void list.refresh();
    setSelectedId(h.id);
  };

  const setStatus = async (h: Hypothesis, status: string) => {
    await patch(`/hypotheses/${h.id}`, { status });
    toast.success(t("状态已更新"));
    void list.refresh();
  };

  const addObservation = async () => {
    if (!selectedId || !obsForm.value) return toast.error(t("请填写观察值"));
    await post(`/hypotheses/${selectedId}/observations`, {
      value: Number(obsForm.value),
      context: obsForm.context_value ? { [obsForm.context_key]: obsForm.context_value } : {},
      note: obsForm.note,
    });
    setObsForm({ ...obsForm, value: "", context_value: "", note: "" });
    toast.success(t("观察已记录"));
    void loadDetail(selectedId, groupKey);
    void list.refresh();
  };

  const designWithAI = async () => {
    if (!selectedId) return;
    await ai.call({
      path: `/ai/hypotheses/${selectedId}/design`,
      successMessage: t("AI 已生成实验设计建议"),
      onDone: () => void list.refresh(),
    });
  };

  if (list.loading && !list.data) return <LoadingBlock rows={4} />;
  if (list.error) return <ErrorState error={list.error} onRetry={list.refresh} />;
  const hypotheses = list.data ?? [];

  return (
    <div>
      <AIBanner />
      <PageHeader
        title={t("假设实验室")}
        description={t("我在上午学习时独立完成率更高——把这样的直觉变成可检验的记录实验。相关不等于因果。")}
        actions={<Button onClick={() => setCreateOpen(true)}><Plus /> {t("新建假设")}</Button>}
      />

      {hypotheses.length === 0 ? (
        <EmptyState icon={FlaskConical} title={t("还没有假设")} hint={t("写下你对自己学习或工作方式的猜想，系统会帮你设计记录方式并跟踪数据。")} action={<Button onClick={() => setCreateOpen(true)}><Plus /> {t("新建假设")}</Button>} />
      ) : (
        <div className="grid gap-4 lg:grid-cols-5">
          <div className="space-y-3 lg:col-span-2">
            {hypotheses.map((h) => {
              const st = L.hypStatus[STATUS_KEYS[h.status] ?? "draft"];
              return (
                <Card
                  key={h.id}
                  className={`cursor-pointer transition-shadow hover:shadow-md ${selectedId === h.id ? "ring-1 ring-primary" : ""}`}
                  onClick={() => setSelectedId(h.id)}
                >
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm leading-snug">{h.statement}</CardTitle>
                    <CardDescription>{t("创建于 {x}", { x: fmtDate(h.created_at) })}</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <Badge variant={st.variant}>{st.label}</Badge>
                  </CardContent>
                </Card>
              );
            })}
          </div>

          <div className="space-y-4 lg:col-span-3">
            {selected && (
              <>
                <Card>
                  <CardHeader>
                    <CardTitle className="text-base">{t("假设详情")}</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3 text-sm">
                    <p className="font-medium">{selected.statement}</p>
                    {selected.rationale && <p className="text-muted-foreground">{selected.rationale}</p>}
                    {selected.criteria && (
                      <pre className="whitespace-pre-wrap rounded bg-muted/40 p-2.5 text-xs">{JSON.stringify(selected.criteria, null, 2)}</pre>
                    )}
                    {selected.design && (
                      <div className="rounded-lg border border-primary/25 bg-primary/5 p-3">
                        <p className="mb-1 flex items-center gap-1 text-xs font-semibold text-primary"><Sparkles className="h-3 w-3" /> {t("AI 实验设计建议")}</p>
                        <pre className="whitespace-pre-wrap text-xs leading-relaxed">{JSON.stringify(selected.design, null, 2)}</pre>
                      </div>
                    )}
                    <div className="flex flex-wrap gap-2">
                      <Button size="sm" variant="outline" disabled={ai.pending} onClick={() => void designWithAI()}>
                        <Sparkles /> {t("AI 设计记录实验")}
                      </Button>
                      <Select className="h-8 w-28 text-xs" value={selected.status} onChange={(e) => void setStatus(selected, e.target.value)}>
                        {Object.entries(L.hypStatus).map(([k, v]) => <option key={k} value={k}>{v.label}</option>)}
                      </Select>
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader><CardTitle className="text-base">{t("记录观察值")}</CardTitle></CardHeader>
                  <CardContent className="space-y-3">
                    <div className="grid grid-cols-3 gap-2">
                      <div>
                        <Label className="text-xs">{t("数值")}</Label>
                        <Input type="number" step={0.01} placeholder={t("如 0.8")} value={obsForm.value} onChange={(e) => setObsForm({ ...obsForm, value: e.target.value })} />
                      </div>
                      <div>
                        <Label className="text-xs">{t("条件标签名")}</Label>
                        <Input value={obsForm.context_key} onChange={(e) => setObsForm({ ...obsForm, context_key: e.target.value })} />
                      </div>
                      <div>
                        <Label className="text-xs">{t("条件取值")}</Label>
                        <Input placeholder={t("如 上午")} value={obsForm.context_value} onChange={(e) => setObsForm({ ...obsForm, context_value: e.target.value })} />
                      </div>
                    </div>
                    <Input placeholder={t("备注（可选）")} value={obsForm.note} onChange={(e) => setObsForm({ ...obsForm, note: e.target.value })} />
                    <Button size="sm" onClick={() => void addObservation()}><Plus /> {t("记录")}</Button>
                  </CardContent>
                </Card>

                {analysis && (
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-base">{t("数据分析")}</CardTitle>
                      <CardDescription>
                        {t("{n} 条观察 · 整体均值 {m}", { n: analysis.n_observations, m: analysis.overall_mean ?? "—" })}
                      </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-3">
                      <div className="flex items-center gap-2">
                        <Label className="text-xs">{t("分组字段")}</Label>
                        <Input className="h-8 w-32 text-xs" value={groupKey} onChange={(e) => setGroupKey(e.target.value)} />
                      </div>
                      {analysis.groups.length > 0 ? (
                        <div className="grid gap-2 sm:grid-cols-2">
                          {analysis.groups.map((g) => (
                            <div key={g.label} className="rounded-lg border p-3">
                              <p className="font-semibold">{g.label}</p>
                              <p className="text-sm text-muted-foreground">n={g.n} · 均值 {g.mean}{g.std !== null && ` · 标准差 ${g.std}`}</p>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <p className="text-sm text-muted-foreground">{t("填写观察值的条件标签后可分组对比。")}</p>
                      )}
                      <p className="rounded bg-primary/5 px-3 py-2 text-sm text-primary">{analysis.verdict_hint}</p>
                      <div>
                        <p className="mb-1 text-xs font-semibold text-warning">{t("局限性（必读）")}</p>
                        <ul className="list-disc space-y-0.5 pl-5 text-xs text-muted-foreground">
                          {analysis.limitations.map((lim, i) => <li key={i}>{lim}</li>)}
                        </ul>
                      </div>
                    </CardContent>
                  </Card>
                )}

                {observations.length > 0 && (
                  <Card>
                    <CardHeader><CardTitle className="text-base">{t("观察记录（{n}）", { n: observations.length })}</CardTitle></CardHeader>
                    <CardContent>
                      <ul className="max-h-52 space-y-1 overflow-y-auto text-sm">
                        {[...observations].reverse().map((o) => (
                          <li key={o.id} className="flex items-center gap-2 border-b py-1.5 last:border-0">
                            <span className="w-24 shrink-0 text-xs text-muted-foreground">{fmtDate(o.observed_at)}</span>
                            <span className="font-semibold tabular-nums">{o.value}</span>
                            <span className="text-xs text-muted-foreground">
                              {Object.entries(o.context).map(([k, v]) => `${k}=${String(v)}`).join(" ") || "—"}
                            </span>
                            <span className="ml-auto truncate text-xs text-muted-foreground">{o.note}</span>
                          </li>
                        ))}
                      </ul>
                    </CardContent>
                  </Card>
                )}
              </>
            )}
          </div>
        </div>
      )}

      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t("新建假设")}</DialogTitle>
            <DialogDescription>{t("好的假设是可检验的：说明在什么条件下、出现什么结果。")}</DialogDescription>
          </DialogHeader>
          <div className="space-y-3">
            <div>
              <Label>{t("假设陈述 *")}</Label>
              <Textarea placeholder={t("如：我在上午学习时独立完成率更高")} value={form.statement} onChange={(e) => setForm({ ...form, statement: e.target.value })} />
            </div>
            <div>
              <Label>{t("依据 / 直觉来源")}</Label>
              <Textarea placeholder={t("为什么会有这个猜想？")} value={form.rationale} onChange={(e) => setForm({ ...form, rationale: e.target.value })} />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCreateOpen(false)}>{t("action.cancel")}</Button>
            <Button onClick={() => void create()}>{t("action.create")}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
      {ai.dialog}
    </div>
  );
}
