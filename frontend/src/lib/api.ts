/** 统一 API 客户端：错误带结构化 detail；AI 确认闸门(428)抛出专属错误。 */
import type { AIConfirmRequiredBody } from "./types";

export class ApiError extends Error {
  status: number;
  detail: unknown;

  constructor(status: number, detail: unknown) {
    const message =
      typeof detail === "object" && detail !== null && "message" in (detail as Record<string, unknown>)
        ? String((detail as Record<string, unknown>).message)
        : typeof detail === "string"
          ? detail
          : `请求失败（${status}）`;
    super(message);
    this.status = status;
    this.detail = detail;
  }
}

/** AI 内容确认闸门：428 响应。UI 据此弹出“发送内容预览”确认框。 */
export class AIConfirmRequiredError extends Error {
  body: AIConfirmRequiredBody;

  constructor(body: AIConfirmRequiredBody) {
    super(body.message);
    this.body = body;
  }
}

/** 后端不可达时的统一提示（含修复指引）。 */
export const BACKEND_UNREACHABLE_MESSAGE =
  "无法连接后端 API（127.0.0.1:8000）。\n" +
  "请确认后端服务已启动：双击仓库根目录的「启动CausaLab.bat」，\n" +
  "或在 backend 目录运行：uv run uvicorn app.main:app --port 8000\n" +
  "然后点击下方「重试」刷新。";

declare global {
  interface Window {
    /** 静态托管场景的运行期注入（由部署方放一个 config.js 设置），优先于构建期配置。 */
    __CAUSALAB_API_BASE__?: string;
    /** 桌面壳（pywebview）注入的 JS 桥：存在即表示运行在桌面版窗口内。 */
    pywebview?: { api?: { open_external?: (url: string) => Promise<unknown> } };
  }
}

/**
 * 后端基址解析（静态产物也能在部署后改，无需重新构建）：
 * 1. `window.__CAUSALAB_API_BASE__`（运行期注入，如 "http://127.0.0.1:8000"）；
 * 2. `NEXT_PUBLIC_API_BASE`（构建期环境变量）；
 * 3. `""`（默认相对路径——同源托管场景零行为变化）。
 */
export function apiBase(): string {
  if (typeof window !== "undefined") {
    const injected = window.__CAUSALAB_API_BASE__;
    if (typeof injected === "string" && injected.trim()) return injected.trim().replace(/\/+$/, "");
  }
  const fromEnv = process.env.NEXT_PUBLIC_API_BASE;
  if (fromEnv && fromEnv.trim()) return fromEnv.trim().replace(/\/+$/, "");
  return "";
}

/** 把 API 路径（形如 "/dashboard"，不含 /api 前缀）解析为可请求的完整 URL。 */
export function apiUrl(path: string): string {
  const base = apiBase();
  return base ? `${base}/api${path}` : `/api${path}`;
}

/** 是否运行在桌面版窗口（pywebview 壳）内——壳会注入 window.pywebview.api。 */
export function isDesktopShell(): boolean {
  return typeof window !== "undefined" && Boolean(window.pywebview?.api?.open_external);
}

/**
 * 打开外部链接 / 触发下载：
 * 桌面壳内交给系统浏览器（webview 内 window.open 与 blob 下载不可靠）；
 * 普通浏览器维持原 window.open 行为。
 */
export function openExternal(url: string): void {
  if (isDesktopShell()) {
    void window.pywebview?.api?.open_external?.(url);
    return;
  }
  window.open(url, "_blank", "noopener");
}

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(apiUrl(path), {
      headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
      cache: "no-store",
      ...init,
    });
  } catch {
    // 网络层失败：浏览器 fetch 抛 TypeError（后端进程未启动 / 代理目标拒绝连接）
    throw new ApiError(0, { message: BACKEND_UNREACHABLE_MESSAGE });
  }
  if (res.status === 204) return undefined as T;
  const text = await res.text();
  let data: unknown = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = text;
  }
  if (!res.ok) {
    const detail = (data as { detail?: unknown })?.detail ?? data;
    if (res.status === 428 && (detail as AIConfirmRequiredBody)?.code === "ai_confirm_required") {
      throw new AIConfirmRequiredError(detail as AIConfirmRequiredBody);
    }
    // 密码保护已启用且无有效会话 → 跳转登录页（登录页自身与 auth 端点除外）
    if (
      res.status === 401 &&
      (detail as { code?: string })?.code === "auth_required" &&
      typeof window !== "undefined" &&
      !window.location.pathname.startsWith("/login") &&
      !path.startsWith("/auth/")
    ) {
      // 刻意整页跳转：清空全部客户端缓存状态，登录后从干净状态重建
      // eslint-disable-next-line @next/next/no-location-assign-relative-destination
      window.location.href = "/login";
      throw new ApiError(401, { message: "需要登录" });
    }
    // 5xx 且无结构化 detail：后端不可达（Next 代理 ECONNREFUSED）或后端内部错误，
    // 两种情况都给出连接指引 + 保留技术信息
    if (res.status >= 500 && typeof detail === "string") {
      throw new ApiError(res.status, {
        message: `${BACKEND_UNREACHABLE_MESSAGE}\n（技术信息：HTTP ${res.status} ${detail.slice(0, 200)}）`,
      });
    }
    throw new ApiError(res.status, detail);
  }
  return data as T;
}

export const get = <T>(path: string) => api<T>(path);
export const post = <T>(path: string, body?: unknown) =>
  api<T>(path, { method: "POST", body: body === undefined ? undefined : JSON.stringify(body) });
export const put = <T>(path: string, body: unknown) =>
  api<T>(path, { method: "PUT", body: JSON.stringify(body) });
export const patch = <T>(path: string, body: unknown) =>
  api<T>(path, { method: "PATCH", body: JSON.stringify(body) });
export const del = <T>(path: string) => api<T>(path, { method: "DELETE" });

/**
 * multipart/form-data 上传（文件上传专用）。
 * 刻意传空的 headers 覆盖掉 api() 默认的 Content-Type: application/json，
 * 让浏览器自己带 multipart boundary，否则后端无法解析。
 */
export const postForm = <T>(path: string, form: FormData) =>
  api<T>(path, { method: "POST", body: form, headers: {} });

/** 带 query 参数的 GET */
export function getWith<T>(path: string, params: Record<string, string | number | boolean | undefined | null>): Promise<T> {
  const qs = Object.entries(params)
    .filter(([, v]) => v !== undefined && v !== null && v !== "")
    .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(String(v))}`)
    .join("&");
  return get<T>(qs ? `${path}?${qs}` : path);
}
