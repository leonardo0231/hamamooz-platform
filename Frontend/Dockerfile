FROM node:22-alpine AS builder
WORKDIR /app
COPY package.json ./
COPY scripts ./scripts
COPY src ./src
COPY public ./public
RUN node scripts/build.mjs

FROM nginxinc/nginx-unprivileged:1.29-alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 8080

HEALTHCHECK --interval=20s --timeout=5s --start-period=5s --retries=5 CMD wget -qO- http://127.0.0.1:8080/healthz >/dev/null || exit 1
