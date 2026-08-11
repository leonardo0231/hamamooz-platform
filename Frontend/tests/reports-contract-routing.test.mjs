import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';

const source = relative => readFile(new URL(relative, import.meta.url), 'utf8');
const catalog = JSON.parse(await source('../src/api/generated/catalog.json'));

function operation(id) {
  const value = catalog.operations.find(item => item.id === id);
  assert.ok(value, `missing operation ${id}`);
  return value;
}

function frontendReporterRoles(reportsPage) {
  const match = reportsPage.match(/const reporterRoles:\s*Role\[\]\s*=\s*\[([\s\S]*?)\];/);
  assert.ok(match, 'reports page must declare its reporter capability roles');
  return [...match[1].matchAll(/'([^']+)'/g)].map(([, role]) => role);
}

function backendReporterRoles(reportsView) {
  const match = reportsView.match(/REPORTERS\s*=\s*\[([\s\S]*?)\]\s*REPORT_REVIEWERS/);
  assert.ok(match, 'backend report reporter policy is missing');
  return [...match[1].matchAll(/Role\.([A-Z_]+)/g)].map(([, role]) => role.toLowerCase());
}

test('submitted-report dashboard drill-down uses the ReportDraft contract, not archive job statuses', async () => {
  const [dashboard, reports] = await Promise.all([
    source('../src/api/role-dashboard.ts'),
    source('../src/pages/reports.ts'),
  ]);
  const drafts = operation('reports_drafts_list');
  const archives = operation('reports_list');

  assert.equal(drafts.path, '/api/v1/reports/drafts/');
  assert.deepEqual(drafts.responseSchema, { $ref: '#/components/schemas/PaginatedReportDraftList' });
  assert.deepEqual(archives.responseSchema, { $ref: '#/components/schemas/PaginatedReportArchiveList' });
  assert.match(dashboard, /const reportDraftsRoute = '\/reports\?view=drafts';/);
  assert.match(dashboard, /\[operationPath\('reports_drafts_list'\)\]: reportDraftsRoute/);
  assert.match(reports, /const draftsListOperation = requiredOperation\('reports_drafts_list'\);/);
  assert.match(reports, /apiRequest<Pagination<ReportDraft>>\(draftsListOperation\.path/);
  assert.match(reports, /status:\s*'submitted'/);
  assert.doesNotMatch(reports, /response\.results\.filter\(report => report\.status === 'draft'/);
  assert.doesNotMatch(reports, /apiRequest<Pagination<ReportArchive>>\(draftsListOperation\.path/);
});

test('report creation and preview are gated by the backend REPORTERS policy plus scope', async () => {
  const [reports, backendViews] = await Promise.all([
    source('../src/pages/reports.ts'),
    source('../../Backend/hamamooz/apps/reports/views.py'),
  ]);

  assert.deepEqual(frontendReporterRoles(reports), backendReporterRoles(backendViews));
  assert.match(backendViews, /"create": REPORTERS/);
  assert.match(backendViews, /"preview": REPORTERS/);
  assert.match(reports, /const hasReporterCapability = hasAnyRole\(reporterRoles\);/);
  assert.match(reports, /const canCreateOrPreview = hasReporterCapability && hasWriteScope\(\);/);
  assert.doesNotMatch(reports, /disabled:\s*!hasWriteScope\(\)/);
});
