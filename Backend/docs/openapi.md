# OpenAPI

منبع قرارداد API، schema پویای drf-spectacular در `/api/v1/schema/` است. فایل static قدیمی حذف شده تا contract منسوخ در repository باقی نماند.

```bash
./scripts/generate_openapi.sh
```

خروجی پیش‌فرض در `build/openapi.yaml` قرار می‌گیرد و در CI باید با `--validate` تولید شود.
