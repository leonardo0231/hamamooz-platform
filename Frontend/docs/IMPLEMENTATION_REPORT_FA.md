# گزارش پیاده‌سازی Frontend هم‌آموز

## 1. نتیجه‌ی تحلیل اولیه

Branch مرجع Frontend اپلیکیشن اجرایی نداشت و فقط README تحویل داده بود. Backend یک پروژه Django REST Framework در Monorepo است و قرارداد رسمی آن در `contracts/openapi.yaml` قرار دارد. قرارداد بررسی‌شده شامل ۹۲ Path، ۱۶۴ Operation و ۱۴۲ Schema است.

منابع بررسی‌شده:

- ساختار کامل Repository و Branchهای مرجع
- کد Backend شامل URLها، Viewها، Serializerها، Modelها، Permissionها و تست‌ها
- `contracts/openapi.yaml` و API changelog/handoff
- تصاویر مرجع Dashboard، Student Profile و Alert Center

## 2. Stack و معماری نهایی

| بخش | پیاده‌سازی |
|---|---|
| زبان | TypeScript Strict |
| Build | TypeScript compiler + Node build scripts |
| Routing | Client-side Router با Dynamic Import |
| Client State | Store مرکزی کوچک و observable |
| Server State | Fetch مستقیم، Cancellation، Retry و Scope invalidation در سطح صفحات |
| Styling | CSS Design Tokens، RTL، Responsive |
| Form | Schema-driven Form از OpenAPI |
| Validation | HTML validation + قواعد Schema + خطاهای Field از Backend |
| HTTP Client | Client مرکزی مبتنی بر Fetch و XHR برای Upload Progress |
| Auth | JWT Access/Refresh، Session Recovery و Shared Refresh Promise |
| Notification | Toast، Alert، Error/Empty/Loading/Skeleton |
| Testing | Node Test Runner + Typecheck + Static Lint |

انتخاب عدم افزودن Framework یا UI Library به این دلیل بود که پروژه‌ی موجود Stack فرانت‌اند نداشت و محیط تحویل نیز وابستگی Runtime آماده‌ای ارائه نمی‌کرد. نتیجه یک SPA واقعی با صفر وابستگی Runtime، Bundle کوچک و API سطح مرورگر است؛ تغییر تکنولوژی موجودی نیز رخ نداده است.

## 3. لایه API

پیاده‌سازی‌شده:

- Base URL و Timeout از Environment
- Endpoint Catalog تولیدشده از OpenAPI
- Endpoint Registry مرکزی که Operation ID را به Path رسمی قرارداد متصل می‌کند
- Request/Response Typeهای مشترک
- Authorization و Scope Headerهای مرکزی
- `X-Request-ID` برای تمام درخواست‌ها
- Shared Refresh Promise برای جلوگیری از Refresh هم‌زمان
- جلوگیری از Retry Loop با `retryAuth: false`
- مدیریت 400، 401، 403، 404، 409، 429، 503 و Network Error
- نگاشت Validation Error به فیلد مربوطه
- AbortSignal و Timeout
- Multipart Upload و Upload Progress
- Refresh Flow برای Uploadهای XHR
- Pagination، Search، Filter و Ordering براساس Query Parameterهای قرارداد
- Blob download برای گزارش‌ها
- Adapterهای محدود و تست‌شده برای Actionهایی که Schema تولیدشده‌ی DRF با Serializer واقعی Backend هم‌خوان نبود

## 4. Authentication و Access Control

کامل شده:

- Login با username یا email در فیلد identifier
- دریافت User واقعی از `auth/me/`
- Refresh Token و Rotation در صورت پاسخ Backend
- Session Recovery
- Remember Me
- Logout و پاک‌سازی State حساس
- Change Password
- Guest Guard و Private Route Guard
- Role-based Route Guard برای مدیریت کاربران، نقش‌ها و Import
- Scope انتخابی Organization/School
- انتقال به صفحه 403 و 404

قابلیت‌های زیر در Backend/OpenAPI وجود ندارند و عمداً حدس زده یا شبیه‌سازی نشده‌اند:

- Register
- Forgot Password
- Reset Password
- Verify Email یا Phone

## 5. صفحات و Flowهای پیاده‌سازی‌شده

- Login
- Dashboard واقعی با Summary API
- Scope Selector برای Organization و School
- Student List، Search، Filter، Sort، Pagination و CRUD
- Student Detail و Guardian Flow
- Alert Center دوپنل با Filter، Acknowledge، Resolve و Evaluate
- Attendance Sessions، Records، Policies و Parent Notifications
- Assessment، Score و Workflow Actionها
- Course Offerings و Results
- Reports: Preview، Create، Archive و Download
- Imports: Multipart Upload، Progress، History و Retry
- Users و Role Assignments
- Profile و Change Password
- Settings و نمایش اطلاعات قرارداد/محیط
- Generic Resource CRUD برای Tagهای رسمی قرارداد
- 403، 404 و Error Page

Operationهای فرعی مانند approve، reject، submit، lock، bulk-mark، finalize، cancel، correct، transfer، retry، roster، scores و results از Catalog واقعی OpenAPI استخراج و اجرا می‌شوند.

## 6. Design System و UI

Tokenهای مرکزی برای رنگ، Typography، Spacing، Radius، Shadow، Breakpoint، Transition و Z-index تعریف شده‌اند. رابط مطابق زبان بصری تصاویر مرجع ساخته شده است:

- Sidebar بنفش تیره
- Metric Cardها و Chart Cardها
- Profile Hero و Tabs
- Alert Center دوپنل
- Button، Input، Select، Table، Card، Badge، Dialog، Toast، Skeleton، Spinner، Empty و Error State
- Focus visible، Keyboard navigation، Dialog Escape و Semantic markup
- RTL کامل و رفتار مناسب متن و UUID/Email با LTR موضعی

Responsive behavior:

- Sidebar در Mobile به Drawer تبدیل می‌شود.
- Tableها در Mobile به Card Row تبدیل می‌شوند.
- Dialog و Form در نمایشگر کوچک تک‌ستونه می‌شوند.
- Touch targetها، Overflow و Wide-screen container کنترل شده‌اند.

## 7. فایل‌های اصلی ایجادشده

- `Frontend/package.json`
- `Frontend/.env.example`
- `Frontend/src/app/*`
- `Frontend/src/api/*`
- `Frontend/src/components/*`
- `Frontend/src/pages/*`
- `Frontend/src/styles/app.css`
- `Frontend/scripts/*`
- `Frontend/tests/*`
- `Frontend/docs/*`

هیچ فایل Backend حذف یا بازنویسی نشده است.

### باگ‌ها و ریسک‌های اصلاح‌شده

- جلوگیری از Refresh هم‌زمان چند درخواست و Retry Loop بی‌نهایت
- اعمال همان Refresh Flow روی Uploadهای XHR و حذف Listener لغو پس از پایان درخواست
- نگاشت پاسخ `204 No Content` در Upload به مقدار Void به‌جای رشته خالی
- پاک‌سازی کامل Session، Cache حساس و Scope هنگام Logout یا شکست Refresh
- جلوگیری از Open Redirect در `returnTo` صفحه Login
- اعتبارسنجی Session با `auth/me/` به‌جای اعتماد صرف به وجود Token
- اصلاح Scope ذخیره‌شده‌ی منقضی یا خارج از دسترسی پس از بارگذاری Organization/School
- اعمال `must_change_password` در Router و الزام رمز فعلی برای تغییر رمز کاربر جاری
- هم‌ترازی Action Payloadها با Serializer واقعی Backend در موارد ناسازگار با Schema خودکار
- حذف Endpointهای پراکنده از صفحات و اتصال آن‌ها به Operation IDهای قرارداد
- جلوگیری از باقی‌ماندن کنترل Write فعال پس از تغییر Scope یا Role

### Dependencyهای اضافه‌شده

تنها Dependency افزوده‌شده `typescript@5.8.3` و فقط در `devDependencies` است. هیچ Dependency Runtime، UI Library یا HTTP Library اضافه نشده است. نسخه TypeScript دقیقاً Pin شده تا تغییر ناخواسته Minor/Minor رخ ندهد.

## 8. نتیجه کنترل کیفیت

| کنترل | نتیجه |
|---|---|
| TypeScript strict compile | موفق |
| Production build | موفق |
| Static lint | موفق |
| Automated Frontend tests | ۱۲ از ۱۲ موفق |
| SPA fallback smoke test | موفق؛ `/`، `/login` و Deep Link |
| OpenAPI critical endpoint assertions | موفق |
| Django system check | موفق با تنظیمات Test |
| Backend automated tests | ۲۷ تست Auth/API/Dashboard/Security موفق |
| API smoke با Backend واقعی | موفق؛ Token، Me، Scope، Dashboard، Students، Alerts، Refresh، Logout و CORS |
| Browser E2E | مسدودشده توسط Policy محیط اجرای Chromium با خطای `ERR_BLOCKED_BY_ADMINISTRATOR` |

## 9. وضعیت بخش‌ها

| بخش | وضعیت | توضیح |
|---|---|---|
| معماری و Build | تکمیل‌شده | Build قابل اجرا و مستند |
| API Client | تکمیل‌شده | شامل Refresh، Scope، Error و Upload |
| Login/Logout/Me/Refresh | تکمیل‌شده | مطابق Backend |
| Register | نیازمند تغییر Backend | Endpoint وجود ندارد |
| Forgot/Reset Password | نیازمند تغییر Backend | Endpoint وجود ندارد |
| Verify Email/Phone | نیازمند تغییر Backend | Endpoint وجود ندارد |
| Dashboard | تکمیل‌شده | متصل به API واقعی |
| Student/Guardian | تکمیل‌شده | CRUD و Flowهای رسمی |
| Attendance/Alerts | تکمیل‌شده | عملیات Workflow رسمی |
| Assessment/Scores | تکمیل‌شده | Resource و Actionهای رسمی |
| Reports | تکمیل‌شده | Preview/Create/Download |
| Imports | تکمیل‌شده | Upload Progress و Retry |
| Users/Roles | تکمیل‌شده | Guard و CRUD |
| Realtime/WebSocket | نیازمند تغییر Backend | قرارداد Realtime وجود ندارد |
| Responsive/RTL | تکمیل‌شده | Mobile تا Wide Desktop |
| Accessibility پایه | تکمیل‌شده | Semantic، Focus، Label، ARIA |
| Browser E2E | مسدودشده | Backend و حساب تست اجرا شدند، اما Policy محیط Chromium دسترسی به URL محلی را با `ERR_BLOCKED_BY_ADMINISTRATOR` بست |

## 10. ریسک‌ها و محدودیت‌های باقی‌مانده

1. قرارداد JWT فعلی Refresh Token را در Body به Client می‌دهد. برای امنیت قوی‌تر Production، پیشنهاد می‌شود Backend از HttpOnly Secure SameSite Cookie استفاده کند.
2. Generic Schema Form برای Relationها UUID واقعی می‌گیرد؛ Endpointهای lookup اختصاصی برای همه Relationها در قرارداد موجود نیستند. مواردی که endpoint مستقل دارند از صفحات مدیریت قابل انتخاب/کپی هستند، اما UX انتخاب Relation با Autocomplete نیازمند قرارداد lookup استاندارد از Backend است.
3. Dashboard و Student Profile فقط داده‌های واقعاً موجود در API را نمایش می‌دهند. Metricهای طراحی که Aggregate API ندارند با عدد ساختگی جایگزین نشده‌اند.
4. گزارش Download طبق کد Backend به‌صورت Blob مصرف می‌شود، هرچند Media Type تولیدشده در OpenAPI برای برخی پاسخ‌ها به‌دقت FileResponse نیست؛ بهتر است Schema Backend اصلاح و OpenAPI بازتولید شود.
5. Schema تولیدشده برای تعدادی از DRF `@action`ها به Serializer مدل اصلی اشاره می‌کرد، در حالی که View از Payload اختصاصی استفاده می‌کند. Frontend برای Actionهای شناخته‌شده Adapter و تست قرارداد دارد، اما منبع اصلی باید در Backend اصلاح و OpenAPI مجدداً تولید شود.
6. تست API واقعی انجام شد؛ اجرای E2E مرورگری فقط به‌دلیل Policy محیط Chromium مسدود ماند و نه به‌دلیل خطای Frontend یا نبود Credential.
7. محیط تحویل به Registry npm دسترسی نداشت؛ بنابراین `package-lock.json` قابل تولید و اعتبارسنجی نبود. Dependency توسعه دقیقاً روی `typescript@5.8.3` Pin شده است و `npm install` در محیط متصل Lockfile را تولید می‌کند. این محدودیت روی Bundle Production اثر Runtime ندارد، اما Lockfile باید پیش از Merge نهایی Commit شود.
