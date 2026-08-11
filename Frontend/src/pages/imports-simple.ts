import * as XLSX from '../vendor/xlsx.js';
import { apiRequest } from '../api/client.js';
import { operationById } from '../api/contract.js';
import { endpoints } from '../api/endpoints.js';
import type { Pagination } from '../api/types.js';
import { hasWriteScope } from '../app/permissions.js';
import { navigate } from '../app/router.js';
import { store } from '../app/store.js';
import { confirmDialog, emptyState, errorState, loadingState, toast } from '../components/feedback.js';
import { icon } from '../components/icons.js';
import { clear, formatDate, formatNumber, h, onWindowEventWhileConnected } from '../utils/dom.js';

interface SchoolOption { id: string; name: string; code?: string; }
interface ImportError { sheet?: string; row: number | null; column?: string; code?: string; message: string; }
interface ImportJob {
  id: string;
  import_type: string;
  status: string;
  status_display: string;
  school_name?: string;
  requested_by_name: string;
  total_rows: number;
  successful_rows: number;
  error_count: number;
  errors: ImportError[];
  result_summary?: Record<string, string | number>;
  created_at: string;
}

const terminalStatuses = new Set(['completed', 'failed', 'cancelled']);
const summaryLabels: Record<string, string> = {
  classes_created: 'کلاس جدید',
  classes_updated: 'کلاس تغییرکرده',
  classes_unchanged: 'کلاس بدون تغییر',
  students_created: 'دانش‌آموز جدید',
  students_updated: 'دانش‌آموز تغییرکرده',
  students_unchanged: 'دانش‌آموز بدون تغییر',
  enrollments_created: 'ثبت‌نام جدید',
  enrollments_updated: 'ثبت‌نام تغییرکرده',
  enrollments_unchanged: 'ثبت‌نام بدون تغییر',
  evaluations_created: 'ارزیابی جدید',
  evaluations_updated: 'ارزیابی تغییرکرده',
  evaluations_unchanged: 'ارزیابی بدون تغییر',
  metric_scores_created: 'شاخص جدید',
  metric_scores_updated: 'شاخص تغییرکرده',
  metric_scores_unchanged: 'شاخص بدون تغییر',
  final_evaluations: 'ارزیابی کامل',
  provisional_evaluations: 'ارزیابی ناقص/موقت',
  records_deleted: 'حذف از طریق فایل',
};

function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const link = h('a', { href: url, download: filename });
  document.body.append(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 0);
}

function statusClass(status: string): string {
  if (status === 'completed') return 'badge--success';
  if (status === 'failed') return 'badge--danger';
  if (status === 'cancelled') return 'badge--neutral';
  return 'badge--warning';
}

function normalize(value: unknown): string {
  return String(value ?? '').replace(/[‌\s]/g, '').replace(/ي/g, 'ی').replace(/ك/g, 'ک');
}

async function previewComprehensive(file: File): Promise<{ rows: string[][]; total: number; error?: string }> {
  try {
    const workbook = XLSX.read(await file.arrayBuffer(), { type: 'array', cellDates: true, sheetStubs: true });
    const specs = [
      { name: 'کلاس‌بندی', headers: ['ردیف', 'کد مدرسه', 'سال تحصیلی', 'کد کلاس', 'نام کلاس', 'پایه تحصیلی', 'ظرفیت'], data: (row: unknown[]) => String(row[3] ?? '').trim() !== '' },
      { name: 'دانش‌آموزان', headers: ['ردیف', 'کد محلی', 'کد ملی', 'شماره دانش‌آموزی', 'نام', 'نام خانوادگی', 'جنسیت', 'تاریخ تولد', 'کد کلاس'], data: (row: unknown[]) => String(row[4] ?? '').trim() !== '' },
      { name: 'ثبت اطلاعات', headers: ['ردیف', 'ماه', 'کد محلی', 'کد ملی', 'نام و نام خانوادگی', 'کد کلاس'], data: (row: unknown[]) => row.slice(6, 80).some(value => String(value ?? '').trim() !== '') || String(row[93] ?? '').trim() !== '' },
    ];
    const rows: string[][] = [];
    let total = 0;
    for (const spec of specs) {
      const actual = workbook.SheetNames.find(name => normalize(name) === normalize(spec.name));
      if (!actual) return { rows: [], total: 0, error: `شیت «${spec.name}» پیدا نشد.` };
      const sheet = workbook.Sheets[actual];
      if (!sheet) return { rows: [], total: 0, error: `شیت «${spec.name}» قابل خواندن نیست.` };
      const matrix = XLSX.utils.sheet_to_json<unknown[]>(sheet, { header: 1, defval: '' });
      const headers = (matrix[3] ?? []).map(value => String(value).trim());
      if (spec.headers.some((header, index) => normalize(headers[index]) !== normalize(header))) {
        return { rows: [], total: 0, error: `عنوان ستون‌های شیت «${spec.name}» با قالب رسمی یکسان نیست.` };
      }
      if (spec.name === 'ثبت اطلاعات') {
        const metricCodes = headers.slice(6, 80).map(header => header.split('|')[0]?.trim());
        if (metricCodes.length !== 74 || new Set(metricCodes).size !== 74) {
          return { rows: [], total: 0, error: '۷۴ شاخص شیت «ثبت اطلاعات» کامل یا یکتا نیستند.' };
        }
      }
      const count = matrix.slice(4).filter(spec.data).length;
      total += count;
      rows.push([spec.name, String(count)]);
    }
    return { rows, total };
  } catch {
    return { rows: [], total: 0, error: 'فایل XLSX قابل خواندن نیست.' };
  }
}

function showSummary(job: ImportJob): void {
  const entries = Object.entries(job.result_summary ?? {}).filter(([key, value]) => key in summaryLabels && typeof value === 'number');
  const dialog = h('dialog', { className: 'dialog', 'aria-label': 'خلاصه فایل جامع' }) as HTMLDialogElement;
  dialog.append(h('form', { method: 'dialog', className: 'dialog__body' },
    h('div', { className: 'dialog__header' }, h('div', {}, h('span', { className: 'eyebrow', text: 'نتیجه پردازش' }), h('h2', { text: 'خلاصه فایل جامع' })), h('button', { className: 'icon-button', value: 'close', 'aria-label': 'بستن' }, icon('close'))),
    entries.length
      ? h('div', { className: 'metric-grid' }, ...entries.map(([key, value]) => h('article', { className: 'metric-card' }, h('span', { text: summaryLabels[key] }), h('strong', { text: formatNumber(Number(value)) }))))
      : h('p', { className: 'muted', text: 'خلاصه عددی برای این Job ثبت نشده است.' }),
    h('p', { className: 'muted', text: 'نبودن یک رکورد در فایل به معنی حذف آن نیست. حذف و تغییر وضعیت فقط به‌صورت صریح از بخش مدیریت دستی انجام می‌شود.' }),
    h('div', { className: 'dialog__actions' }, h('button', { className: 'button button--primary', value: 'close' }, 'بستن')),
  ));
  dialog.addEventListener('close', () => dialog.remove(), { once: true });
  document.body.append(dialog);
  dialog.showModal();
}

function showErrors(job: ImportJob): void {
  const errors = (job.errors ?? []).slice(0, 50);
  const dialog = h('dialog', { className: 'dialog dialog--preview', 'aria-label': 'خطاهای فایل ورودی' }) as HTMLDialogElement;
  dialog.append(h('form', { method: 'dialog', className: 'dialog__body' },
    h('div', { className: 'dialog__header' }, h('div', {}, h('span', { className: 'eyebrow', text: 'خطاهای فایل' }), h('h2', { text: `${formatNumber(job.error_count)} خطا` })), h('button', { className: 'icon-button', value: 'close', 'aria-label': 'بستن' }, icon('close'))),
    errors.length ? h('div', { className: 'table-wrap' }, h('table', { className: 'data-table' },
      h('thead', {}, h('tr', {}, ...['شیت', 'ردیف', 'ستون', 'شرح'].map(value => h('th', { text: value })))),
      h('tbody', {}, ...errors.map(error => h('tr', {},
        h('td', { text: error.sheet || '—' }),
        h('td', { text: error.row ? formatNumber(error.row) : '—' }),
        h('td', { text: error.column || '—' }),
        h('td', { text: error.message }),
      ))),
    )) : h('p', { text: 'خطای ردیفی ثبت نشده است.' }),
    h('div', { className: 'dialog__actions' },
      h('button', { className: 'button button--secondary', type: 'button', onClick: () => void apiRequest<Blob>(endpoints.imports.errors(job.id), { responseType: 'blob' }).then(blob => downloadBlob(blob, `import-${job.id}-errors.xlsx`)) }, icon('download'), 'دانلود همه خطاها'),
      h('button', { className: 'button button--ghost', value: 'close' }, 'بستن'),
    ),
  ));
  dialog.addEventListener('close', () => dialog.remove(), { once: true });
  document.body.append(dialog);
  dialog.showModal();
}

async function openUploadDialog(onCreated: () => Promise<void>): Promise<void> {
  if (!hasWriteScope()) {
    toast('ابتدا مدرسه فعال را از بالای صفحه انتخاب کنید.', 'info');
    return;
  }
  const createOperation = operationById('imports_create');
  if (!createOperation) return;

  let schools: SchoolOption[] = [];
  try {
    const response = await apiRequest<Pagination<SchoolOption>>(endpoints.schools, { query: { page_size: 200, organization: store.state.scope.organizationId ?? undefined } });
    schools = response.results;
  } catch (error) {
    toast('فهرست مدارس دریافت نشد', 'error', error instanceof Error ? error.message : undefined);
    return;
  }

  const school = h('select', { required: true }, ...schools.map(item => h('option', { value: item.id, text: item.name }))) as HTMLSelectElement;
  if (store.state.scope.schoolId && schools.some(item => item.id === store.state.scope.schoolId)) school.value = store.state.scope.schoolId;
  const file = h('input', { type: 'file', accept: '.xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', required: true }) as HTMLInputElement;
  const preview = h('div', { className: 'import-preview', hidden: true });
  const submit = h('button', { className: 'button button--primary', type: 'submit', disabled: true }, icon('upload'), 'ارسال فایل و شروع پردازش') as HTMLButtonElement;

  const selectedSchool = (): SchoolOption | undefined => schools.find(item => item.id === school.value);
  const selectedSchoolDescription = (): string => {
    const target = selectedSchool();
    if (!target) return 'مدرسه مقصد انتخاب نشده است.';
    return target.code
      ? `مدرسه مقصد: ${target.name} (کد مدرسه: ${target.code}). کد مدرسه در شیت کلاس‌بندی باید دقیقاً همین باشد.`
      : `مدرسه مقصد: ${target.name}. کد مدرسه در شیت کلاس‌بندی باید دقیقاً با کد ثبت‌شده در سامانه یکسان باشد.`;
  };

  const refreshPreview = async (): Promise<void> => {
    clear(preview);
    const selected = file.files?.[0];
    preview.hidden = !selected;
    submit.disabled = true;
    if (!selected) return;
    if (!selected.name.toLowerCase().endsWith('.xlsx')) {
      preview.append(h('p', { className: 'validation-message validation-message--error', text: 'فقط فایل جامع با پسوند .xlsx پذیرفته می‌شود.' }));
      return;
    }
    if (selected.size > 10 * 1024 * 1024) {
      preview.append(h('p', { className: 'validation-message validation-message--error', text: 'حجم فایل نباید بیشتر از ۱۰ مگابایت باشد.' }));
      return;
    }
    const result = await previewComprehensive(selected);
    preview.append(
      h('div', { className: 'import-file-meta' }, h('strong', { text: selected.name }), h('span', { text: `${formatNumber(result.total)} ردیف قابل پردازش` })),
      h('p', { className: 'muted', text: selectedSchoolDescription() }),
    );
    if (result.error) {
      preview.append(h('p', { className: 'validation-message validation-message--error', text: result.error }));
      return;
    }
    preview.append(
      h('p', { className: 'validation-message validation-message--success', text: 'ساختار اولیه درست است. کنترل نهایی شناسه‌ها، مدرسه، کلاس و ظرفیت روی سرور انجام می‌شود.' }),
      h('div', { className: 'table-wrap' }, h('table', { className: 'data-table' },
        h('thead', {}, h('tr', {}, h('th', { text: 'شیت' }), h('th', { text: 'تعداد ردیف' }))),
        h('tbody', {}, ...result.rows.map(row => h('tr', {}, h('td', { text: row[0] }), h('td', { text: formatNumber(Number(row[1])) })))),
      )),
    );
    submit.disabled = false;
  };

  file.addEventListener('change', () => void refreshPreview());
  school.addEventListener('change', () => {
    if (file.files?.[0]) void refreshPreview();
  });

  const dialog = h('dialog', { className: 'dialog dialog--preview', 'aria-label': 'بارگذاری فایل جامع مدرسه' }) as HTMLDialogElement;
  const form = h('form', { className: 'dialog__body' },
    h('div', { className: 'dialog__header' }, h('div', {}, h('span', { className: 'eyebrow', text: 'تنها مسیر ورود گروهی' }), h('h2', { text: 'بارگذاری فایل جامع مدرسه' })), h('button', { className: 'icon-button', type: 'button', onClick: () => dialog.close(), 'aria-label': 'بستن' }, icon('close'))),
    h('p', { text: 'فقط قالب جامع رسمی پذیرفته می‌شود. فایل می‌تواند رکوردهای جدید را ایجاد و رکوردهای موجود را به‌روزرسانی کند؛ نبودن رکورد در فایل باعث حذف آن نمی‌شود.' }),
    h('label', { className: 'form-field' }, h('span', { text: 'مدرسه مقصد' }), school, h('small', { text: 'مدرسه باید همان مدرسه‌ای باشد که کد آن داخل شیت کلاس‌بندی ثبت شده است.' })),
    h('label', { className: 'form-field' }, h('span', { text: 'فایل جامع (.xlsx)' }), file, h('small', { text: 'حداکثر ۱۰ مگابایت. کد ملی را ۱۰ رقمی و با صفر ابتدایی نگه دارید.' })),
    preview,
    h('div', { className: 'dialog__actions' }, h('button', { className: 'button button--ghost', type: 'button', onClick: () => dialog.close() }, 'انصراف'), submit),
  ) as HTMLFormElement;

  form.addEventListener('submit', event => {
    event.preventDefault();
    const selected = file.files?.[0];
    if (!selected || submit.disabled) return;
    const payload = new FormData();
    payload.append('school', school.value);
    payload.append('import_type', 'comprehensive_school');
    payload.append('source_file', selected);
    submit.disabled = true;
    void apiRequest<ImportJob>(createOperation.path, { method: 'POST', body: payload })
      .then(async () => {
        toast('فایل دریافت شد و برای پردازش در صف قرار گرفت.', 'success');
        dialog.close();
        await onCreated();
      })
      .catch(error => {
        submit.disabled = false;
        toast('ارسال فایل ناموفق بود', 'error', error instanceof Error ? error.message : undefined);
      });
  });
  dialog.append(form);
  dialog.addEventListener('close', () => dialog.remove(), { once: true });
  document.body.append(dialog);
  dialog.showModal();
}

export async function renderImportsPage(): Promise<HTMLElement> {
  const page = h('section', { className: 'page' });
  const list = h('div', { className: 'card import-list' });
  const polling = new Set<string>();

  const load = async (): Promise<void> => {
    clear(list);
    list.append(loadingState());
    try {
      const response = await apiRequest<Pagination<ImportJob>>(endpoints.imports.list, { query: { page_size: 100, ordering: '-created_at', import_type: 'comprehensive_school' } });
      clear(list);
      if (!response.results.length) {
        list.append(emptyState('هنوز فایل جامعی پردازش نشده است', 'قالب رسمی را دانلود کنید، تکمیل کنید و همین‌جا بارگذاری کنید.'));
        return;
      }
      list.append(
        h('div', { className: 'card-header' }, h('div', {}, h('h2', { text: 'تاریخچه فایل‌های جامع' }), h('p', { text: `${formatNumber(response.count)} پردازش` }))),
        h('div', { className: 'table-wrap' }, h('table', { className: 'data-table' },
          h('thead', {}, h('tr', {}, ...['مدرسه', 'وضعیت', 'کل ردیف', 'موفق', 'خطا', 'تاریخ', 'عملیات'].map(value => h('th', { text: value })))),
          h('tbody', {}, ...response.results.map(job => h('tr', {},
            h('td', { text: job.school_name || '—' }),
            h('td', {}, h('span', { className: `badge ${statusClass(job.status)}`, text: job.status_display || job.status })),
            h('td', { text: formatNumber(job.total_rows) }),
            h('td', { text: formatNumber(job.successful_rows) }),
            h('td', {}, job.error_count ? h('button', { className: 'link-button', type: 'button', onClick: () => showErrors(job) }, formatNumber(job.error_count)) : '۰'),
            h('td', { text: formatDate(job.created_at, true) }),
            h('td', { className: 'row-actions' },
              job.status === 'completed' ? h('button', { className: 'button button--ghost', type: 'button', onClick: () => showSummary(job) }, icon('check'), 'خلاصه') : null,
              !terminalStatuses.has(job.status) ? h('button', { className: 'button button--ghost', type: 'button', onClick: () => void cancel(job) }, icon('close'), 'لغو') : null,
              ['failed', 'processing'].includes(job.status) ? h('button', { className: 'button button--ghost', type: 'button', onClick: () => void retry(job) }, icon('refresh'), 'تلاش مجدد') : null,
            ),
          ))),
        )),
      );
      response.results.filter(job => !terminalStatuses.has(job.status)).forEach(job => {
        if (!polling.has(job.id)) {
          polling.add(job.id);
          void poll(job.id);
        }
      });
    } catch (error) {
      clear(list);
      list.append(errorState(error, () => void load()));
    }
  };

  const poll = async (id: string): Promise<void> => {
    try {
      for (let attempt = 0; attempt < 150 && page.isConnected; attempt += 1) {
        await new Promise(resolve => setTimeout(resolve, 2000));
        try {
          const job = await apiRequest<ImportJob>(endpoints.imports.detail(id));
          if (terminalStatuses.has(job.status)) {
            await load();
            return;
          }
        } catch {
          return;
        }
      }
    } finally {
      polling.delete(id);
    }
  };

  async function retry(job: ImportJob): Promise<void> {
    if (!await confirmDialog({ title: 'تلاش مجدد', message: 'این فایل دوباره پردازش شود؟', confirmLabel: 'تلاش مجدد' })) return;
    try {
      await apiRequest(endpoints.imports.retry(job.id), { method: 'POST', body: {} });
      toast('پردازش دوباره در صف قرار گرفت.', 'success');
      await load();
    } catch (error) {
      toast('تلاش مجدد ناموفق بود', 'error', error instanceof Error ? error.message : undefined);
    }
  }

  async function cancel(job: ImportJob): Promise<void> {
    if (!await confirmDialog({ title: 'لغو پردازش', message: 'پردازش این فایل متوقف شود؟', confirmLabel: 'لغو', dangerous: true })) return;
    try {
      await apiRequest(endpoints.imports.cancel(job.id), { method: 'POST', body: {} });
      toast('پردازش لغو شد.', 'success');
      await load();
    } catch (error) {
      toast('لغو پردازش ناموفق بود', 'error', error instanceof Error ? error.message : undefined);
    }
  }

  page.append(
    h('div', { className: 'page-heading' },
      h('div', {}, h('span', { className: 'eyebrow', text: 'ورود اطلاعات' }), h('h1', { text: 'دو روش ساده برای ثبت اطلاعات' }), h('p', { text: 'برای ورود گروهی فقط فایل جامع رسمی را استفاده کنید. برای یک یا چند رکورد محدود، ثبت دستی ساده‌تر است.' })),
      h('div', { className: 'page-actions' },
        h('button', { className: 'button button--primary', type: 'button', onClick: () => void openUploadDialog(load) }, icon('upload'), 'بارگذاری فایل جامع'),
        h('button', { className: 'button button--secondary', type: 'button', onClick: () => navigate('/manual-entry') }, icon('edit'), 'ثبت و ویرایش دستی'),
      ),
    ),
    h('div', { className: 'import-guide-grid' },
      h('article', { className: 'card guide-card guide-card--primary' }, icon('upload'), h('h2', { text: 'فایل جامع مدرسه' }), h('p', { text: 'کلاس‌ها، دانش‌آموزان و ارزیابی‌های ماهانه را یک‌جا ایجاد یا به‌روزرسانی می‌کند.' }), h('p', { className: 'muted', text: 'حذف از روی نبودن رکورد در فایل انجام نمی‌شود.' }), h('button', { className: 'button button--secondary', type: 'button', onClick: () => void apiRequest<Blob>(endpoints.imports.template('comprehensive_school'), { responseType: 'blob' }).then(blob => downloadBlob(blob, 'comprehensive_school_template.xlsx')).catch(error => toast('دریافت قالب ناموفق بود', 'error', error instanceof Error ? error.message : undefined)) }, icon('download'), 'دانلود قالب رسمی')),
      h('article', { className: 'card guide-card' }, icon('edit'), h('h2', { text: 'ثبت دستی' }), h('p', { text: 'برای ثبت تک‌موردی، اصلاح اطلاعات، تغییر کلاس، انتقال یا تغییر وضعیت از راهنمای مرحله‌ای استفاده کنید.' }), h('p', { className: 'muted', text: 'شناسه‌های فنی را لازم نیست وارد کنید؛ گزینه‌ها با نام و کد نمایش داده می‌شوند.' }), h('button', { className: 'button button--secondary', type: 'button', onClick: () => navigate('/manual-entry') }, icon('plus'), 'باز کردن ثبت دستی')),
    ),
    list,
  );

  onWindowEventWhileConnected(page, 'hamamooz:scope-change', () => void load());
  await load();
  return page;
}
