# مدل داده و قواعد دامنه

## اصول عمومی

- شناسه عمومی مدل‌های دامنه UUID است.
- داده‌های اصلی دامنه از `SoftDeleteModel` استفاده می‌کنند؛ تاریخچه و Snapshot حذف فیزیکی نمی‌شوند.
- رابطه‌های حساس عمدتاً `PROTECT` هستند تا حذف، تاریخچه رسمی را خراب نکند.
- زمان‌های ایجاد/ویرایش در مدل پایه نگهداری می‌شوند.
- constraint دیتابیس مکمل validation دامنه است، نه جایگزین آن.

## سازمان و دسترسی

```mermaid
erDiagram
    ORGANIZATION ||--o{ SCHOOL : owns
    ORGANIZATION ||--o{ ACADEMIC_YEAR : defines
    ACADEMIC_YEAR ||--o{ TERM : contains
    ORGANIZATION ||--o{ GRADE_LEVEL : defines
    SCHOOL ||--o{ CLASS_SECTION : contains
    USER ||--o{ ROLE_ASSIGNMENT : receives
    ORGANIZATION ||--o{ ROLE_ASSIGNMENT : scopes
    SCHOOL ||--o{ ROLE_ASSIGNMENT : scopes
```

قواعد مهم:

- کد مجموعه یکتا است.
- کد شعبه در مجموعه یکتا است.
- فقط یک سال جاری فعال در هر مجموعه وجود دارد.
- کد و ترتیب پایه در مجموعه یکتا است.
- کد کلاس در شعبه/سال یکتا است.
- Scope نقش باید با نوع نقش سازگار باشد؛ نقش سیستمی، مجموعه‌ای و شعبه‌ای constraint جدا دارند.

## دانش‌آموز و ثبت‌نام

```mermaid
erDiagram
    ORGANIZATION ||--o{ STUDENT : owns
    STUDENT ||--o{ ENROLLMENT : has
    SCHOOL ||--o{ ENROLLMENT : receives
    ACADEMIC_YEAR ||--o{ ENROLLMENT : scopes
    GRADE_LEVEL ||--o{ ENROLLMENT : assigns
    CLASS_SECTION ||--o{ ENROLLMENT : groups
    STUDENT ||--o{ STUDENT_GUARDIAN : links
    GUARDIAN ||--o{ STUDENT_GUARDIAN : links
    ENROLLMENT ||--o{ ENROLLMENT_EVENT : records
```

دانش‌آموز FK دائمی به کلاس ندارد. عضویت کلاس فقط در Enrollment و بازه زمانی آن ثبت می‌شود. تغییر کلاس، Enrollment قبلی را می‌بندد و Enrollment جدید می‌سازد؛ انتقال شعبه نیز مبدأ و مقصد را نگه می‌دارد.

قیود:

- کد ملی دانش‌آموز در هر مجموعه یکتا است.
- در هر سال فقط یک Enrollment فعال برای دانش‌آموز وجود دارد.
- شماره دانش‌آموزی فعال در شعبه/سال یکتا است.
- شعبه، سال، پایه و کلاس Enrollment باید متعلق به یک مجموعه و بازه سازگار باشند.
- کاهش ظرفیت کلاس پایین‌تر از تعداد Enrollment فعال رد می‌شود.
- تاریخ خروج/تغییر نمی‌تواند قبل از تاریخ ورود باشد.

## آموزش و نمره

```mermaid
erDiagram
    GRADE_LEVEL ||--o{ GRADE_SUBJECT : defines
    SUBJECT ||--o{ GRADE_SUBJECT : maps
    CLASS_SECTION ||--o{ COURSE_OFFERING : offers
    GRADE_SUBJECT ||--o{ COURSE_OFFERING : scopes
    TERM ||--o{ COURSE_OFFERING : schedules
    COURSE_OFFERING ||--o{ ASSESSMENT : contains
    ASSESSMENT ||--o{ SCORE : records
    ENROLLMENT ||--o{ SCORE : receives
    SCORE ||--o{ SCORE_REVISION : audits
    ENROLLMENT ||--o{ SUBJECT_RESULT : summarizes
    ENROLLMENT ||--o{ TERM_RESULT : summarizes
```

قیود:

- Subject code و AssessmentType code در مجموعه یکتا هستند.
- GradeSubject برای هر پایه/درس یکتا است.
- CourseOffering برای کلاس/درس/نوبت یکتا است.
- Assessment برای offering/title/date یکتا است.
- هر Enrollment برای هر Assessment یک Score دارد.
- نمره منفی در دیتابیس مجاز نیست؛ سقف در validation کنترل می‌شود.
- CalculationPolicy فعال در هر Scope فقط یکی است.

### state machine ارزیابی

```mermaid
stateDiagram-v2
    [*] --> draft
    draft --> submitted: submit + complete roster
    rejected --> submitted: اصلاح و submit
    submitted --> approved: reviewer approve
    submitted --> rejected: reviewer reject
    approved --> locked: reviewer lock
    locked --> locked: correct-locked score + revision
```

ویرایش عادی پس از Lock مسدود است. اصلاح استثنایی نمره قفل‌شده Assessment را Unlock نمی‌کند و ScoreRevision مستقل می‌سازد.

### وضعیت نمره

| مقدار | معنی | رفتار محاسباتی پیش‌فرض |
|---|---|---|
| `present` | نمره ثبت‌شده | نرمال‌سازی و ورود به میانگین |
| `excused_absent` | غیبت موجه | حذف از مخرج |
| `unexcused_absent` | غیبت غیرموجه | صفر، قابل تنظیم در Policy |
| `not_entered` | ثبت نشده | حذف از محاسبه و علامت ناقص |

### فرمول

هر نمره به مقیاس ۲۰ تبدیل می‌شود:

\[
N_i = \frac{raw_i}{max_i} \times 20
\]

میانگین درس:

\[
SubjectAverage = \frac{\sum(N_i \times weight_i)}{\sum weight_i}
\]

معدل نوبت:

\[
TermAverage = \frac{\sum(SubjectAverage_j \times coefficient_j)}{\sum coefficient_j}
\]

تمام محاسبات Decimal هستند. گردکردن فقط در مرز نتیجه با `half_up`، `half_even` یا `down` و صفر تا چهار رقم اعشار انجام می‌شود. رتبه کلاس Dense است؛ نمره‌های برابر رتبه برابر دارند و رتبه بعدی پرش نمی‌کند.

## حضور و غیاب

```mermaid
erDiagram
    ATTENDANCE_POLICY ||--o{ ATTENDANCE_ALERT : produces
    CLASS_SECTION ||--o{ ATTENDANCE_SESSION : has
    COURSE_OFFERING ||--o{ ATTENDANCE_SESSION : period
    ATTENDANCE_SESSION ||--o{ ATTENDANCE_RECORD : contains
    ENROLLMENT ||--o{ ATTENDANCE_RECORD : receives
    ATTENDANCE_RECORD ||--o{ ABSENCE_EVIDENCE : attaches
    ATTENDANCE_RECORD ||--o{ ATTENDANCE_RECORD_REVISION : audits
    ENROLLMENT ||--o{ ATTENDANCE_ALERT : triggers
    ENROLLMENT ||--o{ PARENT_NOTIFICATION : notifies
```

Session دو Scope دارد: `daily` و `period`. وضعیت‌ها `draft`, `finalized`, `cancelled` هستند. رکوردها `present`, `absent_excused`, `absent_unexcused` و workflow عذر `not_required`, `pending`, `approved`, `rejected` دارند.

قواعد:

- جلسه روزانه برای کلاس/تاریخ یکتا است.
- جلسه زنگ برای کلاس/تاریخ/شماره زنگ یکتا است.
- هر Enrollment در هر Session یک رکورد دارد.
- roster بر اساس عضویت معتبر در تاریخ جلسه ساخته می‌شود.
- finalize فقط با roster کامل مجاز است.
- Session نهایی فقط از مسیر correction و همراه revision تغییر می‌کند.
- درخواست عذر تا زمان approval در محاسبه، غیرموجه باقی می‌ماند.
- هشدار فقط از Sessionهای نهایی محاسبه می‌شود.
- هشدار open/acknowledged تکراری برای Scope فعال ساخته نمی‌شود.
- ParentNotification با dedupe key و وضعیت‌های queue تا dead-letter کنترل می‌شود.

## Import و Report

`ImportJob` شامل نوع، checksum، فایل، وضعیت، شمارنده‌ها و خطاهای ردیفی است. فایل تکراری فعال در Scope یکسان با unique constraint رد می‌شود.

`ReportArchive` شامل Scope، نوع، وضعیت، Snapshot JSON، نسخه فرمول و فایل خروجی است. Snapshot باعث می‌شود تغییر بعدی نام کلاس یا نمره، معنای گزارش رسمی قبلی را تغییر ندهد.

## Audit

`AuditEvent` actor، action، entity، Scope، Request ID، IP و metadata/changes پالایش‌شده را نگه می‌دارد. فیلدهای حساس مانند password، national ID، phone، email، address، note و reason در Audit عمومی redacted یا حذف می‌شوند.
