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

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api${path}`, {
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    cache: "no-store",
    ...init,
  });
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

/** 带 query 参数的 GET */
export function getWith<T>(path: string, params: Record<string, string | number | boolean | undefined | null>): Promise<T> {
  const qs = Object.entries(params)
    .filter(([, v]) => v !== undefined && v !== null && v !== "")
    .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(String(v))}`)
    .join("&");
  return get<T>(qs ? `${path}?${qs}` : path);
}
