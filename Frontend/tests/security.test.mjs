import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile, readdir } from 'node:fs/promises';
import { resolve } from 'node:path';

async function sourceFiles(directory) {
  return (await Promise.all((await readdir(directory, { withFileTypes: true })).map(entry => {
    const path = resolve(directory, entry.name);
    return entry.isDirectory() ? sourceFiles(path) : [path];
  }))).flat();
}

test('application source has no runtime CDN or unsafe HTML injection', async () => {
  const files = (await sourceFiles(resolve('src'))).filter(path => /\.(?:js|mjs|html)$/.test(path) && !path.includes('/vendor/'));
  for (const path of files) {
    const content = await readFile(path, 'utf8');
    assert.doesNotMatch(content, /\beval\s*\(/, path);
    assert.doesNotMatch(content, /\.innerHTML\s*=/, path);
    assert.doesNotMatch(content, /https?:\/\/(?:unpkg|cdn\.jsdelivr|cdnjs)/, path);
  }
});

test('access tokens are not persisted to web storage', async () => {
  const store = await readFile(new URL('../src/core/store.js', import.meta.url), 'utf8');
  assert.doesNotMatch(store, /setItem\([^\n]*accessToken/);
  assert.match(store, /REFRESH_REMEMBERED/);
});

test('post-login navigation rejects protocol-relative return targets', async () => {
  const login = await readFile(new URL('../src/pages/login.js', import.meta.url), 'utf8');
  assert.match(login, /!requested\.startsWith\('\/\/'\)/);
});
