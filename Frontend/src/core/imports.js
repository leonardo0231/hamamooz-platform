export const COMPREHENSIVE_IMPORT_TYPE = 'comprehensive_school';
export const MAX_IMPORT_FILE_BYTES = 10 * 1024 * 1024;

const statusLabels = {
  queued: 'در صف',
  processing: 'در حال پردازش',
  completed: 'تکمیل‌شده',
  failed: 'ناموفق',
  cancelled: 'لغوشده',
};

const statusTones = {
  queued: 'info',
  processing: 'important',
  completed: 'success',
  failed: 'critical',
  cancelled: 'neutral',
};

export function validateComprehensiveImportFile(file) {
  if (!file) return 'فایل Excel را انتخاب کنید.';
  const name = String(file.name ?? '').trim().toLowerCase();
  if (!name.endsWith('.xlsx')) return 'فایل جامع مدرسه فقط با پسوند XLSX پذیرفته می‌شود.';
  if (Number(file.size) > MAX_IMPORT_FILE_BYTES) return 'حجم فایل نباید بیشتر از ۱۰ مگابایت باشد.';
  return null;
}

export function isImportInProgress(job) {
  return ['queued', 'processing'].includes(job?.status);
}

export function importStatusLabel(status) {
  return statusLabels[status] ?? status ?? 'نامشخص';
}

export function importStatusTone(status) {
  return statusTones[status] ?? 'neutral';
}

export function canRetryImport(job) {
  return job?.status === 'failed';
}

export function canCancelImport(job) {
  return isImportInProgress(job);
}

export function importFileName(job) {
  const value = String(job?.source_file ?? '');
  if (!value) return 'فایل Excel';
  const last = value.split('/').filter(Boolean).at(-1) ?? value;
  try { return decodeURIComponent(last); } catch { return last; }
}

export function importSummaryEntries(summary) {
  if (!summary || typeof summary !== 'object' || Array.isArray(summary)) return [];
  return Object.entries(summary).filter(([, value]) => ['string', 'number', 'boolean'].includes(typeof value));
}
