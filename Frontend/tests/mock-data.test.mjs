import test from 'node:test';
import assert from 'node:assert/strict';
import { alerts, dashboardData, students } from '../src/core/mock-data.js';

test('dashboard fixtures match chart and label dimensions', () => {
  assert.equal(dashboardData.performance.length, dashboardData.months.length);
  assert.equal(dashboardData.kpis.length, 4);
  assert.ok(dashboardData.grades.every(item => item.value > 0 && item.value <= 20));
});

test('student and alert references are internally consistent', () => {
  const ids = new Set(students.map(student => student.id));
  assert.equal(ids.size, students.length);
  assert.ok(alerts.every(alert => ids.has(alert.studentId)));
  assert.ok(alerts.every(alert => ['critical', 'important', 'review'].includes(alert.severity)));
});
