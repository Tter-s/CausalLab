/**
 * 静态导出构建（跨平台，不引新依赖）：
 *   设置 STATIC_EXPORT=1 后执行 next build，产出纯静态目录 frontend/out/。
 * 该产物可由任意静态服务器托管，或由 FastAPI 同源托管（见 backend/app/main.py）。
 * 用法：npm run build:static
 */
import { spawnSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

const frontendDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
// 直接跑本仓库 node_modules 里的 next CLI（用当前 node 解释器启动，避开 .cmd / shell 差异）
const nextBin = path.join(frontendDir, "node_modules", "next", "dist", "bin", "next");

const result = spawnSync(process.execPath, [nextBin, "build"], {
  cwd: frontendDir,
  stdio: "inherit",
  env: { ...process.env, STATIC_EXPORT: "1" },
});

if (result.error) {
  console.error("静态构建启动失败：", result.error.message);
  process.exit(1);
}
process.exit(result.status ?? 1);
