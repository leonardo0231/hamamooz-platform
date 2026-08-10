import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';

const catalog = JSON.parse(await readFile(new URL('../src/api/generated/catalog.json', import.meta.url), 'utf8'));
const keys = new Set(catalog.operations.map(operation => `${operation.method} ${operation.path}`));

function resolveSchema(schema) {
  if (!schema?.$ref) return schema;
  return catalog.schemas[schema.$ref.split('/').at(-1)];
}

function operation(id) {
  const value = catalog.operations.find(item => item.id === id);
  assert.ok(value, `missing operation ${id}`);
  return value;
}

test('generated API catalog has the expected contract size', () => {
  assert.equal(catalog.operations.length, 173);
  assert.equal(Object.keys(catalog.schemas).length, 170);
});

test('import create contract only exposes the comprehensive school workbook type', () => {
  const request = catalog.schemas.ImportJobCreateRequest;
  assert.ok(request);
  assert.deepEqual(resolveSchema(request.properties.import_type).enum, ['comprehensive_school']);
});

test('dashboard and import page response shapes remain pinned to the OpenAPI contract', () => {
  const dashboard = operation('monthly_evaluations_dashboard_retrieve');
  assert.deepEqual(dashboard.responseSchema, { $ref: '#/components/schemas/EvaluationDashboard' });
  assert.deepEqual(
    Object.keys(catalog.schemas.EvaluationDashboard.properties).sort(),
    ['counts', 'domain_scores', 'monthly_trend', 'performance_distribution', 'rank_scope', 'students'],
  );

  const imports = operation('imports_list');
  assert.deepEqual(imports.responseSchema, { $ref: '#/components/schemas/PaginatedImportJobList' });
  assert.deepEqual(
    Object.keys(catalog.schemas.ImportJob.properties).sort(),
    [
      'checksum', 'created_at', 'error_count', 'errors', 'finished_at', 'id', 'import_type', 'organization',
      'organization_name', 'requested_by', 'requested_by_name', 'result_summary', 'school', 'school_name',
      'source_file', 'started_at', 'status', 'status_display', 'successful_rows', 'total_rows', 'updated_at',
    ],
  );
});

test('critical authentication and dashboard endpoints exist', () => {
  for (const key of [
    'POST /api/v1/auth/token/',
    'POST /api/v1/auth/token/refresh/',
    'POST /api/v1/auth/logout/',
    'GET /api/v1/auth/me/',
    'GET /api/v1/dashboard/summary/',
  ]) assert.equal(keys.has(key), true, `missing ${key}`);
});

test('critical operational endpoints exist', () => {
  for (const key of [
    'GET /api/v1/students/',
    'POST /api/v1/attendance-sessions/{id}/bulk-mark/',
    'POST /api/v1/imports/',
    'POST /api/v1/imports/{id}/cancel/',
    'GET /api/v1/imports/{id}/errors/',
    'GET /api/v1/imports/templates/{template_type}/',
    'GET /api/v1/monthly-evaluations/',
    'POST /api/v1/reports/',
    'GET /api/v1/reports/{id}/download/',
  ]) assert.equal(keys.has(key), true, `missing ${key}`);
});
