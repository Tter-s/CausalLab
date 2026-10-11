import { describe, expect, it } from "vitest";
import { zh, en } from "@/lib/i18n";

describe("i18n dictionaries", () => {
  it("zh and en cover the same nav/action keys (国际化接口预留)", () => {
    const zhKeys = Object.keys(zh).sort();
    const enKeys = Object.keys(en).sort();
    expect(enKeys).toEqual(zhKeys);
  });

  it("every nav key has a non-empty zh translation", () => {
    for (const key of Object.keys(zh)) {
      expect(zh[key].length).toBeGreaterThan(0);
    }
  });
});
