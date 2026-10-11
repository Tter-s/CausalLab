import { describe, expect, it } from "vitest";
import { fmtDate, fmtDateTime, fmtPercent, fromLocalInput, parseDate, toLocalInput } from "@/lib/format";

describe("format utils", () => {
  it("parses ISO strings with Z suffix as UTC", () => {
    const d = parseDate("2026-10-11T08:00:00Z");
    expect(d).not.toBeNull();
    expect(d!.getUTCFullYear()).toBe(2026);
  });

  it("formats datetime for display", () => {
    // UTC 08:00 在 UTC+8 是 16:00；只断言包含日期与时间结构
    expect(fmtDateTime("2026-10-11T08:00:00Z")).toMatch(/^2026-10-11 \d{2}:\d{2}$/);
  });

  it("formats date", () => {
    expect(fmtDate("2026-10-11T08:00:00Z")).toBe("2026-10-11");
  });

  it("returns dash for null/invalid", () => {
    expect(fmtDate(null)).toBe("—");
    expect(fmtDateTime(undefined)).toBe("—");
  });

  it("formats percent", () => {
    expect(fmtPercent(0.627, 1)).toBe("62.7%");
    expect(fmtPercent(null)).toBe("—");
  });

  it("round-trips datetime-local <-> ISO", () => {
    const iso = "2026-10-11T08:30:00.000Z";
    const local = toLocalInput(iso);
    expect(local).toMatch(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/);
    expect(fromLocalInput(local)).toBe(iso);
  });

  it("handles empty input", () => {
    expect(fromLocalInput("")).toBeNull();
    expect(toLocalInput(null)).toBe("");
  });
});
