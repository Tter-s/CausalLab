"use client";
/**
 * Memory Laboratory：卡组与卡片管理、主动回忆复习会话、遗忘/复习统计、策略对照实验。
 */
import * as React from "react";
import { toast } from "sonner";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip as ChartTooltip,
  XAxis,
  YAxis,
} from "recharts";
import { BrainCircuit, Eye, EyeOff, FlaskConical, Plus, RefreshCcw, Trash2 } from "lucide-react";
import { PageHeader, EmptyState, LoadingBlock, ErrorState, AIBanner } from "@/components/layout/shared";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input, Label, Select, Textarea } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { del, get, getWith, patch, post } from "@/lib/api";
import { useApi } from "@/lib/useApi";
import { fmtDate, fmtPercent } from "@/lib/format";
import type { CardItem, Deck, DueQueue, Experiment, ExperimentResults, MLStats, ReviewResult } from "@/lib/types";

export default function MLPage() {
  const stats = useApi<MLStats>("/ml/stats");
  const decks = useApi<Deck[]>("/ml/decks");
  const due = useApi<DueQueue>("/ml/due?limit=20");
  const experiments = useApi<Experiment[]>("/ml/experiments");
  const [deckForm, setDeckForm] = React.useState({ name: "", description: "" });
  const [cardForm, setCardForm] = React.useState({ deck_id: "", front: "", back: "", tags: "" });
  const [cards, setCards] = React.useState<CardItem[]>([]);
  const [cardsDeck, setCardsDeck] = React.useState<string>("");

  React.useEffect(() => {
    const url = cardsDeck ? `/ml/cards?deck_id=${cardsDeck}` : "/ml/cards";
    void get<CardItem[]>(url).then(setCards).catch(() => setCards([]));
  }, [cardsDeck]);

  const createDeck = async () => {
    if (!deckForm.name.trim()) return toast.error("请填写卡组名称");
    await post("/ml/decks", deckForm);
    setDeckForm({ name: "", description: "" });
    toast.success("卡组已创建");
    void decks.refresh();
  };

  const createCard = async () => {
    if (!cardForm.deck_id || !cardForm.front.trim()) return toast.error("请选择卡组并填写卡片正面");
    await post("/ml/cards", {
      deck_id: Number(cardForm.deck_id),
      front: cardForm.front,
      back: cardForm.back,
      tags: cardForm.tags ? cardForm.tags.split(/[,,]/).map((t) => t.trim()).filter(Boolean) : [],
    });
    setCardForm({ ...cardForm, front: "", back: "" });
    toast.success("卡片已创建，立即可复习");
    void due.refresh();
    void stats.refresh();
  };

  return (
    <div>
      <AIBanner />
      <PageHeader title="记忆实验室" description="用自己的数据检验记忆策略：主动回忆 + FSRS 间隔调度 + 对照实验。" />

      <Tabs defaultValue="review">
        <TabsList>
          <TabsTrigger value="review"><BrainCircuit className="h-4 w-4" /> 复习</TabsTrigger>
          <TabsTrigger value="cards">卡片管理</TabsTrigger>
          <TabsTrigger value="stats">统计</TabsTrigger>
          <TabsTrigger value="experiments"><FlaskConical className="h-4 w-4" /> 对照实验</TabsTrigger>
        </TabsList>

        <TabsContent value="review">
          <ReviewSession due={due} onReviewed={() => { void due.refresh(); void stats.refresh(); }} />
        </TabsContent>

        <TabsContent value="cards" className="grid gap-4 lg:grid-cols-3">
          <Card>
            <CardHeader><CardTitle className="text-base">新建卡组</CardTitle></CardHeader>
            <CardContent className="space-y-3">
              <Input placeholder="卡组名称" value={deckForm.name} onChange={(e) => setDeckForm({ ...deckForm, name: e.target.value })} />
              <Input placeholder="描述（可选）" value={deckForm.description} onChange={(e) => setDeckForm({ ...deckForm, description: e.target.value })} />
              <Button size="sm" onClick={() => void createDeck()}><Plus /> 创建</Button>
              <div className="pt-2">
                <p className="mb-1.5 text-xs font-medium text-muted-foreground">已有卡组</p>
                <ul className="space-y-1 text-sm">
                  {(decks.data ?? []).map((d) => (
                    <li key={d.id} className="flex items-center justify-between rounded px-2 py-1 hover:bg-accent">
                      <span>{d.name}</span>
                      <Button variant="ghost" size="icon" className="h-6 w-6 text-muted-foreground" onClick={async () => { await del(`/ml/decks/${d.id}`); void decks.refresh(); }}>
                        <Trash2 className="h-3 w-3" />
                      </Button>
                    </li>
                  ))}
                </ul>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle className="text-base">新建卡片</CardTitle></CardHeader>
            <CardContent className="space-y-3">
              <Select value={cardForm.deck_id} onChange={(e) => setCardForm({ ...cardForm, deck_id: e.target.value })}>
                <option value="">选择卡组…</option>
                {(decks.data ?? []).map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
              </Select>
              <Textarea placeholder="正面（问题/提示）" value={cardForm.front} onChange={(e) => setCardForm({ ...cardForm, front: e.target.value })} />
              <Textarea placeholder="背面（答案）" value={cardForm.back} onChange={(e) => setCardForm({ ...cardForm, back: e.target.value })} />
              <Input placeholder="标签（逗号分隔，可选）" value={cardForm.tags} onChange={(e) => setCardForm({ ...cardForm, tags: e.target.value })} />
              <Button size="sm" onClick={() => void createCard()}><Plus /> 添加卡片</Button>
            </CardContent>
          </Card>

          <Card className="lg:col-span-1">
            <CardHeader className="flex-row items-center justify-between space-y-0">
              <CardTitle className="text-base">卡片列表</CardTitle>
              <Select className="h-8 w-32 text-xs" value={cardsDeck} onChange={(e) => setCardsDeck(e.target.value)}>
                <option value="">全部卡组</option>
                {(decks.data ?? []).map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
              </Select>
            </CardHeader>
            <CardContent className="max-h-[28rem] space-y-2 overflow-y-auto">
              {cards.map((c) => (
                <div key={c.id} className="rounded-lg border p-2.5 text-sm">
                  <div className="flex items-start justify-between gap-2">
                    <p className="min-w-0 flex-1 font-medium">{c.front}</p>
                    <Button variant="ghost" size="icon" className="h-6 w-6 shrink-0 text-muted-foreground" onClick={async () => { await del(`/ml/cards/${c.id}`); setCards((prev) => prev.filter((x) => x.id !== c.id)); void due.refresh(); }}>
                      <Trash2 className="h-3 w-3" />
                    </Button>
                  </div>
                  <p className="mt-0.5 text-muted-foreground">{c.back}</p>
                  {c.state && (
                    <p className="mt-1.5 text-xs text-muted-foreground">
                      {c.state.reps > 0 ? `已复习 ${c.state.reps} 次 · 下次 ${fmtDate(c.state.due_at)}` : "未复习 · 立即可复习"}
                    </p>
                  )}
                </div>
              ))}
              {cards.length === 0 && <p className="py-6 text-center text-sm text-muted-foreground">还没有卡片</p>}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="stats">
          <StatsPanel stats={stats} />
        </TabsContent>

        <TabsContent value="experiments">
          <ExperimentsPanel experiments={experiments} decks={decks.data ?? []} cards={cards} onChanged={() => { void experiments.refresh(); void due.refresh(); }} />
        </TabsContent>
      </Tabs>
    </div>
  );
}

function ReviewSession({ due, onReviewed }: { due: { data: DueQueue | null; loading: boolean; refresh: () => Promise<void> }; onReviewed: () => void }) {
  const [index, setIndex] = React.useState(0);
  const [revealed, setRevealed] = React.useState(false);
  const [shownAt, setShownAt] = React.useState(0); // 客户端挂载后设置，避免预渲染期间读时钟
  const [intervals, setIntervals] = React.useState<Record<number, string> | null>(null);
  const [busy, setBusy] = React.useState(false);

  React.useEffect(() => {
    setShownAt(Date.now());
  }, []);

  const cards = due.data?.cards ?? [];
  const card = cards[index];

  React.useEffect(() => {
    setRevealed(false);
    setIntervals(null);
    setShownAt(Date.now());
  }, [index, card?.id]);

  if (due.loading && !due.data) return <LoadingBlock rows={2} />;
  if (!card) {
    return (
      <EmptyState
        icon={BrainCircuit}
        title="当前没有到期卡片"
        hint="全部卡片都在计划的间隔上。新建卡片或稍后再来。"
        action={<Button variant="outline" size="sm" onClick={() => void due.refresh()}><RefreshCcw /> 刷新队列</Button>}
      />
    );
  }

  const review = async (rating: number) => {
    setBusy(true);
    try {
      const r = await post<ReviewResult>("/ml/reviews", {
        card_id: card.id,
        rating,
        duration_ms: Date.now() - shownAt,
      });
      toast.success(`已记录：下次 ${r.interval_display} 后复习`);
      onReviewed();
      if (index + 1 < cards.length) setIndex(index + 1);
      else { setIndex(0); await due.refresh(); }
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="mx-auto max-w-2xl">
      <div className="mb-3 flex items-center justify-between text-sm text-muted-foreground">
        <span>队列中还有 {Math.max(0, (due.data?.total_due ?? 0))} 张到期</span>
        <span>{index + 1} / {cards.length}</span>
      </div>
      <Card className="min-h-72">
        <CardContent className="flex min-h-72 flex-col items-center justify-center p-8 text-center">
          <p className="text-xl font-semibold">{card.front}</p>
          {revealed ? (
            <div className="mt-6 rounded-lg bg-muted/50 px-6 py-4">
              <p className="whitespace-pre-wrap text-lg">{card.back}</p>
            </div>
          ) : (
            <p className="mt-6 text-sm text-muted-foreground">先在心里回忆答案，再点击显示</p>
          )}
          {!revealed ? (
            <Button className="mt-8" size="lg" onClick={() => { setRevealed(true); void getIntervals(card.id).then(setIntervals); }}>
              <Eye /> 显示答案
            </Button>
          ) : (
            <div className="mt-8 grid w-full grid-cols-2 gap-2 sm:grid-cols-4">
              {[
                { r: 1, label: "忘记了", key: "1" },
                { r: 2, label: "想起来了", key: "2" },
                { r: 3, label: "有点费劲", key: "3" },
                { r: 4, label: "很轻松", key: "4" },
              ].map(({ r, label }) => (
                <Button key={r} variant={r === 1 ? "destructive" : r === 4 ? "default" : "outline"} disabled={busy} onClick={() => void review(r)}>
                  {label}
                  {intervals?.[r] && <span className="block text-[11px] opacity-70">{intervals[r]}</span>}
                </Button>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
      <p className="mt-3 text-center text-xs text-muted-foreground">
        评分 1=完全忘记 2=勉强想起 3=想起但费劲 4=轻松想起；间隔由 FSRS-6 算法按你的记忆状态计算。
      </p>
    </div>
  );
}

async function getIntervals(cardId: number): Promise<Record<number, string>> {
  try {
    return await get<Record<number, string>>(`/ml/cards/${cardId}/preview`);
  } catch {
    return {};
  }
}

function StatsPanel({ stats }: { stats: { data: MLStats | null; loading: boolean; error: Error | null; refresh: () => Promise<void> } }) {
  if (stats.loading && !stats.data) return <LoadingBlock rows={4} />;
  if (stats.error) return <ErrorState error={stats.error} onRetry={stats.refresh} />;
  const s = stats.data;
  if (!s) return null;
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Card>
        <CardHeader>
          <CardTitle className="text-base">每日复习次数（近 14 天）</CardTitle>
        </CardHeader>
        <CardContent className="h-60">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={s.reviews_per_day} margin={{ top: 4, right: 8, left: -22, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-border" vertical={false} />
              <XAxis dataKey="date" tickFormatter={(v: string) => v.slice(5)} tick={{ fontSize: 11 }} tickLine={false} axisLine={false} />
              <YAxis tick={{ fontSize: 11 }} tickLine={false} axisLine={false} allowDecimals={false} />
              <ChartTooltip contentStyle={{ background: "var(--card)", border: "1px solid var(--border)", borderRadius: 8, fontSize: 12 }} />
              <Bar dataKey="count" name="复习次数" fill="var(--chart-1)" radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle className="text-base">记忆状态分布</CardTitle>
          <CardDescription>
            共 {s.total_cards} 张 · 到期 {s.due_now} · 近 7 天复习 {s.reviews_last_7d} 次
            {s.retention_7d !== null && ` · 顺利回忆率 ${fmtPercent(s.retention_7d)}`}
            {s.again_rate_7d !== null && ` · 遗忘率 ${fmtPercent(s.again_rate_7d)}`}
          </CardDescription>
        </CardHeader>
        <CardContent className="h-60">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={s.interval_distribution} layout="vertical" margin={{ top: 4, right: 16, left: 30, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-border" horizontal={false} />
              <XAxis type="number" tick={{ fontSize: 11 }} tickLine={false} axisLine={false} allowDecimals={false} />
              <YAxis type="category" dataKey="label" tick={{ fontSize: 11 }} tickLine={false} axisLine={false} width={64} />
              <ChartTooltip contentStyle={{ background: "var(--card)", border: "1px solid var(--border)", borderRadius: 8, fontSize: 12 }} />
              <Bar dataKey="count" name="卡片数" fill="var(--chart-2)" radius={[0, 3, 3, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>
      <Card className="lg:col-span-2">
        <CardHeader>
          <CardTitle className="text-base">成熟度</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-6 text-sm">
          <div><span className="text-2xl font-bold tabular-nums">{s.maturity.new ?? 0}</span><p className="text-muted-foreground">新卡</p></div>
          <div><span className="text-2xl font-bold tabular-nums">{s.maturity.learning ?? 0}</span><p className="text-muted-foreground">学习中</p></div>
          <div><span className="text-2xl font-bold tabular-nums">{s.maturity.review ?? 0}</span><p className="text-muted-foreground">已进入复习循环</p></div>
        </CardContent>
      </Card>
    </div>
  );
}

function ExperimentsPanel({
  experiments,
  decks,
  cards,
  onChanged,
}: {
  experiments: { data: Experiment[] | null; loading: boolean; refresh: () => Promise<void> };
  decks: Deck[];
  cards: CardItem[];
  onChanged: () => void;
}) {
  const [form, setForm] = React.useState({ question: "", strategy_a: "", strategy_b: "", delayed_test_days: 7 });
  const [assignExpId, setAssignExpId] = React.useState<number | null>(null);
  const [selected, setSelected] = React.useState<number[]>([]);
  const [results, setResults] = React.useState<Record<number, ExperimentResults>>({});

  const create = async () => {
    if (!form.question.trim() || !form.strategy_a.trim() || !form.strategy_b.trim()) return toast.error("请填写实验问题与两种策略");
    await post("/ml/experiments", { ...form, metric: "retention" });
    setForm({ question: "", strategy_a: "", strategy_b: "", delayed_test_days: 7 });
    toast.success("实验已创建，下一步选择卡片随机分组");
    void experiments.refresh();
  };

  const loadResults = async (id: number) => {
    const r = await get<ExperimentResults>(`/ml/experiments/${id}/results`);
    setResults((prev) => ({ ...prev, [id]: r }));
  };

  const assign = async (expId: number) => {
    if (selected.length < 2) return toast.error("至少选择 2 张卡片");
    await post(`/ml/experiments/${expId}/assign`, { card_ids: selected });
    toast.success(`已随机分组 ${selected.length} 张卡片`);
    setSelected([]);
    setAssignExpId(null);
    onChanged();
    void loadResults(expId);
  };

  if (experiments.loading && !experiments.data) return <LoadingBlock rows={3} />;
  const list = experiments.data ?? [];

  return (
    <div className="grid gap-4 lg:grid-cols-3">
      <Card>
        <CardHeader>
          <CardTitle className="text-base">新建对照实验</CardTitle>
          <CardDescription>服务端随机分组；结果只代表你个人的参考证据。</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div>
            <Label>实验问题</Label>
            <Textarea placeholder="如：间隔复习 vs 集中复习，48 小时后谁记得牢？" value={form.question} onChange={(e) => setForm({ ...form, question: e.target.value })} />
          </div>
          <div>
            <Label>策略 A</Label>
            <Input placeholder="如：每天复习一次" value={form.strategy_a} onChange={(e) => setForm({ ...form, strategy_a: e.target.value })} />
          </div>
          <div>
            <Label>策略 B</Label>
            <Input placeholder="如：考前集中复习" value={form.strategy_b} onChange={(e) => setForm({ ...form, strategy_b: e.target.value })} />
          </div>
          <div>
            <Label>延迟测试天数</Label>
            <Input type="number" min={1} max={365} value={form.delayed_test_days} onChange={(e) => setForm({ ...form, delayed_test_days: Number(e.target.value) })} />
          </div>
          <Button size="sm" onClick={() => void create()}><Plus /> 创建实验</Button>
        </CardContent>
      </Card>

      <div className="space-y-4 lg:col-span-2">
        {list.length === 0 && <EmptyState icon={FlaskConical} title="还没有实验" hint="创建实验后选择一组卡片，系统会随机分成 A/B 两组。" />}
        {list.map((e) => {
          const r = results[e.id];
          return (
            <Card key={e.id}>
              <CardHeader className="flex-row items-start justify-between space-y-0">
                <div>
                  <CardTitle className="text-base">{e.question}</CardTitle>
                  <CardDescription className="mt-1">
                    A：{e.strategy_a} · B：{e.strategy_b} · 状态：
                    <Badge variant={e.status === "running" ? "default" : e.status === "completed" ? "success" : "muted"} className="ml-1">
                      {e.status === "running" ? "进行中" : e.status === "completed" ? "已完成" : "准备中"}
                    </Badge>
                  </CardDescription>
                </div>
                <div className="flex shrink-0 gap-2">
                  <Button size="sm" variant="outline" onClick={() => { setAssignExpId(e.id); setSelected([]); }}>选择卡片分组</Button>
                  <Button size="sm" variant="ghost" onClick={() => void loadResults(e.id)}>查看结果</Button>
                </div>
              </CardHeader>
              {assignExpId === e.id && (
                <CardContent className="border-t pt-4">
                  <div className="mb-2 flex items-center justify-between">
                    <p className="text-sm text-muted-foreground">勾选参与实验的卡片（≥2 张，将随机均分）</p>
                    <Button size="sm" onClick={() => void assign(e.id)}>随机分组</Button>
                  </div>
                  <div className="grid max-h-48 grid-cols-1 gap-1.5 overflow-y-auto sm:grid-cols-2">
                    {(decks.length > 0 ? cards : []).map((c) => (
                      <label key={c.id} className="flex items-center gap-2 rounded border px-2.5 py-1.5 text-sm hover:bg-accent">
                        <input
                          type="checkbox"
                          checked={selected.includes(c.id)}
                          onChange={(ev) => setSelected((prev) => (ev.target.checked ? [...prev, c.id] : prev.filter((x) => x !== c.id)))}
                        />
                        <span className="min-w-0 flex-1 truncate">{c.front}</span>
                      </label>
                    ))}
                    {cards.length === 0 && <p className="text-sm text-muted-foreground">先在「卡片管理」中创建卡片</p>}
                  </div>
                </CardContent>
              )}
              {r && (
                <CardContent className="border-t pt-4">
                  <div className="grid gap-3 sm:grid-cols-2">
                    {r.groups.map((g) => (
                      <div key={g.name} className="rounded-lg border p-3 text-sm">
                        <p className="font-semibold">组 {g.name}：{g.strategy}</p>
                        <ul className="mt-1.5 space-y-0.5 text-muted-foreground">
                          <li>卡片数：{g.n_cards}</li>
                          <li>复习次数：{g.n_reviews}</li>
                          <li>遗忘率：{g.again_rate === null ? "暂无数据" : fmtPercent(g.again_rate, 1)}</li>
                          <li>平均回忆用时：{g.mean_duration_ms === null ? "—" : `${(g.mean_duration_ms / 1000).toFixed(1)}s`}</li>
                        </ul>
                      </div>
                    ))}
                  </div>
                  {r.difference_note && <p className="mt-3 text-sm">{r.difference_note}</p>}
                  <p className="mt-2 rounded bg-warning/10 px-3 py-2 text-xs leading-relaxed text-warning">{r.disclaimer}</p>
                </CardContent>
              )}
            </Card>
          );
        })}
      </div>
    </div>
  );
}
