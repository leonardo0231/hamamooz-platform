import { html, render } from './core/view.js';
import { AnalyticalReport, printAnalyticalReport } from './components/analytical-report.js';

const root = document.querySelector('#report-sample');
const printMode = new URLSearchParams(location.search).get('print') === '1';
window.__REPORT_READY__ = false;
if (printMode) {
  document.documentElement.classList.add('report-sample--print');
}
render(html`<${AnalyticalReport}/>`, root);

const assets = [];
if (document.fonts?.ready) assets.push(document.fonts.ready.catch(() => undefined));
[...document.images].forEach(image => {
  if (image.complete) assets.push(Promise.resolve());
  else assets.push(new Promise(resolve => {
    image.addEventListener('load', resolve, { once: true });
    image.addEventListener('error', resolve, { once: true });
  }));
});
Promise.all(assets).finally(() => {
  // Chromium/Playwright integrations can wait for this explicit marker when
  // they print the standalone report entry.  The interactive app uses the
  // same browser DOM and calls `printAnalyticalReport` from its toolbar.
  window.__REPORT_READY__ = true;
  if (printMode) printAnalyticalReport();
});
