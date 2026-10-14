import type { NextConfig } from "next";

const API_PROXY_TARGET = process.env.API_PROXY_TARGET ?? "http://127.0.0.1:8000";

// 静态导出模式（npm run build:static）：产物为纯静态文件（out/），
// 由任意静态服务器或 FastAPI 同源托管。该模式与 rewrites 不兼容，故不注册代理。
const STATIC_EXPORT = process.env.STATIC_EXPORT === "1";

const nextConfig: NextConfig = {
  // Next 16 默认阻止非 localhost 来源访问 dev 资源（HMR/静态块），
  // E2E 与本机 IP 访问需要显式允许 127.0.0.1
  allowedDevOrigins: ["127.0.0.1", "localhost"],
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

if (STATIC_EXPORT) {
  // 纯静态导出：每个路由产出独立 HTML 目录；链接走 ?id= 参数（见详情页改造）
  nextConfig.output = "export";
  nextConfig.trailingSlash = true;
} else {
  // 常规模式（dev / build / start）：前端统一走相对路径 /api/*，由 Next.js 代理到 FastAPI
  nextConfig.rewrites = async () => {
    return [{ source: "/api/:path*", destination: `${API_PROXY_TARGET}/api/:path*` }];
  };
}

export default nextConfig;
