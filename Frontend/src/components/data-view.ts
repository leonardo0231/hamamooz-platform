import { h } from '../utils/dom.js';
import { badgeTone, formatFieldValue, isTechnicalField, isTechnicalValue, labelForField, labelForValue, recordTitle } from '../ui/presentation.js';
import { icon } from './icons.js';

const statusFields = new Set(['status', 'status_display', 'severity', 'scope', 'gender', 'role', 'role_display', 'import_type', 'report_type', 'excuse_status', 'relationship']);

function primitiveNode(field: string, value: unknown): HTMLElement {
  const text = formatFieldValue(field, value);
  if (typeof value === 'boolean' || statusFields.has(field)) {
    return h('span', { className: `badge badge--${badgeTone(value)}`, text });
  }
  return h('span', { className: 'detail-value', text, title: text, tabindex: text.length > 45 ? '0' : undefined });
}

function primitiveList(_field: string, values: unknown[]): HTMLElement {
  if (!values.length) return h('span', { className: 'muted', text: 'موردی ثبت نشده است.' });
  return h('div', { className: 'chip-list' }, ...values.map(value => h('span', { className: 'data-chip', text: labelForValue(value) })));
}

function tableForObjects(values: Record<string, unknown>[]): HTMLElement {
  if (!values.length) return h('span', { className: 'muted', text: 'موردی ثبت نشده است.' });
  const preferred = ['student_name', 'full_name', 'title', 'name', 'class_title', 'status', 'value', 'score', 'created_at', 'updated_at'];
  const keys = [...new Set(values.flatMap(value => Object.keys(value).filter(key => !isTechnicalField(key))))];
  const columns = [...preferred.filter(key => keys.includes(key)), ...keys.filter(key => !preferred.includes(key))].slice(0, 8);
  if (!columns.length) return h('div', { className: 'compact-list' }, ...values.map(value => h('div', { className: 'compact-list__item compact-list__item--static' }, h('strong', { text: recordTitle(value) }))));
  const head = h('thead', {}, h('tr', {}, ...columns.map(column => h('th', { scope: 'col', text: labelForField(column) }))));
  const body = h('tbody', {}, ...values.slice(0, 200).map(value => {
    const cells = columns.map(column => h('td', { dataset: { label: labelForField(column) } }, renderValue(column, value[column], 1)));
    return h('tr', {}, ...cells);
  }));
  const table = h('table', { className: 'data-table detail-table' }, h('caption', { className: 'sr-only', text: 'جزئیات فهرست' }), head, body);
  return h('div', { className: 'table-wrap detail-table-wrap' }, table);
}

function objectSection(value: Record<string, unknown>, depth: number): HTMLElement {
  const entries = Object.entries(value);
  const regular = entries.filter(([key, item]) => !isTechnicalValue(key, item));
  const technical = entries.filter(([key, item]) => isTechnicalValue(key, item));
  const grid = h('dl', { className: `detail-grid detail-grid--viewer${depth > 0 ? ' detail-grid--nested' : ''}` },
    ...regular.map(([key, item]) => h('div', { className: item && typeof item === 'object' ? 'detail-field detail-field--wide' : 'detail-field' },
      h('dt', { text: labelForField(key) }),
      h('dd', {}, renderValue(key, item, depth + 1)),
    )),
  );
  if (!technical.length) return grid;
  const technicalDetails = h('details', { className: 'technical-details' },
    h('summary', {}, icon('settings'), 'جزئیات فنی'),
    h('dl', { className: 'detail-grid detail-grid--technical' }, ...technical.map(([key, item]) => h('div', {}, h('dt', { text: labelForField(key) }), h('dd', { className: 'ltr' }, primitiveNode(key, item))))),
  );
  return h('div', { className: 'structured-detail' }, grid, technicalDetails);
}

export function renderValue(field: string, value: unknown, depth = 0): HTMLElement {
  if (value === null || value === undefined || value === '') return primitiveNode(field, value);
  if (Array.isArray(value)) {
    if (value.every(item => item === null || ['string', 'number', 'boolean'].includes(typeof item))) return primitiveList(field, value);
    const objects = value.filter((item): item is Record<string, unknown> => Boolean(item) && typeof item === 'object' && !Array.isArray(item));
    if (objects.length === value.length) return tableForObjects(objects);
    return h('div', { className: 'nested-list' }, ...value.map((item, index) => h('section', { className: 'nested-item' }, h('h4', { text: `${labelForField(field)} ${index + 1}` }), renderValue(field, item, depth + 1))));
  }
  if (typeof value === 'object') {
    if (depth >= 3) return h('span', { className: 'muted', text: formatFieldValue(field, value) });
    return objectSection(value as Record<string, unknown>, depth);
  }
  return primitiveNode(field, value);
}

export function renderDataView(data: unknown): HTMLElement {
  if (Array.isArray(data)) return renderValue('items', data);
  if (data && typeof data === 'object') return objectSection(data as Record<string, unknown>, 0);
  return h('div', { className: 'detail-empty' }, renderValue('value', data));
}

export function openDataDialog(title: string, data: unknown, description?: string): HTMLDialogElement {
  const titleId = `data-dialog-title-${Math.random().toString(36).slice(2)}`;
  const dialog = h('dialog', { className: 'dialog dialog--wide data-dialog', 'aria-labelledby': titleId }) as HTMLDialogElement;
  const close = h('button', { className: 'icon-button', type: 'button', 'aria-label': 'بستن', title: 'بستن', onClick: () => dialog.close() }, icon('close'));
  dialog.append(h('div', { className: 'dialog__body dialog__body--wide' },
    h('div', { className: 'dialog__header' }, h('div', {}, h('h2', { id: titleId, text: title }), description ? h('p', { text: description }) : null), close),
    h('div', { className: 'data-view' }, renderDataView(data)),
  ));
  dialog.addEventListener('close', () => dialog.remove(), { once: true });
  document.body.append(dialog);
  dialog.showModal();
  return dialog;
}
