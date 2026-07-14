# استقرار روی سرور با دسترسی خارجی محدود

اگر سرور مقصد به GitHub، PyPI یا Registryها دسترسی ندارد، Build را روی یک ماشین متصل با معماری CPU یکسان انجام دهید و Imageها را منتقل کنید.

## ساخت Bundle روی ماشین متصل

```bash
docker compose build web worker frontend
docker compose pull db redis minio minio-init backup
docker image save -o hamamooz-images.tar \
  hamamooz-mvp-web \
  hamamooz-mvp-worker \
  hamamooz-mvp-frontend \
  postgres:17-alpine \
  redis:7.4-alpine \
  minio/minio:RELEASE.2025-04-22T22-12-26Z \
  minio/mc:RELEASE.2025-04-16T18-13-26Z
sha256sum hamamooz-images.tar > hamamooz-images.tar.sha256
```

نام Image ساخته‌شده را با `docker image ls` کنترل کنید؛ Compose ممکن است نام را بر اساس نام پوشه بسازد.

فایل‌های لازم برای انتقال:

```text
hamamooz-images.tar
hamamooz-images.tar.sha256
Backend/docker-compose.yml
Backend/.env تکمیل‌شده در مقصد
Frontend/ برای حفظ Build context تعریف‌شده در Compose
```

## بارگذاری در سرور مقصد

```bash
sha256sum -c hamamooz-images.tar.sha256
docker image load -i hamamooz-images.tar
docker compose up -d --no-build
```

Credential واقعی را داخل Archive عمومی قرار ندهید. `.env` باید مستقیماً روی سرور ساخته، Permission آن `600` و بکاپ امن آن جدا نگهداری شود.

## به‌روزرسانی

نسخه Image را Tag کنید، Bundle جدید بسازید، روی مقصد Load و سپس:

```bash
docker compose run --rm web python manage.py migrate --noinput
docker compose up -d --no-build web worker frontend
```

قبل از Migration بکاپ و تست Restore لازم است. برای Rollback، Image نسخه قبلی و Migration compatibility باید از قبل نگهداری شود.
