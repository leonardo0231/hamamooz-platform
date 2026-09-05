import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import {
  COMPREHENSIVE_IMPORT_TYPE,
  MAX_IMPORT_FILE_BYTES,
  canCancelImport,
  canRetryImport,
  importStatusLabel,
  isImportInProgress,
  validateComprehensiveImportFile,
} from '../src/core/imports.js';

test('comprehensive import accepts only XLSX files up to 10 MB', () => {
  assert.equal(COMPREHENSIVE_IMPORT_TYPE, 'comprehensive_school');
  assert.equal(validateComprehensiveImportFile({ name: 'school.xlsx', size: MAX_IMPORT_FILE_BYTES }), null);
  assert.match(validateComprehensiveImportFile({ name: 'school.xls', size: 1 }), /XLSX/);
  assert.match(validateComprehensiveImportFile({ name: 'school.xlsx', size: MAX_IMPORT_FILE_BYTES + 1 }), /۱۰ مگابایت/);
});

test('import job transitions expose only valid retry and cancel actions', () => {
  assert.equal(isImportInProgress({ status: 'queued' }), true);
  assert.equal(isImportInProgress({ status: 'processing' }), true);
  assert.equal(isImportInProgress({ status: 'completed' }), false);
  assert.equal(canCancelImport({ status: 'processing' }), true);
  assert.equal(canCancelImport({ status: 'failed' }), false);
  assert.equal(canRetryImport({ status: 'failed' }), true);
  assert.equal(canRetryImport({ status: 'completed' }), false);
  assert.equal(importStatusLabel('completed'), 'تکمیل‌شده');
});

test('imports page uses multipart upload, authenticated blob downloads and a dedicated route', async () => {
  const page = await readFile(new URL('../src/pages/imports.js', import.meta.url), 'utf8');
  const main = await readFile(new URL('../src/main.js', import.meta.url), 'utf8');
  assert.match(page, /new FormData\(\)/);
  assert.match(page, /body\.set\('school', selectedSchool\)/);
  assert.match(page, /body\.set\('import_type', COMPREHENSIVE_IMPORT_TYPE\)/);
  assert.match(page, /body\.set\('source_file', file, file\.name\)/);
  assert.match(page, /imports\/\$\{job\.id\}\/retry\//);
  assert.match(page, /imports\/\$\{job\.id\}\/cancel\//);
  assert.match(page, /imports\/\$\{job\.id\}\/errors\//);
  assert.match(page, /responseType: 'blob'/);
  assert.match(page, /downloadBlob/);
  assert.match(main, /ImportsPage/);
  assert.match(main, /case 'imports'/);
});
