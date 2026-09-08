import { html } from '../core/view.js';

/*
 * Report charts are deliberately rendered by the React component tree as
 * inline SVG/HTML. The report is a printable document, so an imperative
 * canvas/chart runtime would make the printed result depend on load timing,
 * font availability, or a second rendering engine. Keeping the small chart
 * primitives here also means the same DOM is used on screen and in the
 * browser's A3 print preview.
 */

const fa = value => {
  const numeric = Number(value);
  return Number.isFinite(numeric)
    ? new Intl.NumberFormat('fa-IR', { maximumFractionDigits: 0 }).format(numeric)
    : '—';
};
const numeric = value => value !== null && value !== undefined && value !== '' && Number.isFinite(Number(value))
  ? Number(value) : null;
const clamp = (value, min = 0, max = 100) => {
  const result = numeric(value);
  return result === null ? null : Math.max(min, Math.min(max, result));
};

function formatMetricValue(value) {
  return fa(value);
}

function chartShell({ label, className, children }) {
  return html`<div class=${`echart ${className}`} role="img" aria-label=${label} data-chart-renderer="svg">${children}</div>`;
}

function pointAt(index, count, width, height, padding, value, min, max) {
  const x = count <= 1
    ? width / 2
    : padding.left + ((width - padding.left - padding.right) * index) / (count - 1);
  const ratio = max === min ? .5 : (max - value) / (max - min);
  const y = padding.top + ratio * (height - padding.top - padding.bottom);
  return { x, y };
}

function lineSegments(values, width, height, padding, min, max) {
  const points = values.map((value, index) => {
    const result = numeric(value);
    return result === null ? null : pointAt(index, values.length, width, height, padding, result, min, max);
  });
  const segments = [];
  let current = [];
  points.forEach(point => {
    if (point) current.push(point);
    else if (current.length) { segments.push(current); current = []; }
  });
  if (current.length) segments.push(current);
  return { points, segments };
}

function linePath(points) {
  return points.map((point, index) => `${index ? 'L' : 'M'} ${point.x.toFixed(2)} ${point.y.toFixed(2)}`).join(' ');
}

function TrendChart({ option, label, className }) {
  const width = 720;
  const height = 240;
  const padding = { top: 18, right: 24, bottom: 45, left: 52 };
  const values = option.series?.[0]?.data ?? [];
  const labels = option.xAxis?.data ?? [];
  const min = numeric(option.yAxis?.min) ?? 0;
  const max = numeric(option.yAxis?.max) ?? 20;
  const ticks = Array.from({ length: 5 }, (_, index) => min + ((max - min) * index) / 4).reverse();
  const { points, segments } = lineSegments(values, width, height, padding, min, max);
  const first = points.find(Boolean);
  const last = [...points].reverse().find(Boolean);
  const area = first && last && segments.length === 1
    ? `${linePath(segments[0])} L ${last.x.toFixed(2)} ${(height - padding.bottom).toFixed(2)} L ${first.x.toFixed(2)} ${(height - padding.bottom).toFixed(2)} Z`
    : '';
  return chartShell({ label, className, children: html`<svg class="echart__svg echart__svg--trend" viewBox=${`0 0 ${width} ${height}`} preserveAspectRatio="xMidYMid meet" focusable="false" aria-hidden="true">
    <title>${label}</title>
    ${ticks.map((tick, index) => {
      const y = padding.top + ((height - padding.top - padding.bottom) * index) / 4;
      return html`<g key=${`trend-grid-${index}`}><line x1=${padding.left} y1=${y} x2=${width - padding.right} y2=${y} stroke="#dce8e5" stroke-dasharray="4 5" vector-effect="non-scaling-stroke"/><text x=${padding.left - 10} y=${y + 4} text-anchor="end" fill="#55716e" font-size="14" font-family="Vazirmatn">${fa(tick)}</text></g>`;
    })}
    <line x1=${padding.left} y1=${height - padding.bottom} x2=${width - padding.right} y2=${height - padding.bottom} stroke="#b9ceca" vector-effect="non-scaling-stroke"/>
    ${area && html`<path d=${area} fill="rgba(15,118,110,.14)" stroke="none"/>`}
    ${segments.map((segment, index) => html`<path key=${`trend-segment-${index}`} d=${linePath(segment)} fill="none" stroke="#0f766e" stroke-width="4" stroke-linecap="round" stroke-linejoin="round" vector-effect="non-scaling-stroke"/>`)}
    ${points.map((point, index) => point && html`<g key=${`trend-point-${index}`}><circle cx=${point.x} cy=${point.y} r="7" fill="#0f766e" stroke="#fff" stroke-width="3" vector-effect="non-scaling-stroke"><title>${labels[index] ?? ''}: ${fa(values[index])} از ۲۰</title></circle><text x=${point.x} y=${point.y - 14} text-anchor="middle" fill="#0d605d" font-size="14" font-weight="700" font-family="Vazirmatn">${fa(values[index])}</text></g>`)}
    ${labels.map((item, index) => {
      const point = pointAt(index, labels.length, width, height, padding, min, min, max);
      return html`<text key=${`trend-label-${index}`} x=${point.x} y=${height - 15} text-anchor="middle" fill="#55716e" font-size="14" font-family="Vazirmatn">${item}</text>`;
    })}
  </svg>`});
}

function radarPoint(index, count, cx, cy, radius, value = 100) {
  const angle = -Math.PI / 2 + (index * Math.PI * 2) / count;
  const scale = (clamp(value) ?? 0) / 100;
  return { x: cx + Math.cos(angle) * radius * scale, y: cy + Math.sin(angle) * radius * scale };
}

function radarRing(count, cx, cy, radius, scale) {
  return Array.from({ length: count }, (_, index) => {
    const angle = -Math.PI / 2 + (index * Math.PI * 2) / count;
    return `${(cx + Math.cos(angle) * radius * scale).toFixed(2)},${(cy + Math.sin(angle) * radius * scale).toFixed(2)}`;
  }).join(' ');
}

function radarSegments(values, count, cx, cy, radius) {
  const points = values.map((value, index) => numeric(value) === null ? null : radarPoint(index, count, cx, cy, radius, value));
  const segments = [];
  let current = [];
  points.forEach(point => {
    if (point) current.push(point);
    else if (current.length) { segments.push(current); current = []; }
  });
  if (current.length) segments.push(current);

  // A segment that crosses the end of the circular list is still contiguous.
  // Rendering it separately keeps an unavailable domain from being treated as
  // a zero score while preserving the shape for complete data.
  if (segments.length > 1 && points[0] && points.at(-1)) {
    const first = segments.shift();
    const last = segments.pop();
    segments.unshift([...last, ...first]);
  }
  return { points, segments };
}

function RadarChart({ option, label, className }) {
  const indicators = option.radar?.indicator ?? [];
  const values = option.series?.[0]?.data?.[0]?.value ?? [];
  const width = 520;
  const height = 260;
  const cx = width / 2;
  const cy = 126;
  const radius = 94;
  const { points, segments } = radarSegments(values, indicators.length, cx, cy, radius);
  const hasData = points.some(Boolean);
  return chartShell({ label, className, children: html`<svg class="echart__svg echart__svg--radar" viewBox=${`0 0 ${width} ${height}`} preserveAspectRatio="xMidYMid meet" focusable="false" aria-hidden="true">
    <title>${label}</title>
    ${[.25, .5, .75, 1].map(scale => html`<polygon key=${`radar-ring-${scale}`} points=${radarRing(indicators.length, cx, cy, radius, scale)} fill=${scale === 1 ? '#f2faf8' : 'none'} stroke="#bfd7d2" stroke-width="1" vector-effect="non-scaling-stroke"/>`)}
    ${indicators.map((item, index) => {
      const edge = radarPoint(index, indicators.length, cx, cy, radius, 100);
      const available = points[index] !== null;
      const markerColor = available ? '#0e7490' : '#748584';
      return html`<g key=${`radar-axis-${index}`}><line x1=${cx} y1=${cy} x2=${edge.x} y2=${edge.y} stroke="#d4e4e0" stroke-width="1" vector-effect="non-scaling-stroke"/><circle cx=${edge.x} cy=${edge.y} r="11" fill=${available ? '#eef8f7' : '#f1f5f4'} stroke=${available ? '#0e7490' : '#aab8b7'} stroke-width="1" vector-effect="non-scaling-stroke"><title>${item.title ?? item.name}: ${available ? `${fa(values[index])}٪` : 'ثبت نشده'}</title></circle><text x=${edge.x} y=${edge.y + 4} text-anchor="middle" fill=${markerColor} font-size="12" font-weight="900" font-family="Vazirmatn">${fa(index + 1)}</text></g>`;
    })}
    ${hasData && segments.length === 1 && points.every(Boolean) && html`<polygon points=${points.map(point => `${point.x.toFixed(2)},${point.y.toFixed(2)}`).join(' ')} fill="rgba(14,116,144,.22)" stroke="none"/>`}
    ${segments.map((segment, index) => html`<path key=${`radar-segment-${index}`} d=${linePath(segment)} fill="none" stroke="#0e7490" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" vector-effect="non-scaling-stroke"/>`)}
    ${points.map((point, index) => point && html`<circle key=${`radar-point-${index}`} cx=${point.x} cy=${point.y} r="5" fill="#0e7490" stroke="#fff" stroke-width="2" vector-effect="non-scaling-stroke"><title>${indicators[index]?.title ?? indicators[index]?.name}: ${fa(values[index])}٪</title></circle>`)}
  </svg><div class="report-radar-legend" aria-label="راهنمای شماره‌گذاری ارزیابی مهارت‌ها">${indicators.map((item, index) => {
    const value = numeric(values[index]);
    const available = value !== null;
    const text = available ? `${formatMetricValue(value)}٪` : 'ثبت نشده';
    return html`<span key=${`radar-legend-${index}`} class=${available ? 'is-available' : 'is-missing'} aria-label=${`${item.title ?? item.name}: ${text}`}><i>${index + 1}</i><em>${item.title ?? item.name}</em><b>${text}</b></span>`;
  })}</div>`});
}

function BarsChart({ option, label, className }) {
  const barSeries = option.series?.[0] ?? {};
  const names = option.yAxis?.data ?? [];
  const values = barSeries.data ?? [];
  const color = barSeries.itemStyle?.color ?? '#08766f';
  return chartShell({ label, className, children: html`<div class="report-metric-bars" data-chart-type="bars">${names.map((name, index) => {
    const value = clamp(values[index]);
    const valueLabel = value === null ? 'ثبت نشده' : `${formatMetricValue(value)}٪`;
    return html`<div class="report-metric-bar" key=${`metric-bar-${index}`}><div class="report-metric-bar__head"><span>${name}</span><b>${valueLabel}</b></div><div class="report-metric-bar__track" role="presentation"><i style=${value === null ? `width:0%;background:${color}` : `width:${value}%;background:${color}`}></i></div></div>`;
  })}</div>`});
}

/**
 * Compatibility component for the report's existing chart call sites. The
 * name is retained to keep the report API stable, but no chart is delegated
 * to canvas or a second server renderer.
 */
export function EChart({ option, label, className = '', emptyLabel = 'داده کافی نیست' }) {
  if (!option) return html`<div class=${`echart echart--empty ${className}`} role="img" aria-label=${label ?? emptyLabel}>${emptyLabel}</div>`;
  const seriesType = option.series?.[0]?.type;
  if (seriesType === 'bar') return html`<${BarsChart} option=${option} label=${label} className=${className}/>`;
  if (option.radar?.indicator?.length) return html`<${RadarChart} option=${option} label=${label} className=${className}/>`;
  if (seriesType === 'line') return html`<${TrendChart} option=${option} label=${label} className=${className}/>`;
  return html`<div class=${`echart echart--empty ${className}`} role="img" aria-label=${label ?? emptyLabel}>${emptyLabel}</div>`;
}

export { formatMetricValue };
