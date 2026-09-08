import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { renderToStaticMarkup } from 'react-dom/server';
import { html } from '../src/core/view.js';

const packageJson = JSON.parse(await readFile(new URL('../package.json', import.meta.url), 'utf8'));
const viewSource = await readFile(new URL('../src/core/view.js', import.meta.url), 'utf8');
const buildSource = await readFile(new URL('../scripts/build.mjs', import.meta.url), 'utf8');
const viteConfig = await readFile(new URL('../vite.config.mjs', import.meta.url), 'utf8');

test('the frontend uses React and ReactDOM with the existing HTM template boundary', () => {
  assert.match(viewSource, /from ['"]react['"]/);
  assert.match(viewSource, /from ['"]react-dom\/client['"]/);
  assert.match(viewSource, /from ['"]react-dom['"]/);
  assert.match(viewSource, /flushSync/);
  assert.match(viewSource, /htm\.bind\(createElement\)/);
  assert.doesNotMatch(viewSource, /vendor\/(?:preact|hooks)/);
  assert.equal(packageJson.dependencies.react, '19.2.8');
  assert.equal(packageJson.dependencies['react-dom'], '19.2.8');
  assert.equal(packageJson.devDependencies.vite, '8.2.2');
  assert.match(buildSource, /from ['"]vite['"]/);
  assert.match(viteConfig, /reportSample/);
});

test('the HTM adapter preserves report classes, styles and SVG attributes in ReactDOM', () => {
  const template = [
    '<div class="report-test" style="',
    '"><svg viewBox="0 0 10 10"><line stroke-width="2" stroke-linecap="round" text-anchor="middle" /></svg></div>',
  ];
  template.raw = template;
  const markup = renderToStaticMarkup(html(template, '--report-accent:#0f766e;width:20px;background:red'));

  assert.match(markup, /class="report-test"/);
  assert.match(markup, /style="--report-accent:#0f766e;width:20px;background:red"/);
  assert.match(markup, /stroke-width="2"/);
  assert.match(markup, /stroke-linecap="round"/);
  assert.match(markup, /text-anchor="middle"/);
});
