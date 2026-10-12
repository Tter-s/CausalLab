import { describe, expect, it } from "vitest";
import { readFileSync, readdirSync, statSync } from "node:fs";
import { join } from "node:path";
import { enPageStrings } from "@/lib/i18n-page-strings";

// 读取 i18n.tsx 内的 zh/en 基础词典（该文件为 .tsx 且含 JSX，直接读源码解析）
const i18nSource = readFileSync(join(__dirname, "../src/lib/i18n.tsx"), "utf8");

function extractDict(name: "zh" | "en"): Record<string, string> {
  const start = i18nSource.indexOf(`const ${name}: Record<string, string> = {`);
  if (start < 0) throw new Error(`dict ${name} not found`);
  const end = i18nSource.indexOf("\n};", start);
  const body = i18nSource.slice(start, end);
  const out: Record<string, string> = {};
  const re = /"((?:[^"\\]|\\.)*)":\s*"((?:[^"\\]|\\.)*)"/g;
  let m: RegExpExecArray | null;
  while ((m = re.exec(body))) out[m[1]] = m[2];
  return out;
}

const baseZh = extractDict("zh");
const baseEn = extractDict("en");

describe("i18n dictionaries", () => {
  it("en covers every base zh key (国际化接口预留)", () => {
    for (const key of Object.keys(baseZh)) {
      expect(baseEn[key], `missing en translation for ${key}`).toBeTruthy();
    }
  });

  it("every base entry has non-empty values", () => {
    for (const v of Object.values(baseZh)) expect(v.length).toBeGreaterThan(0);
    for (const v of Object.values(baseEn)) expect(v.length).toBeGreaterThan(0);
  });

  it("every Chinese-source t() key used in src is translated in enPageStrings", () => {
    const files: string[] = [];
    const walk = (dir: string) => {
      for (const name of readdirSync(dir)) {
        const p = join(dir, name);
        if (statSync(p).isDirectory()) walk(p);
        else if (/\.(tsx|ts)$/.test(name) && !name.includes(".test.") && name !== "i18n.tsx") files.push(p);
      }
    };
    walk(join(__dirname, "../src"));

    const missing: string[] = [];
    const re = /\bt\(\s*"((?:[^"\\]|\\.)*)"/g;
    for (const f of files) {
      const content = readFileSync(f, "utf8");
      let m: RegExpExecArray | null;
      while ((m = re.exec(content))) {
        const key = m[1];
        if (/[\u4e00-\u9fff]/.test(key) && !(key in enPageStrings) && !(key in baseEn)) {
          missing.push(`${f}: ${key}`);
        }
      }
    }
    expect(missing, `untranslated keys:\n${missing.join("\n")}`).toEqual([]);
  });

  it("enPageStrings has no empty translations", () => {
    for (const [k, v] of Object.entries(enPageStrings)) {
      expect(v.length, `empty translation for ${k}`).toBeGreaterThan(0);
    }
  });

  it("interpolation placeholders match between key and translation", () => {
    const placeholders = (s: string) => [...s.matchAll(/\{(\w+)\}/g)].map((m) => m[1]).sort().join(",");
    for (const [k, v] of Object.entries(enPageStrings)) {
      if (/\{\w+\}/.test(k)) {
        expect(placeholders(v), `placeholder mismatch for ${k}`).toBe(placeholders(k));
      }
    }
  });
});
