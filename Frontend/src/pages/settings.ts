import { config } from '../app/config.js';
import { contract } from '../api/contract.js';
import type { Role } from '../api/types.js';
import {
  administrativeRoles,
  curriculumManagementRoles,
  hasAnyRole,
  isSystemAdmin,
  organizationManagementRoles,
  policyManagementRoles,
} from '../app/permissions.js';
import { navigate } from '../app/router.js';
import { h } from '../utils/dom.js';
import { icon } from '../components/icons.js';

interface AdministrationCard {
  title: string;
  description: string;
  route: string;
  icon: string;
  roles: Role[];
}

interface AdministrationGroup {
  id: string;
  title: string;
  description: string;
  cards: AdministrationCard[];
}

const groups: AdministrationGroup[] = [
  {
    id: 'structure',
    title: 'ساختار مدرسه',
    description: 'تنظیمات کم‌تکرار مربوط به مجموعه، شعبه و سال تحصیلی.',
    cards: [
      { title: 'مجموعه‌ها', description: 'ساختار مجموعه‌های آموزشی', route: '/resources/organizations', icon: 'building', roles: ['system_admin'] },
      { title: 'مدارس و شعب', description: 'شعب و حوزه‌های مدرسه', route: '/resources/schools', icon: 'building', roles: organizationManagementRoles },
      { title: 'سال‌های تحصیلی', description: 'بازه و سال جاری', route: '/resources/academic-years', icon: 'calendar', roles: organizationManagementRoles },
      { title: 'نوبت‌های تحصیلی', description: 'تعریف و مدیریت نوبت‌ها', route: '/resources/terms', icon: 'calendar', roles: organizationManagementRoles },
      { title: 'پایه‌های تحصیلی', description: 'پایه و ترتیب آموزشی', route: '/resources/grade-levels', icon: 'book', roles: administrativeRoles },
      { title: 'کلاس‌ها', description: 'کلاس، ظرفیت و سال تحصیلی', route: '/resources/classes', icon: 'building', roles: administrativeRoles },
    ],
  },
  {
    id: 'curriculum',
    title: 'برنامه درسی',
    description: 'تعریف‌هایی که پیش از عملیات روزانه آموزش انجام می‌شوند.',
    cards: [
      { title: 'درس‌ها', description: 'فهرست و کدهای رسمی درس‌ها', route: '/resources/subjects', icon: 'book', roles: curriculumManagementRoles },
      { title: 'درس‌های پایه', description: 'اتصال درس به پایه و ضریب آن', route: '/resources/grade-subjects', icon: 'book', roles: curriculumManagementRoles },
      { title: 'ارائه‌درس‌ها', description: 'کلاس، درس، دبیر و نوبت ارائه', route: '/resources/course-offerings', icon: 'book', roles: curriculumManagementRoles },
      { title: 'انواع ارزیابی', description: 'نوع، وزن و دسته ارزیابی', route: '/resources/assessment-types', icon: 'chart', roles: curriculumManagementRoles },
      { title: 'سیاست محاسبه', description: 'نسخه‌های رسمی محاسبه نمره', route: '/resources/calculation-policies', icon: 'chart', roles: curriculumManagementRoles },
    ],
  },
  {
    id: 'policies',
    title: 'سیاست‌ها و قواعد',
    description: 'تنظیمات قاعده‌مند را از عملیات روزانه جدا نگه دارید.',
    cards: [
      { title: 'سیاست حضور و غیاب', description: 'قواعد تولید هشدارهای حضور', route: '/resources/attendance-policies', icon: 'bell', roles: policyManagementRoles },
    ],
  },
  {
    id: 'access',
    title: 'کاربران و دسترسی',
    description: 'حساب‌ها و نقش‌ها را فقط در سطح مجاز مدیریت کنید.',
    cards: [
      { title: 'کاربران', description: 'حساب‌های قابل مدیریت', route: '/users', icon: 'users', roles: administrativeRoles },
      { title: 'نقش‌ها و دسترسی', description: 'تخصیص نقش در حوزه مجاز', route: '/roles', icon: 'settings', roles: administrativeRoles },
    ],
  },
];

function administrationCard(card: AdministrationCard): HTMLElement {
  return h(
    'button',
    { className: 'settings-card card', type: 'button', onClick: () => navigate(card.route) },
    h('span', { className: 'settings-card__icon' }, icon(card.icon)),
    h('div', {}, h('h2', { text: card.title }), h('p', { text: card.description })),
    icon('chevron'),
  );
}

export function renderSettingsPage(): HTMLElement {
  const selectedGroup = new URLSearchParams(location.search).get('section');
  const visibleGroups = groups
    .map(group => ({ ...group, cards: group.cards.filter(card => hasAnyRole(card.roles)) }))
    .filter(group => group.cards.length);
  const diagnostics = isSystemAdmin()
    ? h('details', { className: 'card system-info technical-details' },
      h('summary', {}, icon('settings'), h('span', {}, h('strong', { text: 'اطلاعات فنی و یکپارچه‌سازی' }), h('small', { text: 'ویژه مدیر کل سامانه و پشتیبانی فنی' }))),
      h('dl', { className: 'detail-grid detail-grid--technical' },
        h('div', {}, h('dt', { text: 'نام برنامه' }), h('dd', { text: config.appName })),
        h('div', {}, h('dt', { text: 'نسخه قرارداد API' }), h('dd', { text: contract.meta.version })),
        h('div', {}, h('dt', { text: 'Base URL' }), h('dd', { className: 'ltr', text: config.apiBaseUrl })),
        h('div', {}, h('dt', { text: 'Timeout' }), h('dd', { text: `${config.requestTimeoutMs.toLocaleString('fa-IR')} میلی‌ثانیه` })),
        h('div', {}, h('dt', { text: 'تعداد عملیات قرارداد' }), h('dd', { text: contract.operations.length.toLocaleString('fa-IR') })),
        h('div', {}, h('dt', { text: 'تعداد Schema' }), h('dd', { text: Object.keys(contract.schemas).length.toLocaleString('fa-IR') })),
      ),
    )
    : null;

  return h(
    'section',
    { className: 'page administration-page' },
    h('div', { className: 'page-heading' }, h('div', {},
      h('span', { className: 'eyebrow', text: 'پیکربندی و دسترسی' }),
      h('h1', { text: 'مدیریت سامانه' }),
      h('p', { text: 'تنظیمات ساختاری و دسترسی از کارهای روزانه جدا شده‌اند. دسترسی نهایی هر بخش همچنان در Backend و بر اساس نقش و حوزه کنترل می‌شود.' }),
    )),
    ...visibleGroups.map(group => h(
      'section',
      { className: `workspace-section${selectedGroup === group.id ? ' workspace-section--focus' : ''}`, 'aria-label': group.title },
      h('div', { className: 'workspace-section__header' }, h('h2', { text: group.title }), h('p', { text: group.description })),
      h('div', { className: 'settings-grid' }, ...group.cards.map(administrationCard)),
    )),
    diagnostics,
  );
}
