import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';

const tokens = await readFile(new URL('../src/styles/tokens.css', import.meta.url), 'utf8');
const responsive = await readFile(new URL('../src/styles/responsive.css', import.meta.url), 'utf8');
const shell = await readFile(new URL('../src/components/shell.js', import.meta.url), 'utf8');

test('reference design tokens and RTL shell are explicit', () => {
  for (const token of ['--nav:', '--primary:', '--surface:', '--radius-md:', '--sidebar-width:']) assert.match(tokens, new RegExp(token));
  assert.match(shell, /sidebar__link/);
  assert.match(shell, /مرکز هشدارها/);
  assert.match(shell, /پیشنهادهای هوشمند/);
});

test('responsive rules cover desktop, tablet and mobile', () => {
  assert.match(responsive, /max-width:1280px/);
  assert.match(responsive, /max-width:1024px/);
  assert.match(responsive, /max-width:768px/);
  assert.match(responsive, /max-width:560px/);
  assert.match(responsive, /prefers-reduced-motion/);
  assert.match(responsive, /@media print/);
});
