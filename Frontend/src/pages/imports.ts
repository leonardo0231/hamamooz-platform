import { apiRequest } from '../api/client.js';
import { endpoints } from '../api/endpoints.js';
import { operationById } from '../api/contract.js';
import type { Pagination } from '../api/types.js';
import { hasWriteScope } from '../app/permissions.js';
import { onWindowEventWhileConnected, h, clear, formatDate, formatNumber } from '../utils/dom.js';
import { confirmDialog, emptyState, errorState, loadingState, toast } from '../components/feedback.js';
import { icon } from '../components/icons.js';
import { openSchemaDialog } from '../components/schema-form.js';

interface ImportJob {
  id: string;
  import_type: string;
  status: string;
  status_display: string;
  school: string;
  requested_by_name: string;
  total_rows: number;
  successful_rows: number;
  error_count: number;
  errors: unknown;
  created_at: string;
}

const importTypeLabels: Record<string, string> = {
  students: 'دانش‌آموزان',
  enrollments: 'ثبت‌نام و کلاس‌بندی',
  scores: 'نمرات اولیه',
  monthly_evaluations: 'ارزیابی جامع ماهانه',
};

export async function renderImportsPage(): Promise<HTMLElement> {
  const page = h('section', { className: 'page' });
  const list = h('div', { className: 'card import-list' });
  const createOperation = operationById('imports_create');
  const progress = h('div', { className: 'upload-progress', hidden: true }, h('div', {}, h('i')), h('span', { text: '۰٪' }));
  const createImport = (): void => {
    if (!createOperation) return;
    openSchemaDialog({
      title: 'ورود فایل اطلاعات', schema: createOperation.requestSchema, multipart: true, submitLabel: 'بارگذاری و اعتبارسنجی',
      onSubmit: async payload => {
        const bar = progress.querySelector<HTMLElement>('i');
        const label = progress.querySelector<HTMLElement>('span');
        if (bar) bar.style.width = '0%';
        if (label) label.textContent = '۰٪';
        progress.hidden = false;
        try {
          await apiRequest<ImportJob>(createOperation.path, { method: 'POST', body: payload, onUploadProgress: percent => { const bar = progress.querySelector<HTMLElement>('i'); const label = progress.querySelector<HTMLElement>('span'); if (bar) bar.style.width = `${percent}%`; if (label) label.textContent = `${formatNumber(percent)}٪`; } });
          toast('فایل دریافت شد و Job پردازش ایجاد شد.', 'success');
          await load();
        } finally {
          progress.hidden = true;
        }
      },
    });
  };
  const writeScopeReady = hasWriteScope();
  page.append(h('div', { className: 'page-heading' }, h('div', {}, h('span', { className: 'eyebrow', text: 'ورود گروهی' }), h('h1', { text: 'ورود اطلاعات از فایل' }), h('p', { text: 'فایل کامل قبل از Write توسط Backend اعتبارسنجی می‌شود.' })), h('button', { className: 'button button--primary', type: 'button', disabled: !writeScopeReady, title: writeScopeReady ? 'بارگذاری فایل' : 'ابتدا حوزه فعال را انتخاب کنید', onClick: createImport }, icon('upload'), 'بارگذاری فایل')), progress,
    h('div', { className: 'import-guide-grid' },
      h('article', { className: 'card guide-card' }, icon('users'), h('h2', { text: 'دانش‌آموزان' }), h('p', { text: 'نوع import_type برابر students و فایل مطابق Template رسمی Backend.' })),
      h('article', { className: 'card guide-card' }, icon('building'), h('h2', { text: 'ثبت‌نام و کلاس‌بندی' }), h('p', { text: 'نوع import_type برابر enrollments و شناسه‌های معتبر حوزه.' })),
      h('article', { className: 'card guide-card' }, icon('chart'), h('h2', { text: 'نمرات اولیه' }), h('p', { text: 'نوع import_type برابر scores و ارزیابی‌های موجود.' })),
      h('article', { className: 'card guide-card' }, icon('check'), h('h2', { text: 'ارزیابی جامع ماهانه' }), h('p', { text: 'نوع monthly_evaluations؛ هر ردیف یک شاخص با امتیاز صحیح ۰ تا ۵ است.' })),
    ), list);

  async function retry(job: ImportJob): Promise<void> {
    if (!await confirmDialog({ title: 'تلاش مجدد', message: 'این Job ناموفق یا منقضی‌شده دوباره پردازش شود؟', confirmLabel: 'تلاش مجدد' })) return;
    try { await apiRequest(endpoints.imports.retry(job.id), { method: 'POST', body: {} }); toast('Job دوباره در صف قرار گرفت.', 'success'); await load(); }
    catch (error) { toast('تلاش مجدد ناموفق بود', 'error', error instanceof Error ? error.message : undefined); }
  }

  async function load(): Promise<void> {
    clear(list); list.append(loadingState());
    try {
      const response = await apiRequest<Pagination<ImportJob>>(endpoints.imports.list, { query: { page_size: 100, ordering: '-created_at' } });
      clear(list);
      if (!response.results.length) { list.append(emptyState('Job ورودی وجود ندارد', 'برای شروع، فایل معتبر را بارگذاری کنید.')); return; }
      list.append(h('div', { className: 'card-header' }, h('div', {}, h('h2', { text: 'تاریخچه پردازش فایل‌ها' }), h('p', { text: `${formatNumber(response.count)} Job` })), h('span', { className: 'card-icon' }, icon('upload'))), h('div', { className: 'table-wrap' }, h('table', { className: 'data-table' },
        h('thead', {}, h('tr', {}, ...['نوع', 'وضعیت', 'درخواست‌دهنده', 'کل ردیف', 'موفق', 'خطا', 'تاریخ', 'عملیات'].map(value => h('th', { scope: 'col', text: value })))),
        h('tbody', {}, ...response.results.map(job => h('tr', {},
          h('td', { dataset: { label: 'نوع' }, text: importTypeLabels[job.import_type] ?? job.import_type }), h('td', { dataset: { label: 'وضعیت' } }, h('span', { className: `badge badge--${job.status === 'completed' ? 'success' : job.status === 'failed' ? 'danger' : 'warning'}`, text: job.status_display || job.status })),
          h('td', { dataset: { label: 'درخواست‌دهنده' }, text: job.requested_by_name || '—' }), h('td', { dataset: { label: 'کل ردیف' }, text: formatNumber(job.total_rows) }), h('td', { dataset: { label: 'موفق' }, text: formatNumber(job.successful_rows) }), h('td', { dataset: { label: 'خطا' }, text: formatNumber(job.error_count) }), h('td', { dataset: { label: 'تاریخ' }, text: formatDate(job.created_at, true) }),
          h('td', { className: 'row-actions', dataset: { label: 'عملیات' } }, h('button', { className: 'button button--ghost', type: 'button', disabled: !hasWriteScope() || !['failed', 'processing'].includes(job.status), title: hasWriteScope() ? 'Backend منقضی‌شدن پردازش را اعتبارسنجی می‌کند' : 'ابتدا حوزه فعال را انتخاب کنید', onClick: () => void retry(job) }, icon('refresh'), 'تلاش مجدد')),
        ))),
      )));
    } catch (error) { clear(list); list.append(errorState(error, () => void load())); }
  }
  onWindowEventWhileConnected(page, 'hamamooz:scope-change', () => void load());
  await load();
  return page;
}
