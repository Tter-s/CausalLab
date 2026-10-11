"use client";
/** 登录页：启用密码保护后，未认证访问任意页面会被重定向到这里。 */
import * as React from "react";
import { useRouter } from "next/navigation";
import { Loader2, Lock } from "lucide-react";
import { BrandMark } from "@/components/brand-mark";
import { useT } from "@/lib/i18n";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input, Label } from "@/components/ui/input";

export default function LoginPage() {
  const t = useT();
  const router = useRouter();
  const [password, setPassword] = React.useState("");
  const [error, setError] = React.useState<string | null>(null);
  const [busy, setBusy] = React.useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!password) return;
    setBusy(true);
    setError(null);
    try {
      const r = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ password }),
      });
      if (r.ok) {
        router.replace("/");
        return;
      }
      const body = await r.json().catch(() => null);
      const code = body?.detail?.code;
      if (code === "rate_limited") setError(t("尝试过于频繁，请一分钟后再试。"));
      else if (code === "auth_not_enabled") router.replace("/");
      else setError(t("密码错误。"));
    } catch {
      setError(t("无法连接后端 API（127.0.0.1:8000）。"));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <Card className="w-full max-w-sm">
        <CardContent className="flex flex-col items-center p-8 text-center">
          <BrandMark className="mb-3 h-14 w-14 rounded-xl shadow-md" />
          <h1 className="text-lg font-bold">CausaLab</h1>
          <p className="mt-1 text-sm text-muted-foreground">{t("个人学习、决策与行动实验室")}</p>

          <form className="mt-6 w-full space-y-3" onSubmit={submit}>
            <div className="text-left">
              <Label htmlFor="login-password">{t("请输入访问密码")}</Label>
              <div className="relative mt-1.5">
                <Lock className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  id="login-password"
                  type="password"
                  autoFocus
                  className="pl-9"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                />
              </div>
            </div>
            {error && <p className="text-left text-sm text-destructive">{error}</p>}
            <Button type="submit" className="w-full" disabled={busy || !password}>
              {busy && <Loader2 className="animate-spin" />}
              {t("解锁")}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
