import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { actionRequestSchema, hasActionSchemaOverride } from '../dist/assets/api/action-schemas.js';

const catalog = JSON.parse(await readFile(new URL('../src/api/generated/catalog.json', import.meta.url), 'utf8'));
const operation = id => {
  const result = catalog.operations.find(item => item.id === id);
  assert.ok(result, `missing operation ${id}`);
  return result;
};

test('custom action bodies use serializers from the backend implementation', () => {
  const reject = actionRequestSchema(operation('assessments_reject_create'));
  assert.deepEqual(reject.required, ['reason']);
  assert.equal(reject.properties.reason.minLength, 3);

  const bulkAttendance = actionRequestSchema(operation('attendance_sessions_bulk_mark_create'));
  assert.deepEqual(bulkAttendance.required, ['records']);
  assert.equal(bulkAttendance.properties.records.type, 'array');

  const guardian = actionRequestSchema(operation('students_guardians_create'));
  assert.equal(Object.hasOwn(guardian.properties, 'can_pick_up'), true);
  assert.equal(Object.hasOwn(guardian.properties, 'can_receive_notifications'), false);
});

test('password and report preview overrides do not expose inferred model serializers', () => {
  const password = actionRequestSchema(operation('users_change_password_create'));
  assert.deepEqual(password.required, ['new_password']);
  assert.equal(Object.hasOwn(password.properties, 'username'), false);
  assert.equal(Object.hasOwn(password.properties, 'new_password'), true);

  const preview = actionRequestSchema(operation('reports_preview_create'));
  assert.deepEqual(preview.required, ['report_type', 'term']);
  assert.equal(Object.hasOwn(preview.properties, 'class_section'), true);
  assert.equal(hasActionSchemaOverride('reports_preview_create'), true);
});
