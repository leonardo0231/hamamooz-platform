import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile, mkdtemp, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { build } from 'esbuild';

const origin = 'https://hamamooz.test';

function installBrowserStubs() {
  const storage = { getItem: () => null, setItem: () => undefined, removeItem: () => undefined };
  globalThis.window = { __HAMAMOOZ_CONFIG__: {}, localStorage: storage, sessionStorage: storage };
  globalThis.Node = class {};
  globalThis.document = {
    querySelector: () => null,
    createElement: () => ({
      className: '', dataset: {}, style: {}, addEventListener: () => undefined,
      appendChild: () => undefined, setAttribute: () => undefined,
    }),
  };
  globalThis.location = new URL(`${origin}/login`);
}

async function loadBundledModule(entry) {
  const directory = await mkdtemp(join(tmpdir(), 'hamamooz-portal-auth-routing-'));
  const output = join(directory, 'router.mjs');
  installBrowserStubs();
  try {
    await build({
      entryPoints: [fileURLToPath(new URL(entry, import.meta.url))],
      bundle: true,
      format: 'esm',
      platform: 'node',
      target: 'node20',
      outfile: output,
    });
    return await import(`${pathToFileURL(output).href}?test=${Date.now()}`);
  } finally {
    await rm(directory, { recursive: true, force: true });
  }
}

const redirectPolicy = loadBundledModule('../src/app/router.ts');
const dashboardPolicy = loadBundledModule('../src/pages/dashboard-entry.ts');

test('post-login routing defaults portal-only identities to the portal and staff identities to home', async () => {
  const { defaultAuthenticatedPath, postLoginRedirectPath } = await redirectPolicy;

  assert.equal(defaultAuthenticatedPath([]), '/portal');
  assert.equal(defaultAuthenticatedPath(['teacher']), '/');
  assert.equal(postLoginRedirectPath(null, [], origin), '/portal');
  assert.equal(postLoginRedirectPath(null, ['teacher'], origin), '/');
  assert.equal(postLoginRedirectPath('/portal?tab=reports#latest', ['teacher'], origin), '/portal?tab=reports#latest');
});

test('post-login routing only accepts same-origin internal return targets', async () => {
  const { postLoginRedirectPath, safeReturnTo } = await redirectPolicy;

  assert.equal(safeReturnTo('/students?status=open#results', origin), '/students?status=open#results');
  for (const unsafeTarget of ['//evil.test', '/\\evil.test', 'https://evil.test', 'javascript:alert(1)', '/login?returnTo=/portal']) {
    assert.equal(safeReturnTo(unsafeTarget, origin), null, `${unsafeTarget} must be rejected`);
    assert.equal(postLoginRedirectPath(unsafeTarget, ['teacher'], origin), '/');
  }
});

test('both login entry paths share the redirect policy, empty roles are not a staff dashboard, and alerts are canonicalized safely', async () => {
  const [login, router, { dashboardKindForRoles }] = await Promise.all([
    readFile(new URL('../src/pages/login.ts', import.meta.url), 'utf8'),
    readFile(new URL('../src/app/router.ts', import.meta.url), 'utf8'),
    dashboardPolicy,
  ]);

  assert.match(login, /navigate\(postLoginRedirectPath\(returnTo\), true\)/);
  assert.match(router, /location\.pathname\.startsWith\('\/login'\)[\s\S]*?navigate\(postLoginRedirectPath\(returnTo\), true\)/);
  assert.match(router, /location\.pathname === '\/' && defaultAuthenticatedPath\(\) === '\/portal'/);
  assert.equal(dashboardKindForRoles([]), null);
  assert.equal(dashboardKindForRoles(['teacher']), 'teacher');
  assert.ok(router.includes("pattern: /^\\/alerts\\/?$/, title: 'مرکز هشدارها', private: true, roles: attendanceWorkspaceRoles"));
  assert.match(router, /navigate\(`\/attendance\/alerts\$\{location\.search\}\$\{location\.hash\}`, true\)/);
});
