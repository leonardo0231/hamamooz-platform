import { access, cp, mkdir, readFile, writeFile } from 'node:fs/promises';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';
const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
spawnSync(process.execPath, [resolve(root, 'scripts/clean.mjs')], { stdio: 'inherit' });
const localTsc = resolve(root, 'node_modules/typescript/bin/tsc');
let result;
try {
  await access(localTsc);
  result = spawnSync(process.execPath, [localTsc, '-p', resolve(root, 'tsconfig.json')], { stdio: 'inherit', cwd: root });
} catch {
  result = spawnSync(process.platform === 'win32' ? 'tsc.cmd' : 'tsc', ['-p', resolve(root, 'tsconfig.json')], { stdio: 'inherit', cwd: root });
}
if (result.error || result.status !== 0) process.exit(result.status ?? 1);
await mkdir(resolve(root, 'dist'), { recursive: true });
const parseEnv = text => Object.fromEntries(text.split(/\r?\n/).filter(line => line && !line.trim().startsWith('#') && line.includes('=')).map(line => { const index = line.indexOf('='); return [line.slice(0, index).trim(), line.slice(index + 1).trim()]; }));
let env = {};
try { env = parseEnv(await readFile(resolve(root, '.env'), 'utf8')); } catch {}
const apiBaseUrl = env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1/';
const appName = env.VITE_APP_NAME || 'هم‌آموز';
const requestTimeoutMs = env.VITE_REQUEST_TIMEOUT_MS || '20000';
const apiOrigin = new URL(apiBaseUrl).origin;
const sourceHtml = await readFile(resolve(root, 'src/index.html'), 'utf8');
await writeFile(resolve(root, 'dist/index.html'), sourceHtml.replaceAll('__API_BASE_URL__', apiBaseUrl).replaceAll('__API_ORIGIN__', apiOrigin).replaceAll('__APP_NAME__', appName).replaceAll('__REQUEST_TIMEOUT_MS__', requestTimeoutMs));
await cp(resolve(root, 'src/styles/app.css'), resolve(root, 'dist/app.css'));
const manifest = { builtAt: new Date().toISOString(), contract: 'contracts/openapi.yaml' };
await writeFile(resolve(root, 'dist/build-manifest.json'), JSON.stringify(manifest, null, 2));
const html = await readFile(resolve(root, 'dist/index.html'), 'utf8');
if (!html.includes('/assets/main.js')) throw new Error('index.html entrypoint is missing');
console.log('Frontend production build completed.');
