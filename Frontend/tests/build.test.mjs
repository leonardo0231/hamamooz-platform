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
