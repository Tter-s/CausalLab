"use client";
/**
 * Knowledge Debt 工作区：
 * - 左：学科/知识点管理 + 交互式知识图谱（React Flow）
 * - 右：学习任务与答题记录；选中知识点后显示诊断面板（依据/置信度/备选解释/用户纠正/建议验证闭环）
 */
import * as React from "react";
import {
  Background,
  Controls,
  MarkerType,
  ReactFlow,
  type Edge,
  type Node,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { toast } from "sonner";
import { AlertTriangle, CheckCircle2, CircleDot, GraduationCap, Network, Plus, ShieldQuestion, Trash2 } from "lucide-react";
import { PageHeader, EmptyState, LoadingBlock, ErrorState, AIBanner } from "@/components/layout/shared";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input, Label, Select, Textarea } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { del, get, getWith, patch, post } from "@/lib/api";
import { useApi } from "@/lib/useApi";
import { useAICall } from "@/lib/ai-client";
import { L } from "@/lib/i18n";
import { fmtDateTime, fmtPercent } from "@/lib/format";
import type { Attempt, Diagnosis, StudyTask, Subject, Suggestion, Topic, TopicEdge } from "@/lib/types";

interface GraphOut {
  nodes: Topic[];
  edges: TopicEdge[];
  subjects: Subject[];
}

export default function KDPage() {
  const graph = useApi<GraphOut>("/kd/graph");
  const tasks = useApi<StudyTask[]>("/kd/tasks");
  const [selectedTopicId, setSelectedTopicId] = React.useState<number | null>(null);
  const [subjectForm, setSubjectForm] = React.useState({ name: "", description: "" });
  const [topicForm, setTopicForm] = React.useState({ subject_id: "", name: "", description: "" });
  const [edgeForm, setEdgeForm] = React.useState({ from: "", to: "", relation: "prerequisite" });
  const [taskForm, setTaskForm] = React.useState({ topic_id: "", title: "", question_text: "" });
  const [diag, setDiag] = React.useState<Diagnosis | null>(null);
  const [diagLoading, setDiagLoading] = React.useState(false);
  const [suggestions, setSuggestions] = React.useState<Suggestion[]>([]);
  const ai = useAICall();

  const selectedTopic = graph.data?.nodes.find((n) => n.id === selectedTopicId) ?? null;
  const topicTasks = (tasks.data ?? []).filter((t) => t.topic_id === selectedTopicId);
  const topicAttempts = useApi<Attempt[]>(selectedTopicId ? `/kd/topics/${selectedTopicId}/attempts` : null);

  React.useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const t = params.get("topic");
    if (t) setSelectedTopicId(Number(t));
  }, []);

  const selectTopic = (id: number) => {
    setSelectedTopicId(id);
    setDiag(null);
    setSuggestions([]);
    void loadDiagnosis(id);
  };

  const loadDiagnosis = async (topicId: number) => {
    const list = await getWith<Diagnosis[]>("/kd/diagnoses", { topic_id: topicId });
    setDiag(list[0] ?? null);
    if (list[0]) setSuggestions(await getWith<Suggestion[]>("/kd/suggestions", { diagnosis_id: list[0].id }));
  };

  const createSubject = async () => {
    if (!subjectForm.name.trim()) return toast.error("请填写学科名称");
    await post("/kd/subjects", subjectForm);
    setSubjectForm({ name: "", description: "" });
    toast.success("学科已创建");
    void graph.refresh();
  };

  const createTopic = async () => {
    if (!topicForm.subject_id || !topicForm.name.trim()) return toast.error("请选择学科并填写名称");
    await post("/kd/topics", { ...topicForm, subject_id: Number(topicForm.subject_id) });
    setTopicForm({ ...topicForm, name: "", description: "" });
    toast.success("知识点已创建");
    void graph.refresh();
  };

  const createEdge = async () => {
    if (!edgeForm.from || !edgeForm.to) return toast.error("请选择两个知识点");
    if (edgeForm.from === edgeForm.to) return toast.error("不能创建自依赖");
    await post("/kd/edges", {
      from_topic_id: Number(edgeForm.from),
      to_topic_id: Number(edgeForm.to),
      relation: edgeForm.relation,
    });
    toast.success("依赖关系已创建");
    void graph.refresh();
  };

  const createTask = async () => {
    if (!taskForm.topic_id || !taskForm.title.trim()) return toast.error("请选择知识点并填写标题");
    await post("/kd/tasks", { ...taskForm, topic_id: Number(taskForm.topic_id) });
    setTaskForm({ ...taskForm, title: "", question_text: "" });
    toast.success("学习任务已创建");
    void tasks.refresh();
  };

  const recordAttempt = async (taskId: number, payload: Record<string, unknown>) => {
    await post(`/kd/tasks/${taskId}/attempts`, payload);
    toast.success("答题已记录");
    void tasks.refresh();
    if (selectedTopicId) void topicAttempts.refresh();
  };

  const runDiagnosis = async () => {
    if (!selectedTopicId) return;
    setDiagLoading(true);
    try {
      // 规则诊断始终可用；AI 诊断经确认闸门
      await ai.call({
        path: "/ai/kd/diagnose",
        params: { topic_id: selectedTopicId },
        successMessage: "诊断完成（AI 分析）",
        onDone: (d) => setDiag(d as Diagnosis),
      });
    } finally {
      setDiagLoading(false);
    }
  };

  const runRuleDiagnosis = async () => {
    if (!selectedTopicId) return;
    setDiagLoading(true);
    try {
      const d = await post<Diagnosis>(`/kd/topics/${selectedTopicId}/diagnose`);
      setDiag(d);
      toast.success("规则诊断完成");
    } finally {
      setDiagLoading(false);
    }
  };

  const generateSuggestions = async () => {
    if (!diag) return;
    await ai.call({
      path: `/ai/kd/diagnoses/${diag.id}/suggestions`,
      successMessage: "已生成建议与验证任务",
      onDone: (data) => {
        const body = data as { suggestions: string[]; verification_tasks: string[] };
        void showSuggestionDialog(body);
      },
    });
  };

  const showSuggestionDialog = async (body: { suggestions: string[]; verification_tasks: string[] }) => {
    if (!diag) return;
    const content = body.suggestions.map((s, i) => `${i + 1}. ${s}`).join("\n");
    const sugg = await post<Suggestion>("/kd/suggestions", { diagnosis_id: diag.id, content });
    for (const vt of body.verification_tasks) {
      await post(`/kd/suggestions/${sugg.id}/verification-task`, { title: vt });
    }
    setSuggestions(await getWith<Suggestion[]>("/kd/suggestions", { diagnosis_id: diag.id }));
    void tasks.refresh();
  };

  const correctDiagnosis = async (category: string, note: string) => {
    if (!diag) return;
    const updated = await patch<Diagnosis>(`/kd/diagnoses/${diag.id}`, {
      corrected_category: category,
      correction_note: note,
    });
    setDiag(updated);
    toast.success("已记录你的纠正");
  };

  const verifySuggestion = async (s: Suggestion, success: boolean) => {
    const updated = await post<Suggestion>(`/kd/suggestions/${s.id}/verification-result`, {
      success,
      note: success ? "验证任务独立完成" : "验证未通过",
    });
    setSuggestions((prev) => prev.map((x) => (x.id === updated.id ? updated : x)));
    toast.success(success ? "已记录：建议有效" : "已记录：建议未生效");
    void tasks.refresh();
  };

  const spawnExperiment = async () => {
    if (!diag) return;
    try {
      const r = await post<{ experiment_id: number }>(
        `/ai/kd/diagnoses/${diag.id}/spawn-experiment?question=${encodeURIComponent(
          "间隔复习能否改善「" + (L.kdDiagCategory[diag.category] ?? diag.category) + "」？",
        )}&strategy_a=${encodeURIComponent("按间隔计划复习")}&strategy_b=${encodeURIComponent("考前集中复习")}`,
      );
      toast.success(`已在记忆实验室创建实验 #${r.experiment_id}`);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "创建实验失败");
    }
  };


  if (graph.loading && !graph.data) return <LoadingBlock rows={5} />;
  if (graph.error) return <ErrorState error={graph.error} onRetry={graph.refresh} />;

  return (
    <div>
      <AIBanner />
      <PageHeader
        title="知识债务"
        description="记录学习障碍的证据，区分概念、提取、方法、执行、迁移五类困难——不凭一次失败下结论。"
      />

      <Tabs defaultValue="graph">
        <TabsList>
          <TabsTrigger value="graph"><Network className="h-4 w-4" /> 知识图谱</TabsTrigger>
          <TabsTrigger value="tasks"><GraduationCap className="h-4 w-4" /> 学习任务与诊断</TabsTrigger>
        </TabsList>

        <TabsContent value="graph" className="grid gap-4 lg:grid-cols-3">
          <Card className="lg:col-span-2">
            <CardHeader>
              <CardTitle className="text-base">依赖关系图</CardTitle>
              <CardDescription>节点 = 知识点（红色为薄弱），箭头 = 前置依赖</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="h-96 rounded-lg border bg-card">
                <TopicGraph
                  nodes={graph.data?.nodes ?? []}
                  edges={graph.data?.edges ?? []}
                  onNodeClick={(id) => selectTopic(id)}
                  selectedId={selectedTopicId}
                />
              </div>
            </CardContent>
          </Card>
          <div className="space-y-4">
            <Card>
              <CardHeader><CardTitle className="text-base">新建学科</CardTitle></CardHeader>
              <CardContent className="space-y-3">
                <Input placeholder="学科名称，如：高等数学" value={subjectForm.name} onChange={(e) => setSubjectForm({ ...subjectForm, name: e.target.value })} />
                <Input placeholder="描述（可选）" value={subjectForm.description} onChange={(e) => setSubjectForm({ ...subjectForm, description: e.target.value })} />
                <Button size="sm" onClick={() => void createSubject()}><Plus /> 创建学科</Button>
              </CardContent>
            </Card>
            <Card>
              <CardHeader><CardTitle className="text-base">新建知识点</CardTitle></CardHeader>
              <CardContent className="space-y-3">
                <Select value={topicForm.subject_id} onChange={(e) => setTopicForm({ ...topicForm, subject_id: e.target.value })}>
                  <option value="">选择学科…</option>
                  {(graph.data?.subjects ?? []).map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
                </Select>
                <Input placeholder="知识点名称" value={topicForm.name} onChange={(e) => setTopicForm({ ...topicForm, name: e.target.value })} />
                <Input placeholder="描述（可选）" value={topicForm.description} onChange={(e) => setTopicForm({ ...topicForm, description: e.target.value })} />
                <Button size="sm" onClick={() => void createTopic()}><Plus /> 创建知识点</Button>
              </CardContent>
            </Card>
            <Card>
              <CardHeader><CardTitle className="text-base">添加依赖</CardTitle></CardHeader>
              <CardContent className="space-y-3">
                <Select value={edgeForm.from} onChange={(e) => setEdgeForm({ ...edgeForm, from: e.target.value })}>
                  <option value="">前置知识点…</option>
                  {(graph.data?.nodes ?? []).map((n) => <option key={n.id} value={n.id}>{n.name}</option>)}
                </Select>
                <Select value={edgeForm.to} onChange={(e) => setEdgeForm({ ...edgeForm, to: e.target.value })}>
                  <option value="">后续知识点…</option>
                  {(graph.data?.nodes ?? []).map((n) => <option key={n.id} value={n.id}>{n.name}</option>)}
                </Select>
                <Button size="sm" onClick={() => void createEdge()}><Plus /> 建立依赖</Button>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="tasks" className="grid gap-4 lg:grid-cols-5">
          {/* 知识点列表 */}
          <Card className="lg:col-span-1">
            <CardHeader><CardTitle className="text-base">知识点</CardTitle></CardHeader>
            <CardContent className="max-h-[32rem] space-y-1 overflow-y-auto">
              {(graph.data?.nodes ?? []).map((n) => (
                <button
                  key={n.id}
                  className={`flex w-full items-center gap-2 rounded-lg px-2.5 py-2 text-left text-sm transition-colors cursor-pointer ${
                    selectedTopicId === n.id ? "bg-primary/10 text-primary" : "hover:bg-accent"
                  }`}
                  onClick={() => selectTopic(n.id)}
                >
                  {n.status === "weak" ? (
                    <AlertTriangle className="h-3.5 w-3.5 shrink-0 text-warning" />
                  ) : (
                    <CircleDot className="h-3.5 w-3.5 shrink-0 text-muted-foreground/50" />
                  )}
                  <span className="min-w-0 flex-1 truncate">{n.name}</span>
                </button>
              ))}
              {(graph.data?.nodes ?? []).length === 0 && (
                <p className="py-6 text-center text-sm text-muted-foreground">先创建学科和知识点</p>
              )}
            </CardContent>
          </Card>

          {/* 任务与答题 */}
          <Card className="lg:col-span-2">
            <CardHeader>
              <CardTitle className="text-base">{selectedTopic ? `任务：${selectedTopic.name}` : "学习任务"}</CardTitle>
              <CardDescription>记录题目、上传解答思路，登记每次答题情况</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {selectedTopic && (
                <div className="space-y-2 rounded-lg border bg-muted/30 p-3">
                  <Input
                    placeholder="任务标题，如：手推梯度下降更新公式"
                    value={taskForm.title}
                    onChange={(e) => setTaskForm({ ...taskForm, title: e.target.value })}
                  />
                  <Textarea
                    placeholder="题目内容 / 你的解答（可选粘贴）"
                    value={taskForm.question_text}
                    onChange={(e) => setTaskForm({ ...taskForm, question_text: e.target.value })}
                  />
                  <Button size="sm" onClick={() => void createTask()}><Plus /> 添加任务</Button>
                </div>
              )}
              {!selectedTopicId && <EmptyState icon={GraduationCap} title="选择左侧知识点" hint="选择知识点后可添加学习任务并记录答题。" />}
              {selectedTopicId && (
                <div className="space-y-2">
                  {topicTasks.map((t) => (
                    <TaskRow key={t.id} task={t} onAttempt={recordAttempt} onDelete={async () => { await del(`/kd/tasks/${t.id}`); void tasks.refresh(); }} />
                  ))}
                  {topicTasks.length === 0 && <p className="py-4 text-center text-sm text-muted-foreground">该知识点还没有任务</p>}
                </div>
              )}
            </CardContent>
          </Card>

          {/* 诊断面板 */}
          <Card className="lg:col-span-2">
            <CardHeader>
              <CardTitle className="text-base">诊断面板</CardTitle>
              <CardDescription>基于答题记录的保守推断，永远可以由你纠正</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {!selectedTopicId && <EmptyState icon={ShieldQuestion} title="先选择知识点" hint="诊断需要至少一条答题记录；样本不足时系统会明确说明而不是硬下结论。" />}
              {selectedTopicId && (
                <>
                  <div className="flex flex-wrap gap-2">
                    <Button size="sm" variant="outline" disabled={diagLoading} onClick={() => void runRuleDiagnosis()}>
                      规则诊断
                    </Button>
                    <Button size="sm" disabled={diagLoading || ai.pending} onClick={() => void runDiagnosis()}>
                      AI 诊断{diagLoading || ai.pending ? "…" : ""}
                    </Button>
                  </div>
                  {diag && (
                    <DiagnosisPanel
                      diag={diag}
                      attempts={topicAttempts.data ?? []}
                      suggestions={suggestions}
                      onCorrect={correctDiagnosis}
                      onGenerateSuggestions={generateSuggestions}
                      onVerify={async (s) => {
                        const ok = window.confirm("验证任务是否通过？（确定=通过，取消=未通过）");
                        await verifySuggestion(s, ok);
                      }}
                    />
                  )}
                </>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
      {ai.dialog}
      <SuggestionCreateBridge onRef={(fn) => { showSuggestionDialogRef = fn; }} />
    </div>
  );
}

let showSuggestionDialogRef: ((b: { suggestions: string[]; verification_tasks: string[] }) => Promise<void>) | null = null;
function SuggestionCreateBridge({ onRef }: { onRef: (fn: (b: { suggestions: string[]; verification_tasks: string[] }) => Promise<void>) => void }) {
  React.useEffect(() => {
    onRef(async () => {});
  }, [onRef]);
  return null;
}

function TopicGraph({
  nodes,
  edges,
  onNodeClick,
  selectedId,
}: {
  nodes: Topic[];
  edges: TopicEdge[];
  onNodeClick: (id: number) => void;
  selectedId: number | null;
}) {
  const rfNodes: Node[] = React.useMemo(() => {
    const byDepth = new Map<number, number[]>();
    const depth = (id: number, seen = new Set<number>()): number => {
      if (seen.has(id)) return 0;
      seen.add(id);
      const incoming = edges.filter((e) => e.to_topic_id === id && e.relation === "prerequisite");
      if (incoming.length === 0) return 0;
      return 1 + Math.max(...incoming.map((e) => depth(e.from_topic_id, seen)));
    };
    for (const n of nodes) {
      const d = depth(n.id);
      byDepth.set(d, [...(byDepth.get(d) ?? []), n.id]);
    }
    return nodes.map((n) => {
      const d = depth(n.id);
      const col = byDepth.get(d)?.indexOf(n.id) ?? 0;
      const weak = n.status === "weak";
      return {
        id: String(n.id),
        position: { x: d * 230, y: col * 96 },
        data: { label: n.name },
        style: {
          background: weak ? "var(--destructive)" : selectedId === n.id ? "var(--primary)" : "var(--card)",
          color: weak ? "var(--destructive-foreground)" : selectedId === n.id ? "var(--primary-foreground)" : "var(--foreground)",
          border: "1px solid var(--border)",
          borderRadius: 10,
          padding: "8px 14px",
          fontSize: 13,
          cursor: "pointer",
        },
      };
    });
  }, [nodes, edges, selectedId]);

  const rfEdges: Edge[] = React.useMemo(
    () =>
      edges.map((e) => ({
        id: String(e.id),
        source: String(e.from_topic_id),
        target: String(e.to_topic_id),
        label: e.relation === "prerequisite" ? "前置" : "相关",
        animated: false,
        style: { stroke: "var(--muted-foreground)", opacity: 0.6 },
        labelStyle: { fontSize: 10, fill: "var(--muted-foreground)" },
        labelBgStyle: { fill: "var(--card)" },
        markerEnd: { type: MarkerType.ArrowClosed, color: "var(--muted-foreground)" },
      })),
    [edges],
  );

  if (nodes.length === 0) {
    return <EmptyState icon={Network} title="还没有知识点" hint="在右侧创建学科和知识点后，这里会自动绘制依赖图。" />;
  }

  return (
    <ReactFlow
      nodes={rfNodes}
      edges={rfEdges}
      fitView
      proOptions={{ hideAttribution: true }}
      onNodeClick={(_, node) => onNodeClick(Number(node.id))}
    >
      <Background gap={18} />
      <Controls showInteractive={false} />
    </ReactFlow>
  );
}

function TaskRow({
  task,
  onAttempt,
  onDelete,
}: {
  task: StudyTask;
  onAttempt: (taskId: number, payload: Record<string, unknown>) => Promise<void>;
  onDelete: () => Promise<void>;
}) {
  const [open, setOpen] = React.useState(false);
  const [form, setForm] = React.useState({ correct: "true", error_category: "none", independent: "false", notes: "" });

  return (
    <div className="rounded-lg border p-3">
      <div className="flex items-center gap-2">
        {task.is_verification && <Badge variant="warning">验证任务</Badge>}
        {task.verification_status === "success" && <Badge variant="success">验证通过</Badge>}
        {task.verification_status === "failure" && <Badge variant="destructive">验证失败</Badge>}
        <p className="min-w-0 flex-1 truncate text-sm font-medium">{task.title}</p>
        <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => setOpen(!open)} aria-label="记录答题">
          <CircleDot className="h-4 w-4" />
        </Button>
        <Button variant="ghost" size="icon" className="h-7 w-7 text-muted-foreground" onClick={() => void onDelete()} aria-label="删除任务">
          <Trash2 className="h-3.5 w-3.5" />
        </Button>
      </div>
      {task.question_text && <p className="mt-1 line-clamp-2 text-xs text-muted-foreground">{task.question_text}</p>}
      {open && (
        <div className="mt-3 grid grid-cols-2 gap-2 rounded-lg bg-muted/40 p-3 text-sm">
          <div>
            <Label className="text-xs">结果</Label>
            <Select value={form.correct} onChange={(e) => setForm({ ...form, correct: e.target.value })}>
              <option value="true">答对</option>
              <option value="false">答错</option>
            </Select>
          </div>
          <div>
            <Label className="text-xs">独立完成</Label>
            <Select value={form.independent} onChange={(e) => setForm({ ...form, independent: e.target.value })}>
              <option value="true">独立</option>
              <option value="false">有辅助</option>
            </Select>
          </div>
          <div className="col-span-2">
            <Label className="text-xs">错误类别（答错时）</Label>
            <Select value={form.error_category} onChange={(e) => setForm({ ...form, error_category: e.target.value })}>
              {Object.entries(L.kdErrorCategory).map(([k, v]) => (
                <option key={k} value={k}>{v}</option>
              ))}
            </Select>
          </div>
          <div className="col-span-2">
            <Input placeholder="备注（如卡在哪一步）" value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} />
          </div>
          <Button
            size="sm"
            className="col-span-2"
            onClick={async () => {
              await onAttempt(task.id, {
                correct: form.correct === "true",
                error_category: form.correct === "true" ? "none" : form.error_category,
                independent: form.independent === "true",
                notes: form.notes,
              });
              setOpen(false);
            }}
          >
            <CheckCircle2 /> 提交答题记录
          </Button>
        </div>
      )}
    </div>
  );
}

function DiagnosisPanel({
  diag,
  attempts,
  suggestions,
  onCorrect,
  onGenerateSuggestions,
  onVerify,
}: {
  diag: Diagnosis;
  attempts: Attempt[];
  suggestions: Suggestion[];
  onCorrect: (category: string, note: string) => Promise<void>;
  onGenerateSuggestions: () => Promise<void>;
  onVerify: (s: Suggestion) => Promise<void>;
}) {
  const [correctOpen, setCorrectOpen] = React.useState(false);
  const [correction, setCorrection] = React.useState({ category: "concept_gap", note: "" });
  const confidence = diag.confidence;

  return (
    <div className="space-y-3">
      <div className="rounded-lg border p-3">
        <div className="flex items-center justify-between">
          <Badge variant={diag.category === "insufficient_data" ? "muted" : "default"}>
            {L.kdDiagCategory[diag.category] ?? diag.category}
          </Badge>
          <span className="text-xs text-muted-foreground">
            {diag.source === "ai" ? "AI 诊断" : diag.source === "rule" ? "规则诊断" : "用户诊断"} · {fmtDateTime(diag.created_at)}
          </span>
        </div>
        <div className="mt-2 flex items-center gap-2">
          <div className="h-2 flex-1 overflow-hidden rounded-full bg-muted">
            <div
              className="h-full rounded-full bg-primary transition-all"
              style={{ width: `${Math.round(confidence * 100)}%` }}
            />
          </div>
          <span className="text-xs tabular-nums text-muted-foreground">置信度 {fmtPercent(confidence)}</span>
        </div>
        <p className="mt-2 whitespace-pre-wrap text-sm leading-relaxed">{diag.rationale}</p>
        <p className="mt-1 text-xs text-muted-foreground">依据 {diag.basis_attempt_count} 条答题记录</p>
        {diag.status === "user_confirmed" && diag.corrected_category && (
          <p className="mt-2 rounded bg-success/10 px-2 py-1 text-xs text-success">
            你已纠正为「{L.kdDiagCategory[diag.corrected_category] ?? diag.corrected_category}」
          </p>
        )}
      </div>

      <div className="rounded-lg border p-3">
        <p className="mb-2 text-xs font-semibold text-muted-foreground">其他可能解释</p>
        <ul className="space-y-1.5 text-sm">
          {diag.alternatives.map((a, i) => (
            <li key={i} className="flex items-start gap-2">
              <Badge variant={a.likelihood === "medium" ? "warning" : "muted"} className="mt-0.5 shrink-0">
                {a.likelihood === "medium" ? "中等可能" : a.likelihood === "high" ? "高可能" : "低可能"}
              </Badge>
              <span className="min-w-0">
                <strong>{L.kdDiagCategory[a.category] ?? a.category}</strong>
                {a.reason && <span className="text-muted-foreground"> — {a.reason}</span>}
              </span>
            </li>
          ))}
        </ul>
      </div>

      <div className="flex flex-wrap gap-2">
        <Button size="sm" variant="outline" onClick={() => setCorrectOpen(true)}>
          纠正诊断
        </Button>
        <Button size="sm" variant="outline" onClick={() => void onGenerateSuggestions()}>
          生成学习建议
        </Button>
      </div>

      {suggestions.length > 0 && (
        <div className="rounded-lg border p-3">
          <p className="mb-2 text-xs font-semibold text-muted-foreground">建议与验证闭环</p>
          <ul className="space-y-2 text-sm">
            {suggestions.map((s) => (
              <li key={s.id} className="rounded border bg-muted/30 p-2">
                <p className="whitespace-pre-wrap">{s.content}</p>
                <div className="mt-2 flex items-center gap-2">
                  <Badge variant={s.status === "effective" ? "success" : s.status === "ineffective" ? "destructive" : s.status === "testing" ? "warning" : "muted"}>
                    {s.status === "effective" ? "已验证有效" : s.status === "ineffective" ? "未生效" : s.status === "testing" ? "验证中" : "待验证"}
                  </Badge>
                  {(s.status === "open" || s.status === "testing") && (
                    <Button size="sm" variant="ghost" className="h-7" onClick={() => void onVerify(s)}>
                      提交验证结论
                    </Button>
                  )}
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}

      {attempts.length > 0 && (
        <div className="rounded-lg border p-3">
          <p className="mb-2 text-xs font-semibold text-muted-foreground">答题记录（{attempts.length}）</p>
          <ul className="max-h-44 space-y-1 overflow-y-auto text-xs">
            {[...attempts].reverse().map((a) => (
              <li key={a.id} className="flex items-center gap-2">
                {a.correct ? (
                  <CheckCircle2 className="h-3.5 w-3.5 shrink-0 text-success" />
                ) : (
                  <AlertTriangle className="h-3.5 w-3.5 shrink-0 text-destructive" />
                )}
                <span>{fmtDateTime(a.occurred_at)}</span>
                <span className="text-muted-foreground">
                  {a.correct ? "答对" : `答错·${L.kdErrorCategory[a.error_category] ?? a.error_category}`} · {a.independent ? "独立" : "有辅助"}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}

      <Dialog open={correctOpen} onOpenChange={setCorrectOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>纠正诊断</DialogTitle>
            <DialogDescription>你的纠正会被记录为证据，帮助系统更贴近真实情况。</DialogDescription>
          </DialogHeader>
          <div className="space-y-3">
            <div>
              <Label>正确类别</Label>
              <Select value={correction.category} onChange={(e) => setCorrection({ ...correction, category: e.target.value })}>
                {Object.entries(L.kdDiagCategory).map(([k, v]) => (
                  <option key={k} value={k}>{v}</option>
                ))}
              </Select>
            </div>
            <div>
              <Label>纠正理由</Label>
              <Textarea placeholder="例如：看答案能懂，是提取失败不是概念问题" value={correction.note} onChange={(e) => setCorrection({ ...correction, note: e.target.value })} />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCorrectOpen(false)}>取消</Button>
            <Button
              onClick={async () => {
                await onCorrect(correction.category, correction.note);
                setCorrectOpen(false);
              }}
            >
              提交纠正
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
