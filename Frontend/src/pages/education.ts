import { curriculumManagementRoles, managementReadRoles, teacherWriteRoles } from '../app/permissions.js';
import { renderWorkspacePage } from './workspace.js';

export function renderEducationWorkspacePage(): HTMLElement {
  return renderWorkspacePage({
    eyebrow: 'فضای کاری آموزش',
    title: 'آموزش و ارزیابی',
    description: 'از کلاس و ارائه‌درس شروع کنید؛ سپس ارزیابی، ثبت نمره و وضعیت تکمیل را در همان جریان پیگیری کنید.',
    groups: [
      {
        title: 'کارهای روزانه',
        description: 'مسیرهای اصلی برای اداره کلاس‌ها و ارزیابی‌های جاری.',
        cards: [
          { id: 'classes', title: 'کلاس‌ها و ارائه‌درس‌ها', description: 'کلاس، درس، دبیر و نوبت را در یک زمینه آموزشی بررسی کنید.', href: '/resources/course-offerings', icon: 'book', roles: teacherWriteRoles },
          { id: 'assessments', title: 'ارزیابی و دفتر نمره', description: 'ارزیابی‌های هر ارائه‌درس را باز کنید و نمره‌ها را از همان جریان ثبت یا پیگیری کنید.', href: '/resources/assessments', icon: 'chart', roles: teacherWriteRoles },
          { id: 'monthly-evaluations', title: 'ارزیابی جامع ماهانه', description: 'شاخص‌های دانش‌آموز را برای یک ماه ثبت یا اصلاح کنید.', href: '/manual-entry?task=education', icon: 'chart', roles: teacherWriteRoles },
          { id: 'results', title: 'نتایج و تکمیل نمرات', description: 'گزارش‌های آموزشی و پیش‌نویس‌های نیازمند پیگیری را بررسی کنید.', href: '/reports', icon: 'file', roles: managementReadRoles },
        ],
      },
      {
        title: 'راه‌اندازی برنامه درسی',
        description: 'تنظیمات کم‌تکرار برنامه درسی را از فضای عملیات روزانه جدا نگه دارید.',
        cards: [
          { id: 'curriculum-settings', title: 'برنامه درسی و انواع ارزیابی', description: 'درس‌ها، پایه‌ها، نوع ارزیابی و سیاست محاسبه را مدیریت کنید.', href: '/administration?section=curriculum', icon: 'settings', roles: curriculumManagementRoles },
        ],
      },
    ],
  });
}
