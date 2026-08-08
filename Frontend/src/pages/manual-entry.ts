import { apiRequest } from '../api/client.js';
import { endpoints } from '../api/endpoints.js';
import { operationsForTag, type ContractOperation } from '../api/contract.js';
import type { Pagination, Role } from '../api/types.js';
import { navigate } from '../app/router.js';
import {
  administrativeRoles,
  broadEducationRoles,
  curriculumManagementRoles,
  hasAnyRole,
  hasWriteScope,
  organizationManagementRoles,
  policyManagementRoles,
  teacherWriteRoles,
} from '../app/permissions.js';
import { toast } from '../components/feedback.js';
import { icon } from '../components/icons.js';
import { openSchemaDialog, schemaHasBinary } from '../components/schema-form.js';
import { debounce, formatNumber, h } from '../utils/dom.js';

interface ManualResource {
  tag: string;
  title: string;
  description: string;
  tip: string;
  roles?: Role[];
}

interface ManualGroup {
  title: string;
  description: string;
  resources: ManualResource[];
}

interface EnrollmentOption {
  id: string;
  student_name?: string;
  student_number?: string;
  class_title?: string;
  school_name?: string;
  status?: string;
}

interface MetricDefinition {
  code: string;
  title: string;
  domain_code: string;
  domain_title: string;
  domain_weight: number;
  order: number;
}

interface MetricValue {
  metric_code: string;
  value: number;
}

interface MonthlyEvaluationRecord {
  id: string;
  enrollment: string;
  month_no: number;
  framework_version: string;
  note: string;
  metric_scores: MetricValue[];
}

interface MetricCatalogResponse {
  framework_version: string;
  score_min: number;
  score_max: number;
  metric_count: number;
  metrics: MetricDefinition[];
}

interface ManualEvaluationSaveResponse {
  evaluation: MonthlyEvaluationRecord;
  result: {
    created: boolean;
    restored: boolean;
    metrics_created: number;
    metrics_updated: number;
    metrics_unchanged: number;
  };
}

const MONTHS = [
  'تیر', 'مرداد', 'شهریور', 'مهر', 'آبان', 'آذر',
  'دی', 'بهمن', 'اسفند', 'فروردین', 'اردیبهشت', 'خرداد',
];

const fieldHints: Record<string, string> = {
  organization: 'مجموعه را از فهرست انتخاب کنید؛ شناسه فنی لازم نیست وارد شود.',
  school: 'مدرسه مقصد را با نام انتخاب کنید. اطلاعات در شعبه دیگری ذخیره نمی‌شود.',
  academic_year: 'سال تحصیلی مرتبط را انتخاب کنید؛ تاریخ‌ها باید داخل همین سال باشند.',
  term: 'نوبت تحصیلی را با عنوان انتخاب کنید.',
  grade_level: 'پایه را با عنوان انتخاب کنید؛ نیازی به UUID نیست.',
  class_section: 'کلاس را با نام یا کد پیدا کنید و انتخاب کنید.',
  student: 'دانش‌آموز را با نام، کد ملی یا شماره دانش‌آموزی پیدا کنید.',
  guardian: 'ولی را با نام یا شماره تماس پیدا کنید.',
  enrollment: 'ثبت‌نام فعال دانش‌آموز را انتخاب کنید؛ این همان ارتباط دانش‌آموز با کلاس و سال است.',
  teacher: 'دبیر را با نام کاربری یا نام و نام خانوادگی انتخاب کنید.',
  user: 'کاربر را با نام یا نام کاربری انتخاب کنید.',
  assessment: 'ارزیابی موردنظر را با عنوان انتخاب کنید.',
  assessment_type: 'نوع ارزیابی مثل امتحان، فعالیت یا پروژه را انتخاب کنید.',
  course_offering: 'ارائه درس یعنی ترکیب کلاس، درس، دبیر و نوبت؛ مورد مناسب را انتخاب کنید.',
  grade_subject: 'درسِ مربوط به پایه را انتخاب کنید.',
  subject: 'درس را از فهرست انتخاب کنید.',
  code: 'یک کد کوتاه و ثابت بنویسید. تغییر کد در ادامه می‌تواند ارتباط گزارش‌ها و فایل جامع را گیج‌کننده کند.',
  national_id: 'دقیقاً ۱۰ رقم وارد کنید و صفر ابتدای کد ملی را حذف نکنید.',
  student_number: 'شماره دانش‌آموزی باید در همان مدرسه و سال تحصیلی یکتا باشد.',
  birth_date: 'تاریخ تولد را به فرم تاریخ انتخاب کنید.',
  enrolled_on: 'تاریخ ثبت‌نام باید داخل بازه سال تحصیلی باشد.',
  left_on: 'فقط برای ثبت‌نام خاتمه‌یافته وارد شود؛ ثبت‌نام فعال نباید تاریخ خروج داشته باشد.',
  transfer_date: 'تاریخ انتقال باید با سابقه ثبت‌نام سازگار باشد.',
  effective_date: 'تاریخی که تغییر کلاس از آن اعمال می‌شود.',
  capacity: 'حداکثر تعداد دانش‌آموز فعال این کلاس.',
  order: 'ترتیب نمایش؛ عدد کوچک‌تر زودتر نمایش داده می‌شود.',
  status: 'اگر برای این رکورد عملیات اختصاصی تغییر وضعیت وجود دارد، همان عملیات را استفاده کنید.',
  is_active: 'برای توقف استفاده از رکورد بدون حذف سابقه، آن را غیرفعال کنید.',
  is_current: 'فقط سال تحصیلی جاری باید این گزینه را داشته باشد.',
  reason: 'دلیل واقعی و قابل پیگیری بنویسید؛ این متن در تاریخچه عملیات استفاده می‌شود.',
  phone: 'شماره تماس را بدون متن اضافه وارد کنید.',
  phone_primary: 'شماره تماس اصلی ولی یا سرپرست.',
  email: 'ایمیل معتبر وارد کنید؛ اگر اختیاری است و ایمیلی ندارید، خالی بگذارید.',
  weight: 'وزن این ارزیابی در محاسبه نتیجه.',
  default_weight: 'وزن پیش‌فرض برای ارزیابی‌های این نوع.',
  max_score: 'حداکثر نمره قابل ثبت برای این ارزیابی.',
  value: 'مقدار نمره را داخل بازه مجاز ارزیابی وارد کنید.',
};

const groups: ManualGroup[] = [
  {
    title: '۱. ساختار مدرسه',
    description: 'این موارد معمولاً یک‌بار در شروع سال تنظیم می‌شوند. ابتدا مجموعه، سال و پایه را بسازید و بعد کلاس‌ها را ثبت کنید.',
    resources: [
      { tag: 'organizations', title: 'مجموعه', description: 'مجموعه مالک مدارس و داده‌های آموزشی.', tip: 'این مورد فقط برای مدیر کل سامانه نمایش داده می‌شود.', roles: ['system_admin'] },
      { tag: 'schools', title: 'مدرسه / شعبه', description: 'نام، کد و اطلاعات تماس شعبه.', tip: 'کد شعبه باید کوتاه، ثابت و قابل تشخیص باشد.', roles: organizationManagementRoles },
      { tag: 'academic-years', title: 'سال تحصیلی', description: 'بازه شروع و پایان سال تحصیلی و سال جاری.', tip: 'در هر مجموعه فقط یک سال تحصیلی را جاری نگه دارید.', roles: organizationManagementRoles },
      { tag: 'terms', title: 'نوبت تحصیلی', description: 'نوبت اول و دوم داخل بازه سال تحصیلی.', tip: 'تاریخ نوبت باید داخل سال تحصیلی انتخاب‌شده باشد.', roles: organizationManagementRoles },
      { tag: 'grade-levels', title: 'پایه تحصیلی', description: 'پایه‌ها مثل هفتم، هشتم و نهم.', tip: 'کد پایه را ثابت نگه دارید تا گزارش‌ها و فایل جامع قابل اتکا باشند.', roles: organizationManagementRoles },
      { tag: 'classes', title: 'کلاس', description: 'کلاس، ظرفیت، پایه و سال تحصیلی.', tip: 'قبل از ثبت دانش‌آموز، کلاس و ظرفیت آن را مشخص کنید.', roles: broadEducationRoles },
    ],
  },
  {
    title: '۲. دانش‌آموز و خانواده',
    description: 'برای ثبت یک دانش‌آموز جدید، اول خود دانش‌آموز را بسازید؛ سپس ولی و در پایان ثبت‌نام او را به کلاس وصل کنید.',
    resources: [
      { tag: 'students', title: 'دانش‌آموز', description: 'مشخصات هویتی و فردی دانش‌آموز.', tip: 'کد ملی را دقیقاً ۱۰ رقم وارد کنید. شناسه فنی UUID را سامانه خودش می‌سازد.', roles: broadEducationRoles },
      { tag: 'guardians', title: 'ولی / سرپرست', description: 'مشخصات تماس و هویتی ولی.', tip: 'بعد از ساخت ولی می‌توانید او را از پرونده دانش‌آموز متصل کنید.', roles: broadEducationRoles },
      { tag: 'enrollments', title: 'ثبت‌نام و کلاس‌بندی', description: 'اتصال دانش‌آموز به مدرسه، سال، پایه و کلاس.', tip: 'برای تغییر کلاس یا انتقال، از عملیات اختصاصی همان ثبت‌نام استفاده کنید؛ رکورد تاریخی را ویرایش خام نکنید.', roles: broadEducationRoles },
    ],
  },
  {
    title: '۳. برنامه درسی و ارزیابی',
    description: 'درس‌ها را تعریف کنید، آن‌ها را به پایه و کلاس ارائه دهید و سپس ارزیابی و نمره ثبت کنید.',
    resources: [
      { tag: 'subjects', title: 'درس', description: 'تعریف درس‌های مدرسه.', tip: 'کد درس بهتر است کوتاه و در طول سال ثابت باشد.', roles: curriculumManagementRoles },
      { tag: 'grade-subjects', title: 'درس پایه', description: 'اتصال درس به پایه همراه با ضریب.', tip: 'ابتدا درس و پایه را بسازید؛ سپس این اتصال را ثبت کنید.', roles: curriculumManagementRoles },
      { tag: 'course-offerings', title: 'ارائه درس', description: 'اتصال درس پایه به کلاس، دبیر و نوبت.', tip: 'از نام‌ها انتخاب کنید؛ نیازی به وارد کردن شناسه‌های فنی نیست.', roles: broadEducationRoles },
      { tag: 'assessment-types', title: 'نوع ارزیابی', description: 'تعریف امتحان، فعالیت، پروژه و وزن پیش‌فرض.', tip: 'نوع ارزیابی را قبل از ساخت ارزیابی‌های کلاسی تعریف کنید.', roles: curriculumManagementRoles },
      { tag: 'assessments', title: 'ارزیابی درسی', description: 'ایجاد ارزیابی برای یک ارائه درس.', tip: 'پس از ثبت نمرات، از ارسال، تأیید و قفل استفاده کنید؛ وضعیت را مستقیم دستکاری نکنید.', roles: teacherWriteRoles },
      { tag: 'scores', title: 'نمره درسی', description: 'ثبت یا اصلاح نمره دانش‌آموز در ارزیابی.', tip: 'برای نمره قفل‌شده فقط عملیات «اصلاح نمره قفل‌شده» مجاز است.', roles: teacherWriteRoles },
      { tag: 'monthly-evaluations', title: 'ارزیابی جامع ماهانه', description: 'ثبت ۷۴ شاخص رفتاری، آموزشی و مهارتی برای یک دانش‌آموز و ماه.', tip: 'شاخص‌ها دسته‌بندی شده‌اند؛ لازم نیست همه ۷۴ مورد را یک‌باره تکمیل کنید.', roles: teacherWriteRoles },
      { tag: 'calculation-policies', title: 'سیاست محاسبه', description: 'قواعد محاسبه نمره و نسخه سیاست.', tip: 'سیاست فعال را با دقت تغییر دهید چون روی محاسبات بعدی اثر دارد.', roles: curriculumManagementRoles },
    ],
  },
  {
    title: '۴. حضور و غیاب',
    description: 'ابتدا سیاست حضور را تنظیم کنید، سپس جلسه بسازید و وضعیت هر دانش‌آموز را ثبت کنید.',
    resources: [
      { tag: 'attendance-policies', title: 'سیاست حضور', description: 'آستانه‌های هشدار و سیاست حضور مدرسه.', tip: 'برای هر مدرسه و سال تحصیلی سیاست درست را انتخاب کنید.', roles: policyManagementRoles },
      { tag: 'attendance-sessions', title: 'جلسه حضور و غیاب', description: 'جلسه روزانه یا زنگ درسی.', tip: 'پس از نهایی‌سازی جلسه، تغییرات باید از عملیات مجاز انجام شوند.', roles: teacherWriteRoles },
      { tag: 'attendance-records', title: 'رکورد حضور', description: 'حاضر، غایب، تأخیر و اطلاعات عذر.', tip: 'برای کلاس کامل، ثبت گروهی معمولاً از ثبت تک‌به‌تک سریع‌تر است.', roles: teacherWriteRoles },
    ],
  },
  {
    title: '۵. کاربران و دسترسی',
    description: 'کاربر را ایجاد کنید و سپس نقش او را در مجموعه یا شعبه مناسب تخصیص دهید.',
    resources: [
      { tag: 'users', title: 'کاربر', description: 'حساب کاربری کارکنان و دبیران.', tip: 'رمز عبور اولیه را امن انتخاب کنید و دسترسی را فقط به حوزه لازم محدود کنید.', roles: administrativeRoles },
      { tag: 'role-assignments', title: 'نقش و دسترسی', description: 'تخصیص نقش به کاربر در مجموعه یا مدرسه.', tip: 'کمترین سطح دسترسی لازم را انتخاب کنید؛ نقش شعبه دیگر را بی‌دلیل اضافه نکنید.', roles: administrativeRoles },
    ],
  },
];

function createOperationFor(tag: string): ContractOperation | undefined {
  return operationsForTag(tag).find(operation => {
    if (operation.method !== 'POST' || operation.path.includes('{id}')) return false;
    return operation.path.split('/').filter(Boolean).at(-1) === tag;
  });
}

function listOperationFor(tag: string): ContractOperation | undefined {
  return operationsForTag(tag).find(operation => operation.method === 'GET' && !operation.path.includes('{id}'));
}

function managementPath(tag: string): string {
  if (tag === 'students') return '/students';
  if (tag === 'users') return '/users';
  if (tag === 'role-assignments') return '/roles';
  return `/resources/${tag}`;
}

function enhanceManualDialog(dialog: HTMLDialogElement, resource: ManualResource): void {
  const intro = dialog.querySelector<HTMLElement>('.dialog__header p');
  if (intro) intro.textContent = `${resource.tip} فیلدهای ستاره‌دار الزامی هستند و گزینه‌های مرتبط با نام نمایش داده می‌شوند.`;

  for (const [name, text] of Object.entries(fieldHints)) {
    const control = dialog.querySelector<HTMLElement>(`[name="${CSS.escape(name)}"]`);
    const wrapper = control?.closest<HTMLElement>('.form-field');
    if (!control || !wrapper || wrapper.querySelector('.manual-field-hint')) continue;
    wrapper.append(h('small', { className: 'manual-field-hint', text }));
  }
}

function enrollmentLabel(item: EnrollmentOption): string {
  const student = item.student_name || 'دانش‌آموز';
  const number = item.student_number ? `شماره ${item.student_number}` : 'بدون شماره';
  const klass = item.class_title || 'کلاس نامشخص';
  return `${student} — ${number} — ${klass}`;
}

async function requestEvaluationDelete(id: string, onDeleted: () => Promise<void>): Promise<void> {
  const dialog = h('dialog', { className: 'dialog' }) as HTMLDialogElement;
  const reason = h('textarea', { rows: 3, required: true, minLength: 3, maxLength: 1000, placeholder: 'مثلاً: ثبت اشتباه برای ماه یا دانش‌آموز دیگر' }) as HTMLTextAreaElement;
  const form = h('form', { className: 'dialog__body' },
    h('div', { className: 'dialog__header' }, h('div', {}, h('h2', { text: 'حذف منطقی ارزیابی' }), h('p', { text: 'ارزیابی از لیست جاری حذف می‌شود اما سابقه آن در پایگاه داده و Audit حفظ می‌شود.' })), h('button', { className: 'icon-button', type: 'button', onClick: () => dialog.close(), 'aria-label': 'بستن' }, icon('close'))),
    h('label', { className: 'form-field' }, h('span', { text: 'دلیل حذف' }), reason, h('small', { text: 'برای امکان پیگیری بعدی، دلیل واقعی حذف را بنویسید.' })),
    h('div', { className: 'dialog__actions' },
      h('button', { className: 'button button--ghost', type: 'button', onClick: () => dialog.close() }, 'انصراف'),
      h('button', { className: 'button button--danger', type: 'submit' }, icon('trash'), 'حذف ارزیابی'),
    ),
  ) as HTMLFormElement;
  form.addEventListener('submit', event => {
    event.preventDefault();
    if (!form.reportValidity()) return;
    void apiRequest(endpoints.monthlyEvaluations.manualDelete(id), {
      method: 'DELETE',
      body: { reason: reason.value.trim() },
      responseType: 'void',
    }).then(async () => {
      toast('ارزیابی از نمای جاری حذف شد و سابقه آن حفظ شد.', 'success');
      dialog.close();
      await onDeleted();
    }).catch(error => toast('حذف ارزیابی ناموفق بود', 'error', error instanceof Error ? error.message : undefined));
  });
  dialog.append(form);
  dialog.addEventListener('close', () => dialog.remove(), { once: true });
  document.body.append(dialog);
  dialog.showModal();
}

async function openMonthlyEvaluationDialog(): Promise<void> {
  if (!hasWriteScope()) {
    toast('ابتدا مدرسه فعال را از بالای صفحه انتخاب کنید.', 'info');
    return;
  }
  const enrollmentOperation = listOperationFor('enrollments');
  if (!enrollmentOperation) {
    toast('فهرست ثبت‌نام‌ها در قرارداد فعلی پیدا نشد.', 'error');
    return;
  }

  let catalog: MetricCatalogResponse;
  try {
    catalog = await apiRequest<MetricCatalogResponse>(endpoints.monthlyEvaluations.catalog);
  } catch (error) {
    toast('دریافت فهرست شاخص‌های ارزیابی ناموفق بود', 'error', error instanceof Error ? error.message : undefined);
    return;
  }

  const dialog = h('dialog', { className: 'dialog dialog--wide' }) as HTMLDialogElement;
  const enrollmentSearch = h('input', { type: 'search', placeholder: 'نام، کد ملی یا شماره دانش‌آموزی…', 'aria-label': 'جست‌وجوی دانش‌آموز' }) as HTMLInputElement;
  const enrollment = h('select', { required: true, disabled: true }, h('option', { value: '', text: 'در حال دریافت دانش‌آموزان…' })) as HTMLSelectElement;
  const month = h('select', { required: true }, h('option', { value: '', text: 'ماه را انتخاب کنید' }), ...MONTHS.map((label, index) => h('option', { value: String(index + 1), text: `${formatNumber(index + 1)} — ${label}` }))) as HTMLSelectElement;
  const note = h('textarea', { rows: 4, maxLength: 5000, placeholder: 'توضیح اختیاری درباره این ماه…' }) as HTMLTextAreaElement;
  const existingState = h('p', { className: 'muted', text: 'دانش‌آموز و ماه را انتخاب کنید.' });
  const progress = h('strong', { text: `۰ از ${formatNumber(catalog.metric_count)} شاخص انتخاب شده` });
  const save = h('button', { className: 'button button--primary', type: 'submit' }, icon('check'), 'ذخیره ارزیابی') as HTMLButtonElement;
  const deleteButton = h('button', { className: 'button button--danger', type: 'button', hidden: true }, icon('trash'), 'حذف ارزیابی') as HTMLButtonElement;
  const metricSelects = new Map<string, HTMLSelectElement>();
  let existingId: string | null = null;
  let loadingVersion = 0;

  const grouped = new Map<string, MetricDefinition[]>();
  for (const metric of catalog.metrics) {
    const key = `${metric.domain_code}|${metric.domain_title}`;
    const items = grouped.get(key) ?? [];
    items.push(metric);
    grouped.set(key, items);
  }

  const updateProgress = (): void => {
    const count = [...metricSelects.values()].filter(select => select.value !== '').length;
    progress.textContent = `${formatNumber(count)} از ${formatNumber(catalog.metric_count)} شاخص انتخاب شده${count === catalog.metric_count ? ' — کامل' : ' — امکان ذخیره موقت وجود دارد'}`;
  };

  const domainSections = [...grouped.entries()].map(([key, metrics], index) => {
    const [, title] = key.split('|');
    const controls = metrics.map(metric => {
      const select = h('select', { 'aria-label': metric.title },
        h('option', { value: '', text: 'ثبت نشده / بدون تغییر' }),
        ...[0, 1, 2, 3, 4, 5].map(value => h('option', { value: String(value), text: formatNumber(value) })),
      ) as HTMLSelectElement;
      select.addEventListener('change', updateProgress);
      metricSelects.set(metric.code, select);
      return h('label', { className: 'form-field' },
        h('span', { text: `${metric.code} — ${metric.title}` }),
        select,
        h('small', { text: 'امتیاز ۰ تا ۵؛ خالی یعنی مقدار قبلی دست‌نخورده بماند.' }),
      );
    });
    return h('details', { className: 'form-section', open: index === 0 },
      h('summary', {}, h('strong', { text: title || key }), h('span', { className: 'muted', text: `${formatNumber(metrics.length)} شاخص` })),
      h('div', { className: 'form-grid form-grid--nested' }, ...controls),
    );
  });

  const loadEnrollments = async (search = ''): Promise<void> => {
    enrollment.disabled = true;
    enrollment.replaceChildren(h('option', { value: '', text: 'در حال دریافت…' }));
    try {
      const response = await apiRequest<Pagination<EnrollmentOption>>(enrollmentOperation.path, {
        query: { page_size: 200, status: 'active', search: search || undefined },
      });
      enrollment.replaceChildren(
        h('option', { value: '', text: response.results.length ? 'دانش‌آموز را انتخاب کنید' : 'موردی پیدا نشد' }),
        ...response.results.map(item => h('option', { value: item.id, text: enrollmentLabel(item) })),
      );
    } catch (error) {
      enrollment.replaceChildren(h('option', { value: '', text: 'دریافت فهرست ناموفق بود' }));
      toast('دریافت دانش‌آموزان ناموفق بود', 'error', error instanceof Error ? error.message : undefined);
    } finally {
      enrollment.disabled = false;
    }
  };

  const clearEvaluation = (): void => {
    existingId = null;
    note.value = '';
    for (const select of metricSelects.values()) select.value = '';
    deleteButton.hidden = true;
    updateProgress();
  };

  const loadExisting = async (): Promise<void> => {
    const currentVersion = ++loadingVersion;
    clearEvaluation();
    if (!enrollment.value || !month.value) {
      existingState.textContent = 'دانش‌آموز و ماه را انتخاب کنید.';
      return;
    }
    existingState.textContent = 'در حال بررسی ارزیابی قبلی…';
    try {
      const response = await apiRequest<Pagination<MonthlyEvaluationRecord>>(endpoints.monthlyEvaluations.list, {
        query: {
          page_size: 5,
          enrollment: enrollment.value,
          month_no: month.value,
          framework_version: catalog.framework_version,
        },
      });
      if (currentVersion !== loadingVersion) return;
      const current = response.results[0];
      if (!current) {
        existingState.textContent = 'برای این دانش‌آموز و ماه هنوز ارزیابی ثبت نشده است؛ می‌توانید یک ثبت جدید شروع کنید.';
        return;
      }
      existingId = current.id;
      note.value = current.note ?? '';
      for (const score of current.metric_scores ?? []) {
        const select = metricSelects.get(score.metric_code);
        if (select) select.value = String(score.value);
      }
      deleteButton.hidden = false;
      existingState.textContent = `ارزیابی قبلی پیدا شد. تغییرات روی همان رکورد ذخیره می‌شوند؛ منبع اولیه و Audit حفظ خواهند شد.`;
      updateProgress();
    } catch (error) {
      if (currentVersion !== loadingVersion) return;
      existingState.textContent = 'بررسی ارزیابی قبلی ناموفق بود.';
      toast('دریافت ارزیابی قبلی ناموفق بود', 'error', error instanceof Error ? error.message : undefined);
    }
  };

  enrollmentSearch.addEventListener('input', debounce(() => void loadEnrollments(enrollmentSearch.value.trim()), 300));
  enrollment.addEventListener('change', () => void loadExisting());
  month.addEventListener('change', () => void loadExisting());
  deleteButton.addEventListener('click', () => {
    if (!existingId) return;
    void requestEvaluationDelete(existingId, async () => {
      clearEvaluation();
      existingState.textContent = 'ارزیابی حذف شد؛ در صورت نیاز می‌توانید دوباره آن را ثبت کنید.';
    });
  });

  const form = h('form', { className: 'dialog__body dialog__body--wide' },
    h('div', { className: 'dialog__header' },
      h('div', {},
        h('span', { className: 'eyebrow', text: 'ثبت دستی ساده' }),
        h('h2', { text: 'ارزیابی جامع ماهانه' }),
        h('p', { text: 'دانش‌آموز و ماه را انتخاب کنید، سپس فقط شاخص‌هایی را که می‌خواهید ثبت یا اصلاح کنید مقدار بدهید. ذخیره ناقص مجاز است و می‌توانید بعداً ادامه دهید.' }),
      ),
      h('button', { className: 'icon-button', type: 'button', onClick: () => dialog.close(), 'aria-label': 'بستن' }, icon('close')),
    ),
    h('div', { className: 'card' },
      h('div', { className: 'form-grid' },
        h('label', { className: 'form-field form-field--relation' }, h('span', { text: 'دانش‌آموز / ثبت‌نام فعال' }), h('div', { className: 'relation-picker' }, enrollmentSearch, enrollment), h('small', { text: 'فقط دانش‌آموزانی نمایش داده می‌شوند که در حوزه دسترسی فعلی شما ثبت‌نام فعال دارند.' })),
        h('label', { className: 'form-field' }, h('span', { text: 'ماه' }), month, h('small', { text: 'ماه‌های سال تحصیلی مطابق ترتیب فایل جامع نمایش داده می‌شوند.' })),
        h('label', { className: 'form-field' }, h('span', { text: 'توضیحات' }), note, h('small', { text: 'اختیاری؛ برای نکته‌های مهم این ماه استفاده کنید.' })),
      ),
      existingState,
      h('div', { className: 'card-header' }, h('div', {}, h('h3', { text: 'شاخص‌ها' }), h('p', { text: 'هر بخش را باز کنید. خالی گذاشتن یک شاخص، مقدار قبلی آن را پاک نمی‌کند.' })), progress),
    ),
    ...domainSections,
    h('div', { className: 'dialog__actions' },
      deleteButton,
      h('button', { className: 'button button--ghost', type: 'button', onClick: () => dialog.close() }, 'بستن'),
      save,
    ),
  ) as HTMLFormElement;

  form.addEventListener('submit', event => {
    event.preventDefault();
    if (!enrollment.value || !month.value) {
      toast('دانش‌آموز و ماه را انتخاب کنید.', 'info');
      return;
    }
    const metrics = [...metricSelects.entries()]
      .filter(([, select]) => select.value !== '')
      .map(([metric_code, select]) => ({ metric_code, value: Number(select.value) }));
    if (!metrics.length && !note.value.trim()) {
      toast('حداقل یک شاخص یا توضیح وارد کنید.', 'info');
      return;
    }
    save.disabled = true;
    void apiRequest<ManualEvaluationSaveResponse>(endpoints.monthlyEvaluations.manual, {
      method: 'POST',
      body: {
        enrollment: enrollment.value,
        month_no: Number(month.value),
        note: note.value.trim(),
        metrics,
      },
    }).then(response => {
      existingId = response.evaluation.id;
      deleteButton.hidden = false;
      const result = response.result;
      existingState.textContent = result.created
        ? 'ارزیابی جدید ثبت شد. می‌توانید همین فرم را باز نگه دارید و شاخص‌های دیگری را اضافه کنید.'
        : 'تغییرات روی ارزیابی قبلی ذخیره شد.';
      toast(result.created ? 'ارزیابی ماهانه ثبت شد.' : 'ارزیابی ماهانه به‌روزرسانی شد.', 'success', `جدید: ${formatNumber(result.metrics_created)}، تغییرکرده: ${formatNumber(result.metrics_updated)}، بدون تغییر: ${formatNumber(result.metrics_unchanged)}`);
    }).catch(error => toast('ذخیره ارزیابی ناموفق بود', 'error', error instanceof Error ? error.message : undefined))
      .finally(() => { save.disabled = false; });
  });

  dialog.append(form);
  dialog.addEventListener('close', () => dialog.remove(), { once: true });
  document.body.append(dialog);
  dialog.showModal();
  await loadEnrollments();
}

function openCreate(resource: ManualResource): void {
  if (resource.tag === 'monthly-evaluations') {
    void openMonthlyEvaluationDialog();
    return;
  }
  if (!hasWriteScope()) {
    toast('ابتدا مجموعه یا مدرسه فعال را از بالای صفحه انتخاب کنید.', 'info');
    return;
  }
  const operation = createOperationFor(resource.tag);
  if (!operation) {
    toast('برای این بخش فرم ایجاد مستقیم تعریف نشده است؛ از صفحه مدیریت استفاده کنید.', 'info');
    navigate(managementPath(resource.tag));
    return;
  }
  const dialog = openSchemaDialog({
    title: `ثبت دستی ${resource.title}`,
    schema: operation.requestSchema,
    multipart: operation.requestMime === 'multipart/form-data' || schemaHasBinary(operation.requestSchema),
    submitLabel: `ثبت ${resource.title}`,
    onSubmit: async payload => {
      await apiRequest(operation.path, { method: 'POST', body: payload });
      toast(`${resource.title} با موفقیت ثبت شد.`, 'success');
    },
  });
  enhanceManualDialog(dialog, resource);
}

function resourceCard(resource: ManualResource): HTMLElement {
  return h(
    'article',
    { className: 'card guide-card' },
    h('span', { className: 'card-icon' }, icon(resource.tag.includes('student') || resource.tag === 'guardians' || resource.tag === 'users' ? 'users' : resource.tag.includes('attendance') ? 'calendar' : resource.tag.includes('assessment') || resource.tag.includes('evaluation') || resource.tag === 'scores' ? 'chart' : 'book')),
    h('h3', { text: resource.title }),
    h('p', { text: resource.description }),
    h('p', { className: 'muted', text: `راهنما: ${resource.tip}` }),
    h('div', { className: 'page-actions' },
      h('button', { className: 'button button--primary', type: 'button', onClick: () => openCreate(resource) }, icon('plus'), 'ثبت جدید'),
      h('button', { className: 'button button--secondary', type: 'button', onClick: () => navigate(managementPath(resource.tag)) }, icon('edit'), 'مشاهده و ویرایش'),
    ),
  );
}

export async function renderManualEntryPage(): Promise<HTMLElement> {
  const page = h('section', { className: 'page' });
  const visibleGroups = groups
    .map(group => ({ ...group, resources: group.resources.filter(resource => hasAnyRole(resource.roles)) }))
    .filter(group => group.resources.length > 0);

  page.append(
    h('div', { className: 'page-heading' },
      h('div', {},
        h('span', { className: 'eyebrow', text: 'ثبت مستقیم در سامانه' }),
        h('h1', { text: 'ثبت و ویرایش دستی اطلاعات' }),
        h('p', { text: 'بدون UUID و بدون فرم‌های مبهم شروع کنید: بخش موردنظر را انتخاب کنید، توضیح کنار هر فیلد را بخوانید و برای تغییرات بعدی از «مشاهده و ویرایش» استفاده کنید.' }),
      ),
      hasAnyRole(broadEducationRoles) ? h('button', { className: 'button button--secondary', type: 'button', onClick: () => navigate('/imports') }, icon('upload'), 'ورود از فایل جامع') : null,
    ),
    h('div', { className: 'card' },
      h('div', { className: 'card-header' }, h('div', {}, h('h2', { text: 'قبل از ثبت دستی' }), h('p', { text: 'سه نکته جلوی بیشتر خطاهای ثبت را می‌گیرد.' }))),
      h('div', { className: 'metric-grid' },
        h('article', { className: 'metric-card' }, h('span', { text: '۱' }), h('strong', { text: 'حوزه درست را انتخاب کنید' }), h('small', { text: 'مجموعه یا مدرسه فعال باید همان جایی باشد که داده به آن تعلق دارد.' })),
        h('article', { className: 'metric-card' }, h('span', { text: '۲' }), h('strong', { text: 'شناسه فنی وارد نکنید' }), h('small', { text: 'UUIDها توسط سامانه ساخته می‌شوند؛ روابط را با نام و کد انتخاب کنید.' })),
        h('article', { className: 'metric-card' }, h('span', { text: '۳' }), h('strong', { text: 'تاریخچه را حذف نکنید' }), h('small', { text: 'برای ثبت‌نام، ارزیابی و داده‌های نهایی از عملیات تغییر وضعیت، انتقال یا حذف منطقی استفاده کنید.' })),
      ),
    ),
  );

  for (const group of visibleGroups) {
    page.append(
      h('section', { className: 'manual-entry-group' },
        h('div', { className: 'card-header' }, h('div', {}, h('h2', { text: group.title }), h('p', { text: group.description }))),
        h('div', { className: 'import-guide-grid' }, ...group.resources.map(resourceCard)),
      ),
    );
  }

  page.append(
    h('div', { className: 'card' },
      h('h2', { text: 'چه چیزهایی دستی ثبت نمی‌شوند؟' }),
      h('p', { text: 'گزارش‌ها، کارنامه‌ها و هشدارها خروجی یا نتیجه داده‌های ثبت‌شده هستند. آن‌ها را از بخش مربوط تولید یا بررسی کنید، نه به‌عنوان داده خام جدید.' }),
    ),
  );
  return page;
}
