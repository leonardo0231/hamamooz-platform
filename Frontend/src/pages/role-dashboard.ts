import {
  roleDashboardApi,
  roleDashboardDrillDownRoutes,
  type RoleDashboard,
  type RoleDashboardKind,
} from '../api/role-dashboard.js';
import { navigate } from '../app/router.js';
import { emptyState, errorState, loadingState } from '../components/feedback.js';
import { icon } from '../components/icons.js';
import { clear, formatNumber, h } from '../utils/dom.js';

interface DashboardPresentation {
  eyebrow: string;
  title: string;
  description: string;
  metrics: Record<string, { label: string; tone: string; icon: string }>;
}

const presentations: Record<RoleDashboardKind, DashboardPresentation> = {
  manager: {
    eyebrow: 'عملیات مدرسه',
    title: 'داشبورد مدیر',
    description: 'نمای تصمیم‌محورِ مدرسه؛ فقط شاخص‌های تجمیعی در محدوده مجاز شما.',
    metrics: {
      active_students: { label: 'دانش‌آموز فعال', tone: 'primary', icon: 'users' },
      high_risk_signals: { label: 'ریسک بالا', tone: 'red', icon: 'warning' },
      open_operational_alerts: { label: 'هشدار عملیاتی باز', tone: 'orange', icon: 'bell' },
      submitted_report_drafts: { label: 'پیش‌نویس منتظر تأیید', tone: 'blue', icon: 'file' },
    },
  },
  educational: {
    eyebrow: 'عملیات آموزشی',
    title: 'داشبورد معاون آموزشی',
    description: 'پایش تکمیل ارزیابی‌ها و سیگنال‌های آموزشی، در محدوده مدرسه مجاز.',
    metrics: {
      active_students: { label: 'دانش‌آموز فعال', tone: 'primary', icon: 'users' },
      open_assessments: { label: 'ارزیابی باز', tone: 'orange', icon: 'chart' },
      missing_teacher_scores: { label: 'نمره ثبت‌نشده', tone: 'red', icon: 'warning' },
      active_risk_signals: { label: 'سیگنال ریسک فعال', tone: 'blue', icon: 'bell' },
    },
  },
  studentAffairs: {
    eyebrow: 'امور دانش‌آموزی',
    title: 'داشبورد معاون امور دانش‌آموزی',
    description: 'پیگیری وقایع رفتاری، follow-upها و هشدارهای عملیاتی در مدرسه مجاز.',
    metrics: {
      confirmed_behavior_events: { label: 'واقعه تأییدشده', tone: 'orange', icon: 'warning' },
      behavior_follow_ups: { label: 'پیگیری باز', tone: 'primary', icon: 'check' },
      open_operational_alerts: { label: 'هشدار عملیاتی باز', tone: 'red', icon: 'bell' },
    },
  },
  counselor: {
    eyebrow: 'حریم محرمانه مشاوره',
    title: 'داشبورد مشاور',
    description: 'فقط شمارش پرونده‌های منتسب به شما نمایش داده می‌شود؛ یادداشت خصوصی هرگز در این داشبورد برنمی‌گردد.',
    metrics: {
      active_assigned_cases: { label: 'پرونده فعال منتسب', tone: 'primary', icon: 'users' },
      high_risk_assigned_cases: { label: 'ریسک مشترک بالا', tone: 'red', icon: 'warning' },
      pending_referrals: { label: 'ارجاع منتظر بررسی', tone: 'orange', icon: 'bell' },
    },
  },
  guideTeacher: {
    eyebrow: 'راهنمایی دانش‌آموز',
    title: 'داشبورد معلم راهنما',
    description: 'فقط assignmentهای فعال و follow-upهای cohort خودتان را می‌بینید.',
    metrics: {
      active_assignments: { label: 'دانش‌آموز منتسب', tone: 'primary', icon: 'users' },
      open_follow_ups: { label: 'پیگیری باز', tone: 'orange', icon: 'check' },
      released_action_plans: { label: 'برنامه منتشرشده', tone: 'blue', icon: 'file' },
    },
  },
  teacher: {
    eyebrow: 'فضای کاری دبیر',
    title: 'داشبورد دبیر',
    description: 'خلاصه‌ای از ارائه‌درس‌ها و وضعیت ارزیابی‌های خودتان.',
    metrics: {
      active_course_offerings: { label: 'ارائه‌درس فعال', tone: 'primary', icon: 'book' },
      open_assessments: { label: 'ارزیابی باز', tone: 'orange', icon: 'chart' },
      locked_assessments: { label: 'ارزیابی قفل‌شده', tone: 'blue', icon: 'check' },
    },
  },
};

const drillDownLabels: Record<string, string> = {
  alerts: 'هشدارهای عملیاتی',
  assessments: 'ارزیابی‌ها',
  assignments: 'تخصیص‌های معلم راهنما',
  behavior: 'وقایع رفتاری',
  cases: 'پرونده‌های مشاوره',
  follow_ups: 'پیگیری‌ها',
  referrals: 'ارجاع‌ها',
  reports: 'پیش‌نویس گزارش‌ها',
  signals: 'سیگنال‌های ریسک',
};

function metricCard(key: string, value: number, presentation: DashboardPresentation): HTMLElement {
  const descriptor = presentation.metrics[key] ?? {
    label: key.replaceAll('_', ' '),
    tone: 'primary',
    icon: 'chart',
  };
  return h(
    'article',
    { className: `metric-card role-metric role-metric--${descriptor.tone}` },
    h('span', { className: `metric-card__icon metric-card__icon--${descriptor.tone}` }, icon(descriptor.icon)),
    h('div', {}, h('small', { text: descriptor.label }), h('strong', { text: formatNumber(value) })),
  );
}

function drillDownCard(dashboard: RoleDashboard): HTMLElement {
  const entries = Object.entries(dashboard.drill_down).filter(([, apiPath]) => roleDashboardDrillDownRoutes[apiPath]);
  if (!entries.length) {
    return emptyState('مسیر پیگیری ثبت نشده است', 'این داشبورد فقط نمای تجمیعی دارد.');
  }
  return h(
    'article',
    { className: 'card decision-card' },
    h('div', { className: 'card-header' }, h('div', {}, h('h2', { text: 'پیگیری جزئیات' }), h('p', { text: 'هر جزئیات در endpoint و سیاست دسترسی همان دامنه بررسی می‌شود.' })), h('span', { className: 'card-icon' }, icon('chevron'))),
    h(
      'div',
      { className: 'decision-list' },
      ...entries.map(([key, apiPath]) => h(
        'button',
        { className: 'decision-list__item', type: 'button', onClick: () => navigate(roleDashboardDrillDownRoutes[apiPath] ?? '/') },
        h('div', {}, h('strong', { text: drillDownLabels[key] ?? key.replaceAll('_', ' ') }), h('small', { text: 'نمایش در محدوده مجاز حساب شما' })),
        icon('chevron'),
      )),
    ),
  );
}

function renderLoadedDashboard(target: HTMLElement, dashboard: RoleDashboard, kind: RoleDashboardKind): void {
  const presentation = presentations[kind];
  clear(target);
  target.append(
    h(
      'div',
      { className: 'page-heading' },
      h('div', {}, h('span', { className: 'eyebrow', text: presentation.eyebrow }), h('h1', { text: presentation.title }), h('p', { text: presentation.description })),
      h('span', { className: 'badge badge--neutral', text: `${formatNumber(dashboard.scope_school_ids.length)} مدرسه در محدوده` }),
    ),
    h('div', { className: 'metric-grid' }, ...Object.entries(dashboard.metrics).map(([key, value]) => metricCard(key, value, presentation))),
    drillDownCard(dashboard),
  );
}

export async function renderRoleDashboardPage(kind: RoleDashboardKind): Promise<HTMLElement> {
  const page = h('section', { className: 'page role-dashboard-page' }, loadingState());
  const load = async (): Promise<void> => {
    clear(page);
    page.append(loadingState());
    try {
      renderLoadedDashboard(page, await roleDashboardApi.get(kind), kind);
    } catch (error) {
      clear(page);
      page.append(errorState(error, () => void load()));
    }
  };
  await load();
  return page;
}
