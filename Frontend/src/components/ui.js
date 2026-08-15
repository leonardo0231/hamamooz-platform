import { html } from '../core/view.js';
import { Icon } from './icons.js';

export function Button({ children, icon, variant = 'primary', className = '', ...props }) {
  return html`<button class=${`button button--${variant} ${className}`} ...${props}>${icon && html`<${Icon} name=${icon} size=${19} />`}${children}</button>`;
}

export function Card({ children, className = '', title, subtitle, icon, action, ...props }) {
  return html`<section class=${`card ${className}`} ...${props}>
    ${(title || action) && html`<header class="card__header"><div class="card__title-wrap">${icon && html`<span class="card__heading-icon"><${Icon} name=${icon} size=${20} /></span>`}<div>${title && html`<h2 class="card__title">${title}</h2>`}${subtitle && html`<p class="card__subtitle">${subtitle}</p>`}</div></div>${action}</header>`}
    ${children}
  </section>`;
}

export function PageHeader({ title, subtitle, eyebrow, actions }) {
  return html`<header class="page-heading"><div>${eyebrow && html`<p class="eyebrow">${eyebrow}</p>`}<h1>${title}</h1>${subtitle && html`<p>${subtitle}</p>`}</div>${actions && html`<div class="page-heading__actions">${actions}</div>`}</header>`;
}

export function StatCard({ label, value, delta, icon, tone = 'purple', description }) {
  return html`<article class=${`stat-card stat-card--${tone}`}><div class="stat-card__top"><span class="stat-card__icon"><${Icon} name=${icon} size=${25} /></span><div><p>${label}</p><strong>${value}</strong></div></div>${delta && html`<div class="stat-card__footer"><span>${delta}</span>${description && html`<small>${description}</small>`}</div>`}</article>`;
}

export function Badge({ children, tone = 'neutral' }) { return html`<span class=${`badge badge--${tone}`}>${children}</span>`; }
export function Avatar({ name, src, size = 'md' }) { return src ? html`<img class=${`avatar avatar--${size}`} src=${src} alt="" />` : html`<span class=${`avatar avatar--${size}`} aria-hidden="true">${name?.split(' ').map(part => part[0]).slice(0, 2).join('') || 'هـ'}</span>`; }

export function SearchField({ value, onInput, placeholder = 'جست‌وجو…', label = 'جست‌وجو' }) {
  return html`<label class="search-field"><span class="sr-only">${label}</span><${Icon} name="search" size=${19} /><input type="search" value=${value} onInput=${onInput} placeholder=${placeholder} /></label>`;
}

export function Skeleton({ lines = 3 }) { return html`<div class="skeleton" aria-label="در حال بارگذاری">${Array.from({ length: lines }, (_, index) => html`<span key=${index}></span>`)}</div>`; }

export function EmptyState({ title = 'داده‌ای پیدا نشد', description = 'فیلترها را تغییر دهید یا دوباره تلاش کنید.', icon = 'folder', action }) {
  return html`<div class="state state--empty"><span><${Icon} name=${icon} size=${30} /></span><h2>${title}</h2><p>${description}</p>${action}</div>`;
}

export function ErrorState({ error, onRetry }) {
  return html`<div class="state state--error" role="alert"><span><${Icon} name="alert" size=${30} /></span><h2>بارگذاری اطلاعات ناموفق بود</h2><p>${error?.message ?? 'خطای پیش‌بینی‌نشده‌ای رخ داد.'}</p>${error?.requestId && html`<small>شناسه پیگیری: ${error.requestId}</small>`}${onRetry && html`<${Button} variant="outline" onClick=${onRetry}>تلاش دوباره</${Button}>`}</div>`;
}

export function Progress({ value, label }) { return html`<div class="progress" aria-label=${label} aria-valuemin="0" aria-valuemax="100" aria-valuenow=${value} role="progressbar"><span style=${`width:${Math.max(0, Math.min(100, value))}%`}></span></div>`; }
