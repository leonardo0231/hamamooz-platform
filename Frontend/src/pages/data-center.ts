import { dataCenterWorkspaceRoles } from '../app/workspaces.js';
import { renderWorkspacePage } from './workspace.js';

export function renderDataCenterWorkspacePage(): HTMLElement {
  return renderWorkspacePage({
    eyebrow: 'عملیات داده',
    title: 'مرکز داده',
    description: 'ورود گروهی را اولویت دهید. ثبت و اصلاح دستی برای استثناها و اصلاح‌های کنترل‌شده نگه داشته شده است.',
    groups: [
      {
        title: 'ورود و کنترل',
        description: 'فایل‌ها، نتیجه پردازش و خطاهای قابل رفع را در یک جریان ببینید.',
        cards: [
          { id: 'imports', title: 'ورود از فایل', description: 'فایل جامع را بارگذاری کنید، نتیجه پردازش را ببینید و خطاها را برطرف کنید.', href: '/imports', icon: 'upload', roles: dataCenterWorkspaceRoles },
        ],
      },
      {
        title: 'اصلاح پیشرفته',
        description: 'این مسیرها برای تصحیح محدود داده هستند، نه گردش کار اصلی مدرسه.',
        cards: [
          { id: 'student-correction', title: 'اصلاح داده دانش‌آموز و خانواده', description: 'رکوردهای دانش‌آموز، ولی و ثبت‌نام را با راهنمایی فرم اصلاح کنید.', href: '/manual-entry?task=students', icon: 'users', roles: dataCenterWorkspaceRoles },
          { id: 'education-correction', title: 'اصلاح آموزشی و نمره', description: 'داده‌های آموزشی و ارزیابی را فقط در صورت نیاز اصلاح کنید.', href: '/manual-entry?task=education', icon: 'edit', roles: dataCenterWorkspaceRoles },
          { id: 'attendance-correction', title: 'اصلاح حضور و غیاب', description: 'جلسه و رکورد حضور را برای رفع استثناهای عملیاتی اصلاح کنید.', href: '/manual-entry?task=attendance', icon: 'calendar', roles: dataCenterWorkspaceRoles },
        ],
      },
    ],
  });
}
