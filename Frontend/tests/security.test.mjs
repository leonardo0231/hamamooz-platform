import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';

const client = await readFile(new URL('../src/api/client.ts', import.meta.url), 'utf8');
const store = await readFile(new URL('../src/app/store.ts', import.meta.url), 'utf8');

test('API client centralizes required headers and shared refresh', () => {
  assert.match(client, /let refreshPromise:/);
  assert.match(client, /X-Request-ID/);
  assert.match(client, /X-School-ID/);
  assert.match(client, /X-Organization-ID/);
  assert.match(client, /retryAuth: false/);
});

test('access token is not persisted in browser storage', () => {
  assert.doesNotMatch(store, /localStorage\.setItem\([^\n]*access/i);
  assert.doesNotMatch(store, /sessionStorage\.setItem\([^\n]*access/i);
});
