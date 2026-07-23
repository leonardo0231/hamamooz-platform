# OpenAPI

منبع حقیقت قرارداد API، endpoint زیر در Runtime همان Commit است:

```text
/api/v1/schema/
```

UIها:

```text
/api/v1/docs/
/api/v1/redoc/
```

تولید و اعتبارسنجی artifact:

```bash
./scripts/generate_openapi.sh build/openapi.yaml
```

فایل‌های `openapi.yaml` و `docs/openapi-schema.yml` که در تاریخچه شاخه وجود دارند، تا زمان تولید مجدد از همان Commit canonical نیستند. Client generation و contract test باید فقط از `build/openapi.yaml` تازه یا Schema زنده استفاده کنند.

کنترل پیشنهادی CI:

```bash
python manage.py spectacular --api-version v1 \
  --file build/openapi.yaml --validate
git diff --exit-code -- build/openapi.yaml
```
