# دستور یک commit برای تمام تغییرات امروز

## ۱. جایگزینی فایل‌ها

محتویات پوشه `Backend` این بسته را روی پوشه `Backend` repository کپی کنید. سپس از ریشه repository:

```bat
cd /d D:\Projects\hamamooz-platform
rmdir /s /q Backend\apps 2>nul
```

حذف `Backend\apps` عمدی است؛ ساختار فعال `Backend\hamamooz\apps` است.

## ۲. کنترل کیفیت

```bat
cd Backend
ruff check . --fix
ruff format .
ruff check .
ruff format --check .
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py migrate
pytest -q
python manage.py spectacular --api-version v1 --file build\openapi.yaml --validate
cd ..
```

روی Windows برای تست PDF، Pango باید نصب باشد یا suite را داخل Docker اجرا کنید.

## ۳. ساخت دقیق یک commit

```bat
git add -A
git diff --cached --check
git status --short
git commit -m "feat(backend): consolidate apps and harden attendance platform"
```

این commit تمام renameها، حذف ساختار legacy، attendance، migrationها، گزارش، امنیت، عملیات و
مستندات امروز را یکجا ثبت می‌کند.

## ۴. Push

اگر روی `backend/mvp-bootstrap` هستید:

```bat
git push origin backend/mvp-bootstrap
```

اگر تغییرات روی `cleanup/backend-consolidation` commit شده‌اند:

```bat
git switch backend/mvp-bootstrap
git merge --ff-only cleanup/backend-consolidation
git push origin backend/mvp-bootstrap
```

`--ff-only` تضمین می‌کند merge commit دوم ساخته نشود و در تاریخچه فقط همان یک commit باقی بماند.
