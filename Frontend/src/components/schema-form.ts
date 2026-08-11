import { apiRequest } from '../api/client.js';
import { operationsForTag, resolveSchema, type ContractOperation, type ContractSchema } from '../api/contract.js';
import type { Pagination } from '../api/types.js';
import { ApiError } from '../api/types.js';
import { debounce, h, safeText } from '../utils/dom.js';
import { labelForField, labelForValue, recordTitle } from '../ui/presentation.js';
import { icon } from './icons.js';
import { confirmDialog } from './feedback.js';

interface FieldControl {
  wrapper: HTMLElement;
  read: () => unknown;
  input: HTMLElement;
  ready?: Promise<void>;
}

const relationTags: Record<string, string> = {
  organization: 'organizations',
  school: 'schools',
  academic_year: 'academic-years',
  term: 'terms',
  grade_level: 'grade-levels',
  class_section: 'classes',
  student: 'students',
  enrollment: 'enrollments',
  guardian: 'guardians',
  teacher: 'users',
  user: 'users',
  assessment: 'assessments',
  assessment_type: 'assessment-types',
  course_offering: 'course-offerings',
  grade_subject: 'grade-subjects',
  subject: 'subjects',
  policy: 'attendance-policies',
};

function formatHint(name: string, schema: ContractSchema): string | null {
  if (schema.description) return schema.description.split('\n')[0] ?? null;
  if (relationTags[name]) return 'مورد موردنظر را با نام یا کد پیدا و انتخاب کنید.';
  if (schema.format === 'uuid') return 'شناسه فنی توسط سامانه مدیریت می‌شود.';
  if (schema.maxLength) return `حداکثر ${schema.maxLength.toLocaleString('fa-IR')} نویسه`;
  if (schema.minItems) return `حداقل ${schema.minItems.toLocaleString('fa-IR')} مورد`;
  return null;
}

function listOperationFor(tag: string): ContractOperation | undefined {
  return operationsForTag(tag).find(operation => operation.method === 'GET' && !operation.path.includes('{id}') && !operation.path.match(/\/(summary|preview|evaluate|student|class|school)\/$/));
}

function relationControl(name: string, schema: ContractSchema, initial: unknown, required: boolean, path: string): FieldControl | null {
  const tag = relationTags[name];
  if (!tag) return null;
  const operation = listOperationFor(tag);
  if (!operation) return null;
  const id = `field-${path.replaceAll('.', '-')}-${Math.random().toString(36).slice(2)}`;
  const hintId = `${id}-hint`;
  const errorId = `${id}-error`;
  const label = h('label', { for: id }, labelForField(name, schema), required ? h('span', { className: 'required-mark', text: ' *' }) : null);
  const hint = formatHint(name, schema);
  const search = h('input', { className: 'relation-search', type: 'search', placeholder: `جست‌وجوی ${labelForField(name, schema)}`, 'aria-label': `جست‌وجوی ${labelForField(name, schema)}` }) as HTMLInputElement;
  const select = h('select', { id, name: path, required, disabled: true, 'aria-describedby': `${hint ? hintId : ''} ${errorId}`.trim() },
    h('option', { value: '', text: 'در حال دریافت گزینه‌ها…' }),
  ) as HTMLSelectElement;
  let records: Record<string, unknown>[] = [];
  let requestVersion = 0;
  let selectedValue = initial === null || initial === undefined ? '' : String(initial);
  const supportsSearch = operation.parameters.some(parameter => parameter.in === 'query' && parameter.name === 'search');

  const renderOptions = (query = ''): void => {
    const normalized = query.trim().toLocaleLowerCase('fa-IR');
    const filtered = normalized
      ? records.filter(record => recordTitle(record).toLocaleLowerCase('fa-IR').includes(normalized))
      : records;
    const current = selectedValue;
    select.replaceChildren(h('option', { value: '', text: required ? 'انتخاب کنید' : 'بدون انتخاب' }));
    for (const record of filtered) {
      const value = record.id;
      if (value === null || value === undefined) continue;
      select.append(h('option', { value: String(value), text: recordTitle(record), selected: String(value) === current }));
    }
    if (current && ![...select.options].some(option => option.value === current)) {
      select.append(h('option', { value: current, text: `انتخاب فعلی — ${current.slice(0, 8)}…`, selected: true }));
    }
    select.value = current;
  };

  const load = async (searchTerm = ''): Promise<void> => {
    const version = ++requestVersion;
    select.disabled = true;
    select.replaceChildren(h('option', { value: '', text: 'در حال دریافت گزینه‌ها…' }));
    try {
      const query: Record<string, string | number> = {};
      if (operation.parameters.some(parameter => parameter.in === 'query' && parameter.name === 'page_size')) query.page_size = 200;
      if (supportsSearch && searchTerm.trim()) query.search = searchTerm.trim();
      const response = await apiRequest<Pagination<Record<string, unknown>> | Record<string, unknown>[]>(operation.path, { query });
      if (version !== requestVersion) return;
      records = Array.isArray(response) ? response : response.results;
      renderOptions(supportsSearch ? '' : search.value);
      select.setCustomValidity('');
      select.disabled = false;
    } catch {
      if (version !== requestVersion) return;
      select.replaceChildren(h('option', { value: '', text: 'دریافت گزینه‌ها ناموفق بود' }));
      select.disabled = false;
      select.setCustomValidity('فهرست گزینه‌ها دریافت نشد. صفحه را دوباره بارگذاری کنید.');
    }
  };

  search.addEventListener('input', debounce(() => {
    if (supportsSearch) void load(search.value);
    else renderOptions(search.value);
  }, 280));
  select.addEventListener('change', () => { selectedValue = select.value; select.setCustomValidity(''); });
  const ready = load();
  const wrapper = h('div', { className: 'form-field form-field--relation' },
    label,
    h('div', { className: 'relation-picker' }, search, select),
    hint ? h('small', { id: hintId, text: hint }) : null,
    h('div', { className: 'field-error', id: errorId, dataset: { field: path }, 'aria-live': 'polite' }),
  );
  return { wrapper, read: () => select.value === '' ? null : select.value, input: select, ready };
}

function primitiveControl(name: string, schema: ContractSchema, initial: unknown, required: boolean, path: string): FieldControl {
  const id = `field-${path.replaceAll('.', '-')}-${Math.random().toString(36).slice(2)}`;
  const hintId = `${id}-hint`;
  const errorId = `${id}-error`;
  const label = h('label', { for: id }, labelForField(name, schema), required ? h('span', { className: 'required-mark', text: ' *' }) : null);
  const hint = formatHint(name, schema);
  let input: HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement;
  let read: () => unknown;

  if (schema.enum?.length) {
    input = h('select', { id, name: path, required }, h('option', { value: '', text: 'انتخاب کنید' }), ...schema.enum.map(value => h('option', { value: String(value), text: labelForValue(value), selected: initial === value }))) as HTMLSelectElement;
    read = () => input.value === '' ? null : input.value;
  } else if (schema.type === 'boolean') {
    input = h('input', { id, name: path, type: 'checkbox', checked: initial === undefined ? Boolean(schema.default) : Boolean(initial), 'aria-describedby': `${hint ? hintId : ''} ${errorId}`.trim() }) as HTMLInputElement;
    read = () => (input as HTMLInputElement).checked;
    const wrapper = h('div', { className: 'form-field form-field--checkbox' }, input, label, hint ? h('small', { id: hintId, text: hint }) : null, h('div', { className: 'field-error', id: errorId, dataset: { field: path }, 'aria-live': 'polite' }));
    return { wrapper, read, input };
  } else if (schema.format === 'binary') {
    input = h('input', { id, name: path, type: 'file', required }) as HTMLInputElement;
    read = () => (input as HTMLInputElement).files?.[0] ?? null;
  } else {
    const multiline = ['description', 'note', 'notes', 'reason', 'error_message'].includes(name) || (schema.maxLength ?? 0) > 300;
    const type = schema.format === 'date' ? 'date'
      : schema.format === 'date-time' ? 'datetime-local'
        : schema.format === 'time' ? 'time'
          : schema.format === 'email' ? 'email'
            : schema.format === 'password' || name.includes('password') ? 'password'
              : schema.type === 'integer' || schema.type === 'number' ? 'number' : 'text';
    input = multiline
      ? h('textarea', { id, name: path, required, rows: 4, value: initial ?? '', maxLength: schema.maxLength }) as HTMLTextAreaElement
      : h('input', {
        id, name: path, type, required, value: initial ?? schema.default ?? '', min: schema.minimum, max: schema.maximum, minLength: schema.minLength, maxLength: schema.maxLength,
        step: schema.type === 'integer' ? '1' : schema.type === 'number' || schema.format === 'decimal' ? 'any' : undefined,
        autocomplete: type === 'password' ? (name === 'current_password' ? 'current-password' : 'new-password') : undefined,
        dir: schema.format === 'email' ? 'ltr' : 'auto',
      }) as HTMLInputElement;
    read = () => {
      if (input.value === '') return schema.nullable ? null : '';
      if (schema.type === 'integer') return Number.parseInt(input.value, 10);
      if (schema.type === 'number') return Number.parseFloat(input.value);
      return input.value;
    };
  }
  input.setAttribute('aria-describedby', `${hint ? hintId : ''} ${errorId}`.trim());
  return {
    wrapper: h('div', { className: 'form-field' }, label, input, hint ? h('small', { id: hintId, text: hint }) : null, h('div', { className: 'field-error', id: errorId, dataset: { field: path }, 'aria-live': 'polite' })),
    read,
    input,
  };
}

function objectControl(name: string, schema: ContractSchema, initial: unknown, _required: boolean, path: string): FieldControl {
  const properties = schema.properties ?? {};
  const requiredFields = new Set(schema.required ?? []);
  const readers = new Map<string, () => unknown>();
  const ready: Promise<void>[] = [];
  const controls: HTMLElement[] = [];
  const initialObject = initial && typeof initial === 'object' && !Array.isArray(initial) ? initial as Record<string, unknown> : {};
  for (const [childName, childSchema] of Object.entries(properties)) {
    const resolved = resolveSchema(childSchema);
    if (resolved.readOnly) continue;
    const child = inputFor(childName, childSchema, initialObject[childName], requiredFields.has(childName), `${path}.${childName}`);
    readers.set(childName, child.read);
    controls.push(child.wrapper);
    if (child.ready) ready.push(child.ready);
  }
  const fieldset = h('fieldset', { className: 'form-section', name: path, tabindex: '-1' }, h('legend', { text: labelForField(name, schema) }), h('div', { className: 'form-grid form-grid--nested' }, ...controls));
  const control: FieldControl = {
    wrapper: fieldset,
    input: fieldset,
    read: () => Object.fromEntries([...readers].map(([key, reader]) => [key, reader()])),
  };
  if (ready.length) control.ready = Promise.allSettled(ready).then(() => undefined);
  return control;
}

function arrayControl(name: string, schema: ContractSchema, initial: unknown, required: boolean, path: string): FieldControl {
  const itemSchema = resolveSchema(schema.items ?? {});
  if (itemSchema.format === 'binary') {
    const primitive = primitiveControl(name, { ...schema, type: 'string', format: 'binary' }, initial, required, path);
    const file = primitive.input as HTMLInputElement;
    file.multiple = true;
    return { ...primitive, read: () => Array.from(file.files ?? []) };
  }
  if (itemSchema.enum?.length) {
    const id = `field-${path.replaceAll('.', '-')}-${Math.random().toString(36).slice(2)}`;
    const select = h('select', { id, name: path, required, multiple: true, size: Math.min(6, itemSchema.enum.length) }, ...itemSchema.enum.map(value => h('option', { value: String(value), text: labelForValue(value), selected: Array.isArray(initial) && initial.includes(value) }))) as HTMLSelectElement;
    return {
      wrapper: h('div', { className: 'form-field' }, h('label', { for: id }, labelForField(name, schema), required ? h('span', { className: 'required-mark', text: ' *' }) : null), select, h('small', { text: 'برای انتخاب چند مورد، کلید Ctrl یا Command را نگه دارید.' }), h('div', { className: 'field-error', dataset: { field: path }, 'aria-live': 'polite' })),
      input: select,
      read: () => Array.from(select.selectedOptions, option => option.value),
    };
  }

  const rows = h('div', { className: 'repeatable-list' });
  const controllers: Array<{ container: HTMLElement; control: FieldControl }> = [];
  const minimum = Math.max(schema.minItems ?? 0, required ? 1 : 0);
  const addButton = h('button', { className: 'button button--secondary repeatable-add', type: 'button', name: path }, icon('plus'), `افزودن ${labelForField(name, schema)}`) as HTMLButtonElement;
  const updateRemoveButtons = (): void => {
    controllers.forEach(({ container }, index) => {
      const button = container.querySelector<HTMLButtonElement>('.repeatable-remove');
      if (button) button.disabled = controllers.length <= minimum;
      container.querySelector<HTMLElement>('.repeatable-index')!.textContent = `ردیف ${(index + 1).toLocaleString('fa-IR')}`;
    });
  };
  const addRow = (value?: unknown): void => {
    if (schema.maxItems !== undefined && controllers.length >= schema.maxItems) return;
    const index = controllers.length;
    const control = itemSchema.type === 'object' || itemSchema.properties
      ? objectControl(name, itemSchema, value, true, `${path}.${index}`)
      : inputFor(name, itemSchema, value, true, `${path}.${index}`);
    const container = h('div', { className: 'repeatable-row' },
      h('div', { className: 'repeatable-row__header' }, h('strong', { className: 'repeatable-index', text: `ردیف ${(index + 1).toLocaleString('fa-IR')}` }), h('button', { className: 'icon-button icon-button--danger repeatable-remove', type: 'button', title: 'حذف ردیف', 'aria-label': 'حذف ردیف' }, icon('trash'))),
      control.wrapper,
    );
    container.querySelector<HTMLButtonElement>('.repeatable-remove')?.addEventListener('click', () => {
      const found = controllers.findIndex(item => item.container === container);
      if (found < 0 || controllers.length <= minimum) return;
      controllers.splice(found, 1);
      container.remove();
      updateRemoveButtons();
    });
    controllers.push({ container, control });
    rows.append(container);
    updateRemoveButtons();
  };
  addButton.addEventListener('click', () => addRow());
  const initialItems = Array.isArray(initial) ? initial : [];
  initialItems.forEach(addRow);
  while (controllers.length < minimum) addRow();
  const wrapper = h('fieldset', { className: 'form-section form-section--repeatable' },
    h('legend', { text: labelForField(name, schema) }),
    formatHint(name, schema) ? h('small', { className: 'form-section__hint', text: formatHint(name, schema) ?? '' }) : null,
    rows,
    addButton,
    h('div', { className: 'field-error', dataset: { field: path }, 'aria-live': 'polite' }),
  );
  return {
    wrapper,
    input: addButton,
    read: () => controllers.map(item => item.control.read()),
    ready: Promise.allSettled(controllers.flatMap(item => item.control.ready ? [item.control.ready] : [])).then(() => undefined),
  };
}

function inputFor(name: string, unresolved: ContractSchema, initial: unknown, required: boolean, path = name): FieldControl {
  const schema = resolveSchema(unresolved);
  const itemSchema = schema.items ? resolveSchema(schema.items) : null;
  if (schema.type === 'array' || itemSchema) return arrayControl(name, schema, initial, required, path);
  if (schema.type === 'object' || schema.properties) return objectControl(name, schema, initial, required, path);
  const relation = relationControl(name, schema, initial, required, path);
  return relation ?? primitiveControl(name, schema, initial, required, path);
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
  const ready: Promise<void>[] = [];
  for (const [name, schema] of Object.entries(resolved.properties ?? {})) {
    const fieldSchema = resolveSchema(schema);
    if (fieldSchema.readOnly) continue;
    const field = inputFor(name, schema, options.initial?.[name], required.has(name));
    readers.set(name, field.read);
    controls.push(field.wrapper);
    if (field.ready) ready.push(field.ready);
  }
  const submit = h('button', { className: 'button button--primary', type: 'submit' }, icon('check'), options.submitLabel) as HTMLButtonElement;
  const generalError = h('div', { className: 'form-error', role: 'alert' });
  const form = h('form', { className: 'schema-form', novalidate: false }, h('div', { className: 'form-grid' }, ...controls), generalError, h('div', { className: 'form-actions' }, submit)) as HTMLFormElement;

  const setErrors = (error: ApiError): void => {
    form.querySelectorAll<HTMLElement>('.field-error').forEach(node => { node.textContent = ''; });
    form.querySelectorAll<HTMLElement>('[aria-invalid="true"]').forEach(control => control.removeAttribute('aria-invalid'));
    let firstInvalid: HTMLElement | null = null;
    for (const [field, messages] of Object.entries(error.fieldErrors)) {
      const exact = `.field-error[data-field="${CSS.escape(field)}"]`;
      const nested = `.field-error[data-field$=".${CSS.escape(field)}"]`;
      const node = form.querySelector<HTMLElement>(exact) ?? form.querySelector<HTMLElement>(nested);
      if (node) node.textContent = messages.join('، ');
      const control = form.querySelector<HTMLElement>(`[name="${CSS.escape(field)}"]`) ?? form.querySelector<HTMLElement>(`[name$=".${CSS.escape(field)}"]`);
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
    if (ready.length) await Promise.allSettled(ready);
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
      if (error instanceof ApiError) setErrors(error);
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
  const close = h('button', { className: 'icon-button', type: 'button', 'aria-label': 'بستن', title: 'بستن', onClick: () => void requestClose() }, icon('close'));
  const form = createSchemaForm({ ...options, onSubmit: async payload => { await options.onSubmit(payload); dirty = false; dialog.close(); } });
  form.element.addEventListener('input', () => { dirty = true; });
  form.element.addEventListener('change', () => { dirty = true; });
  dialog.append(h('div', { className: 'dialog__body dialog__body--wide' }, h('div', { className: 'dialog__header' }, h('div', {}, h('h2', { id: titleId, text: options.title }), h('p', { text: 'فیلدهای رابطه‌ای با نام نمایش داده می‌شوند و بخش‌های چندردیفی قابل افزودن یا حذف هستند.' })), close), form.element));
  dialog.addEventListener('cancel', event => { event.preventDefault(); void requestClose(); });
  dialog.addEventListener('close', () => dialog.remove(), { once: true });
  document.body.append(dialog);
  dialog.showModal();
  return dialog;
}
