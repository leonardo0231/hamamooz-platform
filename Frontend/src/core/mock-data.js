export const dashboardData = {
  school: 'دبیرستان اندیشه', academicYear: '۱۴۰۵–۱۴۰۶', manager: 'مریم نادری', average: 16.82,
  kpis: [
    { label: 'میانگین مدرسه', value: '۱۶٫۸۲', delta: '+۰٫۴', tone: 'purple', icon: 'graduation' },
    { label: 'دانش‌آموزان نیازمند پیگیری', value: '۱۲', delta: '۳ مورد جدید', tone: 'pink', icon: 'users' },
    { label: 'حضور امروز', value: '۹۷٪', delta: '+۱٫۲٪', tone: 'green', icon: 'attendance' },
    { label: 'هشدارهای مهم', value: '۷', delta: '۲ بحرانی', tone: 'orange', icon: 'alert' },
  ],
  performance: [14.5, 15.1, 15.8, 16.2, 16.6, 16.9, 17.2],
  months: ['مهر', 'آبان', 'آذر', 'دی', 'بهمن', 'اسفند', 'فروردین'],
  grades: [
    { label: 'پایه دهم', value: 16.2 }, { label: 'پایه یازدهم', value: 15.7 },
    { label: 'پایه دوازدهم', value: 17.9 }, { label: 'پایه نهم', value: 15.8 },
  ],
};

export const students = [
  { id: 'amir-rezaei', name: 'امیرحسین رضایی', code: '۱۴۰۵۰۱۲۴', grade: 'پایه نهم', className: '۹/۲', average: 17.86, attendance: 96, status: 'فعال', risk: 'critical', avatar: 'ا ر' },
  { id: 'narges-mousavi', name: 'نرگس موسوی', code: '۱۴۰۵۰۱۳۱', grade: 'پایه هشتم', className: '۸/۱', average: 18.42, attendance: 98, status: 'فعال', risk: 'important', avatar: 'ن م' },
  { id: 'ali-mohammadi', name: 'علی محمدی', code: '۱۴۰۵۰۱۴۸', grade: 'پایه دهم', className: '۱۰/۳', average: 16.35, attendance: 91, status: 'فعال', risk: 'review', avatar: 'ع م' },
  { id: 'sara-ahmadi', name: 'سارا احمدی', code: '۱۴۰۵۰۱۵۶', grade: 'پایه نهم', className: '۹/۱', average: 18.06, attendance: 94, status: 'فعال', risk: 'none', avatar: 'س ا' },
  { id: 'parsa-heydari', name: 'پارسا حیدری', code: '۱۴۰۵۰۱۷۲', grade: 'پایه هشتم', className: '۸/۳', average: 15.92, attendance: 89, status: 'فعال', risk: 'important', avatar: 'پ ح' },
  { id: 'niayesh-karimi', name: 'نیایش کریمی', code: '۱۴۰۵۰۱۹۱', grade: 'پایه یازدهم', className: '۱۱/۲', average: 17.44, attendance: 97, status: 'فعال', risk: 'review', avatar: 'ن ک' },
];

export const alerts = [
  { id: 1, studentId: 'amir-rezaei', student: 'امیرحسین رضایی', meta: 'پایه نهم · کلاس ۹/۲', title: 'کاهش معنادار ریاضی در سه آزمون اخیر', type: 'افت تحصیلی', severity: 'critical', time: 'امروز · ۱۰:۳۰', evidence: ['۱۸٫۸ ← ۱۲ ← ۸', 'سه آزمون متوالی', 'غیبت در ۲ جلسه'] },
  { id: 2, studentId: 'narges-mousavi', student: 'نرگس موسوی', meta: 'پایه هشتم · کلاس ۸/۱', title: 'افزایش غیبت در دو هفته اخیر', type: 'غیبت غیرموجه', severity: 'important', time: 'امروز · ۰۹:۱۵', evidence: ['۴ غیبت در ۱۴ روز', 'کاهش مشارکت کلاسی'] },
  { id: 3, studentId: 'ali-mohammadi', student: 'علی محمدی', meta: 'پایه دهم · کلاس ۱۰/۳', title: 'کاهش مشارکت در فعالیت‌های کلاسی', type: 'نیازمند بررسی', severity: 'review', time: 'دیروز · ۱۴:۴۵', evidence: ['۳ تکلیف تحویل‌نشده', 'افت مشارکت ۲۵٪'] },
  { id: 4, studentId: 'sara-ahmadi', student: 'سارا احمدی', meta: 'پایه نهم · کلاس ۹/۱', title: 'رفتار پرخطر در حیاط مدرسه', type: 'رفتاری', severity: 'important', time: 'دیروز · ۱۱:۲۰', evidence: ['ثبت توسط معاون', 'نیازمند گفت‌وگو'] },
  { id: 5, studentId: 'parsa-heydari', student: 'پارسا حیدری', meta: 'پایه هشتم · کلاس ۸/۳', title: 'تأخیر مکرر در حضور', type: 'حضور و غیاب', severity: 'review', time: '۲ روز پیش · ۰۸:۱۰', evidence: ['۵ تأخیر در ماه جاری'] },
];

export const studentProfile = {
  ...students[0], rank: 5, growth: 8, absences: 2,
  strengths: ['فیزیک', 'علوم تجربی', 'انگلیسی', 'تفکر و سبک زندگی'],
  improvements: ['ریاضی', 'عربی', 'ادبیات فارسی'],
  trend: [13.8, 14.9, 15.8, 16.2, 17.1, 17.86],
  events: [
    { title: 'ثبت نمره ریاضی فصل ۳', actor: 'توسط مرضیه کاظمی', date: '۱۴۰۵/۰۲/۱۲', tone: 'purple' },
    { title: 'حضور در جلسه مشاوره تحصیلی', actor: 'توسط دکتر سهرابی', date: '۱۴۰۵/۰۲/۱۰', tone: 'green' },
    { title: 'ثبت تذکر انضباطی (تأخیر)', actor: 'توسط علی محمدی', date: '۱۴۰۵/۰۲/۰۸', tone: 'orange' },
  ],
};

export const genericPageData = {
  performance: { title: 'عملکرد آموزشی', subtitle: 'تحلیل روند نمرات، پایه‌ها و درس‌ها', icon: 'chart', metrics: [['میانگین کل', '۱۶٫۸۲'], ['رشد ماهانه', '+۶٫۲٪'], ['کلاس‌های فعال', '۲۴'], ['ثبت نمره امروز', '۱۸۶']] },
  attendance: { title: 'حضور و غیاب', subtitle: 'پایش وضعیت حضور روزانه و الگوهای غیبت', icon: 'calendar', metrics: [['حضور امروز', '۹۷٪'], ['غیبت موجه', '۱۸'], ['غیبت غیرموجه', '۱۲'], ['تأخیر امروز', '۹']] },
  suggestions: { title: 'پیشنهادهای هوشمند', subtitle: 'اقدام‌های پیشنهادی مبتنی بر داده‌های آموزشی و رفتاری', icon: 'sparkles', metrics: [['پیشنهاد جدید', '۱۶'], ['در حال اجرا', '۹'], ['تکمیل‌شده', '۲۸'], ['نرخ اثرگذاری', '۸۲٪']] },
  reports: { title: 'گزارش‌ساز', subtitle: 'ساخت و دریافت گزارش‌های مدیریتی مدرسه', icon: 'report', metrics: [['گزارش آماده', '۲۴'], ['در حال ساخت', '۳'], ['قالب فعال', '۸'], ['دریافت این ماه', '۱۱۲']] },
  imports: { title: 'ورود اطلاعات', subtitle: 'بارگذاری امن اطلاعات دانش‌آموزان، کلاس‌ها و ارزیابی‌ها', icon: 'upload', metrics: [['ورود موفق', '۳۶'], ['در حال پردازش', '۲'], ['نیازمند اصلاح', '۴'], ['رکورد این ماه', '۲٬۸۴۰']] },
  'manual-entry': { title: 'ثبت و ویرایش دستی', subtitle: 'ثبت مستقیم داده‌های آموزشی در حوزه فعال', icon: 'edit', metrics: [['فرم فعال', '۱۲'], ['پیش‌نویس من', '۵'], ['ثبت امروز', '۳۱'], ['نیازمند تکمیل', '۷']] },
  users: { title: 'مدیریت کاربران', subtitle: 'کاربران، نقش‌ها و سطح دسترسی سامانه', icon: 'users', metrics: [['کاربر فعال', '۸۶'], ['مدیر', '۴'], ['دبیر', '۵۲'], ['ورود امروز', '۶۸']] },
  roles: { title: 'نقش‌ها و دسترسی‌ها', subtitle: 'مدیریت مجوزها در سطح مجموعه و مدرسه', icon: 'shield', metrics: [['نقش تعریف‌شده', '۹'], ['انتساب فعال', '۱۰۴'], ['درخواست جدید', '۲'], ['تغییر این ماه', '۱۴']] },
  settings: { title: 'تنظیمات سامانه', subtitle: 'پیکربندی مدرسه، سال تحصیلی و سیاست‌ها', icon: 'settings', metrics: [['شعب فعال', '۳'], ['سال تحصیلی', '۱۴۰۵–۱۴۰۶'], ['سیاست فعال', '۱۸'], ['آخرین پشتیبان', 'امروز']] },
};
