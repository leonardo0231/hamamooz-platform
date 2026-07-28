import { apiRequest } from '../api/client.js';
import { actionRequestSchema } from '../api/action-schemas.js';
import { contract, operationsForTag, resolveSchema, type ContractOperation, type ContractParameter, type ContractSchema } from '../api/contract.js';
import type { Pagination } from '../api/types.js';
import { navigate } from '../app/router.js';
import { hasAnyRole, hasWriteScope, administrativeRoles, broadEducationRoles, curriculumManagementRoles, organizationManagementRoles, policyManagementRoles, teacherWriteRoles } from '../app/permissions.js';
import { onWindowEventWhileConnected, h, clear, debounce, formatDate, safeText } from '../utils/dom.js';
import { confirmDialog, emptyState, errorState, loadingState, toast } from '../components/feedback.js';
import { icon } from '../components/icons.js';
import { openSchemaDialog, schemaHasBinary } from '../components/schema-form.js';

interface ResourceMeta {
  title: string;
  singular: string;
  icon: string;
  columns?: string[];
  readRoles?: Parameters<typeof hasAnyRole>[0];
  createRoles?: Parameters<typeof hasAnyRole>[0];
  updateRoles?: Parameters<typeof hasAnyRole>[0];
  deleteRoles?: Parameters<typeof hasAnyRole>[0];
}

const resourceMeta: Record<string, ResourceMeta> = {
  'academic-years': { title: 'سال‌های تحصیلی', singular: 'سال تحصیلی', icon: 'calendar', columns: ['title', 'starts_on', 'ends_on', 'is_current'], createRoles: organizationManagementRoles, updateRoles: organizationManagementRoles, deleteRoles: organizationManagementRoles },
  'assessment-types': { title: 'انواع ارزیابی', singular: 'نوع ارزیابی', icon: 'chart', columns: ['title', 'code', 'default_weight', 'is_active'], createRoles: curriculumManagementRoles, updateRoles: curriculumManagementRoles, deleteRoles: curriculumManagementRoles },
  assessments: { title: 'ارزیابی‌ها', singular: 'ارزیابی', icon: 'chart', columns: ['title', 'assessment_type_title', 'class_title', 'assessment_date', 'status'], createRoles: teacherWriteRoles, updateRoles: teacherWriteRoles, deleteRoles: teacherWriteRoles },
  'attendance-alerts': { title: 'هشدارهای حضور و غیاب', singular: 'هشدار', icon: 'bell', columns: ['student_name', 'class_title', 'severity', 'status', 'created_at'], createRoles: policyManagementRoles, updateRoles: policyManagementRoles, deleteRoles: policyManagementRoles },
  'attendance-policies': { title: 'سیاست‌های حضور و غیاب', singular: 'سیاست حضور', icon: 'settings', columns: ['school_name', 'academic_year_title', 'warning_absence_percent', 'critical_absence_percent', 'is_active'], createRoles: policyManagementRoles, updateRoles: policyManagementRoles, deleteRoles: policyManagementRoles },
  'attendance-records': { title: 'رکوردهای حضور و غیاب', singular: 'رکورد حضور', icon: 'calendar', columns: ['session_date', 'student_name', 'status', 'late_minutes', 'excuse_status'], createRoles: teacherWriteRoles, updateRoles: teacherWriteRoles, deleteRoles: teacherWriteRoles },
  'attendance-sessions': { title: 'جلسات حضور و غیاب', singular: 'جلسه حضور', icon: 'calendar', columns: ['session_date', 'class_section', 'course_offering', 'scope', 'status'], createRoles: teacherWriteRoles, updateRoles: teacherWriteRoles, deleteRoles: teacherWriteRoles },
  'calculation-policies': { title: 'سیاست‌های محاسبه نمره', singular: 'سیاست محاسبه', icon: 'settings', columns: ['title', 'organization', 'academic_year', 'version', 'is_active'], createRoles: curriculumManagementRoles, updateRoles: curriculumManagementRoles, deleteRoles: curriculumManagementRoles },
  classes: { title: 'کلاس‌ها', singular: 'کلاس', icon: 'building', columns: ['title', 'school', 'academic_year', 'grade_level', 'capacity', 'is_active'], createRoles: broadEducationRoles, updateRoles: broadEducationRoles, deleteRoles: broadEducationRoles },
  'course-offerings': { title: 'ارائه درس‌ها', singular: 'ارائه درس', icon: 'book', columns: ['class_section', 'grade_subject', 'teacher', 'term', 'is_active'], createRoles: broadEducationRoles, updateRoles: broadEducationRoles, deleteRoles: broadEducationRoles },
  enrollments: { title: 'ثبت‌نام‌ها', singular: 'ثبت‌نام', icon: 'users', columns: ['student', 'school', 'academic_year', 'class_section', 'student_number', 'status'], createRoles: broadEducationRoles, updateRoles: broadEducationRoles, deleteRoles: broadEducationRoles },
  'grade-levels': { title: 'پایه‌های تحصیلی', singular: 'پایه', icon: 'book', columns: ['title', 'code', 'organization', 'order', 'is_active'], createRoles: organizationManagementRoles, updateRoles: organizationManagementRoles, deleteRoles: organizationManagementRoles },
  'grade-subjects': { title: 'درس‌های پایه', singular: 'درس پایه', icon: 'book', columns: ['grade_level', 'subject', 'coefficient', 'is_active'], createRoles: curriculumManagementRoles, updateRoles: curriculumManagementRoles, deleteRoles: curriculumManagementRoles },
  guardians: { title: 'اولیا', singular: 'ولی', icon: 'users', columns: ['first_name', 'last_name', 'phone_primary', 'national_id'], createRoles: broadEducationRoles, updateRoles: broadEducationRoles, deleteRoles: broadEducationRoles },
  imports: { title: 'ورود اطلاعات', singular: 'عملیات ورود', icon: 'upload', columns: ['import_type', 'school', 'status', 'total_rows', 'successful_rows', 'error_count'], readRoles: broadEducationRoles, createRoles: broadEducationRoles },
  organizations: { title: 'مجموعه‌ها', singular: 'مجموعه', icon: 'building', columns: ['name', 'code', 'is_active', 'created_at'], createRoles: ['system_admin'], updateRoles: organizationManagementRoles, deleteRoles: ['system_admin'] },
  'parent-notifications': { title: 'اعلان‌های والدین', singular: 'اعلان', icon: 'bell', columns: ['enrollment', 'channel', 'status', 'attempts', 'created_at'], createRoles: teacherWriteRoles },
  reports: { title: 'گزارش‌های آرشیوی', singular: 'گزارش', icon: 'file', columns: ['report_type', 'status', 'school', 'term', 'created_at'], createRoles: teacherWriteRoles },
  'role-assignments': { title: 'نقش‌ها و دسترسی‌ها', singular: 'تخصیص نقش', icon: 'settings', columns: ['user', 'role_display', 'organization', 'school', 'is_active'], readRoles: administrativeRoles, createRoles: administrativeRoles },
  schools: { title: 'مدارس و شعب', singular: 'مدرسه', icon: 'building', columns: ['name', 'code', 'organization', 'is_active'], createRoles: organizationManagementRoles, updateRoles: organizationManagementRoles, deleteRoles: organizationManagementRoles },
  scores: { title: 'نمرات', singular: 'نمره', icon: 'chart', columns: ['assessment', 'enrollment', 'value', 'status', 'updated_at'], createRoles: teacherWriteRoles, updateRoles: teacherWriteRoles, deleteRoles: teacherWriteRoles },
  students: { title: 'دانش‌آموزان', singular: 'دانش‌آموز', icon: 'users', columns: ['first_name', 'last_name', 'national_id', 'gender', 'birth_date', 'status'], createRoles: broadEducationRoles, updateRoles: broadEducationRoles, deleteRoles: broadEducationRoles },
  subjects: { title: 'درس‌ها', singular: 'درس', icon: 'book', columns: ['title', 'code', 'organization', 'is_active'], createRoles: curriculumManagementRoles, updateRoles: curriculumManagementRoles, deleteRoles: curriculumManagementRoles },
  terms: { title: 'نوبت‌های تحصیلی', singular: 'نوبت', icon: 'calendar', columns: ['title', 'academic_year', 'starts_on', 'ends_on', 'is_active'], createRoles: organizationManagementRoles, updateRoles: organizationManagementRoles, deleteRoles: organizationManagementRoles },
  users: { title: 'کاربران', singular: 'کاربر', icon: 'user', columns: ['username', 'first_name', 'last_name', 'email', 'phone', 'is_active'], readRoles: administrativeRoles, createRoles: administrativeRoles },
};

const fieldLabels: Record<string, string> = {
  id: 'شناسه', title: 'عنوان', name: 'نام', code: 'کد', first_name: 'نام', last_name: 'نام خانوادگی', username: 'نام کاربری', email: 'ایمیل', phone: 'تلفن', national_id: 'کد ملی', status: 'وضعیت', gender: 'جنسیت',
  organization: 'مجموعه', school: 'مدرسه', academic_year: 'سال تحصیلی', term: 'نوبت', grade_level: 'پایه', class_section: 'کلاس', student: 'دانش‌آموز', enrollment: 'ثبت‌نام', teacher: 'دبیر', assessment: 'ارزیابی', assessment_type: 'نوع ارزیابی', course_offering: 'ارائه درس', grade_subject: 'درس پایه', subject: 'درس',
  school_name: 'مدرسه', academic_year_title: 'سال تحصیلی', student_name: 'دانش‌آموز', class_title: 'کلاس', assessment_type_title: 'نوع ارزیابی',
  is_active: 'فعال', is_current: 'جاری', capacity: 'ظرفیت', order: 'ترتیب', coefficient: 'ضریب', value: 'مقدار', weight: 'وزن', default_weight: 'وزن پیش‌فرض', scope: 'نوع', severity: 'شدت', role_display: 'نقش', role: 'نقش',
  starts_on: 'شروع', ends_on: 'پایان', assessment_date: 'تاریخ برگزاری', birth_date: 'تاریخ تولد', session_date: 'تاریخ جلسه', created_at: 'ایجاد', updated_at: 'آخرین تغییر',
  student_number: 'شماره دانش‌آموزی', late_minutes: 'دقایق تأخیر', excuse_status: 'وضعیت عذر', import_type: 'نوع ورود', report_type: 'نوع گزارش', total_rows: 'کل ردیف‌ها', successful_rows: 'موفق', error_count: 'خطا', phone_primary: 'تلفن اصلی', warning_absence_percent: 'هشدار غیبت', critical_absence_percent: 'غیبت بحرانی', channel: 'کانال', attempts: 'تلاش‌ها', version: 'نسخه',
};

const actionLabels: Record<string, string> = {
  approve: 'تأیید', lock: 'قفل', reject: 'رد', submit: 'ارسال', acknowledge: 'مشاهده شد', resolve: 'رفع هشدار', evaluate: 'ارزیابی هشدارها', 'approve-excuse': 'تأیید عذر', correct: 'اصلاح', 'notify-guardians': 'اعلان به اولیا', 'reject-excuse': 'رد عذر', 'submit-excuse': 'ثبت عذر', 'bulk-mark': 'ثبت گروهی', cancel: 'لغو جلسه', finalize: 'نهایی‌سازی', retry: 'تلاش مجدد', 'change-class': 'تغییر کلاس', 'change-status': 'تغییر وضعیت', transfer: 'انتقال', guardians: 'اتصال ولی', 'change_password': 'تغییر رمز', deactivate: 'غیرفعال‌سازی', 'correct-locked': 'اصلاح نمره قفل‌شده', roster: 'فهرست حضور', scores: 'نمرات', results: 'نتایج', download: 'دریافت فایل',
};

function labelForField(field: string): string { return fieldLabels[field] ?? field.replaceAll('_', ' '); }
function metaFor(tag: string): ResourceMeta { return resourceMeta[tag] ?? { title: tag.replaceAll('-', ' '), singular: tag.replaceAll('-', ' '), icon: 'file' }; }
function pathWithId(path: string, id: string | number): string { return path.replace('{id}', encodeURIComponent(String(id))); }

function responseItemSchema(operation: ContractOperation): ContractSchema {
  const response = resolveSchema(operation.responseSchema);
  const results = response.properties?.results;
  return results?.items ? resolveSchema(results.items) : response;
}

function visibleColumns(meta: ResourceMeta, schema: ContractSchema, rows: Record<string, unknown>[]): string[] {
  const properties = Object.keys(resolveSchema(schema).properties ?? rows[0] ?? {});
  if (meta.columns) {
    const configured = meta.columns.filter(column => properties.includes(column) || rows.some(row => column in row));
    if (configured.length) return configured;
  }
  return properties.filter(name => !['id', 'created_by', 'updated_by'].includes(name)).slice(0, 6);
}

function badgeValue(value: unknown): HTMLElement {
  const text = safeText(value);
  const tone = ['critical', 'rejected', 'failed', 'unexcused_absent', 'inactive'].includes(String(value)) ? 'danger'
    : ['warning', 'submitted', 'queued', 'processing', 'draft'].includes(String(value)) ? 'warning'
      : ['active', 'approved', 'completed', 'resolved', 'finalized', 'present'].includes(String(value)) || value === true ? 'success' : 'neutral';
  return h('span', { className: `badge badge--${tone}`, text });
}

function cellContent(field: string, value: unknown): Node {
  if (field.endsWith('_at') || field.endsWith('_on') || field.includes('date') || field === 'last_login') return document.createTextNode(formatDate(value, field.endsWith('_at')));
  if (typeof value === 'boolean' || ['status', 'severity', 'scope', 'gender', 'role_display', 'role', 'import_type', 'report_type', 'excuse_status'].includes(field)) return badgeValue(value);
  if (value && typeof value === 'object') {
    const object = value as Record<string, unknown>;
    return document.createTextNode(safeText(object.full_name ?? object.title ?? object.name ?? object.username ?? object.id ?? value));
  }
  return document.createTextNode(safeText(value));
}

function createFilterControl(parameter: ContractParameter, params: URLSearchParams, onChange: () => void): HTMLElement {
  const schema = resolveSchema(parameter.schema);
  const label = h('span', { text: labelForField(parameter.name) });
  let input: HTMLInputElement | HTMLSelectElement;
  if (schema.enum) {
    input = h('select', {}, h('option', { value: '', text: 'همه' }), ...schema.enum.map(value => h('option', { value: String(value), text: String(value) }))) as HTMLSelectElement;
  } else if (schema.type === 'boolean') {
    input = h('select', {}, h('option', { value: '', text: 'همه' }), h('option', { value: 'true', text: 'بله' }), h('option', { value: 'false', text: 'خیر' })) as HTMLSelectElement;
  } else {
    input = h('input', { type: schema.format === 'date' ? 'date' : 'text', placeholder: labelForField(parameter.name), dir: schema.format === 'uuid' ? 'ltr' : 'auto' }) as HTMLInputElement;
  }
  input.value = params.get(parameter.name) ?? '';
  input.addEventListener('change', onChange);
  return h('label', { className: 'filter-control' }, label, input);
}


function openResultDialog(title: string, data: unknown): void {
  const titleId = `result-dialog-title-${Math.random().toString(36).slice(2)}`;
  const dialog = h('dialog', { className: 'dialog dialog--wide', 'aria-labelledby': titleId }) as HTMLDialogElement;
  const close = h('button', { className: 'icon-button', type: 'button', 'aria-label': 'بستن', onClick: () => dialog.close() }, icon('close'));
  const content = h('pre', { className: 'result-viewer', dir: 'ltr', text: JSON.stringify(data, null, 2) });
  dialog.append(h('div', { className: 'dialog__body dialog__body--wide' }, h('div', { className: 'dialog__header' }, h('h2', { id: titleId, text: title }), close), content));
  dialog.addEventListener('close', () => dialog.remove(), { once: true });
  document.body.append(dialog);
  dialog.showModal();
}

function rolesForAction(operation: ContractOperation): Parameters<typeof hasAnyRole>[0] {
  const action = operation.path.split('/').filter(Boolean).at(-1) ?? operation.id;
  if (['approve', 'reject', 'lock', 'correct-locked', 'approve-excuse', 'reject-excuse', 'acknowledge', 'resolve', 'evaluate'].includes(action)) return policyManagementRoles;
  if (['change-class', 'change-status', 'transfer', 'guardians'].includes(action)) return broadEducationRoles;
  if (action === 'retry') return operation.id.startsWith('imports_') ? broadEducationRoles : teacherWriteRoles;
  if (['submit', 'bulk', 'bulk-mark', 'cancel', 'finalize', 'correct', 'notify-guardians', 'submit-excuse'].includes(action)) return teacherWriteRoles;
  if (['change_password', 'deactivate'].includes(action)) return administrativeRoles;
  return undefined;
}

function canInvokeAction(operation: ContractOperation): boolean {
  if (operation.method === 'GET') return true;
  return hasAnyRole(rolesForAction(operation)) && hasWriteScope();
}

async function invokeAction(operation: ContractOperation, id: string | number, refresh: () => Promise<void>): Promise<void> {
  const action = operation.path.split('/').filter(Boolean).at(-1) ?? operation.id;
  const title = actionLabels[action] ?? operation.summary ?? action.replaceAll('-', ' ');
  const schema = resolveSchema(actionRequestSchema(operation));
  const hasFields = Object.keys(schema.properties ?? {}).length > 0;
  const execute = async (payload?: Record<string, unknown> | FormData): Promise<void> => {
    const result = await apiRequest<unknown>(pathWithId(operation.path, id), { method: operation.method, body: payload ?? (operation.method === 'POST' ? {} : undefined), responseType: operation.statuses.includes('204') ? 'void' : 'json' });
    if (operation.method === 'GET') openResultDialog(title, result);
    else {
      toast(`${title} با موفقیت انجام شد.`, 'success');
      await refresh();
    }
  };
  if (hasFields) {
    openSchemaDialog({ title, schema, multipart: operation.requestMime === 'multipart/form-data' || schemaHasBinary(schema), submitLabel: title, onSubmit: execute });
  } else if (await confirmDialog({ title, message: `عملیات «${title}» برای این رکورد اجرا شود؟`, confirmLabel: title, dangerous: ['reject', 'cancel', 'deactivate'].includes(action) })) {
    await execute();
  }
}

export async function renderResourcePage(tag: string): Promise<HTMLElement> {
  const meta = metaFor(tag);
  const operations = operationsForTag(tag);
  const listOperation = operations.find(op => op.method === 'GET' && !op.path.includes('{id}') && !op.path.match(/\/(summary|preview|evaluate|student|class|school)\/$/));
  const createOperation = operations.find(op => op.method === 'POST' && !op.path.includes('{id}') && op.path.split('/').filter(Boolean).at(-1) === tag);
  const retrieveOperation = operations.find(op => op.method === 'GET' && /\{id\}\/$/.test(op.path));
  const updateOperation = operations.find(op => op.method === 'PATCH' && /\{id\}\/$/.test(op.path));
  const deleteOperation = operations.find(op => op.method === 'DELETE' && /\{id\}\/$/.test(op.path));
  const itemActions = operations.filter(op => op.path.includes('{id}') && !/\{id\}\/$/.test(op.path));
  const page = h('section', { className: 'page' });
  if (!hasAnyRole(meta.readRoles)) {
    page.append(h('div', { className: 'error-page' }, icon('lock'), h('h1', { text: 'دسترسی به این بخش مجاز نیست' }), h('p', { text: 'نقش فعال شما اجازه مشاهده این منبع مدیریتی را نمی‌دهد.' }), h('button', { className: 'button button--primary', type: 'button', onClick: () => navigate('/') }, 'بازگشت به داشبورد')));
    return page;
  }
  const body = h('div', { className: 'card resource-card' });
  const params = new URLSearchParams(location.search);

  const headerActions = h('div', { className: 'page-actions' });
  if (createOperation && hasAnyRole(meta.createRoles ?? broadEducationRoles)) {
    const writeScopeReady = hasWriteScope();
    headerActions.append(h('button', { className: 'button button--primary', type: 'button', disabled: !writeScopeReady, title: writeScopeReady ? `ایجاد ${meta.singular}` : 'ابتدا مجموعه یا شعبه فعال را انتخاب کنید', onClick: () => {
      openSchemaDialog({
        title: `ایجاد ${meta.singular}`,
        schema: createOperation.requestSchema,
        multipart: createOperation.requestMime === 'multipart/form-data' || schemaHasBinary(createOperation.requestSchema),
        submitLabel: 'ثبت اطلاعات',
        onSubmit: async payload => {
          await apiRequest(createOperation.path, { method: 'POST', body: payload });
          toast(`${meta.singular} با موفقیت ایجاد شد.`, 'success');
          await load();
        },
      });
    } }, icon('plus'), `ایجاد ${meta.singular}`));
  }
  page.append(h('div', { className: 'page-heading' }, h('div', {}, h('span', { className: 'eyebrow', text: 'مدیریت اطلاعات' }), h('h1', { text: meta.title }), h('p', { text: 'داده‌ها مستقیماً از API رسمی سامانه دریافت می‌شوند.' })), headerActions), body);

  if (!listOperation) {
    body.append(emptyState('فهرست مستقیمی برای این بخش تعریف نشده است', 'قرارداد OpenAPI برای این Tag عملیات فهرست استاندارد ندارد.'));
    return page;
  }
  const listOp = listOperation;

  const searchInput = h('input', { type: 'search', placeholder: `جست‌وجو در ${meta.title}…`, value: params.get('search') ?? '', 'aria-label': 'جست‌وجو' }) as HTMLInputElement;
  const filterPanel = h('div', { className: 'filters', id: 'resource-filters' });
  const applyFilters = (): void => {
    filterPanel.querySelectorAll<HTMLInputElement | HTMLSelectElement>('input, select').forEach(input => {
      if (input.value) params.set(input.name || input.dataset.name || '', input.value);
      else params.delete(input.name || input.dataset.name || '');
    });
    params.set('page', '1');
    history.replaceState({}, '', `${location.pathname}?${params.toString()}`);
    void load();
  };
  const queryParameters = listOp.parameters.filter(p => p.in === 'query' && !['page', 'page_size', 'search', 'ordering'].includes(p.name));
  for (const parameter of queryParameters) {
    const control = createFilterControl(parameter, params, applyFilters);
    const input = control.querySelector<HTMLInputElement | HTMLSelectElement>('input, select');
    if (input) { input.name = parameter.name; input.dataset.name = parameter.name; }
    filterPanel.append(control);
  }
  const sortSelect = h('select', { name: 'ordering', 'aria-label': 'مرتب‌سازی' }, h('option', { value: '', text: 'مرتب‌سازی پیش‌فرض' })) as HTMLSelectElement;
  sortSelect.value = params.get('ordering') ?? '';
  sortSelect.addEventListener('change', () => { if (sortSelect.value) params.set('ordering', sortSelect.value); else params.delete('ordering'); params.set('page', '1'); void load(); });
  const pageSize = h('select', { name: 'page_size', 'aria-label': 'تعداد در صفحه' }, ...[25, 50, 100, 200].map(value => h('option', { value: String(value), text: `${value.toLocaleString('fa-IR')} ردیف` }))) as HTMLSelectElement;
  pageSize.value = params.get('page_size') ?? '25';
  pageSize.addEventListener('change', () => { params.set('page_size', pageSize.value); params.set('page', '1'); void load(); });
  const filterToggle = h('button', {
    className: 'button button--secondary filter-toggle',
    type: 'button',
    'aria-controls': 'resource-filters',
    'aria-expanded': 'false',
    onClick: () => {
      const open = filterPanel.classList.toggle('is-open');
      filterToggle.setAttribute('aria-expanded', String(open));
    },
  }, icon('filter'), 'فیلترها') as HTMLButtonElement;
  const toolbar = h('div', { className: 'resource-toolbar' }, h('label', { className: 'search-input' }, icon('search'), searchInput), filterToggle, sortSelect, pageSize);
  body.append(toolbar, filterPanel, h('div', { className: 'resource-content' }));
  const content = body.querySelector<HTMLElement>('.resource-content') as HTMLElement;
  searchInput.addEventListener('input', debounce(() => { if (searchInput.value) params.set('search', searchInput.value); else params.delete('search'); params.set('page', '1'); void load(); }, 400));

  async function load(): Promise<void> {
    clear(content);
    content.append(loadingState());
    try {
      const query: Record<string, string> = {};
      params.forEach((value, key) => { query[key] = value; });
      const response = await apiRequest<Pagination<Record<string, unknown>> | Record<string, unknown>[]>(listOp.path, { query });
      const rows = Array.isArray(response) ? response : response.results;
      const total = Array.isArray(response) ? rows.length : response.count;
      const schema = responseItemSchema(listOp);
      const columns = visibleColumns(meta, schema, rows);
      sortSelect.replaceChildren(h('option', { value: '', text: 'مرتب‌سازی پیش‌فرض' }), ...columns.flatMap(field => [h('option', { value: field, text: `${labelForField(field)} صعودی` }), h('option', { value: `-${field}`, text: `${labelForField(field)} نزولی` })]));
      sortSelect.value = params.get('ordering') ?? '';
      clear(content);
      if (!rows.length) {
        content.append(emptyState('داده‌ای یافت نشد', 'فیلترها را تغییر دهید یا رکورد جدیدی ایجاد کنید.'));
        return;
      }
      const table = h('table', { className: 'data-table' },
        h('caption', { className: 'sr-only', text: `فهرست ${meta.title}` }),
        h('thead', {}, h('tr', {}, ...columns.map(field => h('th', { scope: 'col', text: labelForField(field) })), h('th', { scope: 'col', text: 'عملیات' }))),
        h('tbody'),
      );
      const tbody = table.querySelector('tbody') as HTMLTableSectionElement;
      for (const row of rows) {
        const id = row.id as string | number | undefined;
        const actionCell = h('td', { className: 'row-actions', dataset: { label: 'عملیات' } });
        if (tag === 'students' && id !== undefined) actionCell.append(h('button', { className: 'icon-button', type: 'button', title: 'پرونده دانش‌آموز', 'aria-label': 'پرونده دانش‌آموز', onClick: () => navigate(`/students/${id}`) }, icon('eye')));
        else if (retrieveOperation && id !== undefined) actionCell.append(h('button', { className: 'icon-button', type: 'button', title: 'مشاهده', 'aria-label': 'مشاهده', onClick: async () => {
          try {
            const detail = await apiRequest<Record<string, unknown>>(pathWithId(retrieveOperation.path, id));
            openResultDialog(`مشاهده ${meta.singular}`, detail);
          } catch (error) { toast('دریافت جزئیات ناموفق بود', 'error', error instanceof Error ? error.message : undefined); }
        } }, icon('eye')));
        if (updateOperation && id !== undefined && hasAnyRole(meta.updateRoles ?? meta.createRoles ?? broadEducationRoles)) actionCell.append(h('button', { className: 'icon-button', type: 'button', disabled: !hasWriteScope(), title: hasWriteScope() ? 'ویرایش' : 'ابتدا حوزه فعال را انتخاب کنید', 'aria-label': 'ویرایش', onClick: async () => {
          try {
            const detail = retrieveOperation ? await apiRequest<Record<string, unknown>>(pathWithId(retrieveOperation.path, id)) : row;
            openSchemaDialog({ title: `ویرایش ${meta.singular}`, schema: updateOperation.requestSchema, initial: detail, multipart: updateOperation.requestMime === 'multipart/form-data' || schemaHasBinary(updateOperation.requestSchema), submitLabel: 'ذخیره تغییرات', onSubmit: async payload => { await apiRequest(pathWithId(updateOperation.path, id), { method: 'PATCH', body: payload }); toast('تغییرات ذخیره شد.', 'success'); await load(); } });
          } catch (error) { toast('آماده‌سازی فرم ویرایش ناموفق بود', 'error', error instanceof Error ? error.message : undefined); }
        } }, icon('edit')));
        for (const action of itemActions.filter(canInvokeAction).slice(0, 4)) {
          const actionName = action.path.split('/').filter(Boolean).at(-1) ?? '';
          actionCell.append(h('button', { className: 'icon-button', type: 'button', title: actionLabels[actionName] ?? actionName, 'aria-label': actionLabels[actionName] ?? actionName, onClick: () => void invokeAction(action, id ?? '', load).catch(error => toast('اجرای عملیات ناموفق بود', 'error', error instanceof Error ? error.message : undefined)) }, icon(actionName === 'retry' ? 'refresh' : 'more')));
        }
        if (deleteOperation && id !== undefined && hasAnyRole(meta.deleteRoles ?? meta.createRoles ?? broadEducationRoles)) actionCell.append(h('button', { className: 'icon-button icon-button--danger', type: 'button', disabled: !hasWriteScope(), title: hasWriteScope() ? 'حذف' : 'ابتدا حوزه فعال را انتخاب کنید', 'aria-label': 'حذف', onClick: async () => {
          if (!await confirmDialog({ title: `حذف ${meta.singular}`, message: 'این عملیات قابل بازگشت نیست. از حذف این رکورد مطمئن هستید؟', confirmLabel: 'حذف', dangerous: true })) return;
          try { await apiRequest(pathWithId(deleteOperation.path, id), { method: 'DELETE', responseType: 'void' }); toast('رکورد حذف شد.', 'success'); await load(); }
          catch (error) { toast('حذف رکورد ناموفق بود', 'error', error instanceof Error ? error.message : undefined); }
        } }, icon('trash')));
        tbody.append(h('tr', {}, ...columns.map(field => h('td', { dataset: { label: labelForField(field) } }, cellContent(field, row[field]))), actionCell));
      }
      const currentPage = Number(params.get('page') ?? 1);
      const size = Number(params.get('page_size') ?? 25);
      const pages = Math.max(1, Math.ceil(total / size));
      const pagination = h('div', { className: 'pagination' },
        h('span', { text: `${total.toLocaleString('fa-IR')} رکورد` }),
        h('div', {},
          h('button', { className: 'button button--ghost', type: 'button', disabled: currentPage <= 1, onClick: () => { params.set('page', String(currentPage - 1)); void load(); } }, 'قبلی'),
          h('span', { text: `صفحه ${currentPage.toLocaleString('fa-IR')} از ${pages.toLocaleString('fa-IR')}` }),
          h('button', { className: 'button button--ghost', type: 'button', disabled: currentPage >= pages, onClick: () => { params.set('page', String(currentPage + 1)); void load(); } }, 'بعدی'),
        ),
      );
      content.append(h('div', { className: 'table-wrap' }, table), pagination);
      history.replaceState({}, '', `${location.pathname}?${params.toString()}`);
    } catch (error) {
      clear(content);
      content.append(errorState(error, () => void load()));
    }
  }

  onWindowEventWhileConnected(page, 'hamamooz:scope-change', () => void load());
  await load();
  return page;
}

export function availableResourceTags(): string[] {
  return [...new Set(contract.operations.map(operation => operation.tag))].filter(tag => Boolean(tag));
}
