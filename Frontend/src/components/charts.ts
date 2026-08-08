import { formatNumber, h } from '../utils/dom.js';

export interface ChartPoint {
  label: string;
  value: number | null;
  detail?: string;
}

const SVG_NS = 'http://www.w3.org/2000/svg';

function svg<K extends keyof SVGElementTagNameMap>(tag: K, attributes: Record<string, string | number> = {}): SVGElementTagNameMap[K] {
  const element = document.createElementNS(SVG_NS, tag);
  for (const [name, value] of Object.entries(attributes)) element.setAttribute(name, String(value));
  return element;
}

function accessibleValues(points: ChartPoint[], valueSuffix = ''): HTMLElement {
  return h('dl', { className: 'chart-values' }, ...points.flatMap(point => [
    h('div', { className: 'chart-values__item' },
      h('dt', { text: point.label }),
      h('dd', {}, h('strong', { text: point.value === null ? '—' : `${formatNumber(point.value, 2)}${valueSuffix}` }), point.detail ? h('small', { text: point.detail }) : null),
    ),
  ]));
}

export function lineChart(options: {
  title: string;
  points: ChartPoint[];
  min?: number;
  max?: number;
  valueSuffix?: string;
}): HTMLElement {
  const points = options.points.filter(point => point.value !== null && Number.isFinite(point.value));
  if (points.length < 2) {
    return h('div', { className: 'chart-empty', role: 'status' },
      h('strong', { text: 'برای رسم روند داده کافی نیست' }),
      h('p', { text: 'حداقل دو نقطه معتبر برای نمایش روند لازم است.' }),
      accessibleValues(options.points, options.valueSuffix ?? ''),
    );
  }

  const width = 720;
  const height = 270;
  const paddingX = 42;
  const paddingTop = 24;
  const paddingBottom = 42;
  const values = points.map(point => point.value ?? 0);
  const rawMin = Math.min(...values);
  const rawMax = Math.max(...values);
  const min = options.min ?? Math.min(0, rawMin);
  const max = options.max ?? (rawMax === min ? min + 1 : rawMax);
  const range = Math.max(max - min, 1);
  const chartWidth = width - paddingX * 2;
  const chartHeight = height - paddingTop - paddingBottom;
  const x = (index: number): number => paddingX + (points.length === 1 ? chartWidth / 2 : chartWidth * index / (points.length - 1));
  const y = (value: number): number => paddingTop + chartHeight - ((value - min) / range * chartHeight);

  const root = svg('svg', {
    viewBox: `0 0 ${width} ${height}`,
    class: 'native-chart native-chart--line',
    role: 'img',
    'aria-label': options.title,
    preserveAspectRatio: 'xMidYMid meet',
  });
  root.append(svg('title'));
  root.querySelector('title')!.textContent = options.title;

  for (let step = 0; step <= 4; step += 1) {
    const value = min + (range * step / 4);
    const gridY = y(value);
    root.append(svg('line', { x1: paddingX, y1: gridY, x2: width - paddingX, y2: gridY, class: 'native-chart__grid' }));
    const label = svg('text', { x: paddingX - 8, y: gridY + 4, class: 'native-chart__axis-label', 'text-anchor': 'end' });
    label.textContent = formatNumber(value, 1);
    root.append(label);
  }

  const coordinates = points.map((point, index) => `${x(index)},${y(point.value ?? 0)}`).join(' ');
  root.append(svg('polyline', { points: coordinates, class: 'native-chart__line', fill: 'none' }));
  points.forEach((point, index) => {
    const cx = x(index);
    const cy = y(point.value ?? 0);
    const dot = svg('circle', { cx, cy, r: 5, class: 'native-chart__point', tabindex: '0' });
    const title = svg('title');
    title.textContent = `${point.label}: ${formatNumber(point.value, 2)}${options.valueSuffix ?? ''}`;
    dot.append(title);
    root.append(dot);
    const label = svg('text', { x: cx, y: height - 14, class: 'native-chart__axis-label native-chart__axis-label--x', 'text-anchor': 'middle' });
    label.textContent = point.label;
    root.append(label);
  });

  return h('figure', { className: 'chart-figure' }, root, h('figcaption', { className: 'sr-only', text: options.title }), accessibleValues(options.points, options.valueSuffix ?? ''));
}

export function horizontalBarChart(options: {
  title: string;
  points: ChartPoint[];
  max?: number;
  valueSuffix?: string;
  limit?: number;
}): HTMLElement {
  const limit = options.limit ?? options.points.length;
  const rows = options.points.slice(0, limit);
  const values = rows.map(point => point.value ?? 0).filter(Number.isFinite);
  const max = Math.max(options.max ?? 0, ...values, 1);
  if (!rows.length) return h('div', { className: 'chart-empty', role: 'status', text: 'داده‌ای برای مقایسه وجود ندارد.' });

  return h('figure', { className: 'chart-figure chart-figure--bars', 'aria-label': options.title },
    h('div', { className: 'native-bars', role: 'list' }, ...rows.map(point => {
      const value = point.value ?? 0;
      const percent = Math.max(0, Math.min(100, value / max * 100));
      return h('div', { className: `native-bars__row ${point.value === null ? 'is-missing' : ''}`, role: 'listitem' },
        h('div', { className: 'native-bars__label' }, h('strong', { text: point.label }), point.detail ? h('small', { text: point.detail }) : null),
        h('div', {
          className: 'native-bars__track',
          role: 'progressbar',
          'aria-label': point.label,
          'aria-valuemin': '0',
          'aria-valuemax': String(max),
          'aria-valuenow': point.value === null ? undefined : String(value),
          'aria-valuetext': point.value === null ? 'بدون داده' : `${formatNumber(value, 2)}${options.valueSuffix ?? ''}`,
        }, h('i', { style: { width: `${percent}%` } })),
        h('strong', { className: 'native-bars__value', text: point.value === null ? '—' : `${formatNumber(value, 2)}${options.valueSuffix ?? ''}` }),
      );
    })),
    h('figcaption', { className: 'sr-only', text: options.title }),
  );
}

export function distributionChart(options: {
  title: string;
  values: Record<string, number>;
  labels?: Record<string, string>;
}): HTMLElement {
  const rows = Object.entries(options.values).map(([key, value]) => ({ key, label: options.labels?.[key] ?? key, value }));
  const total = rows.reduce((sum, row) => sum + row.value, 0);
  if (!rows.length || total === 0) return h('div', { className: 'chart-empty', role: 'status', text: 'توزیع عملکرد هنوز داده‌ای ندارد.' });
  return h('figure', { className: 'chart-figure distribution-chart', 'aria-label': options.title },
    h('div', { className: 'distribution-chart__track', role: 'img', 'aria-label': `${options.title}؛ مجموع ${formatNumber(total)} مورد` },
      ...rows.filter(row => row.value > 0).map((row, index) => h('i', {
        className: `distribution-chart__segment distribution-chart__segment--${index % 5}`,
        style: { width: `${row.value / total * 100}%` },
        title: `${row.label}: ${formatNumber(row.value)}`,
      })),
    ),
    h('div', { className: 'distribution-chart__legend' }, ...rows.map((row, index) => h('div', { className: 'distribution-chart__legend-item' },
      h('span', { className: `distribution-chart__dot distribution-chart__dot--${index % 5}`, 'aria-hidden': 'true' }),
      h('span', { text: row.label }),
      h('strong', { text: formatNumber(row.value) }),
    ))),
    h('figcaption', { className: 'sr-only', text: options.title }),
  );
}

export function radarChart(options: {
  title: string;
  points: ChartPoint[];
  max?: number;
}): HTMLElement {
  const rows = options.points.filter(point => point.value !== null && Number.isFinite(point.value));
  if (rows.length < 3) {
    return h('div', { className: 'chart-empty', role: 'status' },
      h('strong', { text: 'داده کافی برای نمودار حوزه‌ها وجود ندارد' }),
      accessibleValues(options.points),
    );
  }
  const max = Math.max(options.max ?? 5, 1);
  const size = 310;
  const center = size / 2;
  const radius = 112;
  const angle = (index: number): number => -Math.PI / 2 + (Math.PI * 2 * index / rows.length);
  const coordinate = (index: number, value: number): [number, number] => {
    const r = radius * Math.max(0, Math.min(max, value)) / max;
    return [center + Math.cos(angle(index)) * r, center + Math.sin(angle(index)) * r];
  };
  const outer = (index: number, r = radius): [number, number] => [center + Math.cos(angle(index)) * r, center + Math.sin(angle(index)) * r];
  const root = svg('svg', { viewBox: `0 0 ${size} ${size}`, class: 'native-chart native-chart--radar', role: 'img', 'aria-label': options.title });
  const title = svg('title');
  title.textContent = options.title;
  root.append(title);

  for (let step = 1; step <= 5; step += 1) {
    const r = radius * step / 5;
    root.append(svg('polygon', { points: rows.map((_, index) => outer(index, r).join(',')).join(' '), class: 'native-chart__radar-grid' }));
  }
  rows.forEach((_, index) => {
    const [x, y] = outer(index);
    root.append(svg('line', { x1: center, y1: center, x2: x, y2: y, class: 'native-chart__radar-axis' }));
  });
  const dataPoints = rows.map((point, index) => coordinate(index, point.value ?? 0));
  root.append(svg('polygon', { points: dataPoints.map(point => point.join(',')).join(' '), class: 'native-chart__radar-area' }));
  dataPoints.forEach(([cx, cy], index) => {
    const point = rows[index]!;
    const dot = svg('circle', { cx, cy, r: 4.5, class: 'native-chart__point', tabindex: '0' });
    const dotTitle = svg('title');
    dotTitle.textContent = `${point.label}: ${formatNumber(point.value, 2)} از ${formatNumber(max)}`;
    dot.append(dotTitle);
    root.append(dot);
  });

  return h('figure', { className: 'chart-figure chart-figure--radar' },
    root,
    h('figcaption', { className: 'sr-only', text: options.title }),
    accessibleValues(options.points, ` از ${formatNumber(max)}`),
  );
}
