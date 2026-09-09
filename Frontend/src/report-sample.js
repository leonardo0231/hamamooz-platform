import { html, render } from './core/view.js';
import { AnalyticalReport, printAnalyticalReport } from './components/analytical-report.js';

const root = document.querySelector('#report-sample');
const printMode = new URLSearchParams(location.search).get('print') === '1';
// A trusted renderer may inject the already-authorized snapshot before the
// bundle starts.  Keeping the snapshot out of the query string avoids leaking
// student data into browser history and server logs; the public sample still
// falls back to the reviewed demo payload when no snapshot is supplied.
const snapshot = globalThis.__REPORT_SNAPSHOT__ ?? undefined;
window.__REPORT_READY__ = false;
window.__REPORT_ERROR__ = '';
if (printMode) {
  document.documentElement.classList.add('report-sample--print');
}
render(html`<${AnalyticalReport} snapshot=${snapshot}/>`, root);

const assets = [];
if (document.fonts?.ready) {
  assets.push(document.fonts.ready.then(async () => {
    const requiredFonts = ['Vazirmatn', 'Estedad'];
    await Promise.all(requiredFonts.map(font => document.fonts.load(`16px "${font}"`)));
    const missingFonts = requiredFonts.filter(font => !document.fonts.check(`16px "${font}"`));
    if (missingFonts.length) throw new Error(`Required report fonts unavailable: ${missingFonts.join(', ')}`);
  }));
}
[...document.images].forEach(image => {
  if (image.complete) assets.push(Promise.resolve());
  else assets.push(new Promise(resolve => {
    image.addEventListener('load', resolve, { once: true });
    image.addEventListener('error', resolve, { once: true });
  }));
});
Promise.all(assets).then(() => {
  // Chromium/Playwright integrations can wait for this explicit marker when
  // they print the standalone report entry.  The interactive app uses the
  // same browser DOM and calls `printAnalyticalReport` from its toolbar.
  window.__REPORT_READY__ = true;
  // Manual browser printing still opens the native dialog. The backend
  // Chromium renderer sets this automation marker and calls page.pdf itself;
  // opening window.print() there would race the readiness marker and can
  // leave the print-only body class active during PDF capture.
  if (printMode && !globalThis.__REPORT_AUTOMATION__) printAnalyticalReport();
}).catch(error => {
  window.__REPORT_ERROR__ = error instanceof Error ? error.message : String(error);
  root.setAttribute('data-report-error', 'assets');
});
