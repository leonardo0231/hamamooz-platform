import { html } from '../core/view.js';

function points(values, width, height, padding = 22) {
  const min = Math.min(...values) - 1;
  const max = Math.max(...values) + 1;
  return values.map((value, index) => {
    const x = padding + (index * (width - padding * 2)) / Math.max(1, values.length - 1);
    const y = height - padding - ((value - min) / Math.max(1, max - min)) * (height - padding * 2);
    return { x, y, value };
  });
}

export function LineChart({ values, labels = [], color = '#6936f5', title = 'نمودار روند' }) {
  const width = 680; const height = 250; const plotted = points(values, width, height, 30);
  const line = plotted.map(point => `${point.x},${point.y}`).join(' ');
  const area = `30,${height - 30} ${line} ${width - 30},${height - 30}`;
  return html`<div class="chart"><svg viewBox=${`0 0 ${width} ${height}`} role="img" aria-label=${title} preserveAspectRatio="none">
    <defs><linearGradient id="line-area" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color=${color} stop-opacity=".22"/><stop offset="1" stop-color=${color} stop-opacity="0"/></linearGradient></defs>
    ${[45, 95, 145, 195].map(y => html`<line x1="30" y1=${y} x2=${width - 30} y2=${y} class="chart__grid" />`)}
    <polygon points=${area} fill="url(#line-area)" />
    <polyline points=${line} fill="none" stroke=${color} stroke-width="4" stroke-linecap="round" stroke-linejoin="round" vector-effect="non-scaling-stroke" />
    ${plotted.map((point, index) => html`<g key=${index}><circle cx=${point.x} cy=${point.y} r="6" fill="white" stroke=${color} stroke-width="3" vector-effect="non-scaling-stroke"/><text x=${point.x} y=${point.y - 14} text-anchor="middle" class="chart__value">${String(point.value).replace('.', '٫')}</text><text x=${point.x} y=${height - 7} text-anchor="middle" class="chart__label">${labels[index] ?? ''}</text></g>`)}
  </svg><table class="sr-only"><caption>${title}</caption><tbody>${values.map((value, index) => html`<tr><th>${labels[index]}</th><td>${value}</td></tr>`)}</tbody></table></div>`;
}

export function BarChart({ items, color = '#bf27b8', title = 'نمودار مقایسه‌ای' }) {
  const max = Math.max(...items.map(item => item.value), 20);
  return html`<div class="bar-chart" role="img" aria-label=${title}>${items.map(item => html`<div class="bar-chart__item"><strong>${String(item.value).replace('.', '٫')}</strong><div class="bar-chart__track"><span style=${`height:${Math.max(12, (item.value / max) * 100)}%;background:${color}`}></span></div><small>${item.label}</small></div>`)}</div>`;
}
