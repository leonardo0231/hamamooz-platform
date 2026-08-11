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

test('responsive design system keeps global layout separate from dashboard analytics', async () => {
  const [html, build, appStyles, productStyles] = await Promise.all([
    readFile(new URL('../src/index.html', import.meta.url), 'utf8'),
    readFile(new URL('../scripts/build.mjs', import.meta.url), 'utf8'),
    readFile(new URL('../src/styles/app.css', import.meta.url), 'utf8'),
    readFile(new URL('../src/styles/product.css', import.meta.url), 'utf8'),
  ]);
  assert.match(html, /\/product\.css/);
  assert.match(build, /src\/styles\/product\.css/);
  assert.match(appStyles, /\.schema-form/);
  assert.match(appStyles, /\.manual-entry-group/);
  assert.match(appStyles, /\.table-wrap/);
  assert.match(appStyles, /@media \(max-width: 1080px\)/);
  assert.match(appStyles, /@media \(max-width: 680px\)/);
  assert.match(productStyles, /\.decision-dashboard/);
  assert.match(productStyles, /\.heatmap-table/);
  assert.match(productStyles, /prefers-reduced-motion/);
  assert.doesNotMatch(appStyles, /\.data-table,\s*\.data-table thead,\s*\.data-table tbody,[\s\S]*?display:\s*block/);
});

test('application shell uses a conventional responsive drawer without geometry-driven navigation', async () => {
  const source = await readFile(new URL('../src/components/shell.ts', import.meta.url), 'utf8');
  assert.match(source, /max-width: 1080px/);
  assert.match(source, /sidebar__profile/);
  assert.match(source, /sidebar\.classList\.toggle\('is-open'/);
  assert.match(source, /toggleAttribute\('inert'/);
  assert.doesNotMatch(source, /navigationScrollTop|updateNavigationCurve|nav-spotlight|ellipseRadius/);
});

test('UX audit fixes keep reports, charts, labels, and public navigation truthful and usable', async () => {
  const [reports, alerts, charts, login, router, portal, resource, dataView, schemaForm, presentation, appStyles] = await Promise.all([
    readFile(new URL('../src/pages/reports.ts', import.meta.url), 'utf8'),
    readFile(new URL('../src/pages/alerts.ts', import.meta.url), 'utf8'),
    readFile(new URL('../src/components/charts.ts', import.meta.url), 'utf8'),
    readFile(new URL('../src/pages/login.ts', import.meta.url), 'utf8'),
    readFile(new URL('../src/app/router.ts', import.meta.url), 'utf8'),
    readFile(new URL('../src/pages/portal.ts', import.meta.url), 'utf8'),
    readFile(new URL('../src/pages/resource.ts', import.meta.url), 'utf8'),
    readFile(new URL('../src/components/data-view.ts', import.meta.url), 'utf8'),
    readFile(new URL('../src/components/schema-form.ts', import.meta.url), 'utf8'),
    readFile(new URL('../src/ui/presentation.ts', import.meta.url), 'utf8'),
    readFile(new URL('../src/styles/app.css', import.meta.url), 'utf8'),
  ]);
  assert.match(reports, /report\.output_format === 'docx'/);
  assert.match(reports, /aria-labelledby/);
  assert.match(alerts, /school_name/);
  assert.match(alerts, /academic_year_title/);
  assert.doesNotMatch(alerts, /Pagination<\{ id: string; title: string \}>/);
  assert.match(charts, /const segments/);
  assert.match(charts, /options\.points\.length/);
  assert.doesNotMatch(charts, /native-chart__point', tabindex/);
  assert.match(login, /id: 'page-content'/);
  assert.match(login, /h\('h1', \{ text: 'خوش آمدید' \}\)/);
  assert.match(router, /h\('main', \{ id: 'page-content', tabindex: '-1' \}, page\)/);
  assert.match(router, /document\.title = 'بارگذاری صفحه ناموفق بود \| هم‌آموز'/);
  assert.match(appStyles, /\.sidebar :focus-visible/);
  assert.match(portal, /پرتال خانواده و دانش‌آموز/);
  assert.doesNotMatch(portal, /text: 'Portal'/);
  assert.match(resource, /attendance-sessions[\s\S]*class_title[\s\S]*subject_title/);
  assert.match(resource, /role: 'region', tabindex: '0'/);
  assert.match(dataView, /aria-label': 'جزئیات فهرست'/);
  assert.doesNotMatch(schemaForm, /fieldset-marker/);
  assert.match(schemaForm, /name: path, tabindex: '-1'/);
  assert.match(presentation, /low: 'کم', medium: 'متوسط', high: 'زیاد'/);
});
