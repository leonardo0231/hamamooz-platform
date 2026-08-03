import type { ContractSchema } from '../api/contract.js';
import { formatDate, formatNumber } from '../utils/dom.js';

const fieldLabels: Record<string, string> = {
  id: 'شناسه', title: 'عنوان', name: 'نام', code: 'کد', description: 'توضیحات', note: 'یادداشت', notes: 'یادداشت‌ها', reason: 'دلیل',
  first_name: 'نام', last_name: 'نام خانوادگی', full_name: 'نام و نام خانوادگی', username: 'نام کاربری', email: 'ایمیل', phone: 'تلفن', phone_primary: 'تلفن اصلی', national_id: 'کد ملی',
  organization: 'مجموعه', organization_name: 'مجموعه', school: 'مدرسه', school_name: 'مدرسه', academic_year: 'سال تحصیلی', academic_year_title: 'سال تحصیلی', term: 'نوبت', term_title: 'نوبت',
  grade_level: 'پایه', grade_title: 'پایه', class_section: 'کلاس', class_title: 'کلاس', student: 'دانش‌آموز', student_name: 'دانش‌آموز', enrollment: 'ثبت‌نام', guardian: 'ولی', guardian_name: 'ولی',
  teacher: 'دبیر', assessment: 'ارزیابی', assessment_type: 'نوع ارزیابی', assessment_type_title: 'نوع ارزیابی', course_offering: 'ارائه درس', grade_subject: 'درس پایه', subject: 'درس', user: 'کاربر', policy: 'سیاست',
  status: 'وضعیت', status_display: 'وضعیت', gender: 'جنسیت', role: 'نقش', role_display: 'نقش', severity: 'شدت', scope: 'نوع', channel: 'کانال', relationship: 'نسبت',
  is_active: 'فعال', is_current: 'جاری', is_primary: 'ولی اصلی', can_pick_up: 'مجاز به تحویل‌گرفتن', capacity: 'ظرفیت', order: 'ترتیب', coefficient: 'ضریب', value: 'مقدار', weight: 'وزن', default_weight: 'وزن پیش‌فرض', version: 'نسخه',
  starts_on: 'شروع', ends_on: 'پایان', assessment_date: 'تاریخ برگزاری', birth_date: 'تاریخ تولد', session_date: 'تاریخ جلسه', enrolled_on: 'تاریخ ثبت‌نام', left_on: 'تاریخ خروج', transfer_date: 'تاریخ انتقال', effective_date: 'تاریخ اثر',
  starts_at: 'زمان شروع', ends_at: 'زمان پایان', arrival_time: 'زمان ورود', departure_time: 'زمان خروج', created_at: 'زمان ایجاد', updated_at: 'آخرین تغییر', completed_at: 'زمان تکمیل', acknowledged_at: 'زمان مشاهده', resolved_at: 'زمان رفع', last_login: 'آخرین ورود',
  student_number: 'شماره دانش‌آموزی', late_minutes: 'دقایق تأخیر', early_leave_minutes: 'دقایق خروج زودهنگام', excuse_status: 'وضعیت عذر', import_type: 'نوع ورود', report_type: 'نوع گزارش', total_rows: 'کل ردیف‌ها', successful_rows: 'ردیف‌های موفق', error_count: 'تعداد خطا', attempts: 'تعداد تلاش',
  warning_absence_percent: 'آستانه هشدار غیبت', critical_absence_percent: 'آستانه غیبت بحرانی', absence_percent: 'درصد غیبت', absence_count: 'تعداد غیبت', total_sessions: 'کل جلسات',
  max_score: 'حداکثر نمره', overall_score: 'امتیاز نهایی', completion_percent: 'درصد تکمیل', month_no: 'ماه', domain_scores: 'امتیاز حیطه‌ها', entries: 'ورودی‌ها', records: 'رکوردها', errors: 'خطاها', result_summary: 'خلاصه نتیجه',
  requested_by_name: 'درخواست‌دهنده', formula_version: 'نسخه فرمول', error_message: 'شرح خطا', source_file: 'فایل منبع', evidence_files: 'مدارک',
};

const valueLabels: Record<string, string> = {
  active: 'فعال', inactive: 'غیرفعال', female: 'دختر', male: 'پسر',
  draft: 'پیش‌نویس', submitted: 'ارسال‌شده', approved: 'تأییدشده', rejected: 'ردشده', locked: 'قفل‌شده',
  open: 'باز', acknowledged: 'در حال بررسی', resolved: 'رفع‌شده', warning: 'مهم', critical: 'بحرانی',
  queued: 'در صف', processing: 'در حال پردازش', completed: 'تکمیل‌شده', failed: 'ناموفق', cancelled: 'لغوشده',
  present: 'حاضر', absent_unexcused: 'غیبت غیرموجه', excused_absent: 'غیبت موجه', unexcused_absent: 'غیبت غیرموجه', not_entered: 'ثبت‌نشده', finalized: 'نهایی‌شده',
  daily: 'روزانه', period: 'زنگ درسی', provisional: 'موقت', final: 'نهایی', transferred: 'منتقل‌شده', withdrawn: 'ترک‌تحصیل', graduated: 'فارغ‌التحصیل',
  students: 'دانش‌آموزان', enrollments: 'ثبت‌نام‌ها', scores: 'نمرات', monthly_evaluations: 'ارزیابی جامع ماهانه', comprehensive_school: 'فایل جامع مدرسه',
  student_report_card: 'کارنامه دانش‌آموز', class_report_cards: 'کارنامه‌های کلاس',
  system_admin: 'مدیر کل سامانه', organization_admin: 'مدیر مجموعه', school_manager: 'مدیر مدرسه', educational_deputy: 'معاون آموزشی', operator: 'اپراتور', teacher: 'دبیر',
  father: 'پدر', mother: 'مادر', guardian: 'سرپرست', other: 'سایر', in_app: 'داخل سامانه', email: 'ایمیل', sms: 'پیامک',
};

const technicalFields = new Set([
  'id', 'entity_id', 'actor_id', 'created_by', 'updated_by', 'request_id', 'download_url', 'source_file_url',
]);

const relationIdentifierFields = new Set([
  'organization', 'school', 'academic_year', 'term', 'grade_level', 'class_section', 'student', 'enrollment', 'guardian', 'teacher', 'user',
  'assessment', 'assessment_type', 'course_offering', 'grade_subject', 'subject', 'policy', 'role_assignment',
]);

const uuidPattern = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

export function labelForField(name: string, schema?: ContractSchema): string {
  const schemaTitle = schema?.title?.replace(/\s*\(.*\)$/, '').trim();
  return schemaTitle || fieldLabels[name] || name.replaceAll('_', ' ').replaceAll('-', ' ');
}

export function labelForValue(value: unknown): string {
  if (value === null || value === undefined || value === '') return '—';
  if (typeof value === 'boolean') return value ? 'بله' : 'خیر';
  const raw = String(value);
  return valueLabels[raw] ?? raw;
}

export function isDateField(name: string): boolean {
  return name.endsWith('_at') || name.endsWith('_on') || name.includes('date') || name === 'last_login';
}

export function isTimeField(name: string): boolean {
  return name.endsWith('_time') || name.endsWith('_at_time') || ['starts_at', 'ends_at', 'arrival_time', 'departure_time'].includes(name);
}

export function isTechnicalField(name: string): boolean {
  return technicalFields.has(name) || name.endsWith('_id') || name.startsWith('_');
}

export function isTechnicalValue(name: string, value: unknown): boolean {
  return isTechnicalField(name) || (relationIdentifierFields.has(name) && typeof value === 'string' && uuidPattern.test(value));
}

export function recordTitle(record: Record<string, unknown>): string {
  const primary = record.full_name ?? record.student_name ?? record.guardian_name ?? record.title ?? record.name ?? record.username ?? record.school_name ?? record.class_title;
  const code = record.code ?? record.student_number ?? record.national_id;
  if (primary && code && String(primary) !== String(code)) return `${String(primary)} — ${String(code)}`;
  if (primary) return String(primary);
  if (code) return String(code);
  if (record.id !== undefined) return `رکورد ${String(record.id).slice(0, 8)}`;
  return 'رکورد';
}

export function summarizeObject(value: Record<string, unknown>): string {
  const title = recordTitle(value);
  if (title !== 'رکورد') return title;
  const visible = Object.entries(value).filter(([key, item]) => !isTechnicalField(key) && item !== null && item !== undefined && typeof item !== 'object');
  if (visible.length === 1) return formatFieldValue(visible[0]?.[0] ?? '', visible[0]?.[1]);
  return `${formatNumber(Object.keys(value).length)} مشخصه`;
}

export function formatFieldValue(field: string, value: unknown): string {
  if (value === null || value === undefined || value === '') return '—';
  if (isDateField(field)) return formatDate(value, field.endsWith('_at') || field === 'last_login');
  if (isTimeField(field)) return String(value).slice(0, 5);
  if (typeof value === 'boolean') return value ? 'بله' : 'خیر';
  if (typeof value === 'number') return formatNumber(value);
  if (Array.isArray(value)) {
    if (!value.length) return '—';
    if (value.every(item => item === null || ['string', 'number', 'boolean'].includes(typeof item))) return value.map(labelForValue).join('، ');
    return `${formatNumber(value.length)} مورد`;
  }
  if (typeof value === 'object') return summarizeObject(value as Record<string, unknown>);
  return labelForValue(value);
}

export function badgeTone(value: unknown): 'danger' | 'warning' | 'success' | 'neutral' {
  const raw = String(value);
  if (['critical', 'rejected', 'failed', 'unexcused_absent', 'absent_unexcused', 'inactive'].includes(raw)) return 'danger';
  if (['warning', 'submitted', 'queued', 'processing', 'draft', 'open', 'acknowledged'].includes(raw)) return 'warning';
  if (['active', 'approved', 'completed', 'resolved', 'finalized', 'present', 'locked'].includes(raw) || value === true) return 'success';
  return 'neutral';
}
