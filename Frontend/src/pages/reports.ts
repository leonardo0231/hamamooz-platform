import { apiRequest } from '../api/client.js';
import { endpoints } from '../api/endpoints.js';
import { operationById } from '../api/contract.js';
import { actionRequestSchema } from '../api/action-schemas.js';
import { hasAnyRole, hasWriteScope } from '../app/permissions.js';
import type { Pagination, Role } from '../api/types.js';
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
  school_name: string;
  requested_by_name: string;
  formula_version: string;
  output_format: 'pdf' | 'docx';
  download_url: string | null;
  error_message: string;
  created_at: string;
  completed_at: string | null;
}

interface ReportDraft {
  id: string;
  template: string;
  term: string;
  enrollment: string | null;
  class_section: string | null;
  status: 'draft' | 'submitted' | 'approved' | 'rejected' | 'rendered';
  rejection_reason: string;
  archive_id: string | null;
  created_at: string;
  reviewed_at: string | null;
}

// Keep this in sync with Backend/hamamooz/apps/reports/views.py: REPORTERS.
const reporterRoles: Role[] = [
  'system_admin',
  'organization_admin',
  'school_manager',
  'educational_deputy',
  'operator',
  'teacher',
];

function requiredOperation(id: string) {
  const operation = operationById(id);
  if (!operation) throw new Error(`API operation is missing from the generated contract: ${id}`);
  return operation;
}

function draftStatusLabel(status: ReportDraft['status']): string {
  const labels: Record<ReportDraft['status'], string> = {
    draft: 'پیش‌نویس',
    submitted: 'ارسال‌شده',
    approved: 'تأییدشده',
    rejected: 'ردشده',
    rendered: 'رندرشده',
  };
  return labels[status];
}

function draftStatusTone(status: ReportDraft['status']): string {
  if (status === 'approved' || status === 'rendered') return 'success';
  if (status === 'rejected') return 'danger';
  if (status === 'submitted') return 'warning';
  return 'neutral';
}

function draftScopeLabel(draft: ReportDraft): string {
  if (draft.enrollment) return `ثبت‌نام: ${draft.enrollment}`;
  if (draft.class_section) return `کلاس: ${draft.class_section}`;
  return 'دامنه گزارش مشخص نیست';
}

function openPreviewDialog(preview: ReportPreviewResponse): void {
  const titleId = 'report-preview-title';
  const descriptionId = 'report-preview-description';
  const dialog = h('dialog', { className: 'dialog dialog--preview', 'aria-labelledby': titleId, 'aria-describedby': descriptionId }) as HTMLDialogElement;
  const close = h('button', { className: 'icon-button', type: 'button', 'aria-label': 'بستن', onClick: () => dialog.close() }, icon('close'));
  const frame = h('iframe', { className: 'report-preview-frame', title: 'پیش‌نمایش گزارش' }) as HTMLIFrameElement;
  frame.setAttribute('sandbox', '');
  frame.srcdoc = preview.html;
  dialog.append(h('div', { className: 'dialog__body dialog__body--preview' }, h('div', { className: 'dialog__header' }, h('div', {}, h('h2', { id: titleId, text: 'پیش‌نمایش گزارش' }), h('p', { id: descriptionId, text: 'این خروجی موقت است و در آرشیو رسمی ذخیره نمی‌شود.' })), close), frame));
  dialog.addEventListener('close', () => dialog.remove(), { once: true });
  document.body.append(dialog);
  dialog.showModal();
}

async function downloadReport(report: ReportArchive): Promise<void> {
  try {
    const blob = await apiRequest<Blob>(endpoints.reports.download(report.id), { responseType: 'blob' });
    const url = URL.createObjectURL(blob);
    const extension = report.output_format === 'docx' ? 'docx' : 'pdf';
    const anchor = h('a', { href: url, download: `hamamooz-report-${report.id}.${extension}` }) as HTMLAnchorElement;
    document.body.append(anchor); anchor.click(); anchor.remove(); URL.revokeObjectURL(url);
  } catch (error) { toast('دریافت فایل گزارش ناموفق بود', 'error', error instanceof Error ? error.message : undefined); }
}

export async function renderReportsPage(): Promise<HTMLElement> {
  const page = h('section', { className: 'page' });
  const list = h('div', { className: 'card report-list' });
  const focusDrafts = new URLSearchParams(location.search).get('view') === 'drafts';
  const archiveListOperation = requiredOperation('reports_list');
  const draftsListOperation = requiredOperation('reports_drafts_list');
  const createOperation = operationById('reports_create');
  const previewOperation = operationById('reports_preview_create');
  const hasReporterCapability = hasAnyRole(reporterRoles);
  const canCreateOrPreview = hasReporterCapability && hasWriteScope();
  const reportActionTitle = !hasReporterCapability
    ? 'نقش فعال شما مجاز به تولید یا پیش‌نمایش گزارش نیست.'
    : !hasWriteScope()
      ? 'ابتدا حوزه فعال را انتخاب کنید'
      : '';
  const openForm = (preview: boolean): void => {
    if (!canCreateOrPreview) {
      toast(reportActionTitle, 'info');
      return;
    }
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
  page.append(h('div', { className: 'page-heading' }, h('div', {}, h('span', { className: 'eyebrow', text: 'خروجی رسمی' }), h('h1', { text: 'گزارش‌ها و کارنامه‌ها' }), h('p', { text: 'پیش‌نمایش و تولید گزارش براساس داده‌های قفل‌شده و قرارداد Backend' })), h('div', { className: 'page-actions' }, h('button', { className: 'button button--secondary', type: 'button', disabled: !canCreateOrPreview, title: canCreateOrPreview ? 'پیش‌نمایش گزارش' : reportActionTitle, onClick: () => openForm(true) }, icon('eye'), 'پیش‌نمایش'), h('button', { className: 'button button--primary', type: 'button', disabled: !canCreateOrPreview, title: canCreateOrPreview ? 'تولید گزارش' : reportActionTitle, onClick: () => openForm(false) }, icon('plus'), 'تولید گزارش'))),
    h('article', { className: 'report-banner report-banner--top' }, h('span', { className: 'report-banner__visual' }, icon('file')), h('div', {}, h('h2', { text: focusDrafts ? 'پیش‌نویس‌های ارسال‌شده برای تأیید' : 'گزارش‌های قابل استناد' }), h('p', { text: focusDrafts ? 'این فهرست مستقیماً از مدل پیش‌نویس گزارش دریافت می‌شود.' : 'نسخه فرمول، Snapshot و وضعیت پردازش هر خروجی در آرشیو Backend نگهداری می‌شود.' })), h('span', { className: `badge badge--${focusDrafts ? 'warning' : 'success'}`, text: focusDrafts ? 'پیش‌نویس‌ها' : 'API واقعی' })), list);

  async function load(): Promise<void> {
    clear(list); list.append(loadingState());
    try {
      if (focusDrafts) {
        const response = await apiRequest<Pagination<ReportDraft>>(draftsListOperation.path, { query: { page_size: 100, ordering: '-created_at', status: 'submitted' } });
        const results = response.results;
        clear(list);
        if (!results.length) {
          list.append(emptyState('پیش‌نویس ارسال‌شده‌ای برای تأیید وجود ندارد', 'همه پیش‌نویس‌های قابل مشاهده بررسی شده‌اند یا موردی برای تأیید ارسال نشده است.'));
          return;
        }
        list.append(h('div', { className: 'card-header' }, h('div', {}, h('h2', { text: 'پیش‌نویس‌های گزارش' }), h('p', { text: `${formatNumber(results.length)} پیش‌نویس ارسال‌شده` })), h('span', { className: 'card-icon' }, icon('file'))), h('div', { className: 'report-grid' }, ...results.map(draft => h('article', { className: 'report-item' },
          h('span', { className: 'report-item__icon' }, icon('file')),
          h('div', { className: 'report-item__body' }, h('div', {}, h('strong', { text: 'پیش‌نویس گزارش' }), h('span', { className: `badge badge--${draftStatusTone(draft.status)}`, text: draftStatusLabel(draft.status) })), h('p', { text: draftScopeLabel(draft) }), h('small', { text: `${formatDate(draft.created_at, true)} · قالب ${draft.template} · نوبت ${draft.term}` }), draft.rejection_reason ? h('div', { className: 'inline-error', text: draft.rejection_reason }) : null),
        ))));
        return;
      }
      const response = await apiRequest<Pagination<ReportArchive>>(archiveListOperation.path, { query: { page_size: 100, ordering: '-created_at' } });
      clear(list);
      const results = response.results;
      if (!results.length) { list.append(emptyState('گزارشی تولید نشده است', 'از دکمه تولید گزارش برای ساخت کارنامه دانش‌آموز یا کلاس استفاده کنید.')); return; }
      list.append(h('div', { className: 'card-header' }, h('div', {}, h('h2', { text: 'آرشیو گزارش‌ها' }), h('p', { text: `${formatNumber(results.length)} خروجی قابل مشاهده` })), h('span', { className: 'card-icon' }, icon('file'))), h('div', { className: 'report-grid' }, ...results.map(report => h('article', { className: 'report-item' },
        h('span', { className: 'report-item__icon' }, icon('file')),
        h('div', { className: 'report-item__body' }, h('div', {}, h('strong', { text: report.report_type === 'student_report_card' ? 'کارنامه دانش‌آموز' : 'کارنامه‌های کلاس' }), h('span', { className: `badge badge--${report.status === 'completed' ? 'success' : report.status === 'failed' ? 'danger' : 'warning'}`, text: report.status_display || report.status })), h('p', { text: `درخواست‌دهنده: ${report.requested_by_name || '—'}` }), h('small', { text: `${formatDate(report.created_at, true)} · ${report.school_name || '—'} · ${(report.output_format || 'pdf').toUpperCase()} · فرمول ${report.formula_version || '—'}` }), report.error_message ? h('div', { className: 'inline-error', text: report.error_message }) : null),
        h('button', { className: 'button button--secondary', type: 'button', disabled: report.status !== 'completed', onClick: () => void downloadReport(report) }, icon('download'), 'دانلود'),
      ))));
    } catch (error) { clear(list); list.append(errorState(error, () => void load())); }
  }
  onWindowEventWhileConnected(page, 'hamamooz:scope-change', () => void load());
  await load();
  return page;
}
