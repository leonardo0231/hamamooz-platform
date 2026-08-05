import * as XLSX from '../vendor/xlsx.js';
import { apiRequest } from '../api/client.js';
import { endpoints } from '../api/endpoints.js';
import { operationById } from '../api/contract.js';
import type { Pagination } from '../api/types.js';
import { hasWriteScope } from '../app/permissions.js';
import { store } from '../app/store.js';
import { onWindowEventWhileConnected, h, clear, formatDate, formatNumber } from '../utils/dom.js';
import { confirmDialog, emptyState, errorState, loadingState, toast } from '../components/feedback.js';
import { icon } from '../components/icons.js';

interface ImportError { sheet?: string; row: number | null; column?: string; code?: string; message: string; }
interface SchoolOption { id: string; name: string; }
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
  errors: ImportError[];
  created_at: string;
  started_at?: string | null;
  finished_at?: string | null;
  result_summary?: Record<string, string | number>;
}

const importTypeLabels: Record<string, string> = {
  comprehensive_school: 'فایل جامع مدرسه',
  students: 'دانش‌آموزان',
  enrollments: 'ثبت‌نام و کلاس‌بندی',
  scores: 'نمرات اولیه',
  monthly_evaluations: 'ارزیابی جامع ماهانه',
};
const expectedHeaders: Record<string, string[]> = {
  students: ['national_id', 'first_name', 'last_name', 'birth_date', 'gender'],
  enrollments: ['national_id', 'academic_year_code', 'grade_code', 'class_code', 'student_number', 'enrolled_on'],
  scores: ['assessment_id', 'national_id', 'value', 'status', 'note'],
  monthly_evaluations: ['نسخه قالب', 'کد مدرسه', 'سال تحصیلی', 'کد کلاس', 'شماره دانش‌آموزی', 'کد ملی', 'شماره ماه', 'کد شاخص', 'امتیاز', 'توضیحات'],
};
const terminalStatuses = new Set(['completed', 'failed', 'cancelled']);
const summaryLabels: Record<string, string> = {
  classes_created: 'کلاس ایجادشده', classes_updated: 'کلاس به‌روزشده',
  students_created: 'دانش‌آموز ایجادشده', students_updated: 'دانش‌آموز به‌روزشده',
  enrollments_created: 'ثبت‌نام ایجادشده', enrollments_updated: 'ثبت‌نام به‌روزشده',
  evaluations_created: 'ارزیابی ایجادشده', evaluations_updated: 'ارزیابی به‌روزشده',
  metric_scores_upserted: 'نمره شاخص ثبت‌شده', final_evaluations: 'ارزیابی نهایی',
  provisional_evaluations: 'ارزیابی موقت',
};

function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const link = h('a', { href: url, download: filename });
  document.body.append(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 0);
}

function badgeClass(status: string): string {
  if (status === 'completed') return 'badge--success';
  if (status === 'failed') return 'badge--danger';
  if (status === 'cancelled') return 'badge--neutral';
  return 'badge--warning';
}

async function parsePreview(file: File, type: string): Promise<{ headers: string[]; rows: string[][]; total: number; error?: string }> {
  try {
    const workbook = XLSX.read(await file.arrayBuffer(), { type: 'array', cellDates: true, sheetStubs: true });
    if (type === 'comprehensive_school') {
      const normalize = (value: unknown): string => String(value ?? '').replace(/[‌\s]/g, '').replace(/ي/g, 'ی').replace(/ك/g, 'ک');
      const findSheet = (name: string): XLSX.WorkSheet | undefined => {
        const actual = workbook.SheetNames.find(item => normalize(item) === normalize(name));
        return actual ? workbook.Sheets[actual] : undefined;
      };
      const specifications = [
        { name: 'کلاس‌بندی', headers: ['ردیف', 'کد مدرسه', 'سال تحصیلی', 'کد کلاس', 'نام کلاس', 'پایه تحصیلی', 'ظرفیت'], keyColumn: 3 },
        { name: 'دانش‌آموزان', headers: ['ردیف', 'کد محلی', 'کد ملی', 'شماره دانش‌آموزی', 'نام', 'نام خانوادگی', 'جنسیت', 'تاریخ تولد', 'کد کلاس'], keyColumn: 4 },
        { name: 'ثبت اطلاعات', headers: ['ردیف', 'ماه', 'کد محلی', 'کد ملی', 'نام و نام خانوادگی', 'کد کلاس'], keyColumn: 6 },
      ];
      const summary: string[][] = [];
      let total = 0;
      for (const specification of specifications) {
        const sheet = findSheet(specification.name);
        if (!sheet) return { headers: [], rows: [], total: 0, error: `شیت «${specification.name}» در فایل پیدا نشد.` };
        const matrix = XLSX.utils.sheet_to_json<unknown[]>(sheet, { header: 1, defval: '' });
        const headers = (matrix[3] ?? []).map(value => String(value).trim());
        if (specification.headers.some((header, index) => normalize(headers[index]) !== normalize(header))) {
          return { headers, rows: [], total: 0, error: `عنوان ستون‌های شیت «${specification.name}» در ردیف ۴ با قالب رسمی یکسان نیست.` };
        }
        if (specification.name === 'ثبت اطلاعات') {
          const metricHeaders = headers.slice(6, 80).map(header => header.split('|')[0]?.trim());
          if (metricHeaders.length !== 74 || new Set(metricHeaders).size !== 74 || metricHeaders.some(code => !/^(EDU|DEV|CHR|DIS|CUL|RES|SPT|ART|PER)_\d{2}$/.test(code ?? ''))) {
            return { headers, rows: [], total: 0, error: 'نگاشت ۷۴ شاخص شیت «ثبت اطلاعات» کامل یا معتبر نیست.' };
          }
        }
        const dataRows = matrix.slice(4).filter(row => {
          if (specification.name === 'کلاس‌بندی') return String(row[3] ?? '').trim() !== '';
          if (specification.name === 'دانش‌آموزان') return String(row[4] ?? '').trim() !== '';
          return row.slice(6, 80).some(value => String(value ?? '').trim() !== '') || String(row[93] ?? '').trim() !== '';
        });
        total += dataRows.length;
        summary.push([specification.name, String(dataRows.length)]);
      }
      return { headers: ['شیت', 'تعداد ردیف قابل ورود'], rows: summary, total };
    }
    const firstSheetName = workbook.SheetNames[0];
    if (!firstSheetName) return { headers: [], rows: [], total: 0, error: 'فایل هیچ Sheet قابل خواندنی ندارد.' };
    const sheet = workbook.Sheets[firstSheetName];
    if (!sheet) return { headers: [], rows: [], total: 0, error: 'فایل هیچ Sheet قابل خواندنی ندارد.' };
    const matrix = XLSX.utils.sheet_to_json<unknown[]>(sheet, { header: 1, defval: '' });
    const headers = (matrix[0] ?? []).map(value => String(value).trim());
    const rows = matrix.slice(1).filter(row => row.some(value => String(value ?? '').trim() !== '')).map(row => row.map(value => String(value ?? '')));
    const expected = expectedHeaders[type] ?? [];
    if (headers.length !== expected.length || headers.some((header, index) => header !== expected[index])) {
      return { headers, rows: rows.slice(0, 5), total: rows.length, error: `ستون‌های فایل باید دقیقاً این ترتیب را داشته باشند: ${expected.join('، ')}` };
    }
    if (rows.length > 5000) return { headers, rows: rows.slice(0, 5), total: rows.length, error: 'حداکثر ۵۰۰۰ ردیف قابل واردسازی است.' };
    return { headers, rows: rows.slice(0, 5), total: rows.length };
  } catch {
    return { headers: [], rows: [], total: 0, error: 'فایل Excel قابل خواندن نیست.' };
  }
}

async function showErrors(job: ImportJob): Promise<void> {
  const titleId = `import-errors-title-${job.id}`;
  const dialog = h('dialog', { className: 'dialog dialog--preview', 'aria-labelledby': titleId }) as HTMLDialogElement;
  const errors = (job.errors ?? []).slice(0, 1000);
  const table = h('table', { className: 'data-table' },
    h('caption', { className: 'sr-only', text: 'خطاهای ردیفی فایل واردشده' }),
    h('thead', {}, h('tr', {}, ...['شیت', 'ردیف', 'ستون', 'کد', 'شرح خطا'].map(value => h('th', { scope: 'col', text: value })))),
    h('tbody', {}, ...errors.map(item => h('tr', {},
      h('td', { dataset: { label: 'شیت' }, text: item.sheet || '—' }),
      h('td', { dataset: { label: 'ردیف' }, text: item.row ? formatNumber(item.row) : '—' }),
      h('td', { dataset: { label: 'ستون' }, text: item.column || '—' }),
      h('td', { dataset: { label: 'کد' }, text: item.code || '—' }),
      h('td', { dataset: { label: 'شرح خطا' }, text: item.message }),
    ))),
  );
  const body = h('form', { method: 'dialog', className: 'dialog__body' },
    h('div', { className: 'dialog__header' }, h('div', {}, h('span', { className: 'eyebrow', text: 'گزارش خطا' }), h('h2', { id: titleId, text: `خطاهای ${importTypeLabels[job.import_type] ?? job.import_type}` })), h('button', { className: 'icon-button', value: 'close', 'aria-label': 'بستن' }, icon('close'))),
    h('p', { className: 'muted', text: errors.length ? `نمایش ${formatNumber(errors.length)} خطا از ${formatNumber(job.error_count)} خطا.` : 'برای این Job خطای ردیفی ثبت نشده است.' }),
    errors.length ? h('div', { className: 'table-wrap import-errors' }, table) : null,
    h('div', { className: 'dialog__actions' },
      h('button', { className: 'button button--secondary', type: 'button', onClick: () => void apiRequest<Blob>(endpoints.imports.errors(job.id), { responseType: 'blob' }).then(blob => downloadBlob(blob, `import-${job.id}-errors.xlsx`)).catch(error => toast('دانلود خطاها ناموفق بود', 'error', error instanceof Error ? error.message : undefined)) }, icon('download'), 'خروجی Excel خطاها'),
      h('button', { className: 'button button--ghost', value: 'close' }, 'بستن'),
    ),
  );
  dialog.append(body);
  dialog.addEventListener('close', () => dialog.remove(), { once: true });
  document.body.append(dialog);
  dialog.showModal();
}

function showImportSummary(job: ImportJob): void {
  const items = Object.entries(job.result_summary ?? {}).filter(([key, value]) => key in summaryLabels && typeof value === 'number');
  const dialog = h('dialog', { className: 'dialog' }) as HTMLDialogElement;
  dialog.append(h('form', { method: 'dialog', className: 'dialog__body' },
    h('div', { className: 'dialog__header' }, h('div', {}, h('span', { className: 'eyebrow', text: 'نتیجه Import' }), h('h2', { text: 'خلاصه فایل جامع مدرسه' })), h('button', { className: 'icon-button', value: 'close', 'aria-label': 'بستن' }, icon('close'))),
    h('div', { className: 'metric-grid' }, ...items.map(([key, value]) => h('article', { className: 'metric-card' }, h('span', { text: summaryLabels[key] }), h('strong', { text: formatNumber(Number(value)) })))),
    h('div', { className: 'dialog__actions' }, h('button', { className: 'button button--primary', value: 'close' }, 'بستن')),
  ));
  dialog.addEventListener('close', () => dialog.remove(), { once: true });
  document.body.append(dialog);
  dialog.showModal();
}

async function openImportDialog(onCreated: () => Promise<void>): Promise<void> {
  if (!hasWriteScope()) { toast('ابتدا حوزه مدرسه را انتخاب کنید.', 'info'); return; }
  const createOperation = operationById('imports_create');
  if (!createOperation) return;
  let schools: SchoolOption[] = [];
  try {
    const response = await apiRequest<Pagination<SchoolOption>>(endpoints.schools, { query: { page_size: 200, organization: store.state.scope.organizationId ?? undefined } });
    schools = response.results;
  } catch (error) { toast('فهرست مدارس دریافت نشد', 'error', error instanceof Error ? error.message : undefined); return; }
  const fileInput = h('input', { type: 'file', accept: '.xlsx,.xls,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,application/vnd.ms-excel', required: true }) as HTMLInputElement;
  const typeInput = h('select', { required: true }, ...Object.entries(importTypeLabels).map(([value, label]) => h('option', { value, text: label })) ) as HTMLSelectElement;
  const fileTypeLabel = h('span');
  const schoolInput = h('select', { required: true }, ...schools.map(school => h('option', { value: school.id, text: school.name }))) as HTMLSelectElement;
  if (store.state.scope.schoolId && schools.some(school => school.id === store.state.scope.schoolId)) schoolInput.value = store.state.scope.schoolId;
  const preview = h('div', { className: 'import-preview', hidden: true });
  const progress = h('div', { className: 'upload-progress', hidden: true, role: 'progressbar', 'aria-label': 'پیشرفت بارگذاری فایل', 'aria-valuemin': '0', 'aria-valuemax': '100', 'aria-valuenow': '0' }, h('div', {}, h('i')), h('span', { text: '۰٪' }));
  const submit = h('button', { className: 'button button--primary', type: 'submit', disabled: true }, icon('upload'), 'بارگذاری و اعتبارسنجی');
  const syncFileType = (): void => {
    const comprehensive = typeInput.value === 'comprehensive_school';
    fileInput.accept = comprehensive
      ? '.xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
      : '.xlsx,.xls,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,application/vnd.ms-excel';
    fileTypeLabel.textContent = comprehensive ? 'فایل (.xlsx)' : 'فایل (.xlsx یا .xls)';
  };
  syncFileType();
  const updatePreview = async (): Promise<void> => {
    const file = fileInput.files?.[0];
    clear(preview);
    preview.hidden = !file;
    submit.disabled = true;
    if (!file) return;
    const extension = file.name.toLowerCase().split('.').pop();
    if (extension !== 'xlsx' && extension !== 'xls') { preview.append(h('p', { className: 'validation-message validation-message--error', text: 'فقط فایل‌های .xlsx و .xls پذیرفته می‌شوند.' })); return; }
    if (typeInput.value === 'comprehensive_school' && extension !== 'xlsx') { preview.append(h('p', { className: 'validation-message validation-message--error', text: 'فایل جامع مدرسه فقط با قالب .xlsx پذیرفته می‌شود.' })); return; }
    if (file.size > 10 * 1024 * 1024) { preview.append(h('p', { className: 'validation-message validation-message--error', text: 'حجم فایل نباید بیشتر از ۱۰ مگابایت باشد.' })); return; }
    const parsed = await parsePreview(file, typeInput.value);
    preview.append(h('div', { className: 'import-file-meta' }, h('strong', { text: file.name }), h('span', { text: `${formatNumber(parsed.total)} ردیف` })));
    if (parsed.error) preview.append(h('p', { className: 'validation-message validation-message--error', text: parsed.error }));
    else {
      preview.append(h('p', { className: 'validation-message validation-message--success', text: 'ساختار فایل معتبر است؛ اعتبارسنجی نهایی در سرور انجام می‌شود.' }));
      preview.append(h('div', { className: 'table-wrap' }, h('table', { className: 'data-table import-preview-table' },
        h('caption', { className: 'sr-only', text: 'پیش‌نمایش پنج ردیف نخست فایل' }),
        h('thead', {}, h('tr', {}, ...parsed.headers.map(header => h('th', { scope: 'col', text: header })))),
        h('tbody', {}, ...parsed.rows.map(row => h('tr', {}, ...row.map((value, index) => h('td', { dataset: { label: parsed.headers[index] ?? `ستون ${index + 1}` }, text: value || '—' }))))),
      )));
      submit.disabled = false;
    }
  };
  fileInput.addEventListener('change', () => void updatePreview());
  typeInput.addEventListener('change', () => { syncFileType(); void updatePreview(); });
  const titleId = `import-dialog-title-${Math.random().toString(36).slice(2)}`;
  const dialog = h('dialog', { className: 'dialog dialog--preview', 'aria-labelledby': titleId }) as HTMLDialogElement;
  const form = h('form', { method: 'dialog', className: 'dialog__body' },
    h('div', { className: 'dialog__header' }, h('div', {}, h('span', { className: 'eyebrow', text: 'ورود گروهی' }), h('h2', { id: titleId, text: 'بارگذاری فایل Excel' })), h('button', { className: 'icon-button', type: 'button', 'aria-label': 'بستن', onClick: () => dialog.close() }, icon('close'))),
    h('label', { className: 'form-field' }, h('span', { text: 'نوع اطلاعات' }), typeInput),
    h('label', { className: 'form-field' }, h('span', { text: 'مدرسه مقصد' }), schoolInput),
    h('label', { className: 'form-field' }, fileTypeLabel, fileInput),
    preview, progress,
    h('div', { className: 'dialog__actions' }, h('button', { className: 'button button--ghost', type: 'button', onClick: () => dialog.close() }, 'انصراف'), submit),
  );
  form.addEventListener('submit', event => {
    event.preventDefault();
    const file = fileInput.files?.[0];
    if (!file) return;
    const payload = new FormData();
    payload.append('school', schoolInput.value);
    payload.append('import_type', typeInput.value);
    payload.append('source_file', file);
    const bar = progress.querySelector<HTMLElement>('i');
    const label = progress.querySelector<HTMLElement>('span');
    progress.hidden = false; submit.disabled = true;
    void apiRequest<ImportJob>(createOperation.path, { method: 'POST', body: payload, onUploadProgress: percent => { progress.setAttribute('aria-valuenow', String(percent)); if (bar) bar.style.width = `${percent}%`; if (label) label.textContent = `${formatNumber(percent)}٪`; } })
      .then(async () => { toast('فایل دریافت شد و پردازش در صف قرار گرفت.', 'success'); dialog.close(); await onCreated(); })
      .catch(error => { submit.disabled = false; progress.hidden = true; toast('بارگذاری ناموفق بود', 'error', error instanceof Error ? error.message : undefined); });
  });
  dialog.append(form);
  dialog.addEventListener('close', () => dialog.remove(), { once: true });
  document.body.append(dialog);
  dialog.showModal();
}

export async function renderImportsPage(): Promise<HTMLElement> {
  const page = h('section', { className: 'page' });
  const list = h('div', { className: 'card import-list' });
  const writeScopeReady = hasWriteScope();
  const polling = new Set<string>();
  const load = async (): Promise<void> => {
    clear(list); list.append(loadingState());
    try {
      const response = await apiRequest<Pagination<ImportJob>>(endpoints.imports.list, { query: { page_size: 100, ordering: '-created_at' } });
      clear(list);
      if (!response.results.length) { list.append(emptyState('Job ورودی وجود ندارد', 'برای شروع، فایل معتبر را بارگذاری کنید.')); return; }
      list.append(h('div', { className: 'card-header' }, h('div', {}, h('h2', { text: 'تاریخچه پردازش فایل‌ها' }), h('p', { text: `${formatNumber(response.count)} Job` })), h('span', { className: 'card-icon' }, icon('upload'))), h('div', { className: 'table-wrap' }, h('table', { className: 'data-table' },
        h('thead', {}, h('tr', {}, ...['نوع', 'وضعیت', 'درخواست‌دهنده', 'کل ردیف', 'موفق', 'خطا', 'تاریخ', 'عملیات'].map(value => h('th', { scope: 'col', text: value })))),
        h('tbody', {}, ...response.results.map(job => h('tr', {},
          h('td', { dataset: { label: 'نوع' }, text: importTypeLabels[job.import_type] ?? job.import_type }),
          h('td', { dataset: { label: 'وضعیت' } }, h('span', { className: `badge ${badgeClass(job.status)}`, text: job.status_display || job.status })),
          h('td', { dataset: { label: 'درخواست‌دهنده' }, text: job.requested_by_name || '—' }), h('td', { dataset: { label: 'کل ردیف' }, text: formatNumber(job.total_rows) }), h('td', { dataset: { label: 'موفق' }, text: formatNumber(job.successful_rows) }),
          h('td', { dataset: { label: 'خطا' } }, job.error_count ? h('button', { className: 'link-button', type: 'button', onClick: () => void showErrors(job) }, formatNumber(job.error_count)) : '۰'),
          h('td', { dataset: { label: 'تاریخ' }, text: formatDate(job.created_at, true) }),
          h('td', { className: 'row-actions', dataset: { label: 'عملیات' } },
            job.status === 'completed' && Object.keys(job.result_summary ?? {}).length ? h('button', { className: 'button button--ghost', type: 'button', onClick: () => showImportSummary(job) }, icon('check'), 'خلاصه') : null,
            !terminalStatuses.has(job.status) ? h('button', { className: 'button button--ghost', type: 'button', disabled: !writeScopeReady, onClick: () => void cancel(job) }, icon('close'), 'لغو') : null,
            ['failed', 'processing'].includes(job.status) ? h('button', { className: 'button button--ghost', type: 'button', disabled: !writeScopeReady, onClick: () => void retry(job) }, icon('refresh'), 'تلاش مجدد') : null,
          ),
        ))),
      )));
      response.results.filter(job => !terminalStatuses.has(job.status)).forEach(job => {
        if (!polling.has(job.id)) { polling.add(job.id); void poll(job.id); }
      });
    } catch (error) { clear(list); list.append(errorState(error, () => void load())); }
  };
  const poll = async (id: string): Promise<void> => {
    try {
      for (let attempt = 0; attempt < 150 && page.isConnected; attempt += 1) {
        await new Promise(resolve => setTimeout(resolve, 2000));
        try {
          const job = await apiRequest<ImportJob>(endpoints.imports.detail(id));
          if (terminalStatuses.has(job.status)) { await load(); return; }
        } catch { return; }
      }
    } finally { polling.delete(id); }
  };
  async function retry(job: ImportJob): Promise<void> {
    if (!await confirmDialog({ title: 'تلاش مجدد', message: 'این Job ناموفق یا منقضی‌شده دوباره پردازش شود؟', confirmLabel: 'تلاش مجدد' })) return;
    try { await apiRequest(endpoints.imports.retry(job.id), { method: 'POST', body: {} }); toast('Job دوباره در صف قرار گرفت.', 'success'); await load(); }
    catch (error) { toast('تلاش مجدد ناموفق بود', 'error', error instanceof Error ? error.message : undefined); }
  }
  async function cancel(job: ImportJob): Promise<void> {
    if (!await confirmDialog({ title: 'لغو پردازش', message: 'پردازش این فایل لغو شود؟', confirmLabel: 'لغو پردازش', dangerous: true })) return;
    try { await apiRequest(endpoints.imports.cancel(job.id), { method: 'POST', body: {} }); toast('پردازش لغو شد.', 'success'); await load(); }
    catch (error) { toast('لغو پردازش ناموفق بود', 'error', error instanceof Error ? error.message : undefined); }
  }
  page.append(h('div', { className: 'page-heading' }, h('div', {}, h('span', { className: 'eyebrow', text: 'ورود یکپارچه' }), h('h1', { text: 'ورود اطلاعات از یک فایل' }), h('p', { text: 'فایل جامع، کلاس‌بندی، دانش‌آموزان و همه ارزیابی‌های ماهانه را در یک تراکنش وارد می‌کند.' })), h('button', { className: 'button button--primary', type: 'button', disabled: !writeScopeReady, title: writeScopeReady ? 'بارگذاری فایل جامع' : 'ابتدا حوزه فعال را انتخاب کنید', onClick: () => void openImportDialog(load) }, icon('upload'), 'بارگذاری فایل جامع')),
    h('div', { className: 'import-guide-grid' }, ...Object.entries(importTypeLabels).map(([type, label]) => h('article', { className: `card guide-card${type === 'comprehensive_school' ? ' guide-card--primary' : ''}` }, icon(type === 'students' ? 'users' : type === 'scores' ? 'chart' : type === 'monthly_evaluations' || type === 'comprehensive_school' ? 'check' : 'building'), h('h2', { text: label }), h('p', { text: type === 'comprehensive_school' ? 'گزینه پیشنهادی: کلاس‌ها، دانش‌آموزان و ۷۴ شاخص ارزیابی را یک‌جا وارد کنید.' : `قالب قدیمی ${label} برای سازگاری قبلی همچنان در دسترس است.` }), h('button', { className: 'button button--secondary', type: 'button', onClick: () => void apiRequest<Blob>(endpoints.imports.template(type), { responseType: 'blob' }).then(blob => downloadBlob(blob, `${type}_template.xlsx`)).catch(error => toast('دریافت قالب ناموفق بود', 'error', error instanceof Error ? error.message : undefined)) }, icon('download'), 'دانلود قالب')))),
    list,
  );
  onWindowEventWhileConnected(page, 'hamamooz:scope-change', () => void load());
  await load();
  return page;
}
