# استقرار روی سرور با دسترسی خارجی محدود

اگر سرور مقصد به GitHub، PyPI یا Registry دسترسی ندارد، Imageها را روی ماشین متصل با معماری CPU یکسان Build/Pull و سپس منتقل کنید.

## پیش‌نیاز

- Docker و Compose plugin روی مقصد
- فضای کافی برای Image، DB، رسانه و Backup
- فایل `.env` تولیدشده مستقیم روی مقصد با Permission `600`
- ساعت سیستم و NTP صحیح
- مقصد backup رمزگذاری‌شده و خارج Host

## ساخت Bundle روی ماشین متصل

ابتدا Image برنامه را با tag ثابت بسازید:

```bash
export HAMAMOOZ_VERSION=2026.07.23
docker build -t hamamooz-backend:${HAMAMOOZ_VERSION} .
```

Imageهای وابسته:

```bash
docker pull nginx:1.29-alpine
docker pull postgres:17-alpine
docker pull redis:7.4-alpine
docker pull alpine:3.22
docker pull minio/minio:RELEASE.2025-04-22T22-12-26Z
docker pull minio/mc:RELEASE.2025-04-16T18-13-26Z
```

Bundle بدون S3:

```bash
docker image save -o hamamooz-images.tar \
  hamamooz-backend:${HAMAMOOZ_VERSION} \
  nginx:1.29-alpine \
  postgres:17-alpine \
  redis:7.4-alpine \
  alpine:3.22
sha256sum hamamooz-images.tar > hamamooz-images.tar.sha256
```

در profile S3 دو Image MinIO را نیز به command اضافه کنید.

Compose فعلی برای serviceهای برنامه از `build: .` استفاده می‌کند. برای سرور آفلاین یک override بسازید:

```yaml
services:
  release:
    image: hamamooz-backend:2026.07.23
    build: null
  web:
    image: hamamooz-backend:2026.07.23
    build: null
  worker:
    image: hamamooz-backend:2026.07.23
    build: null
  beat:
    image: hamamooz-backend:2026.07.23
    build: null
```

فایل‌های انتقال:

```text
hamamooz-images.tar
hamamooz-images.tar.sha256
Backend/docker-compose.yml
Backend/docker-compose.offline.yml
Backend/nginx/
Backend/scripts/
Backend/.env.production.example
```

Credential واقعی را داخل Archive عمومی قرار ندهید.

## بارگذاری در مقصد

```bash
sha256sum -c hamamooz-images.tar.sha256
docker image load -i hamamooz-images.tar
cp .env.production.example .env
chmod 600 .env
# مقادیر واقعی را تکمیل کنید

docker compose -f docker-compose.yml -f docker-compose.offline.yml \
  up -d --no-build
```

برای S3:

```bash
docker compose -f docker-compose.yml -f docker-compose.offline.yml \
  --profile s3 up -d --no-build
```

## اعتبارسنجی

```bash
docker compose ps
docker compose logs release
docker compose logs --tail=200 web worker beat
curl -fsS http://localhost:8000/api/v1/health/live/
curl -fsS http://localhost:8000/api/v1/health/ready/
```

## به‌روزرسانی

1. Backup و restore drill اخیر را تأیید کنید.
2. Image جدید را load کنید.
3. `release` را با Image جدید اجرا کنید.
4. web/worker/beat را با همان tag بالا بیاورید.
5. health و smoke test را اجرا کنید.

```bash
docker compose -f docker-compose.yml -f docker-compose.offline.yml \
  run --rm release
docker compose -f docker-compose.yml -f docker-compose.offline.yml \
  up -d --no-build web worker beat gateway
```

Rollback فقط وقتی امن است که Migration backward-compatible باشد. Image قبلی، Compose قبلی و Backup قبل از Migration باید نگهداری شوند.
