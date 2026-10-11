"use client";
/** 改进循环：发现问题 → 提出假设 → 设计干预 → 执行 → 收集数据 → 复盘 → 修改策略。 */
import * as React from "react";
import { toast } from "sonner";
import { ArrowRight, Plus, Repeat, Sparkles } from "lucide-react";
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
import { fmtDateTime } from "@/lib/format";
import type { Hypothesis, Loop, LoopStageItem } from "@/lib/types";
import { cn } from "@/lib/utils";

const STAGES = ["observe", "hypothesize", "intervene", "measure", "review", "adjust"] as const;

export default function LoopsPage() {
  const t = useT();
  const L = useL();
  const loops = useApi<Loop[]>("/loops");
  const hypotheses = useApi<Hypothesis[]>("/hypotheses");
  const ai = useAICall();
  const [createOpen, setCreateOpen] = React.useState(false);
  const [form, setForm] = React.useState({ title: "", problem: "" });
  const [stageLoopId, setStageLoopId] = React.useState<number | null>(null);
  const [stages, setStages] = React.useState<LoopStageItem[]>([]);
  const [stageForm, setStageForm] = React.useState({
    stage: "hypothesize",
    hypothesis_id: "",
    intervention: "",
    content_note: "",
  });
  const [reviewResult, setReviewResult] = React.useState<{ verdict: string; reasoning: string; next_strategy: string[] } | null>(null);

  const selectedLoop = (loops.data ?? []).find((l) => l.id === stageLoopId) ?? null;

  const create = async () => {
    if (!form.title.trim()) return toast.error(t("请填写循环标题"));
    await post("/loops", form);
    setCreateOpen(false);
    setForm({ title: "", problem: "" });
    toast.success(t("改进循环已开启"));
    void loops.refresh();
  };

  const openStages = async (loopId: number) => {
    setStageLoopId(loopId);
    setStages(await get<LoopStageItem[]>(`/loops/${loopId}/stages`));
  };

  const advance = async () => {
    if (!selectedLoop) return;
    const content: Record<string, unknown> = {};
    if (stageForm.hypothesis_id) content.hypothesis_id = Number(stageForm.hypothesis_id);
    if (stageForm.intervention) content.intervention = stageForm.intervention;
    if (stageForm.content_note) content.note = stageForm.content_note;
    await post(`/loops/${selectedLoop.id}/stages`, { stage: stageForm.stage, content });
    toast.success(t("已推进到「{stage}」", { stage: L.loopStage[stageForm.stage] }));
    setStages(await get<LoopStageItem[]>(`/loops/${selectedLoop.id}/stages`));
    void loops.refresh();
  };

  const runAIReview = async () => {
    if (!selectedLoop) return;
    await ai.call({
      path: `/ai/loops/${selectedLoop.id}/review`,
      successMessage: t("AI 循环复盘已生成"),
      onDone: (data) => {
        setReviewResult(data as { verdict: string; reasoning: string; next_strategy: string[] });
        void loops.refresh();
      },
    });
  };

  const closeLoop = async (loop: Loop, verdict: string) => {
    await patch(`/loops/${loop.id}`, { status: "closed", verdict });
    toast.success(t("循环已关闭"));
    void loops.refresh();
  };

  if (loops.loading && !loops.data) return <LoadingBlock rows={4} />;
  if (loops.error) return <ErrorState error={loops.error} onRetry={loops.refresh} />;
  const list = loops.data ?? [];
  const active = list.filter((l) => l.status === "active");
  const closed = list.filter((l) => l.status === "closed");

  return (
    <div>
      <AIBanner />
      <PageHeader
        title={t("改进循环")}
        description={t("发现问题 → 提出假设 → 设计干预 → 执行 → 收集数据 → 复盘 → 修改策略。这是可操作的产品流程，不是流程图。")}
        actions={<Button onClick={() => setCreateOpen(true)}><Plus /> {t("开启循环")}</Button>}
      />

      {list.length === 0 ? (
        <EmptyState icon={Repeat} title={t("还没有改进循环")} hint={t("从一个具体的问题开始，比如做题总是分心。")} action={<Button onClick={() => setCreateOpen(true)}><Plus /> {t("开启第一个循环")}</Button>} />
      ) : (
        <div className="space-y-8">
          <div>
            <h2 className="mb-3 text-sm font-semibold text-muted-foreground">{t("进行中（{n}）", { n: active.length })}</h2>
            <div className="grid gap-3 lg:grid-cols-2">
              {active.map((l) => (
                <Card key={l.id} className="cursor-pointer transition-shadow hover:shadow-md" onClick={() => void openStages(l.id)}>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-base">{l.title}</CardTitle>
                    <CardDescription className="line-clamp-2">{l.problem}</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <StageProgress current={l.current_stage} />
                  </CardContent>
                </Card>
              ))}
              {active.length === 0 && <p className="text-sm text-muted-foreground">{t("没有进行中的循环。")}</p>}
            </div>
          </div>

          {closed.length > 0 && (
            <div>
              <h2 className="mb-3 text-sm font-semibold text-muted-foreground">{t("已关闭")}</h2>
              <div className="grid gap-3 lg:grid-cols-2">
                {closed.map((l) => (
                  <Card key={l.id} className="cursor-pointer opacity-75" onClick={() => void openStages(l.id)}>
                    <CardHeader className="pb-2">
                      <div className="flex items-center justify-between gap-2">
                        <CardTitle className="text-base">{l.title}</CardTitle>
                        <Badge variant={l.verdict === "effective" ? "success" : l.verdict === "ineffective" ? "destructive" : "warning"}>
                          {l.verdict === "effective" ? t("有效") : l.verdict === "ineffective" ? t("无效") : t("不确定")}
                        </Badge>
                      </div>
                    </CardHeader>
                    <CardContent><StageProgress current="adjust" /></CardContent>
                  </Card>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      <Dialog open={stageLoopId !== null} onOpenChange={(v) => { if (!v) { setStageLoopId(null); setReviewResult(null); } }}>
        <DialogContent wide>
          {selectedLoop && (
            <>
              <DialogHeader>
                <DialogTitle>{selectedLoop.title}</DialogTitle>
                <DialogDescription>{selectedLoop.problem}</DialogDescription>
              </DialogHeader>

              <div className="max-h-[52vh] space-y-3 overflow-y-auto pr-1">
                <StageProgress current={selectedLoop.current_stage} large />
                {stages.map((s) => (
                  <div key={s.id} className="rounded-lg border p-3 text-sm">
                    <div className="flex items-center justify-between">
                      <Badge>{L.loopStage[s.stage] ?? s.stage}</Badge>
                      <span className="text-xs text-muted-foreground">{fmtDateTime(s.entered_at)}</span>
                    </div>
                    <pre className="mt-1.5 whitespace-pre-wrap text-muted-foreground">{JSON.stringify(s.content, null, 2)}</pre>
                  </div>
                ))}
              </div>

              {selectedLoop.status === "active" && (
                <div className="mt-4 space-y-3 rounded-lg border bg-muted/30 p-4">
                  <p className="text-sm font-medium">{t("推进到下一阶段")}</p>
                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <Label className="text-xs">{t("目标阶段")}</Label>
                      <Select value={stageForm.stage} onChange={(e) => setStageForm({ ...stageForm, stage: e.target.value })}>
                        {STAGES.map((s) => <option key={s} value={s}>{L.loopStage[s]}</option>)}
                      </Select>
                    </div>
                    <div>
                      <Label className="text-xs">{t("关联假设（可选）")}</Label>
                      <Select value={stageForm.hypothesis_id} onChange={(e) => setStageForm({ ...stageForm, hypothesis_id: e.target.value })}>
                        <option value="">{t("不关联")}</option>
                        {(hypotheses.data ?? []).map((h) => <option key={h.id} value={h.id}>{h.statement.slice(0, 30)}…</option>)}
                      </Select>
                    </div>
                  </div>
                  {(stageForm.stage === "intervene" || stageForm.stage === "measure") && (
                    <div>
                      <Label className="text-xs">{t("干预措施 / 记录内容")}</Label>
                      <Textarea rows={2} value={stageForm.intervention} onChange={(e) => setStageForm({ ...stageForm, intervention: e.target.value })} />
                    </div>
                  )}
                  <div>
                    <Label className="text-xs">{t("备注（可选）")}</Label>
                    <Input value={stageForm.content_note} onChange={(e) => setStageForm({ ...stageForm, content_note: e.target.value })} />
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <Button size="sm" onClick={() => void advance()}><ArrowRight /> {t("推进")}</Button>
                    <Button size="sm" variant="outline" disabled={ai.pending} onClick={() => void runAIReview()}>
                      <Sparkles /> {t("AI 复盘判断")}{ai.pending ? "…" : ""}
                    </Button>
                  </div>
                  {reviewResult && (
                    <div className="rounded-lg border border-primary/25 bg-primary/5 p-3 text-sm">
                      <p className="font-semibold text-primary">
                        结论：{reviewResult.verdict === "effective" ? t("有效") : reviewResult.verdict === "ineffective" ? t("无效") : t("证据不足（不确定）")}
                      </p>
                      <p className="mt-1 text-muted-foreground">{reviewResult.reasoning}</p>
                      {reviewResult.next_strategy.length > 0 && (
                        <ul className="mt-1.5 list-disc pl-5 text-muted-foreground">
                          {reviewResult.next_strategy.map((s, i) => <li key={i}>{s}</li>)}
                        </ul>
                      )}
                    </div>
                  )}
                  <div className="flex gap-2 border-t pt-3">
                    <Button size="sm" variant="outline" onClick={() => void closeLoop(selectedLoop, "effective")}>{t("关闭：有效")}</Button>
                    <Button size="sm" variant="outline" onClick={() => void closeLoop(selectedLoop, "ineffective")}>{t("关闭：无效")}</Button>
                    <Button size="sm" variant="outline" onClick={() => void closeLoop(selectedLoop, "uncertain")}>{t("关闭：不确定")}</Button>
                  </div>
                </div>
              )}
            </>
          )}
        </DialogContent>
      </Dialog>

      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t("开启改进循环")}</DialogTitle>
            <DialogDescription>{t("从一个具体、可观察的问题开始。")}</DialogDescription>
          </DialogHeader>
          <div className="space-y-3">
            <div><Label>{t("标题 *")}</Label><Input placeholder={t("如：减少刷题时的分心")} value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} /></div>
            <div><Label>{t("问题描述")}</Label><Textarea placeholder={t("具体表现是什么？什么时候发生？")} value={form.problem} onChange={(e) => setForm({ ...form, problem: e.target.value })} /></div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCreateOpen(false)}>{t("action.cancel")}</Button>
            <Button onClick={() => void create()}>{t("开启循环")}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
      {ai.dialog}
    </div>
  );
}

function StageProgress({ current, large = false }: { current: string; large?: boolean }) {
  const L = useL();
  const idx = STAGES.indexOf(current as (typeof STAGES)[number]);
  return (
    <div className="flex items-center gap-1">
      {STAGES.map((s, i) => (
        <React.Fragment key={s}>
          <span
            className={cn(
              "rounded-full px-2 py-0.5 text-[10px] font-medium whitespace-nowrap",
              i < idx ? "bg-success/15 text-success" : i === idx ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground",
              large && "px-2.5 py-1 text-xs",
            )}
          >
            {L.loopStage[s]}
          </span>
          {i < STAGES.length - 1 && <span className="h-px w-2 shrink-0 bg-border" />}
        </React.Fragment>
      ))}
    </div>
  );
}
