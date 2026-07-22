# گزارش اعتبارسنجی فنی

## بررسی‌های اجراشده

- `ruff check` روی تمام فایل‌های app: موفق.
- `python -m compileall` روی app: موفق.
- ساخت migration با Django 5.2.16: موفق.
- `migrate` روی SQLite تستی از صفر: موفق.
- `makemigrations --check --dry-run`: بدون تغییر جدید.
- `django check`: بدون issue.
- ۸ تست رفتاری در harness سازگار با نسخه‌ها و روابط پروژه: همگی موفق.

سناریوهای تست‌شده:

1. ایجاد جلسه روزانه از API، ثبت گروهی، محاسبه تأخیر/خروج و finalize.
2. جلوگیری از finalize roster ناقص.
3. جلوگیری از ثبت مستقیم غیبت موجه.
4. بارگذاری PDF معتبر، pending و تأیید مسئول.
5. محاسبه تعداد و درصد گزارش دانش‌آموز و scope مدرسه.
6. idempotency هشدار بعد از acknowledge.
7. اتصال امن اعلان والد به Enrollment و ارسال in-app.
8. رد فایل PDF با signature نامعتبر.

## محدودیت صادقانه اعتبارسنجی

دسترسی GitHub connector برای خواندن فایل‌های واقعی شاخه برقرار بود و معماری، مدل‌ها، RBAC، settings، router، Celery و تست fixture پروژه بررسی شدند. با این حال clone شبکه‌ای کامل مخزن در محیط اجرای محلی به‌دلیل عدم resolve شدن `github.com` ممکن نبود؛ بنابراین کل suite موجود مخزن روی checkout کامل اجرا نشده است. فایل `Backend/tests/test_attendance_api.py` برای اجرای مستقیم در خود مخزن تحویل شده است.
