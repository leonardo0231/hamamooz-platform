import { html, render } from './core/view.js';
import { AnalyticalReport, printAnalyticalReport } from './components/analytical-report.js';

const root = document.querySelector('#report-sample');
const params = new URLSearchParams(location.search);
const printMode = params.get('print') === '1';
const sampleMode = params.get('mode');
// A trusted renderer may inject the already-authorized snapshot before the
// bundle starts.  Keeping the snapshot out of the query string avoids leaking
// student data into browser history and server logs; the public sample still
// falls back to the reviewed Excel-derived payload when no snapshot is supplied.
//
// Source: Data/Excel/803-804.xlsx, sheet «ثبت اطلاعات», Excel row 103.
// The student identifiers are intentionally removed.  EDU_01 is a 0–20 grade,
// EDU_02 is a progress delta/text field, and the remaining rubric indicators
// use the workbook's 0–5 scale.  The cached Excel domain/overall formulas are
// not copied because this workbook contains a #VALUE! overall formula and an
// over-scaled EDU summary; the frontend recomputes those values from raw rows.
// Raw cells such as `{ raw_score: 'ندارد' }` remain visible in the indicator table.
const excelMetric = (code, title, raw_score, raw_unit = 'rubric_5') => ({
  code,
  title,
  domain_code: code.split('_', 1)[0],
  raw_score,
  raw_unit,
});
const excelSampleMetrics = [
  ['EDU_01', 'نمرات درسی', 18.64, 'score_20'],
  ['EDU_02', 'پیشرفت نسبت به قبل', 'ندارد', 'delta'],
  ['EDU_03', 'انجام تکالیف', 4],
  ['EDU_04', 'مشارکت در کلاس', 4],
  ['EDU_05', 'دقت و تمرکز', 4],
  ['EDU_06', 'مهارت حل مسئله', 3],
  ['EDU_07', 'آمادگی برای امتحان', 4],
  ['EDU_08', 'مطالعه غیر درسی', 3],
  ['DEV_01', 'احترام به معلم و همکلاسی', 4],
  ['DEV_02', 'مسئولیت‌پذیری', 2],
  ['DEV_03', 'همکاری با دیگران', 3],
  ['DEV_04', 'ادب و رفتار اجتماعی', 5],
  ['DEV_05', 'اعتماد به نفس', 4],
  ['CHR_01', 'هدف‌گذاری', 4],
  ['CHR_02', 'دوست یابی', 4],
  ['DIS_01', 'حضور و غیاب', 4],
  ['DIS_02', 'تأخیر', 3],
  ['DIS_03', 'رعایت قوانین مدرسه', 4],
  ['DIS_04', 'رعایت پوشش', 4],
  ['DIS_05', 'احترام به مقررات کلاس', 3],
  ['CUL_01', 'مشارکت در برنامه‌های فرهنگی', 4],
  ['CUL_02', 'شناخت ارزش‌های اجتماعی', 4],
  ['CUL_03', 'رفتار مناسب در مراسم‌ها', 4],
  ['RES_01', 'انجام تحقیق', 4],
  ['RES_02', 'خلاقیت در پروژه‌ها', 4],
  ['RES_03', 'تحلیل اطلاعات', 4],
  ['RES_04', 'استفاده از منابع', 4],
  ['RES_05', 'نوآوری', 4],
  ['RES_06', 'پرسشگری', 4],
  ['SPT_01', 'آمادگی جسمانی', 4],
  ['SPT_02', 'مشارکت در فعالیت‌های ورزشی', 5],
  ['SPT_03', 'روحیه تیمی', 4],
  ['SPT_04', 'رعایت قوانین بازی', 4],
  ['SPT_05', 'تلاش و پشتکار', 4],
  ['SPT_06', 'پیشرفت بدنی', 0],
  ['SPT_07', 'مهارت‌های حرکتی', 5],
  ['ART_01', 'خلاقیت', 3],
  ['ART_02', 'مشارکت در فعالیت‌های هنری', 3],
  ['ART_03', 'مهارت در نقاشی / موسیقی / ...', 3],
  ['ART_04', 'دقت در کار هنری', 4],
  ['ART_05', 'نوآوری', 4],
  ['ART_06', 'علاقه‌مندی', 0],
  ['ART_07', 'ارائه آثار', 4],
  ['PER_01', 'مهارت ارتباطی', 3],
  ['PER_02', 'مهارت برنامه‌ریزی', 3],
  ['PER_03', 'ارائه مطلب', 4],
].map(([code, title, raw_score, raw_unit]) => excelMetric(code, title, raw_score, raw_unit));

const monthlySampleSnapshot = {
  report_mode: 'data_monthly',
  title: 'کارنامه ارزیابی تابستانه رشد دانش‌آموز',
  month: { no: 3, title: 'شهریور' },
  organization: { name: 'سامانه هوشمند هم‌آموز', logo_url: '' },
  school: { name: 'مدرسه نمونه هم‌آموز', branch: 'دوره اول', logo_url: '/assets/besat-logo.png' },
  student: {
    name: 'دانش‌آموز نمونه', national_id: null, student_number: null,
    grade: 'پایه هشتم', class_code: '۸۰۳ / نمونه', photo_url: '',
  },
  metrics: excelSampleMetrics,
  domains: [],
  overall_score: '#VALUE!',
  completed_metrics: 45,
  required_metrics: 46,
  completion_ratio: 45 / 46,
  completion_status: 'provisional',
  monthly_scores: [{ month_no: 3, month_title: 'شهریور', overall_score: '#VALUE!' }],
  monthly_change: null,
  monthly_changes: [],
  recommendations: [],
  source_file: 'نمونه Excel · 803-804.xlsx · شیت ثبت اطلاعات',
  source_row: 103,
  missing_sections: ['attendance', 'honors', 'activities', 'counselor', 'official_subject_grades'],
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
