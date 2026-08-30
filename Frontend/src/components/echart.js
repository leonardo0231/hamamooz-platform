import { html, useEffect, useRef, useState } from '../core/view.js';

let modulePromise;
const formatMetricValue = value => new Intl.NumberFormat('fa-IR', { maximumFractionDigits: 0 }).format(Number(value) || 0);

function loadECharts() {
  // The built application places this file on its own origin.  The same path
  // is served from node_modules during local development (see serve.mjs).
  modulePromise ??= import('/vendor/echarts.mjs');
  return modulePromise;
}

/**
 * A small Preact wrapper around Apache ECharts.  SVG rendering keeps labels
 * crisp at every screen size and gives the print template a faithful vector
 * visual language without coupling this Preact application to React.
 */
export function EChart({ option, label, className = '', emptyLabel = 'داده کافی نیست' }) {
  const target = useRef(null);
  const [failed, setFailed] = useState(false);
  const optionKey = JSON.stringify(option ?? {});

  useEffect(() => {
    let chart;
    let observer;
    let disposed = false;

    setFailed(false);
    void loadECharts().then(echarts => {
      if (disposed || !target.current) return;
      chart = echarts.init(target.current, null, { renderer: 'svg' });
      chart.setOption({ animation: false, ...option }, true);
      const resize = () => chart?.resize();
      if ('ResizeObserver' in window) {
        observer = new ResizeObserver(resize);
        observer.observe(target.current);
      } else {
        window.addEventListener('resize', resize);
        observer = { disconnect: () => window.removeEventListener('resize', resize) };
      }
    }).catch(() => setFailed(true));

    return () => {
      disposed = true;
      observer?.disconnect();
      chart?.dispose();
    };
  }, [optionKey]);

  if (!option) return html`<div class=${`echart echart--empty ${className}`}>${emptyLabel}</div>`;
  const barSeries = option.series?.[0]?.type === 'bar' ? option.series[0] : null;
  if (barSeries) {
    const names = option.yAxis?.data ?? [];
    const values = barSeries.data ?? [];
    const color = barSeries.itemStyle?.color ?? '#08766f';
    return html`<div class=${`echart ${className}`} role="img" aria-label=${label}><div class="report-metric-bars">${names.map((name, index) => html`<div class="report-metric-bar"><div class="report-metric-bar__head"><span>${name}</span><b>${formatMetricValue(values[index])}٪</b></div><div class="report-metric-bar__track"><i style=${`width:${Math.max(0, Math.min(100, Number(values[index]) || 0))}%;background:${color}`}></i></div></div>`)}</div></div>`;
  }
  const radarItems = option.radar?.indicator ?? [];
  const radarValues = option.series?.[0]?.data?.[0]?.value ?? [];
  return html`<div class=${`echart ${className}`} role="img" aria-label=${label}>
    <div class="echart__canvas" ref=${target}></div>
    ${radarItems.length > 0 && html`<div class="report-radar-legend" aria-label="راهنمای شماره‌گذاری ارزیابی مهارت‌ها">${radarItems.map((item, index) => html`<span><i>${index + 1}</i><em>${item.title ?? item.name}</em><b>${formatMetricValue(radarValues[index])}٪</b></span>`)}</div>`}
    ${failed && html`<span class="echart__fallback">${emptyLabel}</span>`}
  </div>`;
}
