import { formatNumber, h } from '../utils/dom.js';

export interface HeatmapCell {
  label: string;
  value: number | null;
}

export interface HeatmapRow {
  label: string;
  detail?: string;
  cells: HeatmapCell[];
}

function bucket(value: number | null, max: number): number {
  if (value === null || !Number.isFinite(value)) return -1;
  const ratio = Math.max(0, Math.min(1, value / Math.max(max, 1)));
  return Math.min(4, Math.floor(ratio * 5));
}

export function heatmap(options: {
  title: string;
  rows: HeatmapRow[];
  columns: string[];
  max?: number;
  rowLimit?: number;
}): HTMLElement {
  const max = options.max ?? 20;
  const rows = options.rows.slice(0, options.rowLimit ?? 10);
  if (!rows.length || !options.columns.length) {
    return h('div', { className: 'chart-empty', role: 'status', text: 'داده کافی برای نقشه حرارتی وجود ندارد.' });
  }

  return h('figure', { className: 'chart-figure heatmap-figure' },
    h('div', { className: 'heatmap-scroll', tabindex: '0', role: 'region', 'aria-label': options.title },
      h('table', { className: 'heatmap-table' },
        h('thead', {}, h('tr', {}, h('th', { scope: 'col', text: 'دانش‌آموز' }), ...options.columns.map(column => h('th', { scope: 'col', text: column })))),
        h('tbody', {}, ...rows.map(row => h('tr', {},
          h('th', { scope: 'row' }, h('strong', { text: row.label }), row.detail ? h('small', { text: row.detail }) : null),
          ...options.columns.map((column, index) => {
            const cell = row.cells[index];
            const value = cell?.value ?? null;
            const level = bucket(value, max);
            return h('td', {
              className: `heatmap-cell ${level < 0 ? 'is-missing' : `heatmap-cell--${level}`}`,
              title: `${column}: ${value === null ? 'بدون داده' : `${formatNumber(value, 2)} از ${formatNumber(max)}`}`,
              'aria-label': `${row.label}، ${column}: ${value === null ? 'بدون داده' : `${formatNumber(value, 2)} از ${formatNumber(max)}`}`,
              text: value === null ? '—' : formatNumber(value, 1),
            });
          }),
        ))),
      ),
    ),
    h('div', { className: 'heatmap-scale', 'aria-hidden': 'true' },
      h('span', { text: 'ضعیف‌تر' }),
      ...[0, 1, 2, 3, 4].map(level => h('i', { className: `heatmap-cell--${level}` })),
      h('span', { text: 'قوی‌تر' }),
    ),
    h('figcaption', { className: 'sr-only', text: options.title }),
  );
}
