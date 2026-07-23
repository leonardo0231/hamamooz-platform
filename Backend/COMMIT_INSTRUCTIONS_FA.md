# دستور Commit و Push تغییرات Backend

این پروژه فقط سه Branch دائمی دارد:

```text
main
backend/mvp-bootstrap
frontend/mvp-bootstrap
```

برای تغییرات Backend Branch جدید ایجاد نکنید.

## ۱. ورود به Branch Backend

```powershell
cd D:\Projects\hamamooz-platform
git switch backend/mvp-bootstrap
git pull --ff-only origin backend/mvp-bootstrap
git fetch origin
git merge origin/main
```

قبل از ادامه، `git status` را بررسی کنید و مطمئن شوید تغییر ناشناخته‌ای حذف یا بازنویسی نمی‌شود.

## ۲. کنترل کیفیت

```powershell
cd Backend
ruff check .
ruff format --check .
python manage.py check
python manage.py makemigrations --check --dry-run
pytest --cov=hamamooz --cov-report=term-missing
python manage.py spectacular --api-version v1 --file ..\contracts\openapi.yaml --validate
cd ..
```

تست هم‌زمانی و Locking باید در CI روی PostgreSQL اجرا شود. روی Windows برای تست PDF باید Pango نصب باشد یا تست‌ها داخل Docker اجرا شوند.

## ۳. بررسی فایل‌های قابل Commit

از `git add .` بدون بررسی استفاده نکنید.

```powershell
git status --short
git diff --check
git diff --stat
```

فایل‌های Secret و محلی نباید Commit شوند:

```text
Backend/.env
Backend/db.sqlite3
Backend/.venv/
Backend/media/
Backend/.test-media/
contracts/openapi.generated.yaml
```

## ۴. Stage و Commit

برای تغییر قرارداد Attendance این فایل‌ها باید Stage شوند:

```powershell
git add Backend/hamamooz/apps/attendance/serializers.py
git add Backend/hamamooz/apps/attendance/views.py
git add Backend/config/settings/base.py
git add Backend/tests/test_openapi_schema.py
git add contracts/openapi.yaml
git add contracts/API_CHANGELOG.md
git add README.md
git add docs/FRONTEND_HANDOFF_FA.md
git add .github
git add .gitignore
git add Backend/README.md
git add Backend/scripts/generate_openapi.sh
git add Backend/COMMIT_INSTRUCTIONS_FA.md
```

سپس:

```powershell
git diff --cached --check
git diff --cached --stat
git commit -m "fix(api): complete attendance report OpenAPI contract"
```

## ۵. Push و Pull Request

```powershell
git push origin backend/mvp-bootstrap
```

Pull Request باید از این Branch به `main` ساخته شود:

```powershell
gh pr create `
  --base main `
  --head backend/mvp-bootstrap `
  --title "fix(api): complete attendance report OpenAPI contract" `
  --body "Fixes AttendanceReport OpenAPI serializers, removes schema warnings and duplicate security entries, updates the committed contract, adds regression tests, and repairs repository integration files."
```

پس از سبزشدن CI، PR با Merge Commit ادغام شود و Branch حذف نشود.

## ۶. همگام‌سازی بعد از Merge

```powershell
git fetch origin
git switch backend/mvp-bootstrap
git merge --ff-only origin/main
git push origin backend/mvp-bootstrap
```
