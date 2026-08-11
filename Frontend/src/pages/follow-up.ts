import { counselingRoles, guidanceRoles, managementReadRoles } from '../app/permissions.js';
import { renderWorkspacePage } from './workspace.js';

export function renderFollowUpWorkspacePage(): HTMLElement {
  return renderWorkspacePage({
    eyebrow: 'فضای کاری رشد دانش‌آموز',
    title: 'رشد و پیگیری',
    description: 'رفتار، فعالیت، ریسک و توصیه‌ها را در زمینه پیگیری دانش‌آموز ببینید؛ نه به‌عنوان فهرستی از داده‌های جداگانه.',
    groups: [
      {
        title: 'پیگیری مدرسه',
        description: 'برای مدیران و معاونان: از موارد نیازمند توجه به پرونده دانش‌آموز برسید.',
        cards: [
          { id: 'student-360', title: 'پرونده دانش‌آموزان', description: 'دانش‌آموز را جست‌وجو کنید و Student 360 او را در یک صفحه ببینید.', href: '/students', icon: 'users', roles: managementReadRoles },
          { id: 'operational-alerts', title: 'موارد نیازمند پیگیری', description: 'هشدارهای عملیاتی باز و اقدام‌های بعدی را در صف واحد بررسی کنید.', href: '/resources/operational-alerts', icon: 'bell', roles: managementReadRoles },
          { id: 'behavior', title: 'رویدادهای رفتاری', description: 'رخدادهای رفتاری دانش‌آموزان را برای پیگیری در زمینه درست مرور کنید.', href: '/resources/behavior-events', icon: 'warning', roles: managementReadRoles },
          { id: 'activities', title: 'فعالیت‌ها و مشارکت‌ها', description: 'فعالیت‌های مدرسه و مشارکت دانش‌آموزان را جدا از رویدادهای رفتاری بررسی کنید.', href: '/resources/activities', icon: 'sparkles', roles: managementReadRoles },
          { id: 'risks', title: 'سیگنال‌های ریسک', description: 'ریسک‌هایی را که به اقدام یا بررسی بیشتر نیاز دارند، اولویت‌بندی کنید.', href: '/resources/analytics-risk-signals', icon: 'chart', roles: managementReadRoles },
          { id: 'recommendations', title: 'توصیه‌های پیگیری', description: 'توصیه‌های قابل اقدام را با دانش‌آموز و اولویت آن‌ها مرور کنید.', href: '/resources/recommendations', icon: 'check', roles: managementReadRoles },
        ],
      },
      {
        title: 'راهنمایی',
        description: 'سطوح مجاز هر نقش در Backend اعمال می‌شود.',
        cards: [
          { id: 'guide-assignments', title: 'دانش‌آموزان منتسب', description: 'تخصیص‌های فعال راهنمایی را ببینید و از همان‌جا پیگیری کنید.', href: '/resources/guide-teacher-assignments', icon: 'users', roles: guidanceRoles },
          { id: 'guide-follow-ups', title: 'پیگیری‌های راهنمایی', description: 'برنامه‌ها و پیگیری‌های cohort خود را مدیریت کنید.', href: '/resources/guide-follow-ups', icon: 'check', roles: guidanceRoles },
          { id: 'guide-recommendations', title: 'توصیه‌های cohort', description: 'توصیه‌های دانش‌آموزان منتسب را در همان محدوده مجاز بررسی کنید.', href: '/resources/my-guide-recommendations', icon: 'sparkles', roles: guidanceRoles },
        ],
      },
      {
        title: 'مشاوره محرمانه',
        description: 'این بخش فقط برای نقش مشاور و در محدوده پرونده‌های منتسب نمایش داده می‌شود.',
        cards: [
          { id: 'counseling-cases', title: 'پرونده‌های مشاوره', description: 'پرونده‌های محرمانه منتسب به شما را بررسی کنید.', href: '/resources/counseling-cases', icon: 'lock', exactRoles: counselingRoles },
          { id: 'counseling-referrals', title: 'ارجاع‌ها', description: 'ارجاع‌های منتظر بررسی را در همان فضای محرمانه پیگیری کنید.', href: '/resources/counseling-referrals', icon: 'bell', exactRoles: counselingRoles },
          { id: 'counseling-recommendations', title: 'توصیه‌های مشاوره', description: 'توصیه‌های محرمانه پرونده‌های منتسب را در همان محدوده بررسی کنید.', href: '/resources/my-counselor-recommendations', icon: 'sparkles', exactRoles: counselingRoles },
        ],
      },
    ],
  });
}
