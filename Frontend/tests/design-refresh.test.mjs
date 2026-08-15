import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';

const read = path => readFile(new URL(`../${path}`, import.meta.url), 'utf8');

test('visual refresh stylesheet is wired into source and production build', async () => {
  const [html, buildScript, stylesheet] = await Promise.all([
    read('src/index.html'),
    read('scripts/build.mjs'),
    read('src/styles/design-refresh.css'),
  ]);

  assert.match(html, /<html lang="fa" dir="rtl">/);
  assert.match(html, /href="\/design-refresh\.css"/);
  assert.match(buildScript, /src\/styles\/design-refresh\.css/);
  assert.match(buildScript, /dist\/design-refresh\.css/);
  assert.match(stylesheet, /\.sidebar\s*\{/);
  assert.match(stylesheet, /\.metric-grid/);
  assert.match(stylesheet, /@media \(max-width: 1080px\)/);
  assert.match(stylesheet, /@media \(prefers-reduced-motion: reduce\)/);
});

test('visual refresh keeps semantic status colors distinct', async () => {
  const stylesheet = await read('src/styles/design-refresh.css');

  assert.match(stylesheet, /--hm-success:/);
  assert.match(stylesheet, /--hm-warning:/);
  assert.match(stylesheet, /--hm-danger:/);
  assert.match(stylesheet, /attention-strip--success/);
  assert.match(stylesheet, /attention-strip--warning/);
  assert.match(stylesheet, /attention-strip--danger/);
});
