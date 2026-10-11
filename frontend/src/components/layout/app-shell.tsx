"use client";
import * as React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useTheme } from "next-themes";
import {
  Activity,
  BrainCircuit,
  CalendarClock,
  FlaskConical,
  GraduationCap,
  Layers,
  Menu,
  Moon,
  Search,
  Settings,
  Sun,
  Timer,
  X,
} from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { getWith } from "@/lib/api";
import type { SearchOut } from "@/lib/types";
import { I18nProvider, useI18n, useL, useT } from "@/lib/i18n";
import { cn } from "@/lib/utils";

const NAV = [
  { href: "/", key: "nav.dashboard", icon: Activity },
  { href: "/kd", key: "nav.kd", icon: GraduationCap },
  { href: "/ml", key: "nav.ml", icon: BrainCircuit },
  { href: "/dtm", key: "nav.dtm", icon: CalendarClock },
  { href: "/ta", key: "nav.ta", icon: Layers },
  { href: "/timeline", key: "nav.timeline", icon: Timer },
  { href: "/hypotheses", key: "nav.hypotheses", icon: FlaskConical },
  { href: "/loops", key: "nav.loops", icon: FlaskConical },
  { href: "/settings", key: "nav.settings", icon: Settings },
];

function SidebarNav({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();
  const t = useT();
  return (
    <nav className="flex flex-col gap-1 px-3">
      {NAV.map(({ href, key, icon: Icon }) => {
        const active = href === "/" ? pathname === "/" : pathname.startsWith(href);
        return (
          <Link
            key={href}
            href={href}
            onClick={onNavigate}
            className={cn(
              "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
              active
                ? "bg-primary/10 text-primary"
                : "text-sidebar-foreground/80 hover:bg-accent hover:text-accent-foreground",
            )}
          >
            <Icon className="h-4 w-4 shrink-0" />
            {t(key)}
          </Link>
        );
      })}
    </nav>
  );
}

function SearchDialog({ open, onOpenChange }: { open: boolean; onOpenChange: (v: boolean) => void }) {
  const t = useT();
  const L = useL();
  const [q, setQ] = React.useState("");
  const [results, setResults] = React.useState<SearchOut | null>(null);
  const [busy, setBusy] = React.useState(false);

  React.useEffect(() => {
    if (!open) {
      setQ("");
      setResults(null);
    }
  }, [open]);

  React.useEffect(() => {
    if (!q.trim()) {
      setResults(null);
      return;
    }
    const timer = setTimeout(async () => {
      setBusy(true);
      try {
        setResults(await getWith<SearchOut>("/search", { q }));
      } catch {
        setResults(null);
      } finally {
        setBusy(false);
      }
    }, 250);
    return () => clearTimeout(timer);
  }, [q]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent wide>
        <DialogHeader>
          <DialogTitle>{t("全局搜索")}</DialogTitle>
        </DialogHeader>
        <Input
          autoFocus
          placeholder={t("搜索知识点、决策、任务、卡片、事件…")}
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />
        <div className="mt-3 max-h-80 space-y-3 overflow-y-auto">
          {busy && <p className="text-sm text-muted-foreground">{t("搜索中…")}</p>}
          {results && results.total === 0 && !busy && (
            <p className="text-sm text-muted-foreground">{t("没有匹配结果")}</p>
          )}
          {results &&
            Object.entries(results.groups).map(([group, hits]) => (
              <div key={group}>
                <p className="mb-1 text-xs font-semibold text-muted-foreground">{group}</p>
                <div className="space-y-1">
                  {hits.map((h, i) => (
                    <Link
                      key={`${h.module}-${h.ref_type}-${h.ref_id}-${i}`}
                      href={moduleHref(h.module, h.ref_type, h.ref_id)}
                      onClick={() => onOpenChange(false)}
                      className="block rounded-lg border px-3 py-2 text-sm hover:bg-accent"
                    >
                      <span className="font-medium">{h.title}</span>
                      {h.snippet && <span className="ml-2 text-muted-foreground">{h.snippet}</span>}
                      <Badge variant="muted" className="ml-2">{L.module[h.module] ?? h.module}</Badge>
                    </Link>
                  ))}
                </div>
              </div>
            ))}
        </div>
      </DialogContent>
    </Dialog>
  );
}

function moduleHref(module: string, refType: string, refId: number): string {
  switch (module) {
    case "kd":
      return `/kd?topic=${refId}`;
    case "ml":
      return "/ml";
    case "dtm":
      return `/dtm/${refId}`;
    case "ta":
      return refType === "task" ? "/ta" : `/ta/${refId}`;
    case "hyp":
      return "/hypotheses";
    case "loop":
      return "/loops";
    default:
      return "/timeline";
  }
}

function ThemeToggle() {
  const t = useT();
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = React.useState(false);
  React.useEffect(() => setMounted(true), []);
  return (
    <Button
      variant="ghost"
      size="icon"
      aria-label={t("切换主题")}
      onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
    >
      {mounted && theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
    </Button>
  );
}

function LocaleSwitch() {
  const { locale, setLocale } = useI18n();
  return (
    <div
      className="flex h-8 items-center overflow-hidden rounded-full border bg-card text-xs font-medium"
      role="group"
      aria-label="Language"
    >
      <button
        className={`h-full px-2.5 transition-colors cursor-pointer ${locale === "zh" ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:bg-accent"}`}
        onClick={() => setLocale("zh")}
        aria-pressed={locale === "zh"}
      >
        中
      </button>
      <button
        className={`h-full px-2.5 transition-colors cursor-pointer ${locale === "en" ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:bg-accent"}`}
        onClick={() => setLocale("en")}
        aria-pressed={locale === "en"}
      >
        EN
      </button>
    </div>
  );
}

function TopBar() {
  const [searchOpen, setSearchOpen] = React.useState(false);
  const t = useT();
  return (
    <header className="sticky top-0 z-40 flex h-14 items-center gap-3 border-b bg-background/80 px-4 backdrop-blur lg:px-6">
      <Button variant="ghost" size="icon" className="lg:hidden" onClick={() => setSearchOpen(true)} aria-label={t("全局搜索")}>
        <Search className="h-4 w-4" />
      </Button>
      <button
        className="hidden h-9 w-72 items-center gap-2 rounded-lg border bg-card px-3 text-sm text-muted-foreground transition-colors hover:bg-accent lg:flex cursor-pointer"
        onClick={() => setSearchOpen(true)}
      >
        <Search className="h-4 w-4" />
        {t("全局搜索…")}
      </button>
      <div className="ml-auto flex items-center gap-2">
        <LocaleSwitch />
        <ThemeToggle />
      </div>
      <SearchDialog open={searchOpen} onOpenChange={setSearchOpen} />
    </header>
  );
}

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <I18nProvider>
      <AppShellInner>{children}</AppShellInner>
    </I18nProvider>
  );
}

function AppShellInner({ children }: { children: React.ReactNode }) {
  const [mobileOpen, setMobileOpen] = React.useState(false);
  const t = useT();
  const pathname = usePathname();
  // 登录页独立布局（无侧边栏）
  if (pathname === "/login") {
    return <>{children}</>;
  }
  return (
      <div className="flex min-h-screen">
        {/* 桌面侧边栏 */}
        <aside className="fixed inset-y-0 left-0 z-40 hidden w-60 flex-col border-r bg-sidebar lg:flex">
          <Link href="/" className="flex items-center gap-2.5 px-5 py-5">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
              <BrainCircuit className="h-5 w-5" />
            </span>
            <span>
              <span className="block text-sm font-bold leading-tight">{t("app.name")}</span>
              <span className="block text-[11px] text-muted-foreground">{t("app.tagline")}</span>
            </span>
          </Link>
          <React.Suspense fallback={<div className="h-96" />}>
            <SidebarNav onNavigate={() => setMobileOpen(false)} />
          </React.Suspense>
          <div className="mt-auto px-5 py-4 text-[11px] text-muted-foreground">
            {t("本地单用户模式 · 数据存储在本机")}
          </div>
        </aside>

        {/* 移动端抽屉 */}
        {mobileOpen && (
          <div className="fixed inset-0 z-50 lg:hidden">
            <div className="absolute inset-0 bg-black/50" onClick={() => setMobileOpen(false)} />
            <aside className="absolute inset-y-0 left-0 flex w-64 flex-col border-r bg-sidebar">
              <div className="flex items-center justify-between px-5 py-4">
                <span className="flex items-center gap-2 font-bold">
                  <BrainCircuit className="h-5 w-5 text-primary" /> CausaLab
                </span>
                <Button variant="ghost" size="icon" onClick={() => setMobileOpen(false)}>
                  <X className="h-4 w-4" />
                </Button>
              </div>
              <SidebarNav onNavigate={() => setMobileOpen(false)} />
            </aside>
          </div>
        )}

        <div className="flex min-w-0 flex-1 flex-col lg:pl-60">
          <div className="flex items-center gap-2 lg:hidden">
            <button
              className="mx-3 mt-3 flex h-9 items-center gap-2 rounded-lg border px-3 text-sm"
              onClick={() => setMobileOpen(true)}
            >
              <Menu className="h-4 w-4" /> {t("菜单")}
            </button>
          </div>
          <TopBar />
          <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-6 lg:px-8">{children}</main>
        </div>
      </div>
  );
}

export { toast };
