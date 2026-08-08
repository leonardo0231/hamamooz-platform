import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';

const catalog = JSON.parse(await readFile(new URL('../src/api/generated/catalog.json', import.meta.url), 'utf8'));
const keys = new Set(catalog.operations.map(operation => `${operation.method} ${operation.path}`));

function resolveSchema(schema) {
  if (!schema?.$ref) return schema;
  const name = schema.$ref.split('/').at(-1);
  return catalog.schemas[name];
}

test('generated API catalog has the expected contract surface', () => {
  assert.ok(catalog.operations.length >= 173);
  assert.ok(Object.keys(catalog.schemas).length >= 170);
});

test('import create contract only exposes the comprehensive school workbook type', () => {
  const request = catalog.schemas.ImportJobCreateRequest;
  assert.ok(request);
  const importType = resolveSchema(request.properties.import_type);
  assert.deepEqual(importType.enum, ['comprehensive_school']);
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
    'GET /api/v1/monthly-evaluations/catalog/',
    'POST /api/v1/monthly-evaluations/manual/',
    'DELETE /api/v1/monthly-evaluations/{id}/manual/',
    'POST /api/v1/reports/',
    'GET /api/v1/reports/{id}/download/',
  ]) assert.equal(keys.has(key), true, `missing ${key}`);
});
