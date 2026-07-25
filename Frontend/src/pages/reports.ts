import { apiRequest } from '../api/client.js';
import { endpoints } from '../api/endpoints.js';
import { operationById } from '../api/contract.js';
import { actionRequestSchema } from '../api/action-schemas.js';
import { hasWriteScope } from '../app/permissions.js';
import type { Pagination } from '../api/types.js';
import { onWindowEventWhileConnected, h, clear, formatDate, formatNumber } from '../utils/dom.js';
import { emptyState, errorState, loadingState, toast } from '../components/feedback.js';
import { icon } from '../components/icons.js';
import { openSchemaDialog } from '../components/schema-form.js';

interface ReportPreviewResponse { html: string; snapshot: unknown; }

interface ReportArchive {
  id: string;
  report_type: string;
  status: string;
  status_display: string;
  requested_by_name: string;
  formula_version: string;
  download_url: string | null;
  error_message: string;
  created_at: string;
  completed_at: string | null;
}

function openPreviewDialog(preview: ReportPreviewResponse): void {
  const dialog = h('dialog', { className: 'dialog dialog--preview' }) as HTMLDialogElement;
  const close = h('button', { className: 'icon-button', type: 'button', 'aria-label': 'بستن', onClick: () => dialog.close() }, icon('close'));
  const frame = h('iframe', { className: 'report-preview-frame', title: 'پیش‌نمایش گزارش' }) as HTMLIFrameElement;
  frame.setAttribute('sandbox', '');
  frame.srcdoc = preview.html;
  dialog.append(h('div', { className: 'dialog__body dialog__body--preview' }, h('div', { className: 'dialog__header' }, h('div', {}, h('h2', { text: 'پیش‌نمایش گزارش' }), h('p', { text: 'این خروجی موقت است و در آرشیو رسمی ذخیره نمی‌شود.' })), close), frame));
  dialog.addEventListener('close', () => dialog.remove(), { once: true });
  document.body.append(dialog);
  dialog.showModal();
}

async function downloadReport(report: ReportArchive): Promise<void> {
  try {
    const blob = await apiRequest<Blob>(endpoints.reports.download(report.id), { responseType: 'blob' });
    const url = URL.createObjectURL(blob);
    const anchor = h('a', { href: url, download: `hamamooz-report-${report.id}.pdf` }) as HTMLAnchorElement;
    document.body.append(anchor); anchor.click(); anchor.remove(); URL.revokeObjectURL(url);
  } catch (error) { toast('دریافت فایل گزارش ناموفق بود', 'error', error instanceof Error ? error.message : undefined); }
}

export async function renderReportsPage(): Promise<HTMLElement> {
  const page = h('section', { className: 'page' });
  const list = h('div', { className: 'card report-list' });
  const createOperation = operationById('reports_create');
  const previewOperation = operationById('reports_preview_create');
  const openForm = (preview: boolean): void => {
    const operation = preview ? previewOperation : createOperation;
    if (!operation) return;
    openSchemaDialog({
      title: preview ? 'پیش‌نمایش گزارش' : 'تولید گزارش رسمی',
      schema: preview ? actionRequestSchema(operation) : operation.requestSchema,
      submitLabel: preview ? 'دریافت پیش‌نمایش' : 'شروع تولید',
      onSubmit: async payload => {
        if (preview) {
          const result = await apiRequest<ReportPreviewResponse>(operation.path, { method: 'POST', body: payload });
          openPreviewDialog(result);
          toast('پیش‌نمایش گزارش آماده شد.', 'success');
          return;
        }
        await apiRequest<ReportArchive>(operation.path, { method: 'POST', body: payload });
        toast('گزارش برای تولید در صف قرار گرفت.', 'success');
        await load();
      },
    });
  };
  page.append(h('div', { className: 'page-heading' }, h('div', {}, h('span', { className: 'eyebrow', text: 'خروجی رسمی' }), h('h1', { text: 'گزارش‌ها و کارنامه‌ها' }), h('p', { text: 'پیش‌نمایش و تولید گزارش براساس داده‌های قفل‌شده و قرارداد Backend' })), h('div', { className: 'page-actions' }, h('button', { className: 'button button--secondary', type: 'button', disabled: !hasWriteScope(), title: hasWriteScope() ? 'پیش‌نمایش گزارش' : 'ابتدا حوزه فعال را انتخاب کنید', onClick: () => openForm(true) }, icon('eye'), 'پیش‌نمایش'), h('button', { className: 'button button--primary', type: 'button', disabled: !hasWriteScope(), title: hasWriteScope() ? 'تولید گزارش' : 'ابتدا حوزه فعال را انتخاب کنید', onClick: () => openForm(false) }, icon('plus'), 'تولید گزارش'))),
    h('article', { className: 'report-banner report-banner--top' }, h('span', { className: 'report-banner__visual' }, icon('file')), h('div', {}, h('h2', { text: 'گزارش‌های قابل استناد' }), h('p', { text: 'نسخه فرمول، Snapshot و وضعیت پردازش هر خروجی در آرشیو Backend نگهداری می‌شود.' })), h('span', { className: 'badge badge--success', text: 'API واقعی' })), list);

  async function load(): Promise<void> {
    clear(list); list.append(loadingState());
    try {
      const response = await apiRequest<Pagination<ReportArchive>>(endpoints.reports.list, { query: { page_size: 100, ordering: '-created_at' } });
      clear(list);
      if (!response.results.length) { list.append(emptyState('گزارشی تولید نشده است', 'از دکمه تولید گزارش برای ساخت کارنامه دانش‌آموز یا کلاس استفاده کنید.')); return; }
      list.append(h('div', { className: 'card-header' }, h('div', {}, h('h2', { text: 'آرشیو گزارش‌ها' }), h('p', { text: `${formatNumber(response.count)} خروجی ثبت‌شده` })), h('span', { className: 'card-icon' }, icon('file'))), h('div', { className: 'report-grid' }, ...response.results.map(report => h('article', { className: 'report-item' },
        h('span', { className: 'report-item__icon' }, icon('file')),
        h('div', { className: 'report-item__body' }, h('div', {}, h('strong', { text: report.report_type === 'student_report_card' ? 'کارنامه دانش‌آموز' : 'کارنامه‌های کلاس' }), h('span', { className: `badge badge--${report.status === 'completed' ? 'success' : report.status === 'failed' ? 'danger' : 'warning'}`, text: report.status_display || report.status })), h('p', { text: `درخواست‌دهنده: ${report.requested_by_name || '—'}` }), h('small', { text: `${formatDate(report.created_at, true)} · فرمول ${report.formula_version || '—'}` }), report.error_message ? h('div', { className: 'inline-error', text: report.error_message }) : null),
        h('button', { className: 'button button--secondary', type: 'button', disabled: report.status !== 'completed', onClick: () => void downloadReport(report) }, icon('download'), 'دانلود'),
      ))));
    } catch (error) { clear(list); list.append(errorState(error, () => void load())); }
  }
  onWindowEventWhileConnected(page, 'hamamooz:scope-change', () => void load());
  await load();
  return page;
}
