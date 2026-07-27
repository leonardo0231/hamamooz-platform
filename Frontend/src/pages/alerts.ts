import { apiRequest } from '../api/client.js';
import { endpoints } from '../api/endpoints.js';
import type { Pagination } from '../api/types.js';
import { hasAnyRole, hasWriteScope, policyManagementRoles } from '../app/permissions.js';
import { onWindowEventWhileConnected, h, clear, debounce, formatDate, formatNumber } from '../utils/dom.js';
import { emptyState, errorState, loadingState, toast, confirmDialog } from '../components/feedback.js';
import { icon } from '../components/icons.js';

interface AttendanceAlert {
  id: string;
  school_name: string;
  enrollment: string;
  student: string;
  student_name: string;
  class_title: string;
  scope: string;
  severity: 'critical' | 'warning';
  period_start: string;
  period_end: string;
  absence_count: number;
  total_sessions: number;
  absence_percent: string;
  status: 'open' | 'acknowledged' | 'resolved';
  created_at: string;
  acknowledged_at: string | null;
  resolved_at: string | null;
}

const labels: Record<string, string> = { critical: 'بحرانی', warning: 'مهم', open: 'باز', acknowledged: 'در حال بررسی', resolved: 'حل‌شده', daily: 'روزانه', period: 'زنگ درسی' };

function alertCard(alert: AttendanceAlert, selected: boolean, onSelect: () => void): HTMLElement {
  return h('button', { className: `alert-list-item ${selected ? 'is-selected' : ''}`, type: 'button', dataset: { id: alert.id }, 'aria-pressed': String(selected), onClick: onSelect },
    h('span', { className: 'avatar avatar--soft', text: alert.student_name.split(/\s+/).map(part => part[0]).slice(0, 2).join('') }),
    h('div', {}, h('div', { className: 'alert-list-item__title' }, h('strong', { text: alert.student_name }), h('span', { className: `badge badge--${alert.severity === 'critical' ? 'danger' : 'warning'}`, text: labels[alert.severity] })), h('p', { text: `${alert.class_title} · غیبت ${formatNumber(alert.absence_percent)}٪` }), h('small', { text: formatDate(alert.created_at, true) })),
  );
}

function detailPanel(alert: AttendanceAlert, refresh: () => Promise<void>): HTMLElement {
  const canManage = hasAnyRole(policyManagementRoles) && hasWriteScope();
  const action = async (name: 'acknowledge' | 'resolve'): Promise<void> => {
    const title = name === 'acknowledge' ? 'ثبت مشاهده هشدار' : 'رفع هشدار';
    if (!await confirmDialog({ title, message: `این عملیات برای هشدار ${alert.student_name} ثبت شود؟`, confirmLabel: name === 'acknowledge' ? 'مشاهده شد' : 'رفع هشدار' })) return;
    try {
      await apiRequest(name === 'acknowledge' ? endpoints.alerts.acknowledge(alert.id) : endpoints.alerts.resolve(alert.id), { method: 'POST', body: {} });
      toast(name === 'acknowledge' ? 'هشدار در حال بررسی قرار گرفت.' : 'هشدار رفع شد.', 'success');
      await refresh();
    } catch (error) { toast('ثبت عملیات ناموفق بود', 'error', error instanceof Error ? error.message : undefined); }
  };
  return h('article', { className: 'alert-detail' },
    h('div', { className: 'alert-detail__header' }, h('div', {}, h('span', { className: `badge badge--${alert.severity === 'critical' ? 'danger' : 'warning'}`, text: labels[alert.severity] }), h('h2', { text: `هشدار حضور و غیاب ${alert.student_name}` }), h('p', { text: `${alert.class_title} · ${alert.school_name}` })), h('span', { className: `alert-detail__icon alert-detail__icon--${alert.severity}` }, icon('warning'))),
    h('div', { className: 'alert-evidence-grid' },
      h('div', {}, h('small', { text: 'درصد غیبت' }), h('strong', { text: `${formatNumber(alert.absence_percent)}٪` })),
      h('div', {}, h('small', { text: 'تعداد غیبت' }), h('strong', { text: formatNumber(alert.absence_count) })),
      h('div', {}, h('small', { text: 'کل جلسات' }), h('strong', { text: formatNumber(alert.total_sessions) })),
      h('div', {}, h('small', { text: 'نوع محاسبه' }), h('strong', { text: labels[alert.scope] ?? alert.scope })),
    ),
    h('div', { className: 'evidence-card' }, h('h3', { text: 'شواهد و بازه هشدار' }), h('dl', {},
      h('div', {}, h('dt', { text: 'شروع بازه' }), h('dd', { text: formatDate(alert.period_start) })),
      h('div', {}, h('dt', { text: 'پایان بازه' }), h('dd', { text: formatDate(alert.period_end) })),
      h('div', {}, h('dt', { text: 'وضعیت' }), h('dd', {}, h('span', { className: `badge badge--${alert.status === 'resolved' ? 'success' : 'warning'}`, text: labels[alert.status] }))),
      alert.acknowledged_at ? h('div', {}, h('dt', { text: 'زمان مشاهده' }), h('dd', { text: formatDate(alert.acknowledged_at, true) })) : null,
      alert.resolved_at ? h('div', {}, h('dt', { text: 'زمان رفع' }), h('dd', { text: formatDate(alert.resolved_at, true) })) : null,
    )),
    h('div', { className: 'recommended-action' }, h('span', {}, icon('sparkles')), h('div', {}, h('h3', { text: 'اقدام بعدی' }), h('p', { text: 'پس از بررسی وضعیت دانش‌آموز، هشدار را مشاهده‌شده یا رفع‌شده علامت بزنید. کنترل نهایی دسترسی و گردش‌کار توسط Backend انجام می‌شود.' }))),
    h('div', { className: 'alert-detail__actions' },
      canManage && alert.status === 'open' ? h('button', { className: 'button button--secondary', type: 'button', onClick: () => void action('acknowledge') }, icon('eye'), 'در حال بررسی') : null,
      canManage && alert.status !== 'resolved' ? h('button', { className: 'button button--success', type: 'button', onClick: () => void action('resolve') }, icon('check'), 'رفع هشدار') : null,
    ),
  );
}

export async function renderAlertsPage(): Promise<HTMLElement> {
  const page = h('section', { className: 'page' });
  const stats = h('div', { className: 'metric-grid' });
  const search = h('input', { type: 'search', placeholder: 'جست‌وجوی نام دانش‌آموز…', 'aria-label': 'جست‌وجوی هشدارها' }) as HTMLInputElement;
  const severity = h('select', { 'aria-label': 'شدت هشدار' }, h('option', { value: '', text: 'همه شدت‌ها' }), h('option', { value: 'critical', text: 'بحرانی' }), h('option', { value: 'warning', text: 'مهم' })) as HTMLSelectElement;
  const status = h('select', { 'aria-label': 'وضعیت هشدار' }, h('option', { value: '', text: 'همه وضعیت‌ها' }), h('option', { value: 'open', text: 'باز' }), h('option', { value: 'acknowledged', text: 'در حال بررسی' }), h('option', { value: 'resolved', text: 'حل‌شده' })) as HTMLSelectElement;
  const policy = h('select', { 'aria-label': 'سیاست حضور برای ارزیابی' }, h('option', { value: '', text: 'انتخاب سیاست حضور' })) as HTMLSelectElement;
  const canEvaluate = hasAnyRole(policyManagementRoles);
  const evaluateButton = h('button', { className: 'button button--secondary', type: 'button', disabled: !hasWriteScope(), title: hasWriteScope() ? 'اجرای سیاست انتخاب‌شده' : 'ابتدا حوزه فعال را انتخاب کنید', onClick: () => void evaluate() }, icon('refresh'), 'ارزیابی سیاست‌ها') as HTMLButtonElement;
  const list = h('div', { className: 'alerts-list' });
  const detail = h('div', { className: 'alerts-detail-panel', role: 'region', 'aria-label': 'جزئیات هشدار انتخاب‌شده', 'aria-live': 'polite', tabindex: '-1' });
  const layout = h('div', { className: 'alerts-center card' }, h('div', { className: 'alerts-center__toolbar' }, h('label', { className: 'search-input' }, icon('search'), search), severity, status, canEvaluate ? policy : null, canEvaluate ? evaluateButton : null), h('div', { className: 'alerts-center__content' }, list, detail));
  page.append(h('div', { className: 'page-heading' }, h('div', {}, h('span', { className: 'eyebrow', text: 'تحلیل و پیگیری' }), h('h1', { text: 'مرکز هشدارها و پیگیری' }), h('p', { text: 'هشدارهای حضور و غیاب تولیدشده توسط Policyهای Backend' }))), stats, layout);
  let selectedId = new URLSearchParams(location.search).get('selected');

  async function evaluate(): Promise<void> {
    if (!policy.value) { toast('ابتدا یک سیاست حضور را انتخاب کنید.', 'info'); policy.focus(); return; }
    if (!await confirmDialog({ title: 'ارزیابی سیاست‌های حضور', message: 'Policyهای فعال برای حوزه انتخاب‌شده اجرا شوند؟', confirmLabel: 'اجرای ارزیابی' })) return;
    try { await apiRequest(endpoints.alerts.evaluate, { method: 'POST', body: { policy: policy.value } }); toast('ارزیابی هشدارها در Backend انجام شد.', 'success'); await load(); }
    catch (error) { toast('ارزیابی هشدارها ناموفق بود', 'error', error instanceof Error ? error.message : undefined); }
  }

  async function loadPolicies(): Promise<void> {
    if (!canEvaluate) return;
    policy.replaceChildren(h('option', { value: '', text: 'انتخاب سیاست حضور' }));
    evaluateButton.disabled = true;
    try {
      const response = await apiRequest<Pagination<{ id: string; title: string }>>(endpoints.attendancePolicies, { query: { page_size: 200, is_active: true } });
      policy.append(...response.results.map(item => h('option', { value: item.id, text: item.title })));
      evaluateButton.disabled = !hasWriteScope() || response.results.length === 0;
    } catch (error) {
      toast('دریافت سیاست‌های حضور ناموفق بود', 'error', error instanceof Error ? error.message : undefined);
    }
  }

  async function load(): Promise<void> {
    clear(list); clear(detail); clear(stats);
    list.append(loadingState());
    try {
      const baseQuery = { page_size: 100, ordering: '-created_at', search: search.value || undefined, severity: severity.value || undefined, status: status.value || undefined };
      const [filtered, open, critical, acknowledged, resolved] = await Promise.all([
        apiRequest<Pagination<AttendanceAlert>>(endpoints.alerts.list, { query: baseQuery }),
        apiRequest<Pagination<AttendanceAlert>>(endpoints.alerts.list, { query: { page_size: 1, status: 'open' } }),
        apiRequest<Pagination<AttendanceAlert>>(endpoints.alerts.list, { query: { page_size: 1, severity: 'critical', status: 'open' } }),
        apiRequest<Pagination<AttendanceAlert>>(endpoints.alerts.list, { query: { page_size: 1, status: 'acknowledged' } }),
        apiRequest<Pagination<AttendanceAlert>>(endpoints.alerts.list, { query: { page_size: 1, status: 'resolved' } }),
      ]);
      stats.append(
        h('article', { className: 'metric-card metric-card--border-red' }, h('span', { className: 'metric-card__icon metric-card__icon--red' }, icon('warning')), h('div', {}, h('small', { text: 'بحرانی باز' }), h('strong', { text: formatNumber(critical.count) }))),
        h('article', { className: 'metric-card metric-card--border-orange' }, h('span', { className: 'metric-card__icon metric-card__icon--orange' }, icon('bell')), h('div', {}, h('small', { text: 'کل باز' }), h('strong', { text: formatNumber(open.count) }))),
        h('article', { className: 'metric-card metric-card--border-purple' }, h('span', { className: 'metric-card__icon metric-card__icon--purple' }, icon('search')), h('div', {}, h('small', { text: 'در حال بررسی' }), h('strong', { text: formatNumber(acknowledged.count) }))),
        h('article', { className: 'metric-card metric-card--border-green' }, h('span', { className: 'metric-card__icon metric-card__icon--green' }, icon('check')), h('div', {}, h('small', { text: 'حل‌شده' }), h('strong', { text: formatNumber(resolved.count) }))),
      );
      clear(list);
      if (!filtered.results.length) { list.append(emptyState('هشداری یافت نشد', 'فیلترها را تغییر دهید یا ارزیابی Policyها را اجرا کنید.')); detail.append(emptyState('هشداری انتخاب نشده است', 'یک هشدار را از فهرست انتخاب کنید.')); return; }
      selectedId = filtered.results.some(item => item.id === selectedId) ? selectedId : filtered.results[0]?.id ?? null;
      for (const alert of filtered.results) list.append(alertCard(alert, alert.id === selectedId, () => {
        selectedId = alert.id;
        clear(detail);
        detail.append(detailPanel(alert, load));
        history.replaceState({}, '', `/alerts?selected=${alert.id}`);
        list.querySelectorAll<HTMLElement>('.alert-list-item').forEach(node => {
          const selected = node.dataset.id === alert.id;
          node.classList.toggle('is-selected', selected);
          node.setAttribute('aria-pressed', String(selected));
        });
        detail.focus({ preventScroll: true });
      }));
      const selected = filtered.results.find(item => item.id === selectedId);
      if (selected) detail.append(detailPanel(selected, load));
    } catch (error) {
      clear(list); clear(detail); clear(stats);
      list.append(errorState(error, () => void load()));
    }
  }
  const refresh = debounce(() => void load(), 350);
  search.addEventListener('input', refresh);
  severity.addEventListener('change', () => void load());
  status.addEventListener('change', () => void load());
  onWindowEventWhileConnected(page, 'hamamooz:scope-change', () => { void loadPolicies(); void load(); });
  await Promise.all([loadPolicies(), load()]);
  return page;
}
