import { apiRequest } from '../api/client.js';
import { endpoints } from '../api/endpoints.js';
import type { Pagination } from '../api/types.js';
import { activeRoles } from '../app/permissions.js';
import { navigate } from '../app/router.js';
import { store } from '../app/store.js';
import { distributionChart, horizontalBarChart, lineChart, radarChart } from '../components/charts.js';
import { emptyState, errorState, skeletonCards } from '../components/feedback.js';
import { heatmap, type HeatmapRow } from '../components/heatmap.js';
import { icon } from '../components/icons.js';
import { roleExperience, type DashboardSection, type RoleExperience } from '../ui/role-experience.js';
import { clear, formatDate, formatNumber, h } from '../utils/dom.js';

interface DashboardSummary {
  selected_term: { id: string; title: string };
  counts: { students: number; classes: number; teachers: number; missing_scores: number };
  students_by_school: Array<{ school_name: string; organization_name: string; students: number }>;
  class_averages: Array<{
    enrollment__class_section_id: string;
    enrollment__class_section__title: string;
    average: number | string | null;
    students: number;
  }>;
  assessment_workflow: Record<string, number>;
  latest_activities: Array<{
    id: string;
    action: string;
    entity_type: string;
    entity_id: string;
    actor_id: number | null;
    created_at: string;
  }>;
}

interface AlertSummary {
  id: string;
  student_name: string;
  class_title: string;
  severity: string;
  status: string;
  absence_percent: string;
  created_at: string;
}

interface AcademicYearOption {
  id: string;
  title: string;
  is_current: boolean;
  is_active: boolean;
}

interface ClassOption {
  id: string;
  title: string;
}

interface AnalyticsDomain {
  code: string;
  title: string;
  score: number | null;
}

interface EvaluationStudent {
  enrollment: string;
  student: string;
  student_name: string;
  student_number: string;
  class_section: string;
  completion_status: 'provisional' | 'final';
  completion_percent: number;
  overall_score: number | null;
  performance_level: string | null;
  change: number | null;
  trend: 'improving' | 'stable' | 'declining' | 'insufficient_data';
  trend_label: string;
  recommendation: string | null;
  completion_warning: string | null;
  domain_scores: AnalyticsDomain[];
}

interface EvaluationDashboard {
  rank_scope: 'school' | 'class';
  counts: {
    students: number;
    evaluated: number;
    final: number;
    provisional: number;
    ranked: number;
  };
  monthly_trend: Array<{ month_no: number; average: number; students: number }>;
  domain_scores: Array<{ code: string; title: string; average: number | null }>;
  performance_distribution: Record<string, number>;
  students: EvaluationStudent[];
}

const MONTHS = [
  'تیر', 'مرداد', 'شهریور', 'مهر', 'آبان', 'آذر',
  'دی', 'بهمن', 'اسفند', 'فروردین', 'اردیبهشت', 'خرداد',
];

const workflowLabels: Record<string, string> = {
  draft: 'پیش‌نویس',
  submitted: 'در انتظار تأیید',
  rejected: 'ردشده',
  approved: 'تأییدشده',
  locked: 'قفل‌شده',
};

const metricMeta = {
  students: { label: 'دانش‌آموزان فعال', icon: 'users', tone: 'primary', detail: 'در حوزه فعال' },
  classes: { label: 'کلاس‌های فعال', icon: 'building', tone: 'blue', detail: 'دارای ثبت‌نام فعال' },
  teachers: { label: 'دبیران فعال', icon: 'user', tone: 'green', detail: 'دارای ارائه درس' },
  missing_scores: { label: 'نمره ثبت‌نشده', icon: 'warning', tone: 'red', detail: 'نیازمند پیگیری' },
} as const;

function metricCard(key: keyof DashboardSummary['counts'], value: number, term: string): HTMLElement {
  const meta = metricMeta[key];
  const detail = key === 'classes' ? `نوبت ${term}` : meta.detail;
  return h('article', { className: `metric-card role-metric role-metric--${meta.tone}` },
    h('span', { className: `metric-card__icon metric-card__icon--${meta.tone}` }, icon(meta.icon)),
    h('div', {}, h('small', { text: meta.label }), h('strong', { text: formatNumber(value) }), h('span', { text: detail })),
  );
}

function sectionCard(title: string, description: string, content: HTMLElement, cardIcon = 'chart', className = ''): HTMLElement {
  return h('article', { className: `card decision-card ${className}`.trim() },
    h('div', { className: 'card-header' },
      h('div', {}, h('h2', { text: title }), h('p', { text: description })),
      h('span', { className: 'card-icon' }, icon(cardIcon)),
    ),
    content,
  );
}

function activityLabel(action: string, entityType: string): string {
  const known: Record<string, string> = {
    'auth.login': 'ورود به سامانه',
    'auth.logout': 'خروج از سامانه',
    'score.updated': 'ویرایش نمره',
    'assessment.created': 'ایجاد ارزیابی',
    'attendance.finalized': 'نهایی‌سازی حضور و غیاب',
    'report.created': 'ایجاد گزارش',
    'evaluation.manual_created': 'ثبت ارزیابی ماهانه',
    'evaluation.manual_updated': 'ویرایش ارزیابی ماهانه',
  };
  if (known[action]) return known[action] ?? action;
  const readableEntity = entityType.replaceAll('_', ' ');
  return `${action.replaceAll('.', ' · ')} — ${readableEntity}`;
}

function attentionSection(summary: DashboardSummary, alerts: Pagination<AlertSummary> | null, alertsError: unknown, reload: () => void): HTMLElement {
  if (alertsError) {
    return h('article', { className: 'attention-strip attention-strip--warning', role: 'alert' },
      h('span', { className: 'attention-strip__icon' }, icon('warning')),
      h('div', {}, h('strong', { text: 'بخشی از وضعیت دریافت نشد' }), h('p', { text: 'خلاصه آموزشی آماده است اما وضعیت هشدارها نامشخص است.' })),
      h('button', { className: 'button button--secondary', type: 'button', onClick: reload }, icon('refresh'), 'تلاش دوباره'),
    );
  }
  const openAlerts = alerts?.count ?? 0;
  const attentionCount = openAlerts + summary.counts.missing_scores;
  if (!attentionCount) {
    return h('article', { className: 'attention-strip attention-strip--success', role: 'status' },
      h('span', { className: 'attention-strip__icon' }, icon('check')),
      h('div', {}, h('strong', { text: 'مورد فوری ثبت نشده است' }), h('p', { text: `وضعیت ${summary.selected_term.title} در حوزه فعال پایدار است.` })),
      h('small', { text: `به‌روزرسانی ${formatDate(new Date(), true)}` }),
    );
  }
  return h('article', { className: 'attention-strip attention-strip--danger' },
    h('span', { className: 'attention-strip__icon' }, icon('bell')),
    h('div', {}, h('strong', { text: `${formatNumber(attentionCount)} مورد نیازمند توجه` }), h('p', { text: `${formatNumber(openAlerts)} هشدار باز و ${formatNumber(summary.counts.missing_scores)} نمره ثبت‌نشده` })),
    h('button', { className: 'button button--secondary', type: 'button', onClick: () => navigate(openAlerts ? '/alerts' : '/resources/assessments') }, 'بررسی موارد', icon('chevron')),
  );
}

function alertsSection(alerts: Pagination<AlertSummary> | null, alertsError: unknown): HTMLElement {
  const content = alertsError
    ? errorState(alertsError, () => navigate('/alerts'))
    : alerts?.results.length
      ? h('div', { className: 'decision-list' }, ...alerts.results.map(alert => h('button', {
        className: 'decision-list__item',
        type: 'button',
        onClick: () => navigate(`/alerts?selected=${encodeURIComponent(alert.id)}`),
      },
      h('span', { className: `severity-dot severity-dot--${alert.severity}`, 'aria-hidden': 'true' }),
      h('div', {}, h('strong', { text: alert.student_name }), h('small', { text: `${alert.class_title} · غیبت ${formatNumber(alert.absence_percent, 1)}٪` })),
      icon('chevron'),
      )))
      : emptyState('هشدار بازی وجود ندارد', 'در حال حاضر موردی برای پیگیری فوری در حوزه فعال ثبت نشده است.');
  return sectionCard('پیگیری‌های فوری', alerts ? `${formatNumber(alerts.count)} هشدار باز` : 'وضعیت هشدارها', content, 'bell', 'decision-card--alerts');
}

function classesSection(summary: DashboardSummary): HTMLElement {
  const points = [...summary.class_averages]
    .map(item => ({
      label: item.enrollment__class_section__title,
      value: item.average === null ? null : Number(item.average),
      detail: `${formatNumber(item.students)} دانش‌آموز`,
    }))
    .sort((a, b) => (b.value ?? -1) - (a.value ?? -1));
  return sectionCard(
    'مقایسه عملکرد کلاس‌ها',
    `میانگین نتیجه نوبت ${summary.selected_term.title} از ۲۰`,
    horizontalBarChart({ title: 'مقایسه میانگین کلاس‌ها', points, max: 20, valueSuffix: ' / ۲۰', limit: 12 }),
    'chart',
    'decision-card--wide',
  );
}

function schoolsSection(summary: DashboardSummary): HTMLElement {
  const points = [...summary.students_by_school]
    .map(item => ({ label: item.school_name, value: item.students, detail: item.organization_name }))
    .sort((a, b) => (b.value ?? 0) - (a.value ?? 0));
  return sectionCard(
    'توزیع دانش‌آموزان بین مدارس',
    'فقط ثبت‌نام‌های فعال در حوزه مجاز شما محاسبه شده‌اند.',
    horizontalBarChart({ title: 'دانش‌آموزان به تفکیک مدرسه', points, limit: 12 }),
    'building',
  );
}

function workflowSection(summary: DashboardSummary): HTMLElement {
  return sectionCard(
    'جریان ارزیابی‌ها',
    'وضعیت ارزیابی‌های قابل دسترس در نوبت فعال.',
    distributionChart({ title: 'توزیع وضعیت ارزیابی‌ها', values: summary.assessment_workflow, labels: workflowLabels }),
    'check',
  );
}

function activitySection(summary: DashboardSummary): HTMLElement {
  const content = summary.latest_activities.length
    ? h('ol', { className: 'activity-timeline' }, ...summary.latest_activities.map(item => h('li', {},
      h('span', { className: 'activity-timeline__marker', 'aria-hidden': 'true' }),
      h('div', {}, h('strong', { text: activityLabel(item.action, item.entity_type) }), h('small', { text: formatDate(item.created_at, true) })),
    )))
    : emptyState('فعالیتی ثبت نشده است', 'آخرین تغییرات مجاز سامانه در این بخش نمایش داده می‌شوند.');
  return sectionCard('آخرین فعالیت‌ها', 'ردپای تغییرات قابل مشاهده در حوزه فعال.', content, 'refresh');
}

function evaluationAnalyticsSection(experience: RoleExperience): HTMLElement {
  const schoolId = store.state.scope.schoolId;
  const organizationId = store.state.scope.organizationId;
  const body = h('div', { className: 'evaluation-analytics__body', 'aria-live': 'polite' });
  const yearSelect = h('select', { className: 'analytics-filter', 'aria-label': 'سال تحصیلی' }, h('option', { value: '', text: 'سال تحصیلی' })) as HTMLSelectElement;
  const classSelect = h('select', { className: 'analytics-filter', 'aria-label': 'کلاس' }, h('option', { value: '', text: 'همه کلاس‌های مجاز' })) as HTMLSelectElement;
  const refreshButton = h('button', { className: 'button button--secondary', type: 'button' }, icon('refresh'), 'به‌روزرسانی') as HTMLButtonElement;
  const controls = h('div', { className: 'analytics-controls' }, yearSelect, classSelect, refreshButton);
  const section = sectionCard(experience.evaluationTitle, experience.evaluationDescription, h('div', {}, controls, body), 'sparkles', 'decision-card--full evaluation-analytics');

  if (!schoolId) {
    yearSelect.disabled = true;
    classSelect.disabled = true;
    refreshButton.disabled = true;
    body.append(emptyState('برای تحلیل دقیق یک شعبه انتخاب کنید', 'API تحلیل ارزیابی برای حفظ محدوده دسترسی، دقیقاً یک مدرسه فعال نیاز دارد. از نوار بالای سامانه شعبه را انتخاب کنید.'));
    return section;
  }

  let loadVersion = 0;

  const renderDashboard = (dashboard: EvaluationDashboard): void => {
    clear(body);
    const miniMetrics = h('div', { className: 'analytics-mini-metrics' },
      h('div', {}, h('small', { text: 'دانش‌آموز' }), h('strong', { text: formatNumber(dashboard.counts.students) })),
      h('div', {}, h('small', { text: 'دارای ارزیابی' }), h('strong', { text: formatNumber(dashboard.counts.evaluated) })),
      h('div', {}, h('small', { text: 'نهایی' }), h('strong', { text: formatNumber(dashboard.counts.final) })),
      h('div', {}, h('small', { text: 'ناقص' }), h('strong', { text: formatNumber(dashboard.counts.provisional) })),
    );
    const trend = lineChart({
      title: 'روند ماهانه میانگین ارزیابی جامع',
      points: dashboard.monthly_trend.map(point => ({
        label: MONTHS[point.month_no - 1] ?? `ماه ${formatNumber(point.month_no)}`,
        value: point.average,
        detail: `${formatNumber(point.students)} دانش‌آموز نهایی`,
      })),
      min: 0,
      max: 20,
      valueSuffix: ' / ۲۰',
    });
    const domains = radarChart({
      title: 'نمودار راداری میانگین حوزه‌های ارزیابی',
      max: 20,
      points: dashboard.domain_scores.map(domain => ({ label: domain.title, value: domain.average })),
    });
    const distribution = distributionChart({
      title: 'توزیع سطح عملکرد دانش‌آموزان دارای ارزیابی نهایی',
      values: dashboard.performance_distribution,
    });

    const domainColumns = dashboard.domain_scores.map(domain => domain.title);
    const heatRows: HeatmapRow[] = [...dashboard.students]
      .sort((a, b) => {
        if (a.trend === 'declining' && b.trend !== 'declining') return -1;
        if (b.trend === 'declining' && a.trend !== 'declining') return 1;
        return (a.overall_score ?? 99) - (b.overall_score ?? 99);
      })
      .slice(0, 10)
      .map(student => ({
        label: student.student_name,
        detail: student.trend_label,
        cells: dashboard.domain_scores.map(domain => ({
          label: domain.title,
          value: student.domain_scores.find(item => item.code === domain.code)?.score ?? null,
        })),
      }));

    const declining = dashboard.students
      .filter(student => student.trend === 'declining')
      .sort((a, b) => (a.change ?? 0) - (b.change ?? 0))
      .slice(0, 6);
    const followUps = declining.length
      ? h('div', { className: 'student-followups' }, ...declining.map(student => h('button', {
        className: 'student-followups__item',
        type: 'button',
        onClick: () => navigate(`/students/${encodeURIComponent(student.student)}`),
      },
      h('div', {}, h('strong', { text: student.student_name }), h('small', { text: student.recommendation ?? 'روند نزولی نیازمند بررسی است.' })),
      h('span', { className: 'trend-badge trend-badge--down', text: student.change === null ? 'افت' : `${formatNumber(student.change, 1)}−` }),
      )))
      : emptyState('روند نزولی قطعی ثبت نشده است', 'افت فقط زمانی قطعی محسوب می‌شود که ارزیابی‌های نهایی کافی برای مقایسه وجود داشته باشند.');

    body.append(
      miniMetrics,
      h('div', { className: 'analytics-chart-grid' },
        sectionCard('روند ماهانه', 'میانگین ارزیابی‌های نهایی در هر ماه.', trend, 'chart', 'analytics-subcard analytics-subcard--wide'),
        sectionCard('پروفایل حوزه‌ها', 'مقایسه حوزه‌های آموزشی، تربیتی و مهارتی از ۲۰.', domains, 'sparkles', 'analytics-subcard'),
        sectionCard('توزیع سطح عملکرد', 'فقط دانش‌آموزانی که ارزیابی نهایی دارند.', distribution, 'users', 'analytics-subcard'),
      ),
      sectionCard('نقشه حرارتی حوزه‌های ارزیابی', 'ده دانش‌آموز اولویت‌دار بر اساس افت و امتیاز پایین‌تر. این نمودار حوزه‌های ارزیابی را نشان می‌دهد، نه ضعف دروس.', heatmap({ title: 'نقشه حرارتی حوزه‌های ارزیابی دانش‌آموزان', rows: heatRows, columns: domainColumns, max: 20 }), 'chart', 'analytics-subcard analytics-subcard--wide'),
      sectionCard('نیازمند پیگیری آموزشی', 'روند نزولی فقط بر اساس ارزیابی‌های نهایی محاسبه می‌شود.', followUps, 'warning', 'analytics-subcard analytics-subcard--wide'),
    );
  };

  const loadDashboard = async (): Promise<void> => {
    const academicYear = yearSelect.value;
    if (!academicYear) return;
    const version = ++loadVersion;
    refreshButton.disabled = true;
    body.setAttribute('aria-busy', 'true');
    clear(body);
    body.append(h('div', { className: 'analytics-loading' }, h('span', { className: 'spinner' }), h('span', { text: 'در حال محاسبه نمای تحلیلی…' })));
    try {
      const dashboard = await apiRequest<EvaluationDashboard>(endpoints.monthlyEvaluations.dashboard, {
        query: { academic_year: academicYear, class_section: classSelect.value || undefined },
      });
      if (version !== loadVersion) return;
      renderDashboard(dashboard);
    } catch (error) {
      if (version !== loadVersion) return;
      clear(body);
      body.append(errorState(error, () => void loadDashboard()));
    } finally {
      if (version === loadVersion) {
        body.setAttribute('aria-busy', 'false');
        refreshButton.disabled = false;
      }
    }
  };

  const loadClasses = async (): Promise<void> => {
    classSelect.disabled = true;
    classSelect.replaceChildren(h('option', { value: '', text: 'همه کلاس‌های مجاز' }));
    if (!yearSelect.value) return;
    try {
      const response = await apiRequest<Pagination<ClassOption>>(endpoints.classes, {
        query: { school: schoolId, academic_year: yearSelect.value, is_active: true, page_size: 200, ordering: 'title' },
      });
      classSelect.append(...response.results.map(item => h('option', { value: item.id, text: item.title })));
      classSelect.disabled = false;
    } catch {
      classSelect.replaceChildren(h('option', { value: '', text: 'دریافت کلاس‌ها ناموفق بود' }));
    }
  };

  const initialize = async (): Promise<void> => {
    clear(body);
    body.append(h('div', { className: 'analytics-loading' }, h('span', { className: 'spinner' }), h('span', { text: 'در حال آماده‌سازی فیلترهای تحلیلی…' })));
    try {
      const years = await apiRequest<Pagination<AcademicYearOption>>(endpoints.academicYears, {
        query: { organization: organizationId || undefined, is_active: true, page_size: 50, ordering: '-starts_on' },
      });
      yearSelect.replaceChildren(...years.results.map(item => h('option', { value: item.id, text: `${item.title}${item.is_current ? ' — جاری' : ''}` })));
      const current = years.results.find(item => item.is_current) ?? years.results[0];
      if (!current) {
        yearSelect.replaceChildren(h('option', { value: '', text: 'سال تحصیلی فعالی وجود ندارد' }));
        clear(body);
        body.append(emptyState('سال تحصیلی فعالی پیدا نشد', 'برای نمایش تحلیل‌ها ابتدا سال تحصیلی فعال را در تنظیمات آموزشی تعریف کنید.'));
        return;
      }
      yearSelect.value = current.id;
      await loadClasses();
      await loadDashboard();
    } catch (error) {
      clear(body);
      body.append(errorState(error, () => void initialize()));
    }
  };

  yearSelect.addEventListener('change', () => void loadClasses().then(loadDashboard));
  classSelect.addEventListener('change', () => void loadDashboard());
  refreshButton.addEventListener('click', () => void loadDashboard());
  void initialize();
  return section;
}

export async function renderDashboardPage(): Promise<HTMLElement> {
  const user = store.state.user;
  const roles = activeRoles();
  const experience = roleExperience(roles);
  const name = user?.first_name || user?.username || 'کاربر';
  const page = h('section', { className: `page dashboard-page dashboard-page--${experience.role}` });
  const content = h('div', { className: 'dashboard-content', 'aria-live': 'polite' });
  const actions = h('div', { className: 'page-actions' },
    experience.secondaryAction ? h('button', { className: 'button button--secondary', type: 'button', onClick: () => navigate(experience.secondaryAction!.href) }, icon(experience.secondaryAction.icon), experience.secondaryAction.label) : null,
    h('button', { className: 'button button--primary', type: 'button', onClick: () => navigate(experience.primaryAction.href) }, icon(experience.primaryAction.icon), experience.primaryAction.label),
  );
  page.append(
    h('div', { className: 'page-heading role-heading' },
      h('div', {}, h('span', { className: 'eyebrow', text: experience.eyebrow }), h('h1', { text: experience.title(name) }), h('p', { text: experience.description })),
      actions,
    ),
    content,
  );

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
      const metrics = h('div', { className: 'metric-grid role-metric-grid' }, ...experience.metricOrder.map(key => metricCard(key, summary.counts[key], summary.selected_term.title)));

      const sections = new Map<DashboardSection, HTMLElement>([
        ['attention', attentionSection(summary, alerts, alertsError, () => void load())],
        ['metrics', metrics],
        ['evaluation', evaluationAnalyticsSection(experience)],
        ['classes', classesSection(summary)],
        ['schools', schoolsSection(summary)],
        ['workflow', workflowSection(summary)],
        ['alerts', alertsSection(alerts, alertsError)],
        ['activity', activitySection(summary)],
      ]);

      clear(content);
      content.setAttribute('aria-busy', 'false');
      const grid = h('div', { className: 'decision-dashboard' });
      for (const key of experience.sectionOrder) {
        const section = sections.get(key);
        if (section) grid.append(section);
      }
      content.append(grid);
    } catch (error) {
      clear(content);
      content.setAttribute('aria-busy', 'false');
      content.append(errorState(error, () => void load()));
    }
  }

  void load();
  return page;
}
