// 截图脚本：遍历主要页面输出 PNG（浅色主题）
import { chromium } from "@playwright/test";

const BASE = "http://localhost:3000";
const pages = [
  ["dashboard", "/"],
  ["kd", "/kd"],
  ["ml", "/ml"],
  ["dtm", "/dtm"],
  ["ta", "/ta"],
  ["timeline", "/timeline"],
  ["hypotheses", "/hypotheses"],
  ["loops", "/loops"],
  ["settings", "/settings"],
];

const outDir = process.env.SHOT_DIR ?? "shots";
const browser = await chromium.launch({ channel: "msedge", headless: true });
const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1 });
const page = await ctx.newPage();

for (const [name, path] of pages) {
  await page.goto(`${BASE}${path}`, { waitUntil: "networkidle", timeout: 45000 }).catch(() => {});
  await page.waitForTimeout(1200);
  await page.screenshot({ path: `${outDir}/${name}.png`, fullPage: name !== "dashboard" });
  console.log("shot:", name);
}

// 决策详情
const dec = await fetch("http://127.0.0.1:8000/api/dtm/decisions").then((r) => r.json());
if (dec.length > 0) {
  await page.goto(`${BASE}/dtm/${dec[0].id}`, { waitUntil: "networkidle", timeout: 45000 }).catch(() => {});
  await page.waitForTimeout(1200);
  await page.screenshot({ path: `${outDir}/dtm-detail.png`, fullPage: true });
  console.log("shot: dtm-detail");
}
// 项目详情
const projs = await fetch("http://127.0.0.1:8000/api/ta/projects").then((r) => r.json());
if (projs.length > 0) {
  await page.goto(`${BASE}/ta/${projs[0].id}`, { waitUntil: "networkidle", timeout: 45000 }).catch(() => {});
  await page.waitForTimeout(1200);
  await page.screenshot({ path: `${outDir}/ta-detail.png`, fullPage: true });
  console.log("shot: ta-detail");
}
// 深色主题仪表盘
await page.emulateMedia({ colorScheme: "dark" });
await page.goto(`${BASE}/settings`, { waitUntil: "networkidle" }).catch(() => {});
await page.evaluate(() => {
  document.documentElement.classList.add("dark");
  window.localStorage.setItem("theme", "dark");
});
await page.goto(`${BASE}/`, { waitUntil: "networkidle" }).catch(() => {});
await page.waitForTimeout(1200);
await page.screenshot({ path: `${outDir}/dashboard-dark.png` });
console.log("shot: dashboard-dark");

await browser.close();
