import { html, render } from './core/view.js';
import { AnalyticalReport, printAnalyticalReport } from './components/analytical-report.js';

const root = document.querySelector('#report-sample');
const params = new URLSearchParams(location.search);
const printMode = params.get('print') === '1';
const sampleMode = params.get('mode');
// A trusted renderer may inject the already-authorized snapshot before the
// bundle starts.  Keeping the snapshot out of the query string avoids leaking
// student data into browser history and server logs; the public sample still
// falls back to the reviewed demo payload when no snapshot is supplied.
const monthlySampleSnapshot = {
  report_mode: 'data_monthly',
  title: 'کارنامه جامع رشد سه ساله دانش‌آموز',
  month: { no: 3, title: 'شهریور' },
  organization: { name: 'سامانه هوشمند هم‌آموز', logo_url: '' },
  school: { name: 'دبیرستان پسرانه بعثت', branch: 'دوره اول', logo_url: '/assets/besat-logo.png' },
  student: {
    name: 'دانش‌آموز نمونه', national_id: null, student_number: null,
    grade: 'پایه هفتم', class_code: 'هفتم / الف', photo_url: '',
  },
  metrics: [
    { code: 'EDU_01', title: 'یادگیری مفاهیم درسی', domain_title: 'آموزشی', raw_score: 5, score: 20 },
    { code: 'EDU_02', title: 'پیشرفت نسبت به ارزیابی قبل', domain_title: 'آموزشی', raw_score: 'ندارد', score: null },
    { code: 'DEV_01', title: 'احترام و همکاری', domain_title: 'تربیتی', raw_score: 3, score: 12 },
    { code: 'CHR_01', title: 'مسئولیت‌پذیری', domain_title: 'شخصیتی', raw_score: 4, score: 16 },
    { code: 'DIS_01', title: 'نظم و پیگیری', domain_title: 'انضباطی', raw_score: 4, score: 16 },
    { code: 'PER_01', title: 'مدیریت زمان', domain_title: 'مهارت‌های فردی', raw_score: 3, score: 12 },
  ],
  domains: [
    { code: 'EDU', title: 'آموزشی', score: 100, completed_metrics: 1 },
    { code: 'DEV', title: 'تربیتی', score: 60, completed_metrics: 1 },
    { code: 'CHR', title: 'شخصیتی', score: 80, completed_metrics: 1 },
    { code: 'DIS', title: 'انضباطی', score: 80, completed_metrics: 1 },
    { code: 'COM', title: 'ارتباطی', score: null, completed_metrics: 0 },
    { code: 'EMO', title: 'هیجانی', score: null, completed_metrics: 0 },
    { code: 'SOC', title: 'اجتماعی', score: null, completed_metrics: 0 },
    { code: 'CRE', title: 'خلاقیت', score: null, completed_metrics: 0 },
    { code: 'PHY', title: 'سلامت و آمادگی', score: null, completed_metrics: 0 },
  ],
  overall_score: 16.57,
  completion_percent: 50,
  completion_status: 'provisional',
  monthly_scores: [
    { month_no: 1, overall_score: 15 },
    { month_no: 2, overall_score: null },
    { month_no: 3, overall_score: 16.57 },
  ],
  monthly_change: 1.57,
  monthly_changes: [{ from_month_no: 1, to_month_no: 3, change: 1.57 }],
  recommendations: [
    'برنامهٔ ثابت مطالعهٔ روزانه برای تثبیت رشد ادامه یابد.',
    'در فعالیت‌های گروهی، نقش ارائه‌دهنده تجربه شود.',
  ],
  missing_sections: ['attendance', 'honors', 'activities', 'counselor'],
};
const snapshot = globalThis.__REPORT_SNAPSHOT__
  ?? (sampleMode === 'data_monthly' ? monthlySampleSnapshot : undefined);
window.__REPORT_READY__ = false;
window.__REPORT_ERROR__ = '';
if (printMode) {
  document.documentElement.classList.add('report-sample--print');
}
// A class report can contain one authorized snapshot per student.  React owns
// every page; the print stylesheet only inserts a page break between those
// independently sized A3 sheets.  A single report keeps the original DOM
// shape for the interactive preview.
const pageSnapshots = Array.isArray(snapshot?.reports) && snapshot.reports.length > 1
  ? snapshot.reports.map(report => ({ ...snapshot, reports: [report] }))
  : [snapshot];
render(html`<div class="report-sample__pages">${pageSnapshots.map((pageSnapshot, index) => html`<${AnalyticalReport} key=${`report-page-${index}`} snapshot=${pageSnapshot}/>` )}</div>`, root);

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
