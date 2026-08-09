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
  const source = await readFile(new URL('../src/pages/imports-simple.ts', import.meta.url), 'utf8');
  assert.match(source, /payload\.append\('source_file',\s*selected\)/);
  assert.doesNotMatch(source, /payload\.append\('file',/);
  assert.match(source, /comprehensive_school/);
  for (const sheet of ['کلاس‌بندی', 'دانش‌آموزان', 'ثبت اطلاعات']) {
    assert.match(source, new RegExp(sheet));
  }
});

test('student profile consumes the official evaluation analytics endpoint', async () => {
  const [source, endpoints] = await Promise.all([
    readFile(new URL('../src/pages/student.ts', import.meta.url), 'utf8'),
    readFile(new URL('../src/api/endpoints.ts', import.meta.url), 'utf8'),
  ]);
  assert.match(endpoints, /monthly_evaluations_analytics_retrieve/);
  assert.match(source, /monthlyEvaluations\.analytics/);
  assert.match(source, /روند پیشرفت/);
  assert.match(source, /رتبه در کلاس/);
  assert.match(source, /student\.organization_name/);
});

test('generic resource tables localize common enum values', async () => {
  const [resource, presentation] = await Promise.all([
    readFile(new URL('../src/pages/resource.ts', import.meta.url), 'utf8'),
    readFile(new URL('../src/ui/presentation.ts', import.meta.url), 'utf8'),
  ]);
  assert.match(presentation, /female: 'دختر'/);
  assert.match(presentation, /active: 'فعال'/);
  assert.match(resource, /labelForValue\(value\)/);
});

test('generic UI never renders API responses or object fields as raw JSON', async () => {
  const [resource, form, dom] = await Promise.all([
    readFile(new URL('../src/pages/resource.ts', import.meta.url), 'utf8'),
    readFile(new URL('../src/components/schema-form.ts', import.meta.url), 'utf8'),
    readFile(new URL('../src/utils/dom.ts', import.meta.url), 'utf8'),
  ]);
  assert.doesNotMatch(resource, /JSON\.stringify\(data/);
  assert.doesNotMatch(resource, /result-viewer/);
  assert.doesNotMatch(form, /ساختار JSON معتبر نیست/);
  assert.doesNotMatch(form, /value:\s*initial\s*\?\s*JSON\.stringify/);
  assert.doesNotMatch(dom, /return JSON\.stringify\(value\)/);
});

test('schema forms use named relation pickers and repeatable structured rows', async () => {
  const source = await readFile(new URL('../src/components/schema-form.ts', import.meta.url), 'utf8');
  for (const relation of ['organization', 'school', 'student', 'enrollment', 'class_section', 'assessment']) {
    assert.match(source, new RegExp(`${relation}:`));
  }
  assert.match(source, /relation-picker/);
  assert.match(source, /repeatable-list/);
  assert.match(source, /افزودن/);
});

test('production output retains brand styles, fonts, public assets, and responsive shell rules', async () => {
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
  assert.match(appCss, /\.sidebar__menu-viewport\s*\{[^}]*overflow-y:\s*auto/s);
  assert.match(appCss, /\.sidebar\.is-open\s*\{[^}]*translateX\(0\)/s);
  assert.match(appCss, /\.table-wrap\s*\{[^}]*overflow-x:\s*auto/s);
});
