import { administrativeRoles, hasAnyRole } from './permissions.js';
import { routeFactories, type RouteDefinition } from './routes.js';
import { ensureUser } from './auth.js';
import { store } from './store.js';
import { createShell } from '../components/shell.js';
import { h } from '../utils/dom.js';
import { loadingState } from '../components/feedback.js';

const routes: RouteDefinition[] = [
  { pattern: /^\/login\/?$/, title: 'ورود', private: false, render: routeFactories.login },
  { pattern: /^\/?$/, title: 'داشبورد', private: true, render: routeFactories.dashboard },
  { pattern: /^\/students\/?$/, title: 'دانش‌آموزان', private: true, render: routeFactories.students },
  { pattern: /^\/students\/(?<id>[^/]+)\/?$/, title: 'پرونده دانش‌آموز', private: true, render: routeFactories.student },
  { pattern: /^\/alerts\/?$/, title: 'مرکز هشدارها', private: true, render: routeFactories.alerts },
  { pattern: /^\/attendance\/?$/, title: 'حضور و غیاب', private: true, render: routeFactories.attendance },
  { pattern: /^\/reports\/?$/, title: 'گزارش‌ها', private: true, render: routeFactories.reports },
  { pattern: /^\/portal\/?$/, title: 'پورتال', private: true, render: routeFactories.portal },
  { pattern: /^\/imports\/?$/, title: 'ورود اطلاعات', private: true, roles: ['system_admin', 'organization_admin', 'school_manager', 'educational_deputy', 'operator'], render: routeFactories.imports },
  { pattern: /^\/manual-entry\/?$/, title: 'ثبت و ویرایش دستی', private: true, render: routeFactories.manualEntry },
  { pattern: /^\/users\/?$/, title: 'کاربران', private: true, roles: administrativeRoles, render: routeFactories.users },
  { pattern: /^\/roles\/?$/, title: 'نقش‌ها', private: true, roles: administrativeRoles, render: routeFactories.roles },
  { pattern: /^\/profile\/?$/, title: 'پروفایل', private: true, render: routeFactories.profile },
  { pattern: /^\/settings\/?$/, title: 'تنظیمات', private: true, render: routeFactories.settings },
  { pattern: /^\/forbidden\/?$/, title: 'عدم دسترسی', private: true, render: routeFactories.forbidden },
  { pattern: /^\/resources\/(?<tag>[a-z0-9-]+)\/?$/, title: 'مدیریت اطلاعات', private: true, render: routeFactories.resource },
];

let renderVersion = 0;

export function navigate(path: string, replace = false): void {
  if (replace) history.replaceState({}, '', path);
  else history.pushState({}, '', path);
  void renderRoute();
}

function matchRoute(path: string): { route: RouteDefinition; params: Record<string, string> } | null {
  for (const route of routes) {
    const match = route.pattern.exec(path);
    if (match) return { route, params: match.groups ?? {} };
  }
  return null;
}

export async function renderRoute(): Promise<void> {
  const version = ++renderVersion;
  const root = document.querySelector<HTMLElement>('#app');
  if (!root) throw new Error('Application root is missing.');
  if (!root.childElementCount) root.append(loadingState('در حال آماده‌سازی صفحه…'));
  const matched = matchRoute(location.pathname);
  const route = matched?.route;

  if (!route) {
    const page = await routeFactories.notFound();
    if (version === renderVersion) root.replaceChildren(store.state.user ? createShell(page) : page);
    return;
  }

  if (route.private) {
    const authenticated = await ensureUser();
    if (!authenticated) {
      const returnTo = encodeURIComponent(`${location.pathname}${location.search}`);
      navigate(`/login?returnTo=${returnTo}`, true);
      return;
    }
    if (!hasAnyRole(route.roles)) {
      navigate('/forbidden', true);
      return;
    }
    if (store.state.user?.must_change_password && location.pathname !== '/profile') {
      navigate('/profile?passwordRequired=1', true);
      return;
    }
  } else if (location.pathname.startsWith('/login') && await ensureUser()) {
    navigate('/', true);
    return;
  }

  try {
    const page = await route.render(matched?.params ?? {});
    if (version !== renderVersion) return;
    document.title = `${route.title} | هم‌آموز`;
    document.body.classList.toggle('is-login', !route.private);
    root.replaceChildren(route.private ? createShell(page) : page);
    queueMicrotask(() => document.querySelector<HTMLElement>('#page-content')?.focus({ preventScroll: true }));
  } catch (error) {
    if (version !== renderVersion) return;
    const failure = h('section', { className: 'error-page' }, h('h1', { text: 'بارگذاری صفحه ناموفق بود' }), h('p', { text: error instanceof Error ? error.message : 'خطای ناشناخته' }), h('button', { className: 'button button--primary', type: 'button', onClick: () => void renderRoute() }, 'تلاش دوباره'));
    root.replaceChildren(route.private ? createShell(failure) : failure);
  }
}

export function initRouter(): void {
  window.addEventListener('popstate', () => void renderRoute());
  document.addEventListener('click', event => {
    const anchor = (event.target as Element).closest<HTMLAnchorElement>('a[data-router]');
    if (!anchor || event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    event.preventDefault(); navigate(anchor.pathname + anchor.search);
  });
}
