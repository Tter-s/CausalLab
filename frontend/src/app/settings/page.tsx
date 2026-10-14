"use client";
/** 设置：AI 服务（Provider/Key/预算/隐私）、数据管理（导出/导入/演示/清空）、外观。 */
import * as React from "react";
import { toast } from "sonner";
import { Database, KeyRound, LogOut, Plug, ShieldCheck, ShieldOff, Trash2 } from "lucide-react";
import { PageHeader, ConfirmDialog } from "@/components/layout/shared";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input, Label, Select } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { apiUrl, del, get, post, put } from "@/lib/api";
import { useApi } from "@/lib/useApi";
import { useTheme } from "next-themes";
import { fmtDateTime } from "@/lib/format";
import { useT } from "@/lib/i18n";
import type { AuthStatus } from "@/lib/types";
import type { AIConfig, UsageSummary } from "@/lib/types";

const PROVIDER_KEYS = ["none", "deepseek", "mimo", "moonshot", "openai-compat", "mock"] as const;

/**
 * 可按任务类型单独指定模型的任务清单（与后端 ai/config.py 的 task_type 取值一一对应）。
 * 后端 get_provider(db, task_type) 会用这里的覆盖值；留空表示沿用全局默认模型。
 */
const AI_TASK_TYPES = [
  { key: "kd_diagnosis", label: "知识诊断" },
  { key: "kd_suggestion", label: "学习建议" },
  { key: "ta_review", label: "项目复盘" },
  { key: "dtm_review", label: "决策复盘" },
  { key: "dtm_counterfactual", label: "反事实推演" },
  { key: "hyp_design", label: "实验设计" },
  { key: "loop_review", label: "循环复盘" },
  { key: "general", label: "通用" },
] as const;

interface TaskModelRow {
  task_type: string;
  model_id: string;
  temperature: string;
}

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
    task_models: AI_TASK_TYPES.map((tt) => ({ task_type: tt.key, model_id: "", temperature: "" })) as TaskModelRow[],
  });
  const [testing, setTesting] = React.useState(false);
  const [wipeOpen, setWipeOpen] = React.useState(false);
  const [demoOpen, setDemoOpen] = React.useState(false);
  const authStatus = useApi<AuthStatus>("/auth/status");
  const [secForm, setSecForm] = React.useState({ newPassword: "", confirm: "", oldPassword: "" });
  const [secBusy, setSecBusy] = React.useState(false);

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
        // 把已保存的覆盖合并进固定行，保证界面上始终能看到全部任务类型
        task_models: AI_TASK_TYPES.map((tt) => {
          const found = cfg.data!.task_models.find((m) => m.task_type === tt.key);
          return {
            task_type: tt.key,
            model_id: found?.model_id ?? "",
            temperature: found?.temperature != null ? String(found.temperature) : "",
          };
        }),
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
      // 只提交填了模型名的行；留空的行等于「沿用默认模型」
      task_models: form.task_models
        .filter((m) => m.model_id.trim() !== "")
        .map((m) => ({
          task_type: m.task_type,
          model_id: m.model_id.trim(),
          temperature: m.temperature === "" ? null : Number(m.temperature),
        })),
    });
    toast.success(t("AI 设置已保存"));
    void cfg.refresh();
  };

  const enableProtection = async () => {
    if (secForm.newPassword.length < 6) { toast.error(t("密码至少 6 位。")); return; }
    if (secForm.newPassword !== secForm.confirm) { toast.error(t("两次输入的密码不一致。")); return; }
    setSecBusy(true);
    try {
      await post("/auth/setup", { password: secForm.newPassword });
      toast.success(t("密码保护已启用。"));
      setSecForm({ newPassword: "", confirm: "", oldPassword: "" });
      void authStatus.refresh();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : t("操作失败"));
    } finally { setSecBusy(false); }
  };

  const changePassword = async () => {
    if (secForm.newPassword.length < 6) { toast.error(t("密码至少 6 位。")); return; }
    if (secForm.newPassword !== secForm.confirm) { toast.error(t("两次输入的密码不一致。")); return; }
    setSecBusy(true);
    try {
      await post("/auth/change-password", { old_password: secForm.oldPassword, new_password: secForm.newPassword });
      toast.success(t("密码已修改。"));
      setSecForm({ newPassword: "", confirm: "", oldPassword: "" });
    } catch (e) {
      toast.error(e instanceof Error ? e.message : t("操作失败"));
    } finally { setSecBusy(false); }
  };

  const disableProtection = async () => {
    if (!secForm.oldPassword) { toast.error(t("请输入当前密码以确认。")); return; }
    setSecBusy(true);
    try {
      await post("/auth/disable", { password: secForm.oldPassword });
      toast.success(t("密码保护已关闭。"));
      setSecForm({ newPassword: "", confirm: "", oldPassword: "" });
      void authStatus.refresh();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : t("操作失败"));
    } finally { setSecBusy(false); }
  };

  const logout = async () => {
    await post("/auth/logout").catch(() => undefined);
    // 刻意整页跳转：登出必须清空全部客户端内存状态（软导航会保留路由缓存）
    // eslint-disable-next-line @next/next/no-location-assign-relative-destination
    window.location.href = "/login";
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
    const res = await fetch(apiUrl(path));
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
          <TabsTrigger value="security"><ShieldCheck className="h-4 w-4" /> {t("安全")}</TabsTrigger>
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
              <p className="text-xs text-muted-foreground">
                {t("参考价（DeepSeek 官方，2026-10 查询）：deepseek-flash 输入缓存未命中 ¥1/百万（高峰 ¥2），输出 ¥4/百万（高峰 ¥8）；缓存命中与空闲时段更便宜。费用估算按高峰价计，偏保守。")}
              </p>
              {/* 按任务类型指定模型（可选）：具体任务可用更便宜的模型，复杂任务手动切换 */}
              <div className="space-y-3 rounded-lg border p-3">
                <div>
                  <p className="text-sm font-medium">{t("按任务类型指定模型（可选）")}</p>
                  <p className="text-xs text-muted-foreground">
                    {t("简单任务可用更低成本的模型，复杂任务可手动切换；留空的任务类型沿用上面的默认模型。")}
                  </p>
                </div>
                <div className="space-y-2">
                  {form.task_models.map((row, idx) => (
                    <div key={row.task_type} className="grid grid-cols-12 items-center gap-2">
                      <span className="col-span-3 truncate text-sm text-muted-foreground">
                        {t(AI_TASK_TYPES[idx].label)}
                      </span>
                      <Input
                        className="col-span-5"
                        placeholder={t("模型 ID，如 deepseek-chat")}
                        value={row.model_id}
                        onChange={(e) => {
                          const next = [...form.task_models];
                          next[idx] = { ...row, model_id: e.target.value };
                          setForm({ ...form, task_models: next });
                        }}
                      />
                      <Input
                        className="col-span-4"
                        type="number"
                        min={0}
                        max={2}
                        step={0.1}
                        placeholder={t("Temperature（留空用默认）")}
                        value={row.temperature}
                        onChange={(e) => {
                          const next = [...form.task_models];
                          next[idx] = { ...row, temperature: e.target.value };
                          setForm({ ...form, task_models: next });
                        }}
                      />
                    </div>
                  ))}
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

          <UsageCard usage={usage} budget={Number(form.monthly_budget) || 0} onCleared={() => usage.refresh()} />
        </TabsContent>

        <TabsContent value="security" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base"><ShieldCheck className="h-4 w-4" /> {t("登录密码保护")}</CardTitle>
              <CardDescription>
                {authStatus.data?.enabled
                  ? t("已启用：所有 API 访问需要登录（会话 30 天有效）。适合把 CausaLab 暴露到局域网/公网时使用。")
                  : t("未启用：默认本机单人模式，打开即用。若要把 CausaLab 暴露到局域网/公网，建议启用密码保护。")}
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {!authStatus.data?.enabled ? (
                <div className="max-w-sm space-y-3">
                  <div>
                    <Label>{t("设置密码（至少 6 位）")}</Label>
                    <Input type="password" value={secForm.newPassword} onChange={(e) => setSecForm({ ...secForm, newPassword: e.target.value })} />
                  </div>
                  <div>
                    <Label>{t("确认密码")}</Label>
                    <Input type="password" value={secForm.confirm} onChange={(e) => setSecForm({ ...secForm, confirm: e.target.value })} />
                  </div>
                  <Button disabled={secBusy} onClick={() => void enableProtection()}>
                    <ShieldCheck /> {t("启用密码保护")}
                  </Button>
                </div>
              ) : (
                <div className="max-w-sm space-y-5">
                  <div className="flex items-center gap-2">
                    <Badge variant="success">{t("已启用")}</Badge>
                    <Button variant="outline" size="sm" onClick={() => void logout()}>
                      <LogOut /> {t("退出登录")}
                    </Button>
                  </div>
                  <div className="space-y-3 rounded-lg border p-4">
                    <p className="text-sm font-medium">{t("修改密码")}</p>
                    <div>
                      <Label className="text-xs">{t("当前密码")}</Label>
                      <Input type="password" value={secForm.oldPassword} onChange={(e) => setSecForm({ ...secForm, oldPassword: e.target.value })} />
                    </div>
                    <div>
                      <Label className="text-xs">{t("新密码（至少 6 位）")}</Label>
                      <Input type="password" value={secForm.newPassword} onChange={(e) => setSecForm({ ...secForm, newPassword: e.target.value })} />
                    </div>
                    <div>
                      <Label className="text-xs">{t("确认新密码")}</Label>
                      <Input type="password" value={secForm.confirm} onChange={(e) => setSecForm({ ...secForm, confirm: e.target.value })} />
                    </div>
                    <Button size="sm" disabled={secBusy} onClick={() => void changePassword()}>{t("修改密码")}</Button>
                  </div>
                  <div className="space-y-3 rounded-lg border border-destructive/30 p-4">
                    <p className="flex items-center gap-1.5 text-sm font-medium text-destructive"><ShieldOff className="h-4 w-4" /> {t("关闭密码保护")}</p>
                    <p className="text-xs text-muted-foreground">{t("关闭后任何人都可以直接访问（包括通过网络的访问）。")}</p>
                    <div>
                      <Input type="password" placeholder={t("当前密码")} value={secForm.oldPassword} onChange={(e) => setSecForm({ ...secForm, oldPassword: e.target.value })} />
                    </div>
                    <Button variant="destructive" size="sm" disabled={secBusy} onClick={() => void disableProtection()}>
                      {t("确认关闭")}
                    </Button>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
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
          // 刻意整页刷新：清空所有客户端内存状态，避免各页缓存旧数据
          // eslint-disable-next-line @next/next/no-location-assign-relative-destination
          window.location.href = "/";
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
          // 刻意整页跳转：载入演示数据后从干净状态重建所有页面
          // eslint-disable-next-line @next/next/no-location-assign-relative-destination
          window.location.href = "/";
        }}
      />
    </div>
  );
}

function UsageCard({
  usage,
  budget,
  onCleared,
}: {
  usage: { data: UsageSummary | null; loading: boolean };
  budget: number;
  onCleared: () => Promise<void> | void;
}) {
  const t = useT();
  const [clearOpen, setClearOpen] = React.useState(false);
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
        <div className="flex items-center gap-2">
          {u.rows.length > 0 && (
            <Button variant="outline" onClick={() => setClearOpen(true)}><Trash2 /> {t("清空记录")}</Button>
          )}
          <Badge variant={overBudget ? "destructive" : u.total_cost > 0 ? "warning" : "muted"}>
            估算费用 ¥{u.total_cost.toFixed(4)}{budget > 0 && ` / ${t("预算")} ¥${budget}`}
          </Badge>
        </div>
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
      <ConfirmDialog
        open={clearOpen}
        onOpenChange={setClearOpen}
        title={t("清空全部用量记录？")}
        description={t("所有 API 调用日志与累计费用将被删除（AI 配置与业务数据不受影响）。此操作不可撤销。")}
        confirmText={t("清空")}
        destructive
        onConfirm={async () => {
          await del("/settings/ai/usage");
          toast.success(t("用量记录已清空"));
          await onCleared();
        }}
      />
    </Card>
  );
}
