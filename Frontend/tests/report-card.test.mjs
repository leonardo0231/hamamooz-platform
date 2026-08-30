import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';

const component = await readFile(new URL('../src/components/analytical-report.js', import.meta.url), 'utf8');
const styles = await readFile(new URL('../src/styles/reports.css', import.meta.url), 'utf8');
const sample = await readFile(new URL('../src/report-sample.html', import.meta.url), 'utf8');

test('report preview keeps reference geometry while Persian content stays RTL', () => {
  assert.match(styles, /\.analytical-sheet__header,\.analytical-sheet__grid,\.analytical-sheet__footer\{direction:ltr\}/);
  assert.match(styles, /\.analytical-sheet__header>\* ,\.analytical-sheet__grid>\* ,\.analytical-sheet__footer>\*\{direction:rtl\}/);
  assert.match(styles, /\.analytical-identity\{grid-column:1/);
  assert.match(styles, /\.analytical-counselor\{grid-column:4/);
});

test('report preview exposes its table and ratings to assistive technology', () => {
  assert.match(component, /<caption class="sr-only">/);
  assert.match(component, /scope="col"/);
  assert.match(component, /scope="row"/);
  assert.match(component, /aria-labelledby=\$\{headingId\}/);
  assert.match(component, /role="img" aria-label=/);
  assert.match(component, /aria-hidden="true" class=/);
});

test('print sample does not scale the report down with CSS zoom', () => {
  assert.doesNotMatch(sample, /zoom\s*:/);
});
