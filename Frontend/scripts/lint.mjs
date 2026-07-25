import { readdir, readFile } from 'node:fs/promises';
import { resolve, extname } from 'node:path';
const root = resolve('src');
const failures = [];
async function walk(dir) {
  for (const name of await readdir(dir, { withFileTypes: true })) {
    const path = resolve(dir, name.name);
    if (name.isDirectory()) await walk(path);
    else if (['.ts','.css','.html'].includes(extname(path))) {
      const text = await readFile(path, 'utf8');
      if (/\b(TODO|FIXME)\b/i.test(text)) failures.push(`${path}: unfinished marker`);
      if (/console\.(log|debug)\(/.test(text)) failures.push(`${path}: debug console call`);
      if (/[ \t]+$/m.test(text)) failures.push(`${path}: trailing whitespace`);
    }
  }
}
await walk(root);
if (failures.length) { console.error(failures.join('\n')); process.exit(1); }
console.log('Static lint checks passed.');
