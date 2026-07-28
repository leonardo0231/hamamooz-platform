import { apiRequest } from '../api/client.js';
import { endpoints } from '../api/endpoints.js';
import type { Pagination } from '../api/types.js';
import { store } from '../app/store.js';
import { navigate } from '../app/router.js';
import { hasAnyRole, hasWriteScope, teacherWriteRoles } from '../app/permissions.js';
import { onWindowEventWhileConnected, h, clear, formatDate, formatNumber } from '../utils/dom.js';
import { emptyState, errorState, skeletonCards } from '../components/feedback.js';
import { icon } from '../components/icons.js';

interface DashboardSummary {
  selected_term: { id: string; title: string };
  counts: { students: number; classes: number; teachers: number; missing_scores: number };
  students_by_school: Array<{ school_id: string; school__name: string; students: number }>;
  class_averages: Array<{ enrollment__class_section_id: string; enrollment__class_section__title: string; average: number | string | null; students: number }>;
  assessment_workflow: Record<string, number>;
  latest_activities: Array<{ id: string; action: string; entity_type: string; entity_id: string; actor_id: number | null; created_at: string }>;
}

interface AlertSummary { id: string; student_name: string; class_title: string; severity: string; status: string; absence_percent: string; created_at: string; }

function classComparison(items: DashboardSummary['class_averages']): HTMLElement {
  const rows = items
    .map(item => ({ ...item, numericAverage: item.average === null ? null : Number(item.average) }))
    .sort((a, b) => (b.numericAverage ?? -1) - (a.numericAverage ?? -1));
  const available = rows.filter(row => row.numericAverage !== null && Number.isFinite(row.numericAverage));
  if (!available.length) return emptyState('داده عملکردی وجود ندارد', 'پس از محاسبه نتایج نوبت، مقایسه کلاس‌ها در این بخش نمایش داده می‌شود.');

  const mean = available.reduce((total, row) => total + (row.numericAverage ?? 0), 0) / available.length;
  return h('div', { className: 'class-comparison' },
    h('div', { className: 'chart-summary', role: 'status' },
      h('span', {}, 'میانگین کلاس‌های دارای داده', h('strong', { text: formatNumber(mean, 1) })),
      h('span', {}, 'کلاس بدون داده', h('strong', { text: formatNumber(rows.length - available.length) })),
    ),
    h('div', { className: 'class-comparison__list', role: 'list', 'aria-label': 'مقایسه میانگین کلاس‌ها از ۲۰' },
      ...rows.map(row => {
        const valid = row.numericAverage !== null && Number.isFinite(row.numericAverage);
        const value = valid ? Math.max(0, Math.min(20, row.numericAverage ?? 0)) : 0;
        const valueText = valid ? `${formatNumber(value, 1)} از ۲۰` : 'بدون داده';
        return h('div', { className: `class-comparison__row ${valid ? '' : 'is-missing'}`, role: 'listitem' },
          h('div', { className: 'class-comparison__label' }, h('strong', { text: row.enrollment__class_section__title }), h('small', { text: `${formatNumber(row.students)} دانش‌آموز` })),
          h('div', {
            className: 'class-comparison__track',
            role: 'progressbar',
            'aria-label': `میانگین ${row.enrollment__class_section__title}`,
            'aria-valuemin': '0',
            'aria-valuemax': '20',
            'aria-valuenow': valid ? String(value) : undefined,
            'aria-valuetext': valueText,
          }, h('i', { style: { width: `${value / 20 * 100}%` } })),
          h('strong', { className: 'class-comparison__value', text: valid ? formatNumber(value, 1) : '—' }),
        );
      }),
    ),
  );
}

function metricCard(label: string, value: number, cardIcon: string, tone: string, detail: string): HTMLElement {
  return h('article', { className: 'metric-card' }, h('span', { className: `metric-card__icon metric-card__icon--${tone}` }, icon(cardIcon)), h('div', {}, h('small', { text: label }), h('strong', { text: formatNumber(value) }), h('span', { text: detail })));
}

function activityLabel(action: string): string {
  const known: Record<string, string> = { 'auth.login': 'ورود به سامانه', 'score.updated': 'ویرایش نمره', 'assessment.created': 'ایجاد ارزیابی', 'attendance.finalized': 'نهایی‌سازی حضور و غیاب', 'report.created': 'ایجاد گزارش' };
  return known[action] ?? action.replaceAll('.', ' / ').replaceAll('_', ' ');
}

const workflowLabels: Record<string, { label: string; tone: string }> = {
  draft: { label: 'پیش‌نویس', tone: 'neutral' },
  submitted: { label: 'ارسال‌شده', tone: 'warning' },
  rejected: { label: 'ردشده', tone: 'danger' },
  approved: { label: 'تأییدشده', tone: 'success' },
  locked: { label: 'قفل‌شده', tone: 'success' },
};

export async function renderDashboardPage(): Promise<HTMLElement> {
  const user = store.state.user;
  const name = user?.first_name || user?.username || 'کاربر';
  const page = h('section', { className: 'page dashboard-page' });
  const content = h('div', { 'aria-live': 'polite' });
  const actions = h('div', { className: 'page-actions' }, h('button', { className: 'button button--secondary', type: 'button', onClick: () => navigate('/reports') }, icon('file'), 'گزارش‌ها'));
  if (hasAnyRole(teacherWriteRoles) && hasWriteScope()) actions.append(h('button', { className: 'button button--primary', type: 'button', onClick: () => navigate('/resources/assessments') }, icon('plus'), 'اقدام آموزشی'));
  page.append(h('div', { className: 'page-heading' }, h('div', {}, h('span', { className: 'eyebrow', text: 'نمای مدیریتی' }), h('h1', { text: `صبح بخیر، ${name}` }), h('p', { text: 'خلاصه تصمیم‌محور داده‌های آموزشی در حوزه انتخاب‌شده' })), actions), content);

  async function load(): Promise<void> {
    clear(content);
    content.setAttribute('aria-busy', 'true');
    content.append(skeletonCards(), h('div', { className: 'dashboard-grid' }, h('div', { className: 'card skeleton dashboard-chart' }), h('div', { className: 'card skeleton' })));
    try {
      const [summaryResult, alertsResult] = await Promise.allSettled([
        apiRequest<DashboardSummary>(endpoints.dashboard.summary),
        apiRequest<Pagination<AlertSummary>>(endpoints.alerts.list, { query: { page_size: 5, status: 'open', ordering: '-created_at' } }),
      ]);
      if (summaryResult.status === 'rejected') throw summaryResult.reason;
      const summary = summaryResult.value;
      const alerts = alertsResult.status === 'fulfilled' ? alertsResult.value : null;
      const alertsError = alertsResult.status === 'rejected' ? alertsResult.reason : null;
      clear(content);
      content.setAttribute('aria-busy', 'false');
      const attentionCount = (alerts?.count ?? 0) + summary.counts.missing_scores;
      const attention = alertsError
        ? h('article', { className: 'attention-strip attention-strip--warning', role: 'alert' }, h('span', { className: 'attention-strip__icon' }, icon('warning')), h('div', {}, h('strong', { text: 'بخشی از وضعیت داشبورد دریافت نشد' }), h('p', { text: 'خلاصه آموزشی نمایش داده شده، اما وضعیت هشدارها نامشخص است.' })), h('button', { className: 'button button--secondary', type: 'button', onClick: () => void load() }, icon('refresh'), 'تلاش دوباره'))
        : attentionCount > 0
          ? h('article', { className: 'attention-strip attention-strip--danger' }, h('span', { className: 'attention-strip__icon' }, icon('bell')), h('div', {}, h('strong', { text: `${formatNumber(attentionCount)} مورد نیازمند توجه` }), h('p', { text: `${formatNumber(alerts?.count ?? 0)} هشدار باز و ${formatNumber(summary.counts.missing_scores)} نمره ثبت‌نشده` })), h('button', { className: 'button button--secondary', type: 'button', onClick: () => navigate((alerts?.count ?? 0) > 0 ? '/alerts' : '/resources/assessments') }, 'بررسی موارد', icon('chevron')))
          : h('article', { className: 'attention-strip attention-strip--success', role: 'status' }, h('span', { className: 'attention-strip__icon' }, icon('check')), h('div', {}, h('strong', { text: 'مورد فوری ثبت نشده است' }), h('p', { text: `داده‌های ${summary.selected_term.title} در حوزه فعال پایدار هستند.` })), h('small', { text: `دریافت در ${formatDate(new Date(), true)}` }));
      const metrics = h('div', { className: 'metric-grid' },
        metricCard('کل دانش‌آموزان', summary.counts.students, 'users', 'primary', 'در حوزه فعال'),
        metricCard('کلاس‌های فعال', summary.counts.classes, 'building', 'blue', `نوبت ${summary.selected_term.title}`),
        metricCard('دبیران فعال', summary.counts.teachers, 'user', 'green', 'دارای ارائه درس'),
        metricCard('نمره‌های ثبت‌نشده', summary.counts.missing_scores, 'warning', 'red', 'نیازمند پیگیری'),
      );
      const performance = h('article', { className: 'card dashboard-chart' },
        h('div', { className: 'card-header' }, h('div', {}, h('h2', { text: 'مقایسه عملکرد کلاس‌ها' }), h('p', { text: `میانگین کلاس‌ها از ۲۰ در ${summary.selected_term.title}` })), h('span', { className: 'card-icon' }, icon('chart'))),
        classComparison(summary.class_averages),
      );
      const schools = [...summary.students_by_school].sort((a, b) => b.students - a.students);
      const schoolBars = h('article', { className: 'card' }, h('div', { className: 'card-header' }, h('div', {}, h('h2', { text: 'دانش‌آموزان به تفکیک مدرسه' }), h('p', { text: 'تعداد ثبت‌نام فعال' })), h('span', { className: 'card-icon' }, icon('building'))),
        schools.length ? h('div', { className: 'bar-list', role: 'list', 'aria-label': 'توزیع دانش‌آموزان بین مدارس' }, ...schools.map(item => {
          const max = Math.max(...summary.students_by_school.map(row => row.students), 1);
          const percent = item.students / max * 100;
          return h('div', { className: 'bar-row', role: 'listitem' }, h('span', { text: item.school__name }), h('div', { className: 'bar-track', role: 'progressbar', 'aria-label': `دانش‌آموزان ${item.school__name}`, 'aria-valuemin': '0', 'aria-valuemax': String(max), 'aria-valuenow': String(item.students), 'aria-valuetext': `${formatNumber(item.students)} دانش‌آموز` }, h('i', { style: { width: `${percent}%` } })), h('strong', { text: formatNumber(item.students) }));
        })) : emptyState('مدرسه‌ای در حوزه فعال نیست', 'حوزه سازمان یا مدرسه را از نوار بالا انتخاب کنید.'));
      const alertPanel = h('article', { className: 'card alerts-preview' }, h('div', { className: 'card-header' }, h('div', {}, h('h2', { text: 'پیگیری‌های فوری' }), h('p', { text: alerts ? `${formatNumber(alerts.count)} هشدار باز` : 'وضعیت هشدارها نامشخص' })), h('span', { className: 'card-icon card-icon--danger' }, icon('bell'))),
        alertsError ? errorState(alertsError, () => void load()) : alerts?.results.length ? h('div', { className: 'compact-list' }, ...alerts.results.map(alert => h('button', { className: 'compact-list__item', type: 'button', onClick: () => navigate(`/alerts?selected=${alert.id}`) }, h('span', { className: `severity-dot severity-dot--${alert.severity}` }), h('div', {}, h('strong', { text: alert.student_name }), h('small', { text: `${alert.class_title} · غیبت ${alert.absence_percent}٪` })), icon('chevron')))) : emptyState('هشدار بازی وجود ندارد', 'در حوزه فعال، هشدار نیازمند اقدام ثبت نشده است.'),
        h('button', { className: 'button button--success button--block', type: 'button', onClick: () => navigate('/alerts') }, 'مشاهده مرکز هشدارها', icon('chevron')));
      const workflowStatuses = [...Object.keys(workflowLabels), ...Object.keys(summary.assessment_workflow).filter(status => !workflowLabels[status])];
      const workflowItems = workflowStatuses.map(status => {
        const count = summary.assessment_workflow[status] ?? 0;
        const presentation = workflowLabels[status] ?? { label: status.replaceAll('_', ' '), tone: 'neutral' };
        return h('button', { className: 'workflow-item', type: 'button', onClick: () => navigate(`/resources/assessments?status=${encodeURIComponent(status)}`), 'aria-label': `${presentation.label}: ${formatNumber(count)} ارزیابی` },
          h('span', { className: `badge badge--${presentation.tone}`, text: presentation.label }),
          h('strong', { text: formatNumber(count) }),
        );
      });
      const workflow = h('article', { className: 'card' },
        h('div', { className: 'card-header' }, h('div', {}, h('h2', { text: 'گردش‌کار ارزیابی‌ها' }), h('p', { text: 'وضعیت ارزیابی‌های نوبت فعال' })), h('span', { className: 'card-icon' }, icon('sparkles'))),
        h('div', { className: 'workflow-grid' }, ...workflowItems),
      );
      const activityContent = summary.latest_activities.length
        ? h('ol', { className: 'timeline' }, ...summary.latest_activities.map(item =>
            h('li', {}, h('span', { className: 'timeline__dot' }), h('div', {}, h('strong', { text: activityLabel(item.action) }), h('small', { text: `${item.entity_type} · ${formatDate(item.created_at, true)}` }))),
          ))
        : emptyState('رویدادی ثبت نشده است', 'فعالیت‌های مجاز پس از انجام عملیات در این بخش نمایش داده می‌شوند.');
      const activities = h('article', { className: 'card activities-card' },
        h('div', { className: 'card-header' }, h('div', {}, h('h2', { text: 'آخرین رویدادها' }), h('p', { text: 'رویدادهای ممیزی مجاز' })), h('span', { className: 'card-icon' }, icon('file'))),
        activityContent,
      );
      const banner = h('article', { className: 'report-banner' }, h('span', { className: 'report-banner__visual' }, icon('file')), h('div', {}, h('h2', { text: 'گزارش تحلیلی نوبت فعال' }), h('p', { text: 'گزارش‌های رسمی از داده‌های قفل‌شده و نسخه فرمول محاسبه تولید می‌شوند.' })), h('button', { className: 'button button--success', type: 'button', onClick: () => navigate('/reports') }, icon('file'), 'ساخت گزارش'));
      content.append(attention, metrics, h('div', { className: 'dashboard-grid dashboard-grid--main' }, performance, schoolBars, alertPanel), h('div', { className: 'dashboard-grid dashboard-grid--secondary' }, workflow, activities), banner);
    } catch (error) {
      clear(content);
      content.setAttribute('aria-busy', 'false');
      content.append(errorState(error, () => void load()));
    }
  }
  onWindowEventWhileConnected(page, 'hamamooz:scope-change', () => void load());
  void load();
  return page;
}
