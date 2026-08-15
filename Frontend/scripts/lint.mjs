import { readFile, readdir } from 'node:fs/promises';
import { dirname, extname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');

async function files(directory) {
  return (await Promise.all((await readdir(directory, { withFileTypes: true })).map(async entry => {
    const path = resolve(directory, entry.name);
    return entry.isDirectory() ? files(path) : [path];
  }))).flat();
}

const sourceFiles = (await files(resolve(root, 'src'))).filter(path => ['.js', '.mjs', '.html'].includes(extname(path)));
const failures = [];
for (const path of sourceFiles) {
  const value = await readFile(path, 'utf8');
  if (path.includes('/vendor/')) continue;
  if (/\beval\s*\(/.test(value)) failures.push(`${path}: eval is forbidden`);
  if (/\.innerHTML\s*=/.test(value)) failures.push(`${path}: unsafe innerHTML assignment`);
  if (/https?:\/\/(unpkg|cdn\.jsdelivr|cdnjs)/.test(value)) failures.push(`${path}: runtime CDN dependency`);
}
if (failures.length) throw new Error(failures.join('\n'));
console.log(`Linted ${sourceFiles.length} source files.`);
