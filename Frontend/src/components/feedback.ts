import { ApiError } from '../api/types.js';
import { h } from '../utils/dom.js';
import { icon } from './icons.js';

const toastRegion = h('div', { className: 'toast-region', role: 'status', 'aria-live': 'polite', 'aria-atomic': 'false' });

export function mountToasts(): void {
  if (!toastRegion.isConnected) document.body.append(toastRegion);
}

export function toast(message: string, kind: 'success' | 'error' | 'info' = 'info', detail?: string): void {
  mountToasts();
  const item = h('div', { className: `toast toast--${kind}` },
    icon(kind === 'success' ? 'check' : kind === 'error' ? 'warning' : 'bell'),
    h('div', {}, h('strong', { text: message }), detail ? h('small', { text: detail }) : null),
  );
  toastRegion.append(item);
  setTimeout(() => item.remove(), 5000);
}

export function loadingState(label = 'در حال دریافت اطلاعات…'): HTMLElement {
  return h('div', { className: 'state-panel', role: 'status' }, h('span', { className: 'spinner', 'aria-hidden': 'true' }), h('p', { text: label }));
}

export function emptyState(title: string, description: string, action?: HTMLElement): HTMLElement {
  return h('div', { className: 'state-panel state-panel--empty' }, icon('file', 'state-icon'), h('h3', { text: title }), h('p', { text: description }), action);
}

export function errorState(error: unknown, retry?: () => void): HTMLElement {
  const apiError = error instanceof ApiError ? error : null;
  const message = apiError?.message ?? (error instanceof Error ? error.message : 'خطای ناشناخته');
  return h('div', { className: 'state-panel state-panel--error', role: 'alert' },
    icon('warning', 'state-icon'),
    h('h3', { text: 'دریافت اطلاعات ناموفق بود' }),
    h('p', { text: message }),
    apiError?.requestId ? h('small', { text: `شناسه پیگیری: ${apiError.requestId}` }) : null,
    retry ? h('button', { className: 'button button--secondary', type: 'button', onClick: retry }, icon('refresh'), 'تلاش دوباره') : null,
  );
}

export function skeletonCards(count = 4): HTMLElement {
  return h('div', { className: 'metric-grid', 'aria-hidden': 'true' }, ...Array.from({ length: count }, () => h('div', { className: 'metric-card skeleton' }, h('span'), h('strong'), h('small'))));
}

export async function confirmDialog(options: { title: string; message: string; confirmLabel?: string; dangerous?: boolean }): Promise<boolean> {
  return await new Promise(resolve => {
    const titleId = `confirm-title-${Math.random().toString(36).slice(2)}`;
    const descriptionId = `${titleId}-description`;
    const dialog = h('dialog', { className: 'dialog', 'aria-labelledby': titleId, 'aria-describedby': descriptionId },
      h('form', { method: 'dialog', className: 'dialog__body' },
        h('div', { className: `dialog__icon ${options.dangerous ? 'dialog__icon--danger' : ''}` }, icon(options.dangerous ? 'warning' : 'check')),
        h('h2', { id: titleId, text: options.title }),
        h('p', { id: descriptionId, text: options.message }),
        h('div', { className: 'dialog__actions' },
          h('button', { className: 'button button--ghost', value: 'cancel' }, 'انصراف'),
          h('button', { className: `button ${options.dangerous ? 'button--danger' : 'button--primary'}`, value: 'confirm' }, options.confirmLabel ?? 'تأیید'),
        ),
      ),
    ) as HTMLDialogElement;
    dialog.addEventListener('close', () => { resolve(dialog.returnValue === 'confirm'); dialog.remove(); }, { once: true });
    dialog.addEventListener('cancel', () => { dialog.returnValue = 'cancel'; });
    document.body.append(dialog);
    dialog.showModal();
  });
}
