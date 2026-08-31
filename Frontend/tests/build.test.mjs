import test from 'node:test';
import assert from 'node:assert/strict';
import { access, readFile } from 'node:fs/promises';

test('entrypoint is self-hosted, RTL and CSP-friendly', async () => {
  const index = await readFile(new URL('../src/index.html', import.meta.url), 'utf8');
  assert.match(index, /<html lang="fa" dir="rtl">/);
  assert.match(index, /type="module" src="\/main\.js"/);
  assert.doesNotMatch(index, /<script[^>]+https?:\/\//);
  await access(new URL('../src/vendor/PREACT_LICENSE.txt', import.meta.url));
  await access(new URL('../src/vendor/htm/LICENSE.txt', import.meta.url));
});

test('CI installs build dependencies and Nginx serves native ESM with JavaScript MIME', async () => {
  const workflow = await readFile(new URL('../../.github/workflows/frontend-ci.yml', import.meta.url), 'utf8');
  const nginx = await readFile(new URL('../nginx.conf', import.meta.url), 'utf8');

  const installIndex = workflow.indexOf('run: npm ci');
  assert.notEqual(installIndex, -1, 'Frontend CI must install locked dependencies.');
  assert.ok(installIndex < workflow.indexOf('run: npm run lint'));
  assert.ok(installIndex < workflow.indexOf('run: npm test'));
  assert.match(workflow, /branches: \[main, "codex\/\*\*"\]/);
  assert.ok(nginx.includes('location ~* \\.(?:js|mjs)$'));
  assert.match(nginx, /default_type application\/javascript;/);
});
