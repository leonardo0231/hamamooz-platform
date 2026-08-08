import type { Role } from '../api/types.js';

export type DashboardSection = 'attention' | 'metrics' | 'evaluation' | 'classes' | 'schools' | 'workflow' | 'alerts' | 'activity';

export interface RoleAction {
  label: string;
  href: string;
  icon: string;
}

export interface RoleExperience {
  role: Role;
  eyebrow: string;
  title: (name: string) => string;
  description: string;
  primaryAction: RoleAction;
  secondaryAction?: RoleAction;
  sectionOrder: DashboardSection[];
  metricOrder: Array<'students' | 'classes' | 'teachers' | 'missing_scores'>;
  evaluationTitle: string;
  evaluationDescription: string;
}

const experiences: Record<Role, RoleExperience> = {
  system_admin: {
    role: 'system_admin',
    eyebrow: 'کنترل پلتفرم',
    title: name => `وضعیت سامانه برای ${name}`,
    description: 'نمای چندسازمانی برای کنترل سلامت داده، حجم استفاده، دسترسی‌ها و نقاطی که نیازمند مداخله مدیریتی هستند.',
    primaryAction: { label: 'مدیریت کاربران', href: '/users', icon: 'users' },
    secondaryAction: { label: 'تنظیمات سامانه', href: '/settings', icon: 'settings' },
    sectionOrder: ['attention', 'metrics', 'schools', 'evaluation', 'workflow', 'alerts', 'activity', 'classes'],
    metricOrder: ['students', 'classes', 'teachers', 'missing_scores'],
    evaluationTitle: 'کیفیت ارزیابی در مدرسه انتخاب‌شده',
    evaluationDescription: 'برای تحلیل جزئی، یک شعبه را انتخاب کنید. داده‌ها فقط از API رسمی ارزیابی جامع خوانده می‌شوند.',
  },
  organization_admin: {
    role: 'organization_admin',
    eyebrow: 'مدیریت مجموعه',
    title: name => `نبض مجموعه، ${name}`,
    description: 'مقایسه شعب، کیفیت ثبت داده و نقاط پرریسک برای تصمیم‌گیری در سطح مجموعه؛ بدون ورود به جزئیات غیرضروری روزمره.',
    primaryAction: { label: 'گزارش‌ها', href: '/reports', icon: 'file' },
    secondaryAction: { label: 'ورود اطلاعات', href: '/imports', icon: 'upload' },
    sectionOrder: ['attention', 'metrics', 'schools', 'evaluation', 'classes', 'alerts', 'workflow', 'activity'],
    metricOrder: ['students', 'classes', 'missing_scores', 'teachers'],
    evaluationTitle: 'روند ارزیابی شعبه',
    evaluationDescription: 'با انتخاب یک مدرسه، روند ماهانه و توزیع عملکرد همان شعبه نمایش داده می‌شود.',
  },
  school_manager: {
    role: 'school_manager',
    eyebrow: 'مدیریت مدرسه',
    title: name => `امروز چه چیزی نیاز به توجه دارد، ${name}؟`,
    description: 'خلاصه تصمیم‌محور عملکرد مدرسه، کلاس‌های نیازمند پیگیری، هشدارهای باز و وضعیت تکمیل فرایندهای آموزشی.',
    primaryAction: { label: 'مرکز هشدارها', href: '/alerts', icon: 'bell' },
    secondaryAction: { label: 'گزارش‌ها', href: '/reports', icon: 'file' },
    sectionOrder: ['attention', 'metrics', 'evaluation', 'classes', 'alerts', 'workflow', 'activity', 'schools'],
    metricOrder: ['students', 'classes', 'missing_scores', 'teachers'],
    evaluationTitle: 'روند عملکرد و ارزیابی مدرسه',
    evaluationDescription: 'روند ماهانه، حوزه‌های قوی و ضعیف و توزیع عملکرد دانش‌آموزان در سال تحصیلی انتخاب‌شده.',
  },
  educational_deputy: {
    role: 'educational_deputy',
    eyebrow: 'اتاق عملیات آموزشی',
    title: name => `پیگیری آموزشی، ${name}`,
    description: 'تمرکز روی نمرات ثبت‌نشده، جریان تأیید ارزیابی‌ها، اختلاف عملکرد کلاس‌ها و دانش‌آموزان در حال افت.',
    primaryAction: { label: 'مدیریت ارزیابی‌ها', href: '/resources/assessments', icon: 'chart' },
    secondaryAction: { label: 'ثبت دستی', href: '/manual-entry', icon: 'edit' },
    sectionOrder: ['attention', 'metrics', 'workflow', 'evaluation', 'classes', 'alerts', 'activity', 'schools'],
    metricOrder: ['missing_scores', 'classes', 'students', 'teachers'],
    evaluationTitle: 'تحلیل آموزشی سال جاری',
    evaluationDescription: 'روند ماهانه و فهرست دانش‌آموزان دارای روند نزولی برای پیگیری سریع‌تر.',
  },
  operator: {
    role: 'operator',
    eyebrow: 'مرکز کیفیت داده',
    title: name => `ورود و کنترل اطلاعات، ${name}`,
    description: 'تمرکز روی کامل بودن داده‌ها، نمرات ثبت‌نشده و مسیرهای ورود اطلاعات؛ تحلیل‌ها به اندازه‌ای نمایش داده می‌شوند که خطاهای داده زود دیده شوند.',
    primaryAction: { label: 'ورود اطلاعات', href: '/imports', icon: 'upload' },
    secondaryAction: { label: 'ثبت و ویرایش دستی', href: '/manual-entry', icon: 'edit' },
    sectionOrder: ['attention', 'metrics', 'workflow', 'activity', 'evaluation', 'classes', 'alerts', 'schools'],
    metricOrder: ['missing_scores', 'students', 'classes', 'teachers'],
    evaluationTitle: 'کنترل پوشش ارزیابی‌ها',
    evaluationDescription: 'درصد تکمیل و روند ماهانه برای تشخیص سریع داده‌های ناقص یا ثبت‌های عقب‌افتاده.',
  },
  teacher: {
    role: 'teacher',
    eyebrow: 'فضای کاری دبیر',
    title: name => `کلاس‌های شما، ${name}`,
    description: 'نمای محدود به کلاس‌ها و ارائه‌درس‌های مجاز شما؛ با تمرکز روی ارزیابی، حضور و غیاب و مواردی که هنوز نیاز به ثبت یا پیگیری دارند.',
    primaryAction: { label: 'ثبت و مدیریت ارزیابی', href: '/resources/assessments', icon: 'chart' },
    secondaryAction: { label: 'حضور و غیاب', href: '/attendance', icon: 'calendar' },
    sectionOrder: ['attention', 'metrics', 'evaluation', 'classes', 'alerts', 'workflow', 'activity', 'schools'],
    metricOrder: ['missing_scores', 'classes', 'students', 'teachers'],
    evaluationTitle: 'روند دانش‌آموزان کلاس‌های شما',
    evaluationDescription: 'فقط داده‌های کلاس‌هایی نمایش داده می‌شوند که Backend برای حساب شما مجاز کرده است.',
  },
};

const rolePriority: Role[] = [
  'system_admin',
  'organization_admin',
  'school_manager',
  'educational_deputy',
  'operator',
  'teacher',
];

export function primaryRole(roles: Role[]): Role {
  return rolePriority.find(role => roles.includes(role)) ?? 'teacher';
}

export function roleExperience(roles: Role[]): RoleExperience {
  return experiences[primaryRole(roles)];
}
