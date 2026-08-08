import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';

test('role experience covers every backend-supported role', async () => {
  const source = await readFile(new URL('../src/ui/role-experience.ts', import.meta.url), 'utf8');
  for (const role of [
    'system_admin',
    'organization_admin',
    'school_manager',
    'educational_deputy',
    'operator',
    'teacher',
  ]) {
    assert.match(source, new RegExp(`${role}:\\s*\\{`), `missing dashboard experience for ${role}`);
  }
  assert.match(source, /sectionOrder/);
  assert.match(source, /metricOrder/);
});

test('role dashboard uses official aggregate endpoints and backend response names', async () => {
  const [dashboard, endpoints] = await Promise.all([
    readFile(new URL('../src/pages/dashboard-v2.ts', import.meta.url), 'utf8'),
    readFile(new URL('../src/api/endpoints.ts', import.meta.url), 'utf8'),
  ]);
  assert.match(endpoints, /monthly_evaluations_dashboard_retrieve/);
  assert.match(endpoints, /academic_years_list/);
  assert.match(endpoints, /classes_list/);
  assert.match(dashboard, /monthlyEvaluations\.dashboard/);
  assert.match(dashboard, /school_name/);
  assert.doesNotMatch(dashboard, /school__name/);
  assert.match(dashboard, /class_section/);
  assert.match(dashboard, /academic_year/);
});

test('analytics exposes line bar radar and heatmap views without a chart dependency', async () => {
  const [dashboard, charts, heatmap, packageJson] = await Promise.all([
    readFile(new URL('../src/pages/dashboard-v2.ts', import.meta.url), 'utf8'),
    readFile(new URL('../src/components/charts.ts', import.meta.url), 'utf8'),
    readFile(new URL('../src/components/heatmap.ts', import.meta.url), 'utf8'),
    readFile(new URL('../package.json', import.meta.url), 'utf8'),
  ]);
  assert.match(dashboard, /lineChart/);
  assert.match(dashboard, /horizontalBarChart/);
  assert.match(dashboard, /radarChart/);
  assert.match(dashboard, /heatmap/);
  assert.match(charts, /role:\s*'img'/);
  assert.match(charts, /role:\s*'progressbar'/);
  assert.match(heatmap, /<table|h\('table'/);
  assert.doesNotMatch(packageJson, /chart\.js|recharts|apexcharts|echarts/i);
});

test('product stylesheet is part of the production build and form polish remains contract-driven', async () => {
  const [html, build, styles] = await Promise.all([
    readFile(new URL('../src/index.html', import.meta.url), 'utf8'),
    readFile(new URL('../scripts/build.mjs', import.meta.url), 'utf8'),
    readFile(new URL('../src/styles/product.css', import.meta.url), 'utf8'),
  ]);
  assert.match(html, /\/product\.css/);
  assert.match(build, /src\/styles\/product\.css/);
  assert.match(styles, /\.schema-form/);
  assert.match(styles, /\.manual-entry-group/);
  assert.match(styles, /prefers-reduced-motion/);
  assert.match(styles, /\.heatmap-table/);
});
