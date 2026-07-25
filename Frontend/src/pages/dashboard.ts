import { apiRequest } from '../api/client.js';
import { endpoints } from '../api/endpoints.js';
import type { Pagination } from '../api/types.js';
import { store } from '../app/store.js';
import { navigate } from '../app/router.js';
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

function lineChart(values: number[]): SVGSVGElement {
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  svg.setAttribute('viewBox', '0 0 600 220');
  svg.classList.add('line-chart');
  if (!values.length) return svg;
  const min = Math.min(...values, 0);
  const max = Math.max(...values, 20);
  const points = values.map((value, index) => {
    const x = 30 + (index * 540 / Math.max(1, values.length - 1));
    const y = 190 - ((value - min) / Math.max(1, max - min)) * 150;
    return { x, y, value };
  });
  const grid = [40, 80, 120, 160, 200].map(y => `<line x1="20" y1="${y}" x2="580" y2="${y}" class="chart-grid"/>`).join('');
  const path = points.map((p, index) => `${index ? 'L' : 'M'}${p.x},${p.y}`).join(' ');
  const area = `${path} L${points.at(-1)?.x},200 L${points[0]?.x},200 Z`;
  svg.innerHTML = `${grid}<path d="${area}" class="chart-area"/><path d="${path}" class="chart-line"/>${points.map(p => `<circle cx="${p.x}" cy="${p.y}" r="6" class="chart-point"><title>${p.value}</title></circle>`).join('')}`;
  return svg;
}

function metricCard(label: string, value: number, cardIcon: string, tone: string, detail: string): HTMLElement {
  return h('article', { className: 'metric-card' }, h('span', { className: `metric-card__icon metric-card__icon--${tone}` }, icon(cardIcon)), h('div', {}, h('small', { text: label }), h('strong', { text: formatNumber(value) }), h('span', { text: detail })));
}

function activityLabel(action: string): string {
  const known: Record<string, string> = { 'auth.login': 'ورود به سامانه', 'score.updated': 'ویرایش نمره', 'assessment.created': 'ایجاد ارزیابی', 'attendance.finalized': 'نهایی‌سازی حضور و غیاب', 'report.created': 'ایجاد گزارش' };
  return known[action] ?? action.replaceAll('.', ' / ').replaceAll('_', ' ');
}

export async function renderDashboardPage(): Promise<HTMLElement> {
  const user = store.state.user;
  const name = user?.first_name || user?.username || 'کاربر';
  const page = h('section', { className: 'page dashboard-page' });
  const content = h('div');
  page.append(h('div', { className: 'page-heading' }, h('div', {}, h('span', { className: 'eyebrow', text: 'نمای مدیریتی' }), h('h1', { text: `صبح بخیر، ${name}` }), h('p', { text: 'نمای زنده‌ی داده‌های آموزشی در حوزه انتخاب‌شده' })), h('div', { className: 'page-actions' }, h('button', { className: 'button button--secondary', type: 'button', onClick: () => navigate('/reports') }, icon('file'), 'گزارش‌ها'), h('button', { className: 'button button--primary', type: 'button', onClick: () => navigate('/resources/assessments') }, icon('plus'), 'اقدام آموزشی'))), content);

  async function load(): Promise<void> {
    clear(content);
    content.append(skeletonCards(), h('div', { className: 'dashboard-grid' }, h('div', { className: 'card skeleton dashboard-chart' }), h('div', { className: 'card skeleton' })));
    try {
      const [summary, alerts] = await Promise.all([
        apiRequest<DashboardSummary>(endpoints.dashboard.summary),
        apiRequest<Pagination<AlertSummary>>(endpoints.alerts.list, { query: { page_size: 5, status: 'open', ordering: '-created_at' } }).catch(() => ({ count: 0, next: null, previous: null, results: [] })),
      ]);
      clear(content);
      const metrics = h('div', { className: 'metric-grid' },
        metricCard('کل دانش‌آموزان', summary.counts.students, 'users', 'purple', 'در حوزه فعال'),
        metricCard('کلاس‌های فعال', summary.counts.classes, 'building', 'blue', `نوبت ${summary.selected_term.title}`),
        metricCard('دبیران فعال', summary.counts.teachers, 'user', 'green', 'دارای ارائه درس'),
        metricCard('نمره‌های ثبت‌نشده', summary.counts.missing_scores, 'warning', 'red', 'نیازمند پیگیری'),
      );
      const averages = summary.class_averages.map(item => Number(item.average ?? 0));
      const performance = h('article', { className: 'card dashboard-chart' },
        h('div', { className: 'card-header' }, h('div', {}, h('h2', { text: 'روند عملکرد کلاس‌ها' }), h('p', { text: `میانگین ثبت‌شده در ${summary.selected_term.title}` })), h('span', { className: 'card-icon' }, icon('chart'))),
        averages.length ? lineChart(averages) : emptyState('داده عملکردی وجود ندارد', 'پس از محاسبه نتایج نوبت، نمودار کلاس‌ها نمایش داده می‌شود.'),
        averages.length ? h('div', { className: 'chart-labels' }, ...summary.class_averages.map(item => h('span', { text: item.enrollment__class_section__title }))) : null,
      );
      const schoolBars = h('article', { className: 'card' }, h('div', { className: 'card-header' }, h('div', {}, h('h2', { text: 'دانش‌آموزان به تفکیک مدرسه' }), h('p', { text: 'تعداد ثبت‌نام فعال' })), h('span', { className: 'card-icon' }, icon('building'))),
        summary.students_by_school.length ? h('div', { className: 'bar-list' }, ...summary.students_by_school.map(item => {
          const max = Math.max(...summary.students_by_school.map(row => row.students), 1);
          return h('div', { className: 'bar-row' }, h('span', { text: item.school__name }), h('div', { className: 'bar-track' }, h('i', { style: { width: `${Math.max(4, item.students / max * 100)}%` } })), h('strong', { text: formatNumber(item.students) }));
        })) : emptyState('مدرسه‌ای در حوزه فعال نیست', 'حوزه سازمان یا مدرسه را از نوار بالا انتخاب کنید.'));
      const alertPanel = h('article', { className: 'card alerts-preview' }, h('div', { className: 'card-header' }, h('div', {}, h('h2', { text: 'پیگیری‌های فوری' }), h('p', { text: `${formatNumber(alerts.count)} هشدار باز` })), h('span', { className: 'card-icon card-icon--danger' }, icon('bell'))),
        alerts.results.length ? h('div', { className: 'compact-list' }, ...alerts.results.map(alert => h('button', { className: 'compact-list__item', type: 'button', onClick: () => navigate(`/alerts?selected=${alert.id}`) }, h('span', { className: `severity-dot severity-dot--${alert.severity}` }), h('div', {}, h('strong', { text: alert.student_name }), h('small', { text: `${alert.class_title} · غیبت ${alert.absence_percent}٪` })), icon('chevron')))) : emptyState('هشدار بازی وجود ندارد', 'در حوزه فعال، هشدار نیازمند اقدام ثبت نشده است.'),
        h('button', { className: 'button button--success button--block', type: 'button', onClick: () => navigate('/alerts') }, 'مشاهده مرکز هشدارها', icon('chevron')));
      const workflowItems = Object.entries(summary.assessment_workflow).map(([status, count]) =>
        h('div', {},
          h('span', { className: `badge badge--${status === 'locked' || status === 'approved' ? 'success' : status === 'rejected' ? 'danger' : 'warning'}`, text: status }),
          h('strong', { text: formatNumber(count) }),
        ),
      );
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
      content.append(metrics, h('div', { className: 'dashboard-grid dashboard-grid--main' }, performance, schoolBars, alertPanel), h('div', { className: 'dashboard-grid dashboard-grid--secondary' }, workflow, activities), banner);
    } catch (error) {
      clear(content);
      content.append(errorState(error, () => void load()));
    }
  }
  onWindowEventWhileConnected(page, 'hamamooz:scope-change', () => void load());
  await load();
  return page;
}
