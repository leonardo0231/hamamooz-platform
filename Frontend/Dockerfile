FROM node:22-alpine AS build

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY tsconfig.json ./
COPY scripts ./scripts
COPY src ./src
COPY public ./public

ARG VITE_API_BASE_URL=/api/v1/
ARG VITE_APP_NAME=هم‌آموز
ARG VITE_REQUEST_TIMEOUT_MS=20000
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL} \
    VITE_APP_NAME=${VITE_APP_NAME} \
    VITE_REQUEST_TIMEOUT_MS=${VITE_REQUEST_TIMEOUT_MS}

RUN npm run build

FROM nginxinc/nginx-unprivileged:1.29-alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 8080

HEALTHCHECK --interval=20s --timeout=5s --start-period=5s --retries=5 \
  CMD wget -qO- http://127.0.0.1:8080/healthz >/dev/null || exit 1
