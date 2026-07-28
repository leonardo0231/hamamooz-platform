import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile, readdir } from 'node:fs/promises';
import { join } from 'node:path';

const root = new URL('../src/', import.meta.url);
const catalog = JSON.parse(await readFile(new URL('../src/api/generated/catalog.json', import.meta.url), 'utf8'));
const operationIds = new Set(catalog.operations.map(operation => operation.id));


function literalApiRequestOffsets(source) {
  const offsets = [];
  let cursor = 0;
  while ((cursor = source.indexOf('apiRequest', cursor)) !== -1) {
    let index = cursor + 'apiRequest'.length;
    while (/\s/.test(source[index] ?? '')) index += 1;
    if (source[index] === '<') {
      let depth = 0;
      do {
        if (source[index] === '<') depth += 1;
        if (source[index] === '>') depth -= 1;
        index += 1;
      } while (index < source.length && depth > 0);
      while (/\s/.test(source[index] ?? '')) index += 1;
    }
    if (source[index] !== '(') { cursor += 1; continue; }
    index += 1;
    while (/\s/.test(source[index] ?? '')) index += 1;
    if (["'", '"', '`'].includes(source[index] ?? '')) offsets.push(cursor);
    cursor += 1;
  }
  return offsets;
}

async function sourceFiles(relativeDirectory) {
  const directoryUrl = new URL(relativeDirectory, root);
  const entries = await readdir(directoryUrl, { withFileTypes: true });
  const files = [];
  for (const entry of entries) {
    const relativePath = join(relativeDirectory, entry.name);
    if (entry.isDirectory()) files.push(...await sourceFiles(`${relativePath}/`));
    else if (entry.isFile() && entry.name.endsWith('.ts')) files.push(new URL(relativePath, root));
  }
  return files;
}

test('central endpoint registry only references operation IDs present in OpenAPI', async () => {
  const source = await readFile(new URL('../src/api/endpoints.ts', import.meta.url), 'utf8');
  const referencedIds = [...source.matchAll(/operationPath\('([^']+)'\)/g)].map(match => match[1]);
  assert.ok(referencedIds.length > 0, 'endpoint registry does not contain operation bindings');
  for (const id of referencedIds) assert.equal(operationIds.has(id), true, `unknown operation ID ${id}`);
  assert.doesNotMatch(source, /\/api\/v1\//, 'endpoint registry must not duplicate literal API paths');
});

test('application pages and components do not pass literal endpoints to apiRequest', async () => {
  const files = [
    ...await sourceFiles('app/'),
    ...await sourceFiles('components/'),
    ...await sourceFiles('pages/'),
  ];
  for (const file of files) {
    const source = await readFile(file, 'utf8');
    assert.deepEqual(literalApiRequestOffsets(source), [], `literal endpoint passed to apiRequest in ${file.pathname}`);
    assert.doesNotMatch(source, /['"`]\/api\/v1\//, `literal API path found in ${file.pathname}`);
  }
});
