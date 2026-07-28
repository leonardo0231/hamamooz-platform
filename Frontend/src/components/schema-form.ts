import type { ContractSchema } from '../api/contract.js';
import { resolveSchema } from '../api/contract.js';
import { ApiError } from '../api/types.js';
import { h, safeText } from '../utils/dom.js';
import { icon } from './icons.js';
import { confirmDialog } from './feedback.js';

const fieldLabels: Record<string, string> = {
  username: 'نام کاربری', email: 'ایمیل', password: 'رمز عبور', first_name: 'نام', last_name: 'نام خانوادگی', phone: 'تلفن', national_id: 'کد ملی', is_active: 'فعال',
  organization: 'مجموعه', school: 'مدرسه', academic_year: 'سال تحصیلی', term: 'نوبت', grade_level: 'پایه', class_section: 'کلاس', student: 'دانش‌آموز', enrollment: 'ثبت‌نام', guardian: 'ولی',
  title: 'عنوان', name: 'نام', code: 'کد', description: 'توضیحات', status: 'وضعیت', note: 'یادداشت', reason: 'دلیل', starts_on: 'تاریخ شروع', ends_on: 'تاریخ پایان', session_date: 'تاریخ جلسه',
  source_file: 'فایل منبع', import_type: 'نوع ورود اطلاعات', report_type: 'نوع گزارش', role: 'نقش', is_current: 'سال جاری', capacity: 'ظرفیت', gender: 'جنسیت', birth_date: 'تاریخ تولد', student_number: 'شماره دانش‌آموزی',
  current_password: 'رمز فعلی', new_password: 'رمز جدید', refresh: 'توکن تازه‌سازی', entries: 'ورودی‌ها', value: 'مقدار', severity: 'شدت', scope: 'نوع جلسه',
};

const enumLabels: Record<string, string> = {
  active: 'فعال', inactive: 'غیرفعال', female: 'دختر', male: 'پسر', draft: 'پیش‌نویس', submitted: 'ارسال‌شده', approved: 'تأییدشده', rejected: 'ردشده', locked: 'قفل‌شده',
  open: 'باز', acknowledged: 'مشاهده‌شده', resolved: 'رفع‌شده', warning: 'مهم', critical: 'بحرانی', queued: 'در صف', processing: 'در حال پردازش', completed: 'تکمیل‌شده', failed: 'ناموفق',
  present: 'حاضر', excused_absent: 'غیبت موجه', unexcused_absent: 'غیبت غیرموجه', not_entered: 'ثبت‌نشده', cancelled: 'لغوشده', finalized: 'نهایی‌شده', daily: 'روزانه', period: 'زنگ درسی',
  students: 'دانش‌آموزان', enrollments: 'ثبت‌نام‌ها', scores: 'نمرات', monthly_evaluations: 'ارزیابی جامع ماهانه', student_report_card: 'کارنامه دانش‌آموز', class_report_cards: 'کارنامه کلاس',
  system_admin: 'مدیر کل سامانه', organization_admin: 'مدیر مجموعه', school_manager: 'مدیر مدرسه', educational_deputy: 'معاون آموزشی', operator: 'اپراتور', teacher: 'دبیر',
};

function fieldLabel(name: string, schema: ContractSchema): string {
  return schema.title?.replace(/\s*\(.*\)$/, '') || fieldLabels[name] || name.replaceAll('_', ' ');
}

function formatHint(schema: ContractSchema): string | null {
  if (schema.description) return schema.description.split('\n')[0] ?? null;
  if (schema.format === 'uuid') return 'شناسه UUID معتبر';
  if (schema.maxLength) return `حداکثر ${schema.maxLength.toLocaleString('fa-IR')} نویسه`;
  return null;
}

function inputFor(name: string, unresolved: ContractSchema, initial: unknown, required: boolean): { wrapper: HTMLElement; read: () => unknown; input: HTMLElement } {
  const schema = resolveSchema(unresolved);
  const id = `field-${name}-${Math.random().toString(36).slice(2)}`;
  const hintId = `${id}-hint`;
  const errorId = `${id}-error`;
  const label = h('label', { for: id }, fieldLabel(name, schema), required ? h('span', { className: 'required-mark', text: ' *' }) : null);
  const hint = formatHint(schema);
  let input: HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement;
  let read: () => unknown;

  const itemSchema = schema.items ? resolveSchema(schema.items) : null;
  if (schema.type === 'array' && itemSchema?.format === 'binary') {
    input = h('input', { id, name, type: 'file', required, multiple: true }) as HTMLInputElement;
    read = () => Array.from((input as HTMLInputElement).files ?? []);
  } else if (schema.type === 'array' && itemSchema?.enum?.length) {
    input = h('select', { id, name, required, multiple: true, size: Math.min(5, itemSchema.enum.length) }, ...itemSchema.enum.map(value => h('option', { value: String(value), text: enumLabels[String(value)] ?? String(value), selected: Array.isArray(initial) && initial.includes(value) }))) as HTMLSelectElement;
    read = () => Array.from((input as HTMLSelectElement).selectedOptions, option => option.value);
  } else if (schema.enum?.length) {
    input = h('select', { id, name, required }, h('option', { value: '', text: 'انتخاب کنید' }), ...schema.enum.map(value => h('option', { value: String(value), text: enumLabels[String(value)] ?? String(value), selected: initial === value }))) as HTMLSelectElement;
    read = () => input.value === '' ? null : input.value;
  } else if (schema.type === 'boolean') {
    input = h('input', { id, name, type: 'checkbox', checked: Boolean(initial), 'aria-describedby': `${hint ? hintId : ''} ${errorId}`.trim() }) as HTMLInputElement;
    read = () => (input as HTMLInputElement).checked;
    const wrapper = h('div', { className: 'form-field form-field--checkbox' }, input, label, hint ? h('small', { id: hintId, text: hint }) : null, h('div', { className: 'field-error', id: errorId, dataset: { field: name }, 'aria-live': 'polite' }));
    return { wrapper, read, input };
  } else if (schema.format === 'binary') {
    input = h('input', { id, name, type: 'file', required }) as HTMLInputElement;
    read = () => (input as HTMLInputElement).files?.[0] ?? null;
  } else if (schema.type === 'object' || schema.type === 'array' || schema.properties || schema.items) {
    input = h('textarea', { id, name, rows: 5, required, spellcheck: false, value: initial ? JSON.stringify(initial, null, 2) : schema.type === 'array' ? '[]' : '{}' }) as HTMLTextAreaElement;
    read = () => {
      const text = input.value.trim();
      return text ? JSON.parse(text) as unknown : schema.type === 'array' ? [] : {};
    };
  } else {
    const type = schema.format === 'date' ? 'date' : schema.format === 'date-time' ? 'datetime-local' : schema.format === 'time' ? 'time' : schema.format === 'email' ? 'email' : schema.format === 'password' || name.includes('password') ? 'password' : schema.type === 'integer' || schema.type === 'number' ? 'number' : 'text';
    input = h('input', {
      id, name, type, required, value: initial ?? '', min: schema.minimum, max: schema.maximum, minLength: schema.minLength, maxLength: schema.maxLength,
      step: schema.type === 'integer' ? '1' : schema.type === 'number' ? 'any' : undefined,
      autocomplete: type === 'password' ? (name === 'current_password' ? 'current-password' : 'new-password') : undefined,
      dir: schema.format === 'uuid' || schema.format === 'email' ? 'ltr' : 'auto',
    }) as HTMLInputElement;
    read = () => {
      if (input.value === '') return schema.nullable ? null : '';
      if (schema.type === 'integer') return Number.parseInt(input.value, 10);
      if (schema.type === 'number') return Number.parseFloat(input.value);
      return input.value;
    };
  }
  input.setAttribute('aria-describedby', `${hint ? hintId : ''} ${errorId}`.trim());
  return { wrapper: h('div', { className: 'form-field' }, label, input, hint ? h('small', { id: hintId, text: hint }) : null, h('div', { className: 'field-error', id: errorId, dataset: { field: name }, 'aria-live': 'polite' })), read, input };
}


export function schemaHasBinary(schema: ContractSchema): boolean {
  const resolved = resolveSchema(schema);
  if (resolved.format === 'binary') return true;
  if (resolved.items && schemaHasBinary(resolved.items)) return true;
  return Object.values(resolved.properties ?? {}).some(schemaHasBinary);
}

export interface SchemaFormResult {
  element: HTMLFormElement;
  setErrors: (error: ApiError) => void;
  setSubmitting: (submitting: boolean) => void;
}

export function createSchemaForm(options: {
  schema: ContractSchema;
  initial?: Record<string, unknown>;
  multipart?: boolean;
  submitLabel: string;
  onSubmit: (payload: Record<string, unknown> | FormData) => Promise<void>;
}): SchemaFormResult {
  const resolved = resolveSchema(options.schema);
  const required = new Set(resolved.required ?? []);
  const readers = new Map<string, () => unknown>();
  const controls: HTMLElement[] = [];
  for (const [name, schema] of Object.entries(resolved.properties ?? {})) {
    const fieldSchema = resolveSchema(schema);
    if (fieldSchema.readOnly) continue;
    const field = inputFor(name, schema, options.initial?.[name], required.has(name));
    readers.set(name, field.read);
    controls.push(field.wrapper);
  }
  const submit = h('button', { className: 'button button--primary', type: 'submit' }, icon('check'), options.submitLabel) as HTMLButtonElement;
  const generalError = h('div', { className: 'form-error', role: 'alert' });
  const form = h('form', { className: 'schema-form', novalidate: false }, h('div', { className: 'form-grid' }, ...controls), generalError, h('div', { className: 'form-actions' }, submit)) as HTMLFormElement;

  const setErrors = (error: ApiError): void => {
    form.querySelectorAll<HTMLElement>('.field-error').forEach(node => { node.textContent = ''; });
    form.querySelectorAll<HTMLElement>('[aria-invalid="true"]').forEach(control => control.removeAttribute('aria-invalid'));
    let firstInvalid: HTMLElement | null = null;
    for (const [field, messages] of Object.entries(error.fieldErrors)) {
      const node = form.querySelector<HTMLElement>(`.field-error[data-field="${CSS.escape(field)}"]`);
      if (node) node.textContent = messages.join('، ');
      const control = form.querySelector<HTMLElement>(`[name="${CSS.escape(field)}"]`);
      if (control) {
        control.setAttribute('aria-invalid', 'true');
        firstInvalid ??= control;
      }
    }
    generalError.textContent = error.message + (error.requestId ? ` — شناسه پیگیری: ${error.requestId}` : '');
    firstInvalid?.focus();
  };
  const setSubmitting = (submitting: boolean): void => {
    submit.disabled = submitting;
    submit.replaceChildren(submitting ? h('span', { className: 'spinner spinner--small' }) : icon('check'), submitting ? 'در حال ارسال…' : options.submitLabel);
  };

  form.addEventListener('submit', async event => {
    event.preventDefault();
    generalError.textContent = '';
    if (!form.reportValidity()) return;
    try {
      const values: Record<string, unknown> = {};
      for (const [name, read] of readers) {
        const value = read();
        if (!required.has(name) && (value === '' || value === null || value === undefined || (Array.isArray(value) && value.length === 0))) continue;
        values[name] = value;
      }
      let payload: Record<string, unknown> | FormData = values;
      if (options.multipart) {
        const data = new FormData();
        for (const [key, value] of Object.entries(values)) {
          if (value instanceof File) data.append(key, value);
          else if (Array.isArray(value) && value.every(item => item instanceof File)) {
            for (const file of value) data.append(key, file);
          } else if (value !== null && value !== undefined) data.append(key, typeof value === 'object' ? JSON.stringify(value) : String(value));
        }
        payload = data;
      }
      setSubmitting(true);
      await options.onSubmit(payload);
    } catch (error) {
      if (error instanceof SyntaxError) generalError.textContent = `ساختار JSON معتبر نیست: ${error.message}`;
      else if (error instanceof ApiError) setErrors(error);
      else generalError.textContent = error instanceof Error ? error.message : safeText(error);
    } finally {
      setSubmitting(false);
    }
  });
  form.addEventListener('input', event => {
    const control = event.target as HTMLElement;
    const name = control.getAttribute('name');
    if (!name || control.getAttribute('aria-invalid') !== 'true') return;
    control.removeAttribute('aria-invalid');
    const message = form.querySelector<HTMLElement>(`.field-error[data-field="${CSS.escape(name)}"]`);
    if (message) message.textContent = '';
  });
  return { element: form, setErrors, setSubmitting };
}

export function openSchemaDialog(options: {
  title: string;
  schema: ContractSchema;
  initial?: Record<string, unknown>;
  multipart?: boolean;
  submitLabel: string;
  onSubmit: (payload: Record<string, unknown> | FormData) => Promise<void>;
}): HTMLDialogElement {
  const titleId = `dialog-title-${Math.random().toString(36).slice(2)}`;
  const dialog = h('dialog', { className: 'dialog dialog--wide', 'aria-labelledby': titleId }) as HTMLDialogElement;
  let dirty = false;
  const requestClose = async (): Promise<void> => {
    if (dirty && !await confirmDialog({ title: 'تغییرات ذخیره‌نشده', message: 'اطلاعات واردشده ذخیره نشده‌اند. فرم بسته شود؟', confirmLabel: 'بستن فرم', dangerous: true })) return;
    dirty = false;
    dialog.close();
  };
  const close = h('button', { className: 'icon-button', type: 'button', 'aria-label': 'بستن', onClick: () => void requestClose() }, icon('close'));
  const form = createSchemaForm({ ...options, onSubmit: async payload => { await options.onSubmit(payload); dirty = false; dialog.close(); } });
  form.element.addEventListener('input', () => { dirty = true; });
  form.element.addEventListener('change', () => { dirty = true; });
  dialog.append(h('div', { className: 'dialog__body dialog__body--wide' }, h('div', { className: 'dialog__header' }, h('h2', { id: titleId, text: options.title }), close), form.element));
  dialog.addEventListener('cancel', event => { event.preventDefault(); void requestClose(); });
  dialog.addEventListener('close', () => dialog.remove(), { once: true });
  document.body.append(dialog);
  dialog.showModal();
  return dialog;
}
