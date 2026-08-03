import { config } from '../app/config.js';
import { contract } from '../api/contract.js';
import type { Role } from '../api/types.js';
import { administrativeRoles, hasAnyRole, isSystemAdmin } from '../app/permissions.js';
import { navigate } from '../app/router.js';
import { h } from '../utils/dom.js';
import { icon } from '../components/icons.js';

const sections: Array<{ title: string; description: string; route: string; icon: string; roles?: Role[] }> = [
  { title: 'مجموعه‌ها', description: 'ساختار مجموعه‌های آموزشی', route: '/resources/organizations', icon: 'building' },
  { title: 'مدارس و شعب', description: 'شعب و حوزه‌های مدرسه', route: '/resources/schools', icon: 'building' },
  { title: 'سال‌های تحصیلی', description: 'بازه و سال جاری', route: '/resources/academic-years', icon: 'calendar' },
  { title: 'نوبت‌های تحصیلی', description: 'تعریف و مدیریت نوبت‌ها', route: '/resources/terms', icon: 'calendar' },
  { title: 'پایه‌های تحصیلی', description: 'پایه و ترتیب آموزشی', route: '/resources/grade-levels', icon: 'book' },
  { title: 'کلاس‌ها', description: 'کلاس، ظرفیت و سال تحصیلی', route: '/resources/classes', icon: 'building' },
  { title: 'درس‌ها', description: 'فهرست درس‌های مجموعه', route: '/resources/subjects', icon: 'book' },
  { title: 'درس‌های پایه', description: 'اتصال درس به پایه و ضریب', route: '/resources/grade-subjects', icon: 'book' },
  { title: 'ارائه درس‌ها', description: 'کلاس، دبیر و نوبت ارائه', route: '/resources/course-offerings', icon: 'book' },
  { title: 'انواع ارزیابی', description: 'نوع، وزن و دسته ارزیابی', route: '/resources/assessment-types', icon: 'chart' },
  { title: 'سیاست محاسبه', description: 'نسخه‌های رسمی محاسبه نمره', route: '/resources/calculation-policies', icon: 'chart' },
  { title: 'سیاست حضور', description: 'قواعد تولید هشدار حضور', route: '/resources/attendance-policies', icon: 'bell' },
  { title: 'کاربران', description: 'حساب‌های قابل مدیریت', route: '/users', icon: 'users', roles: administrativeRoles },
  { title: 'نقش‌ها و دسترسی', description: 'تخصیص نقش در حوزه مجاز', route: '/roles', icon: 'settings', roles: administrativeRoles },
];

export function renderSettingsPage(): HTMLElement {
  const visibleSections = sections.filter(section => hasAnyRole(section.roles));
  const diagnostics = isSystemAdmin()
    ? h('details', { className: 'card system-info technical-details' },
      h('summary', {}, icon('settings'), h('span', {}, h('strong', { text: 'اطلاعات فنی و یکپارچه‌سازی' }), h('small', { text: 'ویژه مدیر کل سامانه و پشتیبانی فنی' }))),
      h('dl', { className: 'detail-grid detail-grid--technical' }, h('div', {}, h('dt', { text: 'نام برنامه' }), h('dd', { text: config.appName })), h('div', {}, h('dt', { text: 'نسخه قرارداد API' }), h('dd', { text: contract.meta.version })), h('div', {}, h('dt', { text: 'Base URL' }), h('dd', { className: 'ltr', text: config.apiBaseUrl })), h('div', {}, h('dt', { text: 'Timeout' }), h('dd', { text: `${config.requestTimeoutMs.toLocaleString('fa-IR')} میلی‌ثانیه` })), h('div', {}, h('dt', { text: 'تعداد عملیات قرارداد' }), h('dd', { text: contract.operations.length.toLocaleString('fa-IR') })), h('div', {}, h('dt', { text: 'تعداد Schema' }), h('dd', { text: Object.keys(contract.schemas).length.toLocaleString('fa-IR') }))),
    )
    : null;
  return h('section', { className: 'page' },
    h('div', { className: 'page-heading' }, h('div', {}, h('span', { className: 'eyebrow', text: 'پیکربندی' }), h('h1', { text: 'تنظیمات سامانه' }), h('p', { text: 'دسترسی هر بخش در Backend و براساس نقش و Scope کنترل می‌شود.' }))),
    h('div', { className: 'settings-grid' }, ...visibleSections.map(section => h('button', { className: 'settings-card card', type: 'button', onClick: () => navigate(section.route) }, h('span', { className: 'settings-card__icon' }, icon(section.icon)), h('div', {}, h('h2', { text: section.title }), h('p', { text: section.description })), icon('chevron')))),
    diagnostics,
  );
}
