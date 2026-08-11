import { portalApi, type PortalSnapshot, type PortalStudent } from '../api/portal.js';
import { ApiError } from '../api/types.js';
import { emptyState, errorState, loadingState, toast } from '../components/feedback.js';
import { icon } from '../components/icons.js';
import { clear, formatDate, formatNumber, h, safeText } from '../utils/dom.js';
import { labelForValue } from '../ui/presentation.js';

function download(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const anchor = h('a', { href: url, download: filename }) as HTMLAnchorElement;
  document.body.append(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

function section(title: string, description: string, glyph: string, content: HTMLElement): HTMLElement {
  return h(
    'article',
    { className: 'card' },
    h('div', { className: 'card-header' }, h('div', {}, h('h2', { text: title }), h('p', { text: description })), h('span', { className: 'card-icon' }, icon(glyph))),
    content,
  );
}

function snapshotView(snapshot: PortalSnapshot, onDownload: (reportId: string) => Promise<void>): HTMLElement {
  const attendance = h(
    'div',
    { className: 'metric-grid' },
    h('div', { className: 'metric-card metric-card--border-blue' }, h('small', { text: 'جلسات نهایی‌شده' }), h('strong', { text: formatNumber(snapshot.attendance.finalized_session_count) })),
    h('div', { className: 'metric-card metric-card--border-orange' }, h('small', { text: 'غیبت‌های غیرموجه' }), h('strong', { text: formatNumber(snapshot.attendance.unexcused_absence_count) })),
    h('div', { className: 'metric-card metric-card--border-green' }, h('small', { text: 'غیبت‌های موجه' }), h('strong', { text: formatNumber(snapshot.attendance.excused_absence_count) })),
  );
  const reports = snapshot.reports.length
    ? h('div', { className: 'report-list' }, ...snapshot.reports.map(report => h(
      'div',
      { className: 'report-item' },
      h('span', { className: 'report-item__icon' }, icon('file')),
      h('div', { className: 'report-item__body' }, h('strong', { text: labelForValue(report.report_type) }), h('small', { text: `${safeText(report.term)} · ${formatDate(report.released_at, true)} · ${report.output_format.toUpperCase()}` })),
      h('button', { className: 'button button--secondary', type: 'button', onClick: () => void onDownload(report.id) }, icon('download'), 'دریافت'),
    )))
    : emptyState('گزارش منتشرشده‌ای وجود ندارد', 'فقط گزارش‌هایی که کارکنان مدرسه منتشر کرده‌اند در اینجا نمایش داده می‌شوند.');
  const recommendations = snapshot.recommendations.length
    ? h('ul', { className: 'plain-list' }, ...snapshot.recommendations.map(item => h('li', {}, h('strong', { text: labelForValue(item.priority) }), h('p', { text: safeText(item.approved_text) }), h('small', { text: formatDate(item.approved_at, true) }))))
    : emptyState('توصیه تأییدشده‌ای وجود ندارد', 'پیش‌نویس‌ها و توصیه‌های مخاطبان دیگر نمایش داده نمی‌شوند.');
  const guidePlans = snapshot.guidePlans.length
    ? h('ul', { className: 'plain-list' }, ...snapshot.guidePlans.map(plan => h('li', {}, h('strong', { text: safeText(plan.title) }), h('p', { text: safeText(plan.objectives) }), h('small', { text: formatDate(plan.released_at, true) }))))
    : emptyState('برنامه پیگیری منتشرشده‌ای وجود ندارد', 'فقط برنامه‌های راهنمایی منتشرشده توسط مدرسه نمایش داده می‌شوند.');
  return h(
    'div',
    { className: 'portal-content-grid' },
    section('خلاصه حضور و غیاب', 'فقط جلسات نهایی‌شده نمایش داده می‌شوند.', 'calendar', attendance),
    section('گزارش‌های منتشرشده', 'گزارش‌های رسمی منتشرشده برای شما.', 'file', reports),
    section('توصیه‌های تأییدشده', 'پیشنهادهایی که برای مخاطبان این پرتال تأیید شده‌اند.', 'check', recommendations),
    section('برنامه‌های پیگیری', 'فقط برنامه‌های راهنمایی منتشرشده.', 'check', guidePlans),
  );
}

function errorStatus(error: unknown): number | null {
  return error instanceof ApiError ? error.status : null;
}

export async function renderPortalPage(): Promise<HTMLElement> {
  const page = h('section', { className: 'page portal-page' });
  const content = h('div');
  page.append(
    h('div', { className: 'page-heading' }, h('div', {}, h('h1', { text: 'پرتال خانواده و دانش‌آموز' }), h('p', { text: 'گزارش‌های منتشرشده، توصیه‌های تأییدشده و برنامه‌های پیگیری.' }))),
    content,
  );

  async function loadParent(children: PortalStudent[]): Promise<void> {
    clear(content);
    if (!children.length) {
      content.append(emptyState('دانش‌آموز مرتبطی یافت نشد', 'برای این حساب ولی، ارتباط فعال با دانش‌آموزی ثبت نشده است.'));
      return;
    }
    const selector = h('select', { className: 'scope-select', 'aria-label': 'انتخاب دانش‌آموز' }, ...children.map(child => h('option', { value: child.id, text: child.full_name }))) as HTMLSelectElement;
    const selected = h('div');
    const loadChild = async (): Promise<void> => {
      clear(selected);
      selected.append(loadingState());
      try {
        const studentId = selector.value;
        const snapshot = await portalApi.childSnapshot(studentId);
        clear(selected);
        selected.append(snapshotView(snapshot, async reportId => {
        try {
          const report = snapshot.reports.find(item => item.id === reportId);
          download(await portalApi.downloadChildReport(studentId, reportId), `released-report-${reportId}.${report?.output_format ?? 'pdf'}`);
        }
          catch (error) { toast('دریافت گزارش ناموفق بود.', 'error', error instanceof Error ? error.message : undefined); }
        }));
      } catch (error) {
        clear(selected);
        selected.append(errorState(error, () => void loadChild()));
      }
    };
    selector.addEventListener('change', () => void loadChild());
    content.append(section('دانش‌آموزان من', 'فهرست دانش‌آموزان مرتبط توسط سامانه تعیین می‌شود.', 'users', selector), selected);
    await loadChild();
  }

  async function loadStudent(): Promise<void> {
    clear(content);
    content.append(loadingState());
    const snapshot = await portalApi.studentSnapshot();
    clear(content);
    content.append(snapshotView(snapshot, async reportId => {
        try {
          const report = snapshot.reports.find(item => item.id === reportId);
          download(await portalApi.downloadStudentReport(reportId), `released-report-${reportId}.${report?.output_format ?? 'pdf'}`);
        }
        catch (error) { toast('دریافت گزارش ناموفق بود.', 'error', error instanceof Error ? error.message : undefined); }
    }));
  }

  async function load(): Promise<void> {
    clear(content);
    content.append(loadingState());
    try {
      const { children } = await portalApi.children();
      await loadParent(children);
    } catch (parentError) {
      if (errorStatus(parentError) !== 403) {
        clear(content);
        content.append(errorState(parentError, () => void load()));
        return;
      }
      try {
        await loadStudent();
      } catch (studentError) {
        clear(content);
        if (errorStatus(studentError) === 403) {
          content.append(emptyState('دسترسی پرتال پیکربندی نشده است', 'این حساب نه ولی فعال است و نه حساب فعال پرتال دانش‌آموز.'));
        } else {
          content.append(errorState(studentError, () => void load()));
        }
      }
    }
  }

  await load();
  return page;
}
