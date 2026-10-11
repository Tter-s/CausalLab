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

  it("ApiError falls back to generic message", () => {
    const err = new ApiError(500, "plain error");
    expect(err.message).toBe("plain error");
    expect(new ApiError(500, { detail: {} }).message).toContain("500");
  });
});
