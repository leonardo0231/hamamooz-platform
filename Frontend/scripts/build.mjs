import { cp, mkdir, readFile, rm, writeFile } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const source = resolve(root, 'src');
const output = resolve(root, 'dist');

await rm(output, { recursive: true, force: true });
await mkdir(output, { recursive: true });
await cp(source, output, { recursive: true });
await cp(resolve(root, 'public'), output, { recursive: true });

// Report charts are inline SVG in the report component.  Do not copy a
// canvas/chart runtime into the production bundle: the same DOM must be used
// for screen preview and the browser's A3 print dialog, even when the school
// network cannot install optional npm packages.

const index = await readFile(resolve(output, 'index.html'), 'utf8');
if (!index.includes('dir="rtl"') || !index.includes('type="module"')) {
  throw new Error('Build validation failed: RTL document or module entry is missing.');
}

await writeFile(resolve(output, 'build-meta.json'), JSON.stringify({
  app: 'hamamooz-frontend',
  architecture: 'preact-esm-react-compatible-report',
  builtAt: new Date().toISOString(),
}, null, 2));

console.log('Built HamAmoz frontend into dist/.');
