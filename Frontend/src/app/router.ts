import { activeRoles, administrativeRoles, hasAnyRole, teacherWriteRoles } from './permissions.js';
import { routeFactories, type RouteDefinition } from './routes.js';
import { ensureUser } from './auth.js';
import { store } from './store.js';
import { createShell } from '../components/shell.js';
import { createPortalShell } from '../components/portal-shell.js';
import { h } from '../utils/dom.js';
import { loadingState } from '../components/feedback.js';
import { administrationWorkspaceRoles, attendanceWorkspaceRoles, dataCenterWorkspaceRoles, educationWorkspaceRoles, followUpWorkspaceRoles, reportWorkspaceRoles, studentWorkspaceRoles } from './workspaces.js';

const routes: RouteDefinition[] = [
  { pattern: /^\/login\/?$/, title: 'ورود', private: false, render: routeFactories.login },
  { pattern: /^\/?$/, title: 'داشبورد', private: true, render: routeFactories.dashboard },
  { pattern: /^\/students\/?$/, title: 'دانش‌آموزان', private: true, roles: studentWorkspaceRoles, render: routeFactories.students },
  { pattern: /^\/students\/(?<id>[^/]+)\/?$/, title: 'پرونده دانش‌آموز', private: true, roles: studentWorkspaceRoles, render: routeFactories.student },
  { pattern: /^\/alerts\/?$/, title: 'مرکز هشدارها', private: true, roles: attendanceWorkspaceRoles, render: routeFactories.alerts },
  { pattern: /^\/education\/?$/, title: 'آموزش', private: true, roles: educationWorkspaceRoles, render: routeFactories.education },
  { pattern: /^\/attendance\/?$/, title: 'حضور و غیاب', private: true, roles: attendanceWorkspaceRoles, render: routeFactories.attendance },
  { pattern: /^\/attendance\/(?<tab>sessions|records|alerts|notifications)\/?$/, title: 'حضور و غیاب', private: true, roles: attendanceWorkspaceRoles, render: routeFactories.attendance },
  { pattern: /^\/follow-up\/?$/, title: 'رشد و پیگیری', private: true, roles: followUpWorkspaceRoles, render: routeFactories.followUp },
  { pattern: /^\/reports\/?$/, title: 'گزارش‌ها', private: true, roles: reportWorkspaceRoles, render: routeFactories.reports },
  { pattern: /^\/portal\/?$/, title: 'پورتال', private: true, shell: 'portal', render: routeFactories.portal },
  { pattern: /^\/data-center\/?$/, title: 'مرکز داده', private: true, roles: dataCenterWorkspaceRoles, render: routeFactories.dataCenter },
  { pattern: /^\/imports\/?$/, title: 'ورود اطلاعات', private: true, roles: dataCenterWorkspaceRoles, render: routeFactories.imports },
  { pattern: /^\/manual-entry\/?$/, title: 'ثبت و ویرایش دستی', private: true, roles: teacherWriteRoles, render: routeFactories.manualEntry },
  { pattern: /^\/users\/?$/, title: 'کاربران', private: true, roles: administrativeRoles, render: routeFactories.users },
  { pattern: /^\/roles\/?$/, title: 'نقش‌ها', private: true, roles: administrativeRoles, render: routeFactories.roles },
  { pattern: /^\/profile\/?$/, title: 'پروفایل', private: true, render: routeFactories.profile },
  { pattern: /^\/administration\/?$/, title: 'مدیریت سامانه', private: true, roles: administrationWorkspaceRoles, render: routeFactories.settings },
  { pattern: /^\/settings\/?$/, title: 'مدیریت سامانه', private: true, roles: administrationWorkspaceRoles, render: routeFactories.settings },
  { pattern: /^\/forbidden\/?$/, title: 'عدم دسترسی', private: true, render: routeFactories.forbidden },
  { pattern: /^\/resources\/(?<tag>[a-z0-9-]+)\/?$/, title: 'مدیریت اطلاعات', private: true, render: routeFactories.resource },
];

let renderVersion = 0;

/**
 * A return target must stay on this origin and never re-enter the login route.
 * The latter avoids an authenticated user looping through /login?returnTo=/login.
 */
export function safeReturnTo(returnTo: string | null, origin = location.origin): string | null {
  if (!returnTo?.startsWith('/') || returnTo.startsWith('//')) return null;
  try {
    const appOrigin = new URL(origin).origin;
    const target = new URL(returnTo, appOrigin);
    if (target.origin !== appOrigin || target.pathname === '/login' || target.pathname === '/login/') return null;
    return `${target.pathname}${target.search}${target.hash}`;
  } catch {
    return null;
  }
}

export function defaultAuthenticatedPath(roles = activeRoles()): string {
  return roles.length ? '/' : '/portal';
}

export function postLoginRedirectPath(returnTo: string | null, roles = activeRoles(), origin = location.origin): string {
  return safeReturnTo(returnTo, origin) ?? defaultAuthenticatedPath(roles);
}

function wrapPrivatePage(route: RouteDefinition, page: HTMLElement): HTMLElement {
  return route.shell === 'portal' ? createPortalShell(page) : createShell(page);
}

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
    if (version === renderVersion) {
      document.title = 'صفحه پیدا نشد | هم‌آموز';
      document.body.classList.toggle('is-login', !store.state.user);
      root.replaceChildren(store.state.user ? createShell(page) : h('main', { id: 'page-content', tabindex: '-1' }, page));
      queueMicrotask(() => document.querySelector<HTMLElement>('#page-content')?.focus({ preventScroll: true }));
    }
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
    if (location.pathname === '/' && defaultAuthenticatedPath() === '/portal') {
      navigate('/portal', true);
      return;
    }
    if (location.pathname === '/alerts' || location.pathname === '/alerts/') {
      navigate(`/attendance/alerts${location.search}${location.hash}`, true);
      return;
    }
  } else if (location.pathname.startsWith('/login') && await ensureUser()) {
    const returnTo = new URLSearchParams(location.search).get('returnTo');
    navigate(postLoginRedirectPath(returnTo), true);
    return;
  }

  try {
    const page = await route.render(matched?.params ?? {});
    if (version !== renderVersion) return;
    document.title = `${route.title} | هم‌آموز`;
    document.body.classList.toggle('is-login', !route.private);
    root.replaceChildren(route.private ? wrapPrivatePage(route, page) : page);
    queueMicrotask(() => document.querySelector<HTMLElement>('#page-content')?.focus({ preventScroll: true }));
  } catch (error) {
    if (version !== renderVersion) return;
    const failure = h('section', { className: 'error-page' }, h('h1', { text: 'بارگذاری صفحه ناموفق بود' }), h('p', { text: error instanceof Error ? error.message : 'خطای ناشناخته' }), h('button', { className: 'button button--primary', type: 'button', onClick: () => void renderRoute() }, 'تلاش دوباره'));
    document.title = 'بارگذاری صفحه ناموفق بود | هم‌آموز';
    document.body.classList.toggle('is-login', !route.private);
    root.replaceChildren(route.private ? wrapPrivatePage(route, failure) : h('main', { id: 'page-content', tabindex: '-1' }, failure));
    queueMicrotask(() => document.querySelector<HTMLElement>('#page-content')?.focus({ preventScroll: true }));
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
