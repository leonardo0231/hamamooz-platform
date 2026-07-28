# MVP Permission Matrix

این ماتریس خلاصه نقش‌هاست. همه سلول‌ها علاوه بر نقش، به RoleAssignment فعال، Scope هدر، QuerySet، مالکیت کلاس/درس و object permission محدود می‌شوند.

راهنما: `G` کل سامانه، `O` مجموعه، `S` شعبه، `T` فقط تخصیص تدریس خود، `R` فقط خواندن، `-` ممنوع.

| قابلیت | System admin | Organization admin | School manager | Educational deputy | Operator | Teacher |
|---|---:|---:|---:|---:|---:|---:|
| ایجاد/حذف مجموعه | G | - | - | - | - | - |
| ویرایش مجموعه | G | O | - | - | - | - |
| مدیریت شعبه/سال/نوبت/پایه | G | O | R | R | R | R |
| مدیریت کلاس | G | O | S | S | S | R در کلاس تدریس |
| مدیریت کاربر و RoleAssignment | G | O | S با محدودیت سلسله‌مراتب | R | - | فقط خود |
| مدیریت دانش‌آموز/ولی/ثبت‌نام | G | O | S | S | S | R در کلاس تدریس |
| تغییر کلاس/انتقال/وضعیت ثبت‌نام | G | O | S | S | S | - |
| مدیریت Subject/GradeSubject/AssessmentType | G | O | R | O از Scope مجاز | R | R |
| مدیریت CourseOffering | G | O | S | S | S | R برای خود |
| ایجاد/ویرایش ارزیابی | G | O | S | S | S | T |
| ثبت گروهی و Submit نمره | G | O | S | S | S | T |
| Approve/Reject/Lock ارزیابی | G | O | S | S | - | - |
| اصلاح نمره قفل‌شده | G | O | S | S | - | - |
| مدیریت CalculationPolicy | G | O | R | O از Scope مجاز | R | R |
| Import | G | O | S | S | S | - |
| پیش‌نمایش/تولید گزارش | G | O | S | S | S | T/کلاس مجاز |
| ثبت Attendance روزانه | G | O | S | S | S | - |
| ثبت Attendance زنگ | G | O | S | S | S | T |
| اصلاح Attendance و ثبت عذر | G | O | S | S | S | T برای جلسه خود |
| تأیید/رد عذر | G | O | S | S | - | - |
| مدیریت Policy/Alert حضور | G | O | S | S | - | - |
| گزارش Attendance | G | O | S | S | S | کلاس‌های مجاز |
| retry اعلان والدین | G | O | S | S | S | T در Scope مجاز |

## قواعد تکمیلی

- Write برای کاربر غیر `system_admin` بدون `X-School-ID` یا `X-Organization-ID` صریح رد می‌شود.
- Teacher فقط CourseOffering خودش را مدیریت می‌کند و Attendance روزانه برای او مجاز نیست.
- School manager نمی‌تواند حسابی را مدیریت کند که نقش فعال خارج از حوزه او دارد.
- Organization admin از طریق نقش مجموعه به همه شعب همان مجموعه دسترسی دارد.
- Action ناامن بدون mapping در `required_roles_by_action` به‌صورت پیش‌فرض رد می‌شود.
- AuditEvent در API عمومی ViewSet ندارد و از Django Admin یا ابزار عملیاتی مجاز بررسی می‌شود.
