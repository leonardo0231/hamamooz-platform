import { readFile, writeFile } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { build } from 'vite';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const output = resolve(root, 'dist');

await build({
  configFile: resolve(root, 'vite.config.mjs'),
  mode: 'production',
});

const index = await readFile(resolve(output, 'index.html'), 'utf8');
const reportSample = await readFile(resolve(output, 'report-sample.html'), 'utf8');
if (!index.includes('dir="rtl"') || !index.includes('type="module"')) {
  throw new Error('Build validation failed: RTL document or module entry is missing.');
}
if (!reportSample.includes('A3 landscape') || !reportSample.includes('type="module"')) {
  throw new Error('Build validation failed: standalone A3 report entry is missing.');
}

await writeFile(resolve(output, 'build-meta.json'), JSON.stringify({
  app: 'hamamooz-frontend',
  architecture: 'react-esm-vite-htm-svg-report',
  entries: ['index.html', 'report-sample.html'],
  builtAt: new Date().toISOString(),
}, null, 2));

console.log('Built HamAmoz frontend into dist/.');
