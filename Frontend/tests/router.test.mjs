import test from 'node:test';
import assert from 'node:assert/strict';
import { matchRoute, routes } from '../src/core/router.js';

test('route manifest keeps every production surface reachable', () => {
  assert.ok(routes.length >= 17);
  assert.equal(new Set(routes.map(route => route.id)).size, routes.length);
  assert.equal(matchRoute('/').id, 'dashboard');
  assert.equal(matchRoute('/students').id, 'students');
  assert.deepEqual({ ...matchRoute('/students/student-42').params }, { id: 'student-42' });
  assert.equal(matchRoute('/resources/behavior-events').params.tag, 'behavior-events');
  assert.equal(matchRoute('/unknown').id, 'not-found');
});

test('only login is public', () => {
  assert.deepEqual(routes.filter(route => route.public).map(route => route.id), ['login']);
});

test('administrative routes keep explicit role gates', () => {
  for (const id of ['imports', 'users', 'roles']) {
    const route = routes.find(item => item.id === id);
    assert.ok(route.roles?.length, `${id} must declare authorized roles`);
  }
});
