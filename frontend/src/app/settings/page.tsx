"use client";
/** 设置：AI 服务（Provider/Key/预算/隐私）、数据管理（导出/导入/演示/清空）、外观。 */
import * as React from "react";
import { toast } from "sonner";
import { Database, KeyRound, Plug, ShieldCheck, Trash2 } from "lucide-react";
import { PageHeader, ConfirmDialog } from "@/components/layout/shared";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input, Label, Select } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { del, get, post, put } from "@/lib/api";
import { useApi } from "@/lib/useApi";
import { useTheme } from "next-themes";
import { fmtDateTime } from "@/lib/format";
import { useT } from "@/lib/i18n";
import type { AIConfig, UsageSummary } from "@/lib/types";

const PROVIDER_KEYS = ["none", "deepseek", "mimo", "moonshot", "openai-compat", "mock"] as const;

export default function SettingsPage() {
  const t = useT();
  const cfg = useApi<AIConfig>("/settings/ai");
  const usage = useApi<UsageSummary>("/settings/ai/usage");
  const { theme, setTheme } = useTheme();
  const [form, setForm] = React.useState({
    provider: "none",
    base_url: "",
    api_key: "",
    model_id: "",
    temperature: "0.4",
    max_tokens: "2048",
    timeout_seconds: "60",
    monthly_budget: "20",
    auto_confirm_send: false,
    price_prompt_per_m: "2",
    price_completion_per_m: "8",
  });
  const [testing, setTesting] = React.useState(false);
  const [wipeOpen, setWipeOpen] = React.useState(false);
  const [demoOpen, setDemoOpen] = React.useState(false);

  React.useEffect(() => {
    if (cfg.data) {
      setForm({
        provider: cfg.data.provider,
        base_url: cfg.data.base_url,
        api_key: "",
        model_id: cfg.data.model_id,
        temperature: cfg.data.temperature?.toString() ?? "",
        max_tokens: String(cfg.data.max_tokens),
        timeout_seconds: String(cfg.data.timeout_seconds),
        monthly_budget: String(cfg.data.monthly_budget),
        auto_confirm_send: cfg.data.auto_confirm_send,
        price_prompt_per_m: String(cfg.data.price_prompt_per_m),
        price_completion_per_m: String(cfg.data.price_completion_per_m),
      });
    }
  }, [cfg.data]);

  const save = async () => {
    await put("/settings/ai", {
      provider: form.provider,
      base_url: form.base_url,
      api_key: form.api_key || null,
      model_id: form.model_id,
      temperature: form.temperature === "" ? null : Number(form.temperature),
      max_tokens: Number(form.max_tokens) || 2048,
      timeout_seconds: Number(form.timeout_seconds) || 60,
      monthly_budget: Number(form.monthly_budget) || 0,
      auto_confirm_send: form.auto_confirm_send,
      price_prompt_per_m: Number(form.price_prompt_per_m) || 2,
      price_completion_per_m: Number(form.price_completion_per_m) || 8,
    });
    toast.success(t("AI 设置已保存"));
    void cfg.refresh();
  };

  const testConnection = async () => {
    setTesting(true);
    try {
      const r = await post<{ ok: boolean; error?: string; provider?: string; latency_ms?: number }>("/settings/ai/test");
      if (r.ok) toast.success(t("连接成功：{p}，{ms}ms", { p: r.provider ?? "?", ms: r.latency_ms ?? 0 }));
      else toast.error(t("连接失败：{e}", { e: r.error ?? "?" }));
    } finally {
      setTesting(false);
    }
  };

  const exportAll = async () => {
    const data = await get<Record<string, unknown>>("/data/export");
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `causalab-export-${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
    URL.revokeObjectURL(url);
    toast.success(t("导出完成"));
  };

  const importAll = async (file: File) => {
    const text = await file.text();
    try {
      const data = JSON.parse(text);
      await post("/data/import", data);
      toast.success(t("导入完成（全量替换）"));
    } catch (e) {
      toast.error(e instanceof Error ? e.message : t("导入失败：文件格式不正确"));
    }
  };

  const exportCsv = async (path: string, name: string) => {
    const res = await fetch(`/api${path}`);
    const text = await res.text();
    const blob = new Blob(["\ufeff" + text], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = name;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div>
      <PageHeader title={t("设置")} description={t("AI 服务、数据管理与外观。")} />

      <Tabs defaultValue="ai">
        <TabsList>
          <TabsTrigger value="ai"><Plug className="h-4 w-4" /> {t("AI 服务")}</TabsTrigger>
          <TabsTrigger value="data"><Database className="h-4 w-4" /> {t("数据管理")}</TabsTrigger>
          <TabsTrigger value="appearance">{t("外观")}</TabsTrigger>
        </TabsList>

        <TabsContent value="ai" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base"><KeyRound className="h-4 w-4" /> {t("Provider 配置")}</CardTitle>
              <CardDescription>
                {t("所有 AI 请求经本服务端代理；API Key 加密存储在本机，绝不回传前端或出现在日志中。")}
                {cfg.data && cfg.data.api_key_masked && (
                  <span className="ml-1">{t("当前 Key：")}<code className="rounded bg-muted px-1">{cfg.data.api_key_masked}</code></span>
                )}
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-4 md:grid-cols-2">
                <div>
                  <Label>{t("Provider")}</Label>
                  <Select value={form.provider} onChange={(e) => setForm({ ...form, provider: e.target.value })}>
                    {PROVIDER_KEYS.map((v) => <option key={v} value={v}>{t("provider." + v)}</option>)}
                  </Select>
                </div>
                <div>
                  <Label>{t("API Base URL")}</Label>
                  <Input placeholder={t("如 https://api.deepseek.com")} value={form.base_url} onChange={(e) => setForm({ ...form, base_url: e.target.value })} />
                </div>
                <div>
                  <Label>{t("API Key")}{cfg.data?.api_key_masked ? t("（留空保持不变）") : ""}</Label>
                  <Input type="password" placeholder="sk-…" value={form.api_key} onChange={(e) => setForm({ ...form, api_key: e.target.value })} />
                </div>
                <div>
                  <Label>{t("模型 ID（不硬编码，按服务商文档填写）")}</Label>
                  <Input placeholder={t("如 deepseek-chat")} value={form.model_id} onChange={(e) => setForm({ ...form, model_id: e.target.value })} />
                </div>
                <div>
                  <Label>{t("Temperature")}</Label>
                  <Input type="number" min={0} max={2} step={0.1} value={form.temperature} onChange={(e) => setForm({ ...form, temperature: e.target.value })} />
                </div>
                <div>
                  <Label>{t("最大输出 Token")}</Label>
                  <Input type="number" min={64} max={65536} value={form.max_tokens} onChange={(e) => setForm({ ...form, max_tokens: e.target.value })} />
                </div>
                <div>
                  <Label>{t("请求超时（秒）")}</Label>
                  <Input type="number" min={5} max={600} value={form.timeout_seconds} onChange={(e) => setForm({ ...form, timeout_seconds: e.target.value })} />
                </div>
                <div>
                  <Label>{t("每月预算上限（元，0 = 不设限）")}</Label>
                  <Input type="number" min={0} value={form.monthly_budget} onChange={(e) => setForm({ ...form, monthly_budget: e.target.value })} />
                </div>
                <div>
                  <Label>{t("Prompt 价格（元/百万 token，用于费用估算）")}</Label>
                  <Input type="number" min={0} step={0.1} value={form.price_prompt_per_m} onChange={(e) => setForm({ ...form, price_prompt_per_m: e.target.value })} />
                </div>
                <div>
                  <Label>{t("输出价格（元/百万 token）")}</Label>
                  <Input type="number" min={0} step={0.1} value={form.price_completion_per_m} onChange={(e) => setForm({ ...form, price_completion_per_m: e.target.value })} />
                </div>
              </div>
              <div className="flex items-center justify-between rounded-lg border p-3">
                <div>
                  <p className="flex items-center gap-1.5 text-sm font-medium"><ShieldCheck className="h-4 w-4" /> {t("自动确认发送")}</p>
                  <p className="text-xs text-muted-foreground">{t("关闭时，每次向云端模型发送内容前都会弹出预览让你确认（默认，推荐）。")}</p>
                </div>
                <Switch checked={form.auto_confirm_send} onCheckedChange={(v) => setForm({ ...form, auto_confirm_send: v })} />
              </div>
              <div className="flex flex-wrap gap-2">
                <Button onClick={() => void save()}>{t("保存设置")}</Button>
                <Button variant="outline" disabled={testing} onClick={() => void testConnection()}>
                  {testing ? t("测试中…") : t("测试连接")}
                </Button>
              </div>
            </CardContent>
          </Card>

          <UsageCard usage={usage} budget={Number(form.monthly_budget) || 0} />
        </TabsContent>

        <TabsContent value="data" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">{t("导出")}</CardTitle>
              <CardDescription>{t("你的数据属于你。JSON 为全量备份，CSV 用于表格分析。")}</CardDescription>
            </CardHeader>
            <CardContent className="flex flex-wrap gap-2">
              <Button variant="outline" onClick={() => void exportAll()}>{t("导出全部数据（JSON）")}</Button>
              <Button variant="outline" onClick={() => void exportCsv("/data/export/kd-attempts.csv", "causalab-attempts.csv")}>{t("导出答题记录（CSV）")}</Button>
              <Button variant="outline" onClick={() => void exportCsv("/data/export/ml-reviews.csv", "causalab-reviews.csv")}>{t("导出复习记录（CSV）")}</Button>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">{t("导入")}</CardTitle>
              <CardDescription>{t("只接受本应用导出的 JSON 文件；导入会替换当前全部业务数据（设置保留）。")}</CardDescription>
            </CardHeader>
            <CardContent>
              <Input type="file" accept=".json" onChange={(e) => { const f = e.target.files?.[0]; if (f) void importAll(f); }} />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">{t("演示数据")}</CardTitle>
              <CardDescription>{t("载入一套标记为 Demo 的示例数据，用于快速了解产品；随时可清除。")}</CardDescription>
            </CardHeader>
            <CardContent className="flex flex-wrap gap-2">
              <Button variant="outline" onClick={() => setDemoOpen(true)}>{t("载入演示数据")}</Button>
              <Button variant="destructive" onClick={() => setWipeOpen(true)}><Trash2 /> {t("清空全部业务数据")}</Button>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="appearance">
          <Card>
            <CardHeader><CardTitle className="text-base">{t("主题")}</CardTitle></CardHeader>
            <CardContent>
              <Select value={theme ?? "system"} onChange={(e) => setTheme(e.target.value as string)} className="max-w-48">
                <option value="light">{t("浅色")}</option>
                <option value="dark">{t("深色")}</option>
                <option value="system">{t("跟随系统")}</option>
              </Select>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      <ConfirmDialog
        open={wipeOpen}
        onOpenChange={setWipeOpen}
        title={t("清空全部业务数据？")}
        description={t("决策、任务、卡片、答题记录、事件等将被永久删除（AI 设置保留）。此操作不可撤销，建议先导出备份。")}
        confirmText={t("永久删除")}
        destructive
        onConfirm={async () => {
          await del("/data/all");
          toast.success(t("已清空全部业务数据"));
          window.location.reload();
        }}
      />
      <ConfirmDialog
        open={demoOpen}
        onOpenChange={setDemoOpen}
        title={t("载入演示数据？")}
        description={t("将先清空当前业务数据，再载入一套标记为 Demo 的示例数据。")}
        confirmText={t("载入演示数据")}
        onConfirm={async () => {
          await post("/data/demo");
          toast.success(t("演示数据已载入"));
          window.location.href = "/";
        }}
      />
    </div>
  );
}

function UsageCard({ usage, budget }: { usage: { data: UsageSummary | null; loading: boolean }; budget: number }) {
  const t = useT();
  if (usage.loading && !usage.data) return null;
  const u = usage.data;
  if (!u) return null;
  const overBudget = budget > 0 && u.total_cost >= budget;
  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between space-y-0">
        <div>
          <CardTitle className="text-base">{t("本月用量（{m}）", { m: u.month })}</CardTitle>
          <CardDescription>
            {t("{n} 次调用 · 输入 {a} tokens · 输出 {b} tokens", { n: u.total_calls, a: u.total_prompt_tokens.toLocaleString(), b: u.total_completion_tokens.toLocaleString() })}
          </CardDescription>
        </div>
        <Badge variant={overBudget ? "destructive" : u.total_cost > 0 ? "warning" : "muted"}>
          估算费用 ¥{u.total_cost.toFixed(4)}{budget > 0 && ` / ${t("预算")} ¥${budget}`}
        </Badge>
      </CardHeader>
      <CardContent>
        {u.rows.length === 0 ? (
          <p className="py-4 text-center text-sm text-muted-foreground">{t("本月还没有 AI 调用记录。")}</p>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>{t("时间")}</TableHead>
                <TableHead>{t("任务")}</TableHead>
                <TableHead>{t("模型")}</TableHead>
                <TableHead className="text-right">Tokens</TableHead>
                <TableHead className="text-right">{t("费用")}</TableHead>
                <TableHead className="text-right">{t("耗时")}</TableHead>
                <TableHead className="text-right">{t("状态")}</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {u.rows.slice(0, 20).map((r) => (
                <TableRow key={r.id}>
                  <TableCell className="text-xs">{fmtDateTime(r.created_at)}</TableCell>
                  <TableCell className="text-xs">{r.task_type}</TableCell>
                  <TableCell className="text-xs">{r.provider}/{r.model}</TableCell>
                  <TableCell className="text-right text-xs tabular-nums">{r.prompt_tokens}/{r.completion_tokens}</TableCell>
                  <TableCell className="text-right text-xs tabular-nums">¥{r.cost_estimated.toFixed(4)}</TableCell>
                  <TableCell className="text-right text-xs tabular-nums">{r.latency_ms}ms</TableCell>
                  <TableCell className="text-right">
                    <Badge variant={r.ok ? "success" : "destructive"}>{r.ok ? t("成功") : t("失败")}</Badge>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  );
}
