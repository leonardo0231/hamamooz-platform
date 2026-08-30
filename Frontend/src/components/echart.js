import { html, useEffect, useRef, useState } from '../core/view.js';

let modulePromise;

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
  return html`<div class=${`echart ${className}`} role="img" aria-label=${label}>
    <div class="echart__canvas" ref=${target}></div>
    ${failed && html`<span class="echart__fallback">${emptyLabel}</span>`}
  </div>`;
}
