"use client";
/** Task Autopsy 列表页：项目卡片 + 全局改进措施追踪。 */
import * as React from "react";
import Link from "next/link";
import { toast } from "sonner";
import { Layers, Plus } from "lucide-react";
import { PageHeader, EmptyState, LoadingBlock, ErrorState, AIBanner } from "@/components/layout/shared";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input, Label, Textarea } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { post } from "@/lib/api";
import { useApi } from "@/lib/useApi";
import { useT } from "@/lib/i18n";
import { fmtDate } from "@/lib/format";
import type { Improvement, Project } from "@/lib/types";

export default function TAPage() {
  const t = useT();
  const projects = useApi<Project[]>("/ta/projects");
  const improvements = useApi<Improvement[]>("/ta/improvements");
  const [open, setOpen] = React.useState(false);
  const [form, setForm] = React.useState({ name: "", description: "" });

  const create = async () => {
    if (!form.name.trim()) return toast.error(t("请填写项目名称"));
    await post("/ta/projects", form);
    setOpen(false);
    setForm({ name: "", description: "" });
    toast.success(t("项目已创建"));
    void projects.refresh();
  };

  if (projects.loading && !projects.data) return <LoadingBlock rows={4} />;
  if (projects.error) return <ErrorState error={projects.error} onRetry={projects.refresh} />;
  const list = projects.data ?? [];

  return (
    <div>
      <AIBanner />
      <PageHeader
        title={t("任务复盘")}
        description={t("用真实的过程数据（阻塞、返工、中断）解释延期与失败，而不是事后归因于态度。")}
        actions={<Button onClick={() => setOpen(true)}><Plus /> {t("新建项目")}</Button>}
      />

      {list.length === 0 ? (
        <EmptyState icon={Layers} title={t("还没有项目")} hint={t("创建项目后添加任务、预估耗时，执行中记录每一次阻塞与返工。")} action={<Button onClick={() => setOpen(true)}><Plus /> {t("创建项目")}</Button>} />
      ) : (
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {list.map((p) => (
            <Link key={p.id} href={`/ta/detail?id=${p.id}`}>
              <Card className="h-full transition-shadow hover:shadow-md">
                <CardHeader className="pb-2">
                  <div className="flex items-start justify-between gap-2">
                    <CardTitle className="text-base">{p.name}</CardTitle>
                    <Badge variant={p.status === "active" ? "default" : p.status === "done" ? "success" : "muted"}>
                      {p.status === "active" ? t("进行中") : p.status === "done" ? t("已完成") : t("已归档")}
                    </Badge>
                  </div>
                  <CardDescription className="line-clamp-2">{p.description || t("（无描述）")}</CardDescription>
                </CardHeader>
                <CardContent className="text-xs text-muted-foreground">
                  <p>{t("开始 {x}", { x: fmtDate(p.started_at) })}{p.deadline && ` · ${t("截止 {x}", { x: fmtDate(p.deadline) })}`}</p>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      )}

      <ImprovementsSection improvements={improvements} onChanged={() => void improvements.refresh()} />

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader><DialogTitle>{t("新建项目")}</DialogTitle></DialogHeader>
          <div className="space-y-3">
            <div><Label>{t("名称 *")}</Label><Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></div>
            <div><Label>{t("描述")}</Label><Textarea value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} /></div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setOpen(false)}>{t("action.cancel")}</Button>
            <Button onClick={() => void create()}>创建</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

export function ImprovementsSection({ improvements, onChanged }: { improvements: { data: Improvement[] | null }; onChanged: () => void }) {
  const t = useT();
  const setStatus = async (id: number, status: string) => {
    const { patch } = await import("@/lib/api");
    await patch(`/ta/improvements/${id}`, { status });
    toast.success(t("改进措施状态已更新"));
    onChanged();
  };
  const list = improvements.data ?? [];
  if (list.length === 0) return null;
  return (
    <Card className="mt-8">
      <CardHeader>
        <CardTitle className="text-base">{t("改进措施追踪")}</CardTitle>
        <CardDescription>{t("从复盘中诞生的改进，追踪其后续效果")}</CardDescription>
      </CardHeader>
      <CardContent>
        <ul className="divide-y">
          {list.map((a) => (
            <li key={a.id} className="flex flex-wrap items-center gap-3 py-2.5 text-sm">
              <span className="min-w-0 flex-1">{a.action}</span>
              <select
                className="h-8 rounded-md border bg-card px-2 text-xs cursor-pointer"
                value={a.status}
                onChange={(e) => void setStatus(a.id, e.target.value)}
              >
                <option value="proposed">{t("已提出")}</option>
                <option value="trying">{t("试行中")}</option>
                <option value="adopted">{t("已采纳")}</option>
                <option value="discarded">{t("已放弃")}</option>
              </select>
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}
