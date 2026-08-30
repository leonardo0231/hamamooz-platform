import { copyFile, cp, mkdir, readFile, rm, writeFile } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const source = resolve(root, 'src');
const output = resolve(root, 'dist');

await rm(output, { recursive: true, force: true });
await mkdir(output, { recursive: true });
await cp(source, output, { recursive: true });
await cp(resolve(root, 'public'), output, { recursive: true });

// The application is deliberately served as native ESM rather than through a
// JavaScript bundler.  Keep ECharts on the same origin for the production
// build: report charts must work in restricted school networks too.
await copyFile(
  resolve(root, 'node_modules', 'echarts', 'dist', 'echarts.esm.min.js'),
  resolve(output, 'vendor', 'echarts.mjs'),
);
await copyFile(
  resolve(root, 'node_modules', 'echarts', 'LICENSE'),
  resolve(output, 'vendor', 'ECHARTS_LICENSE.txt'),
);

const index = await readFile(resolve(output, 'index.html'), 'utf8');
if (!index.includes('dir="rtl"') || !index.includes('type="module"')) {
  throw new Error('Build validation failed: RTL document or module entry is missing.');
}

await writeFile(resolve(output, 'build-meta.json'), JSON.stringify({
  app: 'hamamooz-frontend',
  architecture: 'preact-esm',
  builtAt: new Date().toISOString(),
}, null, 2));

console.log('Built HamAmoz frontend into dist/.');
