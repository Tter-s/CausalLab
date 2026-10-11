"use client";
/** Evidence Timeline：跨模块统一事件流，可按模块筛选、按天分组，点开查看证据与关联。 */
import * as React from "react";
import Link from "next/link";
import { Timer } from "lucide-react";
import { PageHeader, EmptyState, LoadingBlock, ErrorState, EvidenceBadge } from "@/components/layout/shared";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { getWith } from "@/lib/api";
import { useL, useT } from "@/lib/i18n";
import { dayKey, dayLabel, fmtDateTime } from "@/lib/format";
import type { EvidenceItem, EventItem, EventPage, EntityLinkItem } from "@/lib/types";
import { cn } from "@/lib/utils";

const MODULES: { id: string; key: string }[] = [
  { id: "", key: "全部" },
  { id: "kd", key: "kd" },
  { id: "ml", key: "ml" },
  { id: "dtm", key: "dtm" },
  { id: "ta", key: "ta" },
  { id: "hyp", key: "hyp" },
  { id: "loop", key: "loop" },
  { id: "sys", key: "sys" },
];

const PAGE_SIZE = 30;

function eventHref(e: EventItem): string {
  if (e.module === "dtm") return `/dtm/${e.ref_id}`;
  if (e.module === "kd") return `/kd?topic=${e.ref_id}`;
  if (e.module === "ta") return e.ref_type === "project" ? `/ta/${e.ref_id}` : "/ta";
  if (e.module === "ml") return "/ml";
  if (e.module === "hyp") return "/hypotheses";
  if (e.module === "loop") return "/loops";
  return "/timeline";
}

export default function TimelinePage() {
  const t = useT();
  const L = useL();
  const [module, setModule] = React.useState("");
  const [q, setQ] = React.useState("");
  const [query, setQuery] = React.useState("");
  const [items, setItems] = React.useState<EventItem[]>([]);
  const [total, setTotal] = React.useState(0);
  const [hasMore, setHasMore] = React.useState(false);
  const [cursor, setCursor] = React.useState<{ at: string; id: number } | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [loadingMore, setLoadingMore] = React.useState(false);
  const [error, setError] = React.useState<Error | null>(null);
  const [selected, setSelected] = React.useState<EventItem | null>(null);
  const [evidence, setEvidence] = React.useState<EvidenceItem[]>([]);
  const [links, setLinks] = React.useState<EntityLinkItem[]>([]);

  const load = React.useCallback(
    async (mode: "reset" | "more") => {
      const params: Record<string, string | number> = { limit: PAGE_SIZE };
      if (module) params.module = module;
      if (query) params.q = query;
      if (mode === "more" && cursor) {
        params.before_at = cursor.at;
        params.before_id = cursor.id;
      }
      try {
        if (mode === "reset") setLoading(true);
        else setLoadingMore(true);
        setError(null);
        const page = await getWith<EventPage>("/timeline", params);
        setTotal(page.total);
        setHasMore(page.has_more);
        setCursor(
          page.has_more && page.next_before_at && page.next_before_id != null
            ? { at: page.next_before_at, id: page.next_before_id }
            : null,
        );
        setItems((prev) => (mode === "more" ? [...prev, ...page.items] : page.items));
      } catch (e) {
        setError(e as Error);
      } finally {
        setLoading(false);
        setLoadingMore(false);
      }
    },
    [module, query, cursor],
  );

  React.useEffect(() => {
    void load("reset");
  }, [module, query, load]);

  const openEvent = async (e: EventItem) => {
    setSelected(e);
    try {
      const [ev, ln] = await Promise.all([
        getWith<EvidenceItem[]>("/evidence", { module: e.module, ref_type: e.ref_type, ref_id: e.ref_id }),
        getWith<EntityLinkItem[]>("/links", { module: e.module, ref_type: e.ref_type, ref_id: e.ref_id }),
      ]);
      setEvidence(ev);
      setLinks(ln);
    } catch {
      setEvidence([]);
      setLinks([]);
    }
  };

  const groups = React.useMemo(() => {
    const map = new Map<string, EventItem[]>();
    for (const e of items) {
      const k = dayKey(e.occurred_at);
      map.set(k, [...(map.get(k) ?? []), e]);
    }
    return [...map.entries()].sort((a, b) => b[0].localeCompare(a[0]));
  }, [items]);

  return (
    <div>
      <PageHeader
        title={t("证据时间线")}
        description={t("一个判断是在什么时候、依据什么形成的？后来出现了哪些新证据？判断为什么变化？")}
      />

      <div className="mb-4 flex flex-wrap items-center gap-2">
        {MODULES.map((m) => (
          <Button
            key={m.id}
            size="sm"
            variant={module === m.id ? "default" : "outline"}
            onClick={() => setModule(m.id)}
          >
            {m.id ? L.module[m.id] : t("全部")}
          </Button>
        ))}
        <form
          className="ml-auto flex gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            setQuery(q);
          }}
        >
          <input
            className="h-8 w-52 rounded-md border bg-card px-3 text-sm outline-none focus:ring-2 focus:ring-ring/50"
            placeholder={t("搜索事件标题…")}
            value={q}
            onChange={(e) => setQ(e.target.value)}
          />
          <Button size="sm" type="submit">{t("action.search")}</Button>
        </form>
      </div>

      {loading && items.length === 0 ? (
        <LoadingBlock rows={6} />
      ) : error ? (
        <ErrorState error={error} onRetry={() => void load("reset")} />
      ) : groups.length === 0 ? (
        <EmptyState icon={Timer} title={t("没有匹配的事件")} hint={t("换一个筛选条件，或先在其他模块产生一些记录。")} />
      ) : (
        <div className="space-y-6">
          {hasMore && (
            <div className="flex justify-center pt-2">
              <Button variant="outline" disabled={loadingMore} onClick={() => void load("more")}>
                {loadingMore ? t("state.loading") : t("加载更多")}
              </Button>
            </div>
          )}
          {!hasMore && items.length > 0 && (
            <p className="pt-2 text-center text-xs text-muted-foreground">{t("已加载全部 {n} 条", { n: total })}</p>
          )}
          {groups.map(([day, evs]) => (
            <div key={day}>
              <p className="mb-2 text-xs font-semibold text-muted-foreground">{dayLabel(day)}</p>
              <div className="relative ml-2 space-y-2 border-l pl-5">
                {evs.map((e) => (
                  <button
                    key={e.id}
                    className="block w-full text-left"
                    onClick={() => void openEvent(e)}
                  >
                    <Card className="transition-shadow hover:shadow-md">
                      <CardContent className="flex items-center gap-3 p-3.5">
                        <span className={cn("h-2.5 w-2.5 shrink-0 rounded-full",
                          e.importance >= 3 ? "bg-destructive" : e.importance === 2 ? "bg-primary" : "bg-muted-foreground/40")} />
                        <span className="min-w-0 flex-1">
                          <span className="block truncate text-sm">{e.title}</span>
                          <span className="text-xs text-muted-foreground">{fmtDateTime(e.occurred_at)}</span>
                        </span>
                        <Badge variant="muted" className="shrink-0">{L.module[e.module] ?? e.module}</Badge>
                      </CardContent>
                    </Card>
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {selected && (
        <div className="fixed inset-0 z-50" onClick={() => setSelected(null)}>
          <div className="absolute inset-0 bg-black/50" />
          <div
            className="absolute right-0 top-0 h-full w-full max-w-md overflow-y-auto border-l bg-card p-6 shadow-xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="mb-4 flex items-start justify-between gap-3">
              <div>
                <Badge variant="muted">{L.module[selected.module] ?? selected.module}</Badge>
                <h2 className="mt-2 font-semibold leading-snug">{selected.title}</h2>
                <p className="mt-1 text-xs text-muted-foreground">{fmtDateTime(selected.occurred_at)}</p>
              </div>
              <Button variant="ghost" size="icon" onClick={() => setSelected(null)}>×</Button>
            </div>
            {Object.keys(selected.detail).length > 0 && (
              <pre className="mb-4 overflow-x-auto whitespace-pre-wrap rounded-lg bg-muted/40 p-3 text-xs">
                {JSON.stringify(selected.detail, null, 2)}
              </pre>
            )}

            <h3 className="mb-2 text-sm font-semibold">{t("证据记录")}</h3>
            {evidence.length === 0 && <p className="mb-4 text-sm text-muted-foreground">{t("暂无证据记录")}</p>}
            <ul className="mb-6 space-y-2">
              {evidence.map((ev) => (
                <li key={ev.id} className="rounded-lg border p-3 text-sm">
                  <div className="mb-1 flex items-center gap-2">
                    <EvidenceBadge kind={ev.kind} />
                    {ev.confidence !== null && <span className="text-xs text-muted-foreground">{t("可信度 {p}", { p: Math.round(ev.confidence * 100) + "%" })}</span>}
                    <span className="text-xs text-muted-foreground">{ev.source}</span>
                  </div>
                  <p className="text-muted-foreground">{ev.content}</p>
                </li>
              ))}
            </ul>

            <h3 className="mb-2 text-sm font-semibold">{t("跨模块关联")}</h3>
            {links.length === 0 && <p className="text-sm text-muted-foreground">{t("暂无关联")}</p>}
            <ul className="space-y-1.5">
              {links.map((ln) => (
                <li key={ln.id} className="flex items-center gap-2 rounded-lg border px-3 py-2 text-sm">
                  <span className="text-xs text-muted-foreground">
                    {L.module[ln.from_module]}#{ln.from_ref_id} → {L.module[ln.to_module]}#{ln.to_ref_id}
                  </span>
                  <Badge variant="outline" className="ml-auto text-[10px]">{ln.relation}</Badge>
                </li>
              ))}
            </ul>

            <Link
              href={eventHref(selected)}
              className="mt-6 block rounded-lg bg-primary px-4 py-2.5 text-center text-sm font-medium text-primary-foreground hover:bg-primary/90"
              onClick={() => setSelected(null)}
            >
              {t("打开源模块查看完整上下文")}
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}
