import * as React from 'react';
import { createRoot } from 'react-dom/client';
import { flushSync } from 'react-dom';
import htm from '../vendor/htm/index.mjs';

const roots = new WeakMap();

// The existing templates use HTM's browser-friendly attribute spelling. React
// uses a small set of camelCase DOM/SVG names and requires style to be an
// object, so normalize at the single element boundary instead of rewriting
// every report/dashboard template. This keeps the reviewed DOM and print CSS
// stable while making the renderer a real React element tree.
const propertyAliases = {
  class: 'className',
  for: 'htmlFor',
  tabindex: 'tabIndex',
  autocomplete: 'autoComplete',
  cellpadding: 'cellPadding',
  cellspacing: 'cellSpacing',
  colspan: 'colSpan',
  rowspan: 'rowSpan',
  readonly: 'readOnly',
  maxlength: 'maxLength',
  minlength: 'minLength',
  'stroke-width': 'strokeWidth',
  'stroke-linecap': 'strokeLinecap',
  'stroke-linejoin': 'strokeLinejoin',
  'stroke-dasharray': 'strokeDasharray',
  'text-anchor': 'textAnchor',
  'font-size': 'fontSize',
  'font-family': 'fontFamily',
  'font-weight': 'fontWeight',
  'stop-color': 'stopColor',
  'stop-opacity': 'stopOpacity',
  'vector-effect': 'vectorEffect',
};

function styleTextToObject(value) {
  if (typeof value !== 'string') return value;
  return Object.fromEntries(value.split(';').flatMap(declaration => {
    const separator = declaration.indexOf(':');
    if (separator < 0) return [];
    const property = declaration.slice(0, separator).trim();
    const styleValue = declaration.slice(separator + 1).trim();
    if (!property || !styleValue) return [];
    const reactProperty = property.startsWith('--')
      ? property
      : property.replace(/-([a-z])/g, (_, letter) => letter.toUpperCase());
    return [[reactProperty, styleValue]];
  }));
}

function normalizeProps(props) {
  if (!props) return props;
  const normalized = {};
  for (const [name, value] of Object.entries(props)) {
    const property = propertyAliases[name] ?? name;
    normalized[property] = property === 'style' ? styleTextToObject(value) : value;
  }
  return normalized;
}

export function createElement(type, props, ...children) {
  return React.createElement(type, normalizeProps(props), ...children);
}

export const html = htm.bind(createElement);

export function render(element, container) {
  let root = roots.get(container);
  if (!root) {
    root = createRoot(container);
    roots.set(container, root);
  }
  // Report readiness and the native print path inspect the DOM immediately
  // after this call. Flush the initial commit so React's concurrent root
  // cannot expose a half-rendered photo/chart tree to that readiness check.
  flushSync(() => root.render(element));
  return root;
}

export const h = createElement;
export const { Fragment } = React;
export * from 'react';
