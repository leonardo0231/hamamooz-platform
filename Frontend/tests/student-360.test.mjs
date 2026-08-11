import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';

const catalog = JSON.parse(
  await readFile(new URL('../src/api/generated/catalog.json', import.meta.url), 'utf8'),
);

test('Student 360 exposes independent generated-contract operations and lazy tabs', async () => {
  const [endpoints, page] = await Promise.all([
    readFile(new URL('../src/api/endpoints.ts', import.meta.url), 'utf8'),
    readFile(new URL('../src/pages/student.ts', import.meta.url), 'utf8'),
  ]);
  const operationIds = new Set(catalog.operations.map(operation => operation.id));
  const requiredIds = [
    'students_360_summary_retrieve',
    'students_360_academics_retrieve',
    'students_360_attendance_retrieve',
    'students_360_evaluations_retrieve',
    'students_360_reports_retrieve',
    'students_360_behavior_retrieve',
    'students_360_activities_retrieve',
    'students_360_risks_retrieve',
    'students_360_recommendations_retrieve',
  ];

  for (const operationId of requiredIds) {
    assert.equal(operationIds.has(operationId), true, `missing generated operation ${operationId}`);
    assert.match(endpoints, new RegExp(`operationPath\\('${operationId}'\\)`));
  }
  assert.match(page, /student360Api\.summary/);
  assert.match(page, /student360Api\.academics/);
  assert.match(page, /student360Api\.attendance/);
  assert.match(page, /student360Api\.evaluations/);
  assert.match(page, /student360Api\.reports/);
  assert.match(page, /student360Api\.behavior/);
  assert.match(page, /student360Api\.activities/);
  assert.match(page, /student360Api\.risks/);
  assert.match(page, /student360Api\.recommendations/);
  assert.doesNotMatch(page, /student360Api\.counseling/);
  assert.match(page, /aria-selected/);
});
