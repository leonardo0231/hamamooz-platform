import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';

const catalog = JSON.parse(await readFile(new URL('../src/api/generated/catalog.json', import.meta.url), 'utf8'));
const keys = new Set(catalog.operations.map(operation => `${operation.method} ${operation.path}`));

test('generated API catalog has the expected contract size', () => {
  assert.equal(catalog.operations.length, 170);
  assert.equal(Object.keys(catalog.schemas).length, 160);
});

test('import contract exposes the comprehensive school workbook type', () => {
  assert.ok(catalog.schemas.ImportTypeEnum);
  assert.equal(catalog.schemas.ImportTypeEnum.enum.includes('comprehensive_school'), true);
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
