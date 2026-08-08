export type Child = Node | string | number | null | undefined | false;

export function h<K extends keyof HTMLElementTagNameMap>(
  tag: K,
  attributes: Record<string, unknown> = {},
  ...children: Child[]
): HTMLElementTagNameMap[K] {
  const element = document.createElement(tag);
  for (const [key, value] of Object.entries(attributes)) {
    if (value === null || value === undefined || value === false) continue;
    if (key === 'className') element.className = String(value);
    else if (key === 'text') element.textContent = String(value);
    else if (key === 'dataset' && typeof value === 'object') Object.assign(element.dataset, value);
    else if (key === 'style' && typeof value === 'object') Object.assign(element.style, value);
    else if (key.startsWith('on') && typeof value === 'function') element.addEventListener(key.slice(2).toLowerCase(), value as EventListener);
    else if (key in element && !key.startsWith('aria-')) (element as unknown as Record<string, unknown>)[key] = value;
    else element.setAttribute(key, value === true ? '' : String(value));
  }
  append(element, ...children);
  return element;
}

export function append(parent: Node, ...children: Child[]): void {
  for (const child of children.flat(Infinity) as Child[]) {
    if (child === null || child === undefined || child === false) continue;
    parent.appendChild(child instanceof Node ? child : document.createTextNode(String(child)));
  }
}

export function clear(element: Element): void {
  element.replaceChildren();
}

export function qs<T extends Element>(selector: string, parent: ParentNode = document): T | null {
  return parent.querySelector<T>(selector);
}

export function formatNumber(value: unknown, maximumFractionDigits = 2): string {
  const numeric = typeof value === 'number' ? value : Number(value);
  return Number.isFinite(numeric) ? new Intl.NumberFormat('fa-IR', { maximumFractionDigits }).format(numeric) : '—';
}

export function formatDate(value: unknown, withTime = false): string {
  if (!value) return '—';
  const date = new Date(String(value));
  if (Number.isNaN(date.getTime())) return String(value);
  return new Intl.DateTimeFormat('fa-IR-u-ca-persian', withTime ? { dateStyle: 'medium', timeStyle: 'short' } : { dateStyle: 'medium' }).format(date);
}

export function debounce<T extends (...args: never[]) => void>(callback: T, wait: number): (...args: Parameters<T>) => void {
  let timer: ReturnType<typeof setTimeout> | undefined;
  return (...args: Parameters<T>) => {
    clearTimeout(timer);
    timer = setTimeout(() => callback(...args), wait);
  };
}

export function initials(name: string): string {
  return name.split(/\s+/).filter(Boolean).slice(0, 2).map(part => part[0]).join('') || 'ک';
}

export function safeText(value: unknown): string {
  if (value === null || value === undefined || value === '') return '—';
  if (typeof value === 'boolean') return value ? 'بله' : 'خیر';
  if (Array.isArray(value)) return value.map(item => safeText(item)).join('، ');
  if (typeof value === 'object') {
    const object = value as Record<string, unknown>;
    const label = object.full_name ?? object.student_name ?? object.title ?? object.name ?? object.username ?? object.code;
    if (label !== null && label !== undefined && label !== '') return String(label);
    const primitive = Object.values(object).find(item => item !== null && item !== undefined && ['string', 'number', 'boolean'].includes(typeof item));
    return primitive === undefined ? 'اطلاعات ثبت‌شده' : safeText(primitive);
  }
  return String(value);
}


export function onWindowEventWhileConnected(
  element: HTMLElement,
  type: string,
  handler: (event: Event) => void,
): () => void {
  const listener = (event: Event): void => {
    if (!element.isConnected) {
      window.removeEventListener(type, listener);
      return;
    }
    handler(event);
  };
  window.addEventListener(type, listener);
  return () => window.removeEventListener(type, listener);
}
