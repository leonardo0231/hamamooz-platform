import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile, readdir } from 'node:fs/promises';

async function filesUnder(directory) {
  const entries = await readdir(directory, { withFileTypes: true });
  const files = await Promise.all(entries.map(entry => {
    const url = new URL(`${entry.name}${entry.isDirectory() ? '/' : ''}`, directory);
    return entry.isDirectory() ? filesUnder(url) : [url];
  }));
  return files.flat();
}

test('imports route is browser-resolvable without CDN or bare module imports', async () => {
  const assets = new URL('../dist/assets/', import.meta.url);
  const scripts = (await filesUnder(assets)).filter(file => file.pathname.endsWith('.js'));
  assert.ok(scripts.length > 1, 'expected the application and its lazy route chunks');

  const bareSpecifiers = [];
  let includesSpreadsheetParser = false;
  for (const script of scripts) {
    const source = await readFile(script, 'utf8');
    includesSpreadsheetParser ||= source.includes('sheet_to_json');
    for (const match of source.matchAll(/\b(?:from\s*|import\s*\()(['"])([^'"]+)\1/g)) {
      const specifier = match[2];
      if (!specifier.startsWith('.') && !specifier.startsWith('/') && !URL.canParse(specifier)) {
        bareSpecifiers.push(`${script.pathname}: ${specifier}`);
      }
    }
  }

  assert.equal(includesSpreadsheetParser, true, 'spreadsheet preview parser was not bundled');
  assert.deepEqual(bareSpecifiers, [], `browser-unresolvable module imports found:\n${bareSpecifiers.join('\n')}`);
});

test('imports upload uses the multipart field required by the API contract', async () => {
  const source = await readFile(new URL('../src/pages/imports.ts', import.meta.url), 'utf8');
  assert.match(source, /payload\.append\('source_file', file\)/);
  assert.doesNotMatch(source, /payload\.append\('file', file\)/);
});

test('production output retains brand styles, fonts, and public assets', async () => {
  const output = new URL('../dist/', import.meta.url);
  const [appCss, brandCss, favicon, estedad, vazirmatn] = await Promise.all([
    readFile(new URL('app.css', output), 'utf8'),
    readFile(new URL('brand.css', output), 'utf8'),
    readFile(new URL('favicon.svg', output), 'utf8'),
    readFile(new URL('fonts/Estedad.woff2', output)),
    readFile(new URL('fonts/Vazirmatn.woff2', output)),
  ]);

  assert.match(appCss, /@import\s+["']\.\/brand\.css["']/);
  assert.match(brandCss, /@font-face/);
  assert.match(favicon, /<svg/);
  assert.ok(estedad.byteLength > 0);
  assert.ok(vazirmatn.byteLength > 0);
});
