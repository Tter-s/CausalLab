import { defineConfig, devices } from "@playwright/test";

/**
 * E2E 配置：复用系统 Edge（本机不下载浏览器）。
 * webServer 自动拉起后端（独立 e2e 数据目录）与前端 dev server。
 */
const BACKEND_PORT = 8010;
const FRONTEND_PORT = 3100;

process.env.PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD = "1";

export default defineConfig({
  testDir: "./e2e",
  timeout: 60_000,
  fullyParallel: false,
  retries: 0,
  reporter: [["list"]],
  use: {
    channel: "msedge",
    baseURL: `http://127.0.0.1:${FRONTEND_PORT}`,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [
    {
      name: "edge",
      use: { ...devices["Desktop Chrome"], channel: "msedge" },
    },
  ],
  webServer: [
    {
      command: `cd ../backend && uv run uvicorn app.main:app --port ${BACKEND_PORT}`,
      url: `http://127.0.0.1:${BACKEND_PORT}/api/health`,
      reuseExistingServer: false,
      timeout: 60_000,
      env: {
        CAUSALAB_DATA_DIR: "../backend/data-e2e",
      } as Record<string, string>,
    },
    {
      command: `npx next dev --port ${FRONTEND_PORT}`,
      url: `http://127.0.0.1:${FRONTEND_PORT}`,
      reuseExistingServer: false,
      timeout: 90_000,
      env: {
        API_PROXY_TARGET: `http://127.0.0.1:${BACKEND_PORT}`,
      } as Record<string, string>,
    },
  ],
});
