import { html, useEffect, useState } from '../core/view.js';
import { navigate } from '../core/router.js';
import { activeRoles, roleLabels, store, useStore } from '../core/store.js';
import { logout } from '../core/api.js';
import { Avatar, SearchField } from './ui.js';
import { Icon } from './icons.js';

const primaryNavigation = [
  ['dashboard', '/', 'داشبورد', 'home'], ['students', '/students', 'دانش‌آموزان', 'users'],
  ['performance', '/performance', 'عملکرد آموزشی', 'chart'], ['attendance', '/attendance', 'حضور و غیاب', 'calendar'],
  ['alerts', '/alerts', 'مرکز هشدارها', 'alert', '۷'], ['suggestions', '/suggestions', 'پیشنهادهای هوشمند', 'sparkles'],
  ['reports', '/reports', 'گزارش‌ها', 'report'], ['imports', '/imports', 'ورود اطلاعات', 'upload'],
  ['settings', '/settings', 'تنظیمات', 'settings'],
];

function Link({ href, children, className = '', onClick, ...props }) {
  return html`<a href=${href} class=${className} onClick=${event => { if (!event.defaultPrevented && event.button === 0 && !event.metaKey && !event.ctrlKey) { event.preventDefault(); onClick?.(); navigate(href); } }} ...${props}>${children}</a>`;
}

function Sidebar({ routeId, open, close }) {
  return html`<aside class=${`sidebar ${open ? 'sidebar--open' : ''}`} aria-label="ناوبری اصلی">
    <div class="sidebar__brand"><span class="sidebar__logo"><${Icon} name="graduation" size=${27} /></span><div><strong>سامانه هوشمند مدرسه</strong><small>مدیریت هوشمند، آینده‌ای روشن</small></div><button class="icon-button sidebar__close" onClick=${close} aria-label="بستن منو"><${Icon} name="close" /></button></div>
    <nav class="sidebar__nav">${primaryNavigation.map(([id, href, label, icon, badge]) => html`<${Link} key=${id} href=${href} onClick=${close} className=${`sidebar__link ${routeId === id ? 'is-active' : ''}`} aria-current=${routeId === id ? 'page' : undefined}><${Icon} name=${icon} size=${22} /><span>${label}</span>${badge && html`<b>${badge}</b>`}</${Link}>`)}</nav>
    <div class="sidebar__footer"><button onClick=${() => navigate('/profile')}><${Avatar} name="مریم نادری" size="sm"/><span><small>نقش فعال</small><strong>${roleLabels[activeRoles()[0]] ?? 'مدیر مدرسه'}</strong></span><${Icon} name="chevron" size=${16}/></button></div>
  </aside>`;
}

export function Shell({ route, children }) {
  const [search, setSearch] = useState('');
  const sidebarOpen = useStore(state => state.sidebarOpen);
  const user = useStore(state => state.user);
  useEffect(() => {
    const escape = event => event.key === 'Escape' && store.patch({ sidebarOpen: false });
    addEventListener('keydown', escape);
    document.body.classList.toggle('has-drawer', sidebarOpen);
    return () => { removeEventListener('keydown', escape); document.body.classList.remove('has-drawer'); };
  }, [sidebarOpen]);

  const fullName = `${user?.first_name ?? ''} ${user?.last_name ?? ''}`.trim() || user?.username || 'کاربر سامانه';
  return html`<div class="app-shell">
    <${Sidebar} routeId=${route.id} open=${sidebarOpen} close=${() => store.patch({ sidebarOpen: false })}/>
    ${sidebarOpen && html`<button class="drawer-backdrop" onClick=${() => store.patch({ sidebarOpen: false })} aria-label="بستن منو"></button>`}
    <div class="app-shell__body">
      <header class="topbar">
        <div class="topbar__identity"><button class="icon-button topbar__menu" onClick=${() => store.patch({ sidebarOpen: true })} aria-label="باز کردن منو"><${Icon} name="menu" /></button><${Avatar} name=${fullName} size="sm"/><span><strong>${fullName}</strong><small>${roleLabels[activeRoles()[0]] ?? 'مدیر مدرسه'}</small></span><${Icon} name="chevron" size=${15}/></div>
        <div class="topbar__search"><${SearchField} value=${search} onInput=${event => setSearch(event.currentTarget.value)} placeholder="جست‌وجو در دانش‌آموزان، کلاس‌ها و گزارش‌ها…" /></div>
        <div class="topbar__context"><button class="context-picker"><span class="context-picker__icon"><${Icon} name="school" size=${19}/></span><span><small>مدرسه فعال</small><strong>دبیرستان اندیشه</strong></span><${Icon} name="chevron" size=${15}/></button><button class="icon-button notification-button" aria-label="اعلان‌ها"><${Icon} name="alert"/><b>۷</b></button><button class="icon-button desktop-only" aria-label="راهنما"><${Icon} name="help"/></button></div>
      </header>
      <main id="main-content" class="main-content" tabindex="-1">${children}</main>
      <footer class="app-footer"><span>هم‌آموز · نسخه ۲</span><button onClick=${async () => { await logout(); navigate('/login', true); }}><${Icon} name="logout" size=${16}/> خروج</button></footer>
    </div>
  </div>`;
}
