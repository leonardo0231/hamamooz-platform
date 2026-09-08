import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import {
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

test('report output is browser-native and never exposes the legacy PDF/ZIP controls', () => {
  assert.match(report, /printAnalyticalReport/);
  assert.match(report, /report-printing/);
  assert.match(page, /printAnalyticalReport/);
  assert.doesNotMatch(page, /downloadFile|downloadBlob|downloadError|downloading|zip_download_url/);
  assert.doesNotMatch(page, /reports\/(?:[^'"` ]+\/)?download\//);
  assert.match(chart, /data-chart-renderer="svg"/);
  assert.match(chart, /<svg class="echart__svg/);
  assert.match(chart, /preserveAspectRatio=\\"xMidYMid meet\\"/);
  assert.match(chart, /report-radar-legend/);
  assert.match(chart, /is-missing/);
  assert.doesNotMatch(chart, /<canvas\b/);
  assert.doesNotMatch(chart, /import\(['"]\/vendor\/echarts\.mjs/);
  assert.doesNotMatch(build, /node_modules['"`]?,\s*['"]echarts|echarts\.esm/);
});

test('standalone report entry exposes a readiness marker for browser print automation', () => {
  assert.match(sampleScript, /window\.__REPORT_READY__\s*=\s*false/);
  assert.match(sampleScript, /window\.__REPORT_READY__\s*=\s*true/);
  assert.match(sampleScript, /globalThis\.__REPORT_SNAPSHOT__/);
  assert.match(sampleScript, /snapshot=\$\{snapshot\}/);
  assert.match(sampleScript, /printAnalyticalReport/);
  assert.match(styles, /body\.report-printing \.sidebar/);
  assert.match(styles, /height:\s*calc\(297mm - 12mm\)/);
  assert.match(styles, /grid-template-rows:\s*165px 145px 250px 85px 75px 70px/);
  assert.match(styles, /\.echart--radar \{ height: 212px; min-height: 212px; padding-bottom: 72px; \}/);
  assert.match(styles, /\.echart__svg--radar text \{ font-size: 20px; \}/);
  assert.match(styles, /\.analytical-sheet__footer \{ flex: 0 0 86px; min-height: 86px; max-height: 86px; margin-top: auto/);
  assert.match(styles, /\.report-recommendation-group \.report-bullet-list li \{ white-space: normal; overflow-wrap: anywhere;/);
  assert.doesNotMatch(page, /React\\/Preact/);
});

test('photo, logo and family-support fallbacks are explicit', () => {
  assert.match(report, /MissingPhoto/);
  assert.match(report, /MissingLogo/);
  assert.match(report, /schoolLogoUrl: assetUrl\(report\.school\?\.logo_url \|\| organization\.logo_url/);
  assert.match(report, /support: supportNotes/);
  assert.match(report, /report-recommendation-group--empty/);
});
