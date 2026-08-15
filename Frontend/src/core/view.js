import { h, render, Fragment } from '../vendor/preact.mjs';
import htm from '../vendor/htm/index.mjs';
export * from '../vendor/hooks.mjs';

export const html = htm.bind(h);
export { h, render, Fragment };
