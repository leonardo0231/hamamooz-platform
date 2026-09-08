import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';

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
  assert.doesNotMatch(chart, /import\(['"]\/vendor\/echarts\.mjs/);
  assert.doesNotMatch(build, /node_modules['"`]?,\s*['"]echarts|echarts\.esm/);
});

test('standalone report entry exposes a readiness marker for browser print automation', () => {
  assert.match(sampleScript, /window\.__REPORT_READY__\s*=\s*false/);
  assert.match(sampleScript, /window\.__REPORT_READY__\s*=\s*true/);
  assert.match(sampleScript, /printAnalyticalReport/);
  assert.match(styles, /body\.report-printing \.sidebar/);
  assert.match(styles, /grid-template-rows:\s*112px 225px 160px 115px 98px 85px/);
});

test('photo, logo and family-support fallbacks are explicit', () => {
  assert.match(report, /MissingPhoto/);
  assert.match(report, /MissingLogo/);
  assert.match(report, /schoolLogoUrl: assetUrl\(report\.school\?\.logo_url \|\| organization\.logo_url/);
  assert.match(report, /support: supportNotes/);
  assert.match(report, /report-recommendation-group--empty/);
});
