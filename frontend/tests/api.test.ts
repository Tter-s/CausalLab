import { describe, expect, it, vi } from "vitest";
import { AIConfirmRequiredError, ApiError } from "@/lib/api";

// api.ts 使用全局 fetch，node 环境下 mock 它
describe("api client", () => {
  it("throws ApiError with message from detail on error", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: { message: "决策不存在" } }), { status: 404 })),
    );
    const { get } = await import("@/lib/api");
    await expect(get("/dtm/decisions/999")).rejects.toMatchObject({ status: 404, message: "决策不存在" });
    vi.unstubAllGlobals();
  });

  it("throws AIConfirmRequiredError on 428 confirm gate", async () => {
    const body = {
      code: "ai_confirm_required",
      message: "需要确认",
      provider: "deepseek",
      model_id: "m",
      payload_preview: "内容预览",
    };
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: body }), { status: 428 })));
    const { get } = await import("@/lib/api");
    try {
      await get("/ai/kd/diagnose");
      expect.unreachable("should throw");
    } catch (e) {
      expect(e).toBeInstanceOf(AIConfirmRequiredError);
      expect((e as AIConfirmRequiredError).body.payload_preview).toBe("内容预览");
    }
    vi.unstubAllGlobals();
  });

  it("returns parsed json on 204 as undefined", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(null, { status: 204 })));
    const { del } = await import("@/lib/api");
    await expect(del("/kd/subjects/1")).resolves.toBeUndefined();
    vi.unstubAllGlobals();
  });

  it("shows friendly guidance when backend is unreachable (network failure)", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));
    const { get, BACKEND_UNREACHABLE_MESSAGE } = await import("@/lib/api");
    try {
      await get("/dashboard");
      expect.unreachable("should throw");
    } catch (e) {
      expect((e as Error).message).toContain("无法连接后端 API");
      expect((e as Error).message).toBe(BACKEND_UNREACHABLE_MESSAGE);
    }
    vi.unstubAllGlobals();
  });

  it("shows friendly guidance when proxy returns 500 with plain text (backend down)", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response("Internal Server Error", { status: 500 })),
    );
    const { get } = await import("@/lib/api");
    try {
      await get("/dashboard");
      expect.unreachable("should throw");
    } catch (e) {
      expect((e as Error).message).toContain("无法连接后端 API");
      expect((e as Error).message).toContain("HTTP 500");
    }
    vi.unstubAllGlobals();
  });

  it("keeps structured FastAPI 500 errors as-is (not masked as unreachable)", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ detail: { message: "业务错误" } }), { status: 500 }),
      ),
    );
    const { get } = await import("@/lib/api");
    await expect(get("/x")).rejects.toMatchObject({ message: "业务错误" });
    vi.unstubAllGlobals();
  });

  it("ApiError falls back to generic message", () => {
    const err = new ApiError(500, "plain error");
    expect(err.message).toBe("plain error");
    expect(new ApiError(500, { detail: {} }).message).toContain("500");
  });

  it("postForm 发送 FormData 且不写 JSON Content-Type（浏览器需自行带 multipart boundary）", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ id: 1 }), { status: 201 }));
    vi.stubGlobal("fetch", fetchMock);
    const { postForm } = await import("@/lib/api");
    const fd = new FormData();
    fd.append("module", "kd");
    await expect(postForm("/uploads", fd)).resolves.toMatchObject({ id: 1 });

    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("/api/uploads");
    expect(init.method).toBe("POST");
    expect(init.body).toBe(fd);
    // 关键：不能带上 api() 默认的 application/json，否则后端无法解析 multipart
    expect((init.headers as Record<string, string>)["Content-Type"]).toBeUndefined();
    vi.unstubAllGlobals();
  });

  // ---- 静态托管基址解析（window 注入 → 构建期 env → 相对路径）----
  it("默认相对路径：同源托管与开发代理场景零行为变化", async () => {
    const { apiBase, apiUrl } = await import("@/lib/api");
    expect(apiBase()).toBe("");
    expect(apiUrl("/dashboard")).toBe("/api/dashboard");
  });

  it("优先取运行期注入的 window.__CAUSALAB_API_BASE__，容忍结尾斜杠", async () => {
    vi.stubGlobal("window", { __CAUSALAB_API_BASE__: "http://192.0.2.10:8000/" });
    const { apiUrl } = await import("@/lib/api");
    expect(apiUrl("/dashboard")).toBe("http://192.0.2.10:8000/api/dashboard");
    vi.unstubAllGlobals();
  });

  it("其次取构建期 NEXT_PUBLIC_API_BASE", async () => {
    const prev = process.env.NEXT_PUBLIC_API_BASE;
    process.env.NEXT_PUBLIC_API_BASE = "http://192.0.2.11:9000";
    try {
      const { apiUrl } = await import("@/lib/api");
      expect(apiUrl("/x")).toBe("http://192.0.2.11:9000/api/x");
    } finally {
      process.env.NEXT_PUBLIC_API_BASE = prev;
    }
  });

  it("注入基址时 api() 使用完整 URL 发起请求", async () => {
    vi.stubGlobal("window", { __CAUSALAB_API_BASE__: "http://host:99" });
    const fetchMock = vi.fn().mockResolvedValue(new Response("{}", { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    const { get } = await import("@/lib/api");
    await get("/dashboard");
    expect(fetchMock.mock.calls[0][0]).toBe("http://host:99/api/dashboard");
    vi.unstubAllGlobals();
  });
});
