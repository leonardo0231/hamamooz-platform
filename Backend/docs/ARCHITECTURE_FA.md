# معماری ماژول حضور و غیاب

## مدل دامنه

### AttendancePolicy
سیاست هر شعبه و سال تحصیلی برای آستانه تعداد/درصد غیبت، بازه محاسبه، احتساب غیبت موجه، الزام مدرک و کانال‌های گزارش والدین.

### AttendanceSession
جلسه حضور و غیاب در دو scope مستقل:

- `daily`: حضور روزانه کلاس
- `period`: حضور به تفکیک زنگ و `CourseOffering`

وضعیت‌های جلسه: `draft`، `finalized` و `cancelled`.

### AttendanceRecord
رکورد هر `Enrollment` در یک جلسه. اتصال به Enrollment باعث حفظ تاریخچه صحیح مدرسه، سال تحصیلی و کلاس حتی پس از انتقال دانش‌آموز می‌شود.

وضعیت‌ها:

- `present`
- `absent_unexcused`
- `absent_excused`

تأخیر و خروج زودهنگام به‌صورت دقیقه و زمان ورود/خروج نگهداری می‌شوند.

### AbsenceEvidence
مدارک خصوصی غیبت موجه با validation اندازه، پسوند و signature فایل.

### AttendanceRecordRevision
تاریخچه before/after همه اصلاحات رکورد همراه دلیل و کاربر تغییر‌دهنده.

### AttendanceAlert
هشدار warning/critical برای هر Enrollment و scope. هشدار `acknowledged` همچنان active محسوب می‌شود تا اجرای بعدی هشدار تکراری نسازد.

### ParentNotification
outbox اعلان والدین برای `in_app`، `email` و `sms`. هر اعلان مستقیماً به Enrollment متصل است تا scope کلاس و شعبه دقیق بماند.

## قواعد کلیدی

- یک جلسه روزانه برای هر کلاس/تاریخ.
- یک جلسه زنگ برای هر کلاس/تاریخ/شماره زنگ.
- یک رکورد برای هر Enrollment در هر جلسه.
- غیبت موجه فقط با `excuse_status=approved` و reviewer/time معتبر است.
- درخواست توجیه تا زمان تأیید همچنان غیبت غیرموجه محسوب می‌شود.
- جلسه نهایی‌شده فقط از endpoint اصلاح رکورد و همراه revision قابل تغییر است؛ bulk فقط روی draft کار می‌کند.
- هشدارها فقط از جلسات نهایی‌شده محاسبه می‌شوند.
- گزارش‌های دانش‌آموز، کلاس و مدرسه از aggregation گروهی استفاده می‌کنند تا N+1 query ایجاد نشود.

## RBAC

- ثبت روزانه: مدیر کل، مدیر مجموعه، مدیر شعبه، معاون آموزشی و اپراتور.
- ثبت زنگ: نقش‌های بالا و دبیر همان `CourseOffering`.
- تأیید/رد غیبت موجه: مدیر کل، مدیر مجموعه، مدیر شعبه و معاون آموزشی.
- مدیریت Policy و هشدار: reviewerها.
- خواندن گزارش‌ها: مطابق scope موجود پروژه و کلاس‌های مجاز کاربر.

## امنیت و قابلیت اطمینان

- استفاده از `RolePermission`، `selected_school_ids` و `allowed_class_ids` پروژه.
- transaction و `select_for_update` برای bulk، finalize، review و alert evaluation.
- audit با `record_audit` موجود پروژه.
- soft delete مطابق base model پروژه.
- dedupe key برای جلوگیری از اعلان تکراری.
- unique constraint فعال برای هشدارهای open/acknowledged.
- storage-neutral؛ سازگار با FileSystem در تست و S3/MinIO در production.
