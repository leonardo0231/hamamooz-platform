import { html, render } from './core/view.js';
import { AnalyticalReport } from './components/analytical-report.js';

const root = document.querySelector('#report-sample');
if (new URLSearchParams(location.search).get('print') === '1') {
  document.documentElement.classList.add('report-sample--print');
}
render(html`<${AnalyticalReport}/>`, root);
