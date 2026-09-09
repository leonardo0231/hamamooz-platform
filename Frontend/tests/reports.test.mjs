import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import {
  mapSnapshot,
  normalizeReportDomainPercent,
  normalizeReportDomainScores,
  normalizeReportMetricValue,
  normalizeReportSubjectScore,
} from '../src/components/analytical-report.js';

const report = await readFile(new URL('../src/components/analytical-report.js', import.meta.url), 'utf8');
const chart = await readFile(new URL('../src/components/echart.js', import.meta.url), 'utf8');
const icons = await readFile(new URL('../src/components/icons.js', import.meta.url), 'utf8');
const page = await readFile(new URL('../src/pages/reports.js', import.meta.url), 'utf8');
const styles = await readFile(new URL('../src/styles/reports.css', import.meta.url), 'utf8');
const defaultPhoto = await readFile(new URL('../public/assets/report-default-student.svg', import.meta.url), 'utf8');
const sample = await readFile(new URL('../src/report-sample.html', import.meta.url), 'utf8');
const sampleScript = await readFile(new URL('../src/report-sample.js', import.meta.url), 'utf8');
const build = await readFile(new URL('../scripts/build.mjs', import.meta.url), 'utf8');

test('analytical report preserves all nine analysis domains and marks missing data', () => {
  for (const code of ['EDU', 'DEV', 'CHR', 'DIS', 'CUL', 'RES', 'SPT', 'ART', 'PER']) {
    assert.match(report, new RegExp(`code: '${code}'`));
  }
  assert.match(report, /hasData: value !== null/);
  assert.match(report, /ثبت نشده/);
  assert.doesNotMatch(report, /radarItems\s*=\s*items\.slice\(0,\s*6\)/);
  assert.doesNotMatch(report, /radarItems\.slice\(0,\s*6\)/);
});

test('React data boundary rejects ambiguous metric values without hiding their rows', () => {
  assert.equal(normalizeReportMetricValue(0), 0);
  assert.equal(normalizeReportMetricValue('5'), 100);
  for (const value of [3.5, -1, 'ندارد', '20', '']) {
    assert.equal(normalizeReportMetricValue(value), null, `value ${String(value)} must stay unavailable`);
  }

  assert.equal(normalizeReportSubjectScore({ average: '18.75' }), 18.75);
  assert.equal(normalizeReportSubjectScore({ average: -1 }), null);
  assert.equal(normalizeReportSubjectScore({ average: 21 }), null);

  assert.equal(normalizeReportDomainPercent({ score: 0 }), 0);
  assert.equal(normalizeReportDomainPercent({ score: 18.5 }), 92.5);
  assert.equal(normalizeReportDomainPercent({ score: -1 }), null);
  assert.equal(normalizeReportDomainPercent({ value: 18 }), null);
  assert.equal(normalizeReportDomainPercent({ value: 18, value_unit: 'score_20' }), 90);
  assert.equal(normalizeReportDomainPercent({ value: 90, value_unit: 'percent' }), 90);

  const domains = normalizeReportDomainScores([{ code: 'EDU', score: 0, completed_metrics: 0 }]);
  assert.equal(domains.length, 9);
  assert.equal(domains[0].value, 0);
  assert.equal(domains[0].hasData, true);
  assert.equal(domains[1].hasData, false);
  assert.equal(normalizeReportDomainScores(null).length, 9);
});

test('invalid EDU metrics remain printable as explicit missing rows', () => {
  assert.match(report, /hasData: value !== null/);
  assert.doesNotMatch(report, /\.filter\(item => item\.value !== null\)/);
  assert.match(report, /report-rating-missing/);
  assert.match(report, /Number\.isInteger\(numeric\)/);
  assert.match(report, /numeric < 0 \|\| numeric > 5/);
  assert.match(report, /value_unit \?\? item\.unit \?\? item\.scale/);
  assert.match(report, /score >= 0 && score <= 20/);
  assert.match(report, /latest\?\.metrics\?\.length \? latest\.metrics/);
  assert.match(report, /const sourceRows = Array\.isArray\(rows\) \? rows : \[\]/);
});

test('report uses semantic SVG icons and has no CSS-text sticker fallback', () => {
  assert.match(report, /discipline:\s*'shieldCheck'/);
  assert.match(report, /<\$\{Sticker\}/);
  assert.match(icons, /shieldCheck:/);
  assert.match(icons, /star:/);
  assert.doesNotMatch(report, /<svg class="report-avatar-demo"/);
  assert.doesNotMatch(report, /★/);
  assert.doesNotMatch(styles, /\.report-sticker(?:::before|--[^ ]+::before)/);
});

test('report preview and PDF request use one fixed A3 landscape format', () => {
  assert.match(page, /REPORT_PAGE_SIZE\s*=\s*'a3_landscape'/);
  assert.match(page, /page_size:\s*REPORT_PAGE_SIZE/);
  assert.doesNotMatch(page, /digital_3x2|a4_portrait/);
  assert.match(styles, /@page\s*\{\s*size:\s*A3 landscape;\s*margin:\s*6mm;/);
  assert.match(sample, /@page\s*\{\s*size: A3 landscape; margin: 6mm;\s*\}/);
  assert.doesNotMatch(sample, /zoom\s*:/);
});

test('report header and signatures are reference-aligned and data-driven', () => {
  assert.match(report, /کارنامه جامع رشد سه ساله دانش‌آموز/);
  assert.match(report, /historyGradeRange/);
  assert.match(report, /report\.academic\?\.grade_range \?\?/);
  assert.match(report, /normalizeSignatureLabels/);
  assert.match(report, /ولی دانش‌آموز/);
  assert.doesNotMatch(report, /Class Expert|Elementary Assistant|Educational Assistant|Executive Assistant|High School Principal/);
  assert.match(styles, /\.analytical-identity \.analytical-panel__body \{ display: grid; grid-template-columns: 88px/);
  assert.match(styles, /\.analytical-identity \.report-portrait \{ grid-row: 1; width: 88px; height: 106px/);
  assert.match(styles, /\.analytical-identity \.report-mini-kpis \{ display: none; \}/);
});

test('report output is browser-native and never exposes the legacy PDF/ZIP controls', () => {
  assert.match(report, /printAnalyticalReport/);
  assert.match(report, /report-printing/);
  assert.match(page, /printAnalyticalReport/);
  assert.doesNotMatch(page, /downloadFile|downloadBlob|downloadError|downloading|zip_download_url/);
  assert.doesNotMatch(page, /reports\/(?:[^'"` ]+\/)?download\//);
  assert.match(chart, /data-chart-renderer="svg"/);
  assert.match(chart, /<svg class="echart__svg/);
  assert.match(chart, /preserveAspectRatio="xMidYMid meet"/);
  assert.match(chart, /report-radar-legend/);
  assert.match(chart, /is-missing/);
  assert.doesNotMatch(chart, /radarLabelPoint/);
  assert.match(chart, /x=\$\{edge\.x\} y=\$\{edge\.y \+ 4\} text-anchor="middle"/);
  assert.match(chart, /fa\(index \+ 1\)/);
  assert.doesNotMatch(chart, /<text[^>]*>\$\{item\.title \?\? item\.name\}<\/text>/);
  assert.match(chart, /const displayText = available/);
  assert.match(chart, /const accessibleText = available \? displayText : 'ثبت نشده'/);
  assert.match(chart, /<b>\$\{displayText\}<\/b>/);
  assert.doesNotMatch(chart, /<canvas\b/);
  assert.doesNotMatch(chart, /import\(['"]\/vendor\/echarts\.mjs/);
  assert.doesNotMatch(build, /node_modules['"`]?,\s*['"]echarts|echarts\.esm/);
});

test('standalone report entry exposes a readiness marker for browser print automation', () => {
  assert.match(sampleScript, /window\.__REPORT_READY__\s*=\s*false/);
  assert.match(sampleScript, /window\.__REPORT_READY__\s*=\s*true/);
  assert.match(sampleScript, /globalThis\.__REPORT_SNAPSHOT__/);
  assert.match(sampleScript, /snapshot=\$\{pageSnapshot\}/);
  assert.match(sampleScript, /printAnalyticalReport/);
  assert.match(styles, /body\.report-printing \.sidebar/);
  assert.match(styles, /height:\s*calc\(297mm - 12mm\)/);
  assert.match(styles, /grid-template-rows:\s*182px 278px 195px 95px/);
  assert.match(styles, /\.echart--radar \{ height: 242px; min-height: 242px; padding-bottom: 72px; \}/);
  assert.match(styles, /\.echart__svg--radar text \{ font-size: 20px; \}/);
  assert.match(styles, /\.echart--radar \.echart__svg \{ display: block; width: 100%; min-width: 0; height: 170px; min-height: 170px; \}/);
  assert.match(styles, /\.report-radar-legend \{ grid-template-columns: repeat\(3, minmax\(0, 1fr\)\); height: 72px;/);
  assert.match(styles, /\.report-radar-legend span \{ display: flex; align-items: flex-start; min-width: 0; gap: 4px;/);
  assert.match(styles, /\.report-radar-legend em \{ flex: 1 1 auto; min-width: 0; overflow: visible; overflow-wrap: anywhere; text-overflow: clip; white-space: normal/);
  assert.match(styles, /\.report-radar-legend b \{ flex: none;/);
  assert.doesNotMatch(styles, /@media print[\s\S]*?\.report-radar-legend span \{[^}]*flex-wrap:\s*nowrap/);
  assert.match(styles, /\.report-recommendation-group \{ min-height: 0; overflow: visible;/);
  assert.match(styles, /\.analytical-sheet__footer \{ flex: 0 0 86px; min-height: 86px; max-height: 86px; margin-top: auto/);
  assert.match(styles, /\.report-recommendation-group \.report-bullet-list li \{ white-space: normal; overflow-wrap: anywhere;/);
  assert.match(styles, /\.analytical-recommendations \.analytical-panel__body \{ padding: 0; overflow: visible; \}/);
  assert.match(styles, /\.analytical-sheet__grid \{ flex: 0 0 790px; height: 790px; min-height: 790px;[\s\S]*grid-template-areas: "identity trend trend behavior insights" "table radar strengths improvements recommendations" "attendance skills21 activities activities readiness" "awards awards awards awards awards";[\s\S]*overflow: visible; \}/);
  assert.match(styles, /\.analytical-sheet__header[^\{]*\{[^}]*direction: ltr/);
  assert.match(styles, /\.analytical-sheet__grid[^\{]*\{[^}]*direction: ltr/);
  assert.match(styles, /\.analytical-panel[^\{]*\{[^}]*direction: rtl/);
  assert.match(sampleScript, /pageSnapshots = Array\.isArray\(snapshot\?\.reports\)/);
  assert.match(sampleScript, /reports: \[report\]/);
  assert.match(styles, /\.report-sample__pages > \.analytical-sheet \{ break-after: page; page-break-after: always; \}/);
  assert.match(styles, /\.report-sample__pages > \.analytical-sheet:last-child \{ break-after: auto; page-break-after: auto; \}/);
  assert.match(sample, /\.report-sample--print \.report-sample\{display:flex;flex-direction:column;[\s\S]*overflow:visible/);
  assert.doesNotMatch(page, /React\/Preact/);
});

test('photo, logo and family-support fallbacks are explicit', () => {
  assert.match(report, /MissingPhoto/);
  assert.match(report, /MissingLogo/);
  assert.match(report, /DEFAULT_STUDENT_PHOTO_URL = '\/assets\/report-default-student\.svg'/);
  assert.match(report, /schoolLogoUrl: '\/assets\/besat-logo\.png'/);
  assert.match(defaultPhoto, /تصویر پیش‌فرض دانش‌آموز/);
  assert.match(report, /schoolLogoUrl: assetUrl\(report\.school\?\.logo_url \|\| organization\.logo_url/);
  assert.match(report, /support: supportNotes/);
  assert.match(report, /report-recommendation-group--empty/);
});

test('report output contains no QR or access-code panel', () => {
  assert.doesNotMatch(report, /QR|QrCode|accessQr|access_qr|report-qr|دسترسی سریع/);
  assert.doesNotMatch(styles, /QR|report-qr|report-access|analytical-access/);
});

test('long subject names have a wrapping presentation path', () => {
  assert.match(report, /report-score-table__subject/);
  assert.match(styles, /\.report-score-table__subject \{ display: block; overflow-wrap: anywhere;/);
  assert.match(styles, /\.report-rating-list > div > span:first-child \{ min-width: 0;[^}]*overflow-wrap: anywhere; white-space: normal/);
  assert.match(styles, /\.report-metric-bar__head span \{ min-width: 0; overflow-wrap: anywhere; white-space: normal/);
  assert.match(styles, /\.report-activities strong, \.report-activities small \{ display: -webkit-box;[^}]*-webkit-line-clamp: 2/);
});

test('one-page caps stay explicit instead of silently dropping report data', () => {
  assert.match(report, /const bounded = \(items, limit\)/);
  assert.match(report, /subjectsOmitted: visibleSubjects\.omitted/);
  assert.match(report, /activitiesOmitted: activities\.omitted/);
  assert.match(report, /recommendationsOmitted: parentRecommendations\.omitted/);
  assert.match(report, /class="report-overflow-row"/);
  assert.match(report, /class="report-overflow-note"/);
  assert.match(styles, /\.report-overflow-note/);
  assert.match(styles, /\.report-overflow-row td/);
});

test('unknown pass status stays explicit and trend charts cover the full score range', () => {
  assert.match(report, /if \(subject\.passed === true\) return/);
  assert.match(report, /if \(subject\.passed === false\) return/);
  assert.match(report, /const min = Math\.max\(0, Math\.floor\(minValue - 1\)\)/);
  assert.match(report, /const max = Math\.min\(20, Math\.max\(min \+ 4, Math\.ceil\(maxValue \+ 1\)\)\)/);
  assert.doesNotMatch(report, /yAxis: \{ type: 'value', min: 10, max: 20/);
});

test('printed report preserves color hierarchy and table semantics', () => {
  assert.match(styles, /print-color-adjust: exact/);
  assert.match(styles, /-webkit-print-color-adjust: exact/);
  assert.match(report, /<caption class="sr-only">نمرات و وضعیت آموزشی دانش‌آموز<\/caption>/);
  assert.match(report, /<th scope="col">درس \/ شاخص<\/th>/);
  assert.match(report, /<th scope="row"><span class="report-score-table__subject">/);
});

test('real empty snapshots render explicit missing data instead of fictional demo data', () => {
  assert.equal(mapSnapshot(undefined).demo, true);
  const empty = mapSnapshot({ reports: [] });
  assert.equal(empty.demo, false);
  assert.equal(empty.student.name, 'ثبت نشده');
  assert.equal(empty.average, null);
  assert.equal(empty.domainScores.length, 9);
  assert.equal(empty.activities.length, 0);
});

test('standalone print entry rejects unavailable required fonts', () => {
  assert.match(sampleScript, /window\.__REPORT_ERROR__\s*=\s*['"]['"]/);
  assert.match(sampleScript, /Vazirmatn/);
  assert.match(sampleScript, /Estedad/);
  assert.match(sampleScript, /document\.fonts\.check/);
  assert.match(sampleScript, /data-report-error/);
});
