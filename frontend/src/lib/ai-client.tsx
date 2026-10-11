"use client";
/**
 * AI 调用统一封装：
 * - 先以 confirm_send=false 尝试；
 * - 后端返回 428 时弹出“发送内容预览”确认框，用户确认后以 confirm_send=true 重发；
 * - 设置中开启“自动确认”时后端直接放行，无感知。
 */
import * as React from "react";
import { post } from "@/lib/api";
import { AIConfirmRequiredError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { toast } from "sonner";
import { useT } from "@/lib/i18n";

interface AICallOptions {
  path: string;
  params?: Record<string, string | number>;
  onDone?: (data: unknown) => void;
  successMessage?: string;
}

export function useAICall() {
  const t = useT();
  const [pending, setPending] = React.useState(false);
  const [preview, setPreview] = React.useState<{ provider: string; model_id: string; payload: string; resolve: (v: boolean) => void } | null>(null);
  const [lastOptions, setLastOptions] = React.useState<AICallOptions | null>(null);

  const execute = React.useCallback(async (opts: AICallOptions, confirmSend: boolean): Promise<boolean> => {
    setPending(true);
    try {
      const search = new URLSearchParams({ ...(opts.params ?? {}), confirm_send: String(confirmSend) }).toString();
      const data = await post<unknown>(`${opts.path}?${search}`);
      opts.onDone?.(data);
      if (opts.successMessage) toast.success(opts.successMessage);
      return true;
    } catch (e) {
      if (e instanceof AIConfirmRequiredError) {
        const confirmed = await new Promise<boolean>((resolve) => {
          setPreview({ provider: e.body.provider, model_id: e.body.model_id, payload: e.body.payload_preview, resolve });
        });
        setPreview(null);
        if (confirmed) return await execute(opts, true);
        return false;
      }
      toast.error(e instanceof Error ? e.message : "AI 调用失败");
      return false;
    } finally {
      setPending(false);
    }
  }, []);

  const call = React.useCallback(
    (opts: AICallOptions) => {
      setLastOptions(opts);
      return execute(opts, false);
    },
    [execute],
  );

  const retry = React.useCallback(() => {
    if (lastOptions) void execute(lastOptions, false);
  }, [lastOptions, execute]);

  const dialog = preview ? (
    <Dialog open onOpenChange={() => preview.resolve(false)}>
      <DialogContent wide>
        <DialogHeader>
          <DialogTitle>{t("发送内容到云端模型？")}</DialogTitle>
          <DialogDescription>
            {t("以下内容将发送给 {provider} 的模型 {model}。请确认其中没有你不想发出的隐私信息。你也可以在「设置 → AI 服务」中开启自动确认。", {
              provider: preview.provider,
              model: preview.model_id || t("（未命名）"),
            })}
          </DialogDescription>
        </DialogHeader>
        <pre className="max-h-72 overflow-y-auto whitespace-pre-wrap rounded-lg border bg-muted/40 p-3 text-xs leading-relaxed">
          {preview.payload}
        </pre>
        <DialogFooter>
          <Button variant="outline" onClick={() => preview.resolve(false)}>
            {t("action.cancel")}
          </Button>
          <Button onClick={() => preview.resolve(true)}>{t("确认发送")}</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  ) : null;

  return { call, retry, pending, dialog };
}
