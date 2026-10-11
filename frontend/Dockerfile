# 仅前端镜像（本机 Docker 不可用，此文件未在本机验证 —— 见 README「未在本机验证」清单）
FROM node:22-alpine AS builder

WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
# 构建时把 API 代理目标指向容器网络中的后端服务
ENV API_PROXY_TARGET=http://backend:8000
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

FROM node:22-alpine
WORKDIR /app
ENV NODE_ENV=production
ENV API_PROXY_TARGET=http://backend:8000
ENV NEXT_TELEMETRY_DISABLED=1

COPY --from=builder /app/package.json /app/package-lock.json ./
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public
COPY --from=builder /app/next.config.ts ./next.config.ts

EXPOSE 3000
CMD ["npx", "next", "start", "--port", "3000"]
