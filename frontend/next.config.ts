import type { NextConfig } from "next";

const API_PROXY_TARGET = process.env.API_PROXY_TARGET ?? "http://127.0.0.1:8000";

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
  async rewrites() {
    // 前端统一走相对路径 /api/*，由 Next.js 代理到 FastAPI（开发与同机部署均适用）
    return [{ source: "/api/:path*", destination: `${API_PROXY_TARGET}/api/:path*` }];
  },
};

export default nextConfig;
