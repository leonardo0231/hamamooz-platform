import { apiRequest } from '../api/client.js';
import { endpoints } from '../api/endpoints.js';
import type { Pagination, Role } from '../api/types.js';
import { activeRoles, administrativeRoles, broadEducationRoles, roleLabel, teacherWriteRoles } from '../app/permissions.js';
import { store } from '../app/store.js';
import { navigate } from '../app/router.js';
import { h, initials, onWindowEventWhileConnected } from '../utils/dom.js';
import { icon } from './icons.js';
import { toast } from './feedback.js';

interface NamedItem { id: string; name?: string; title?: string; organization?: string; }
interface NavigationItem { href: string; label: string; icon: string; roles?: Role[]; }

const navigation: NavigationItem[] = [
  { href: '/', label: 'نمای کلی', icon: 'home' },
  { href: '/students', label: 'دانش‌آموزان', icon: 'users' },
  { href: '/resources/assessments', label: 'آموزش و ارزیابی', icon: 'chart' },
  { href: '/attendance', label: 'حضور و غیاب', icon: 'calendar' },
  { href: '/resources/course-offerings', label: 'کلاس‌ها و برنامه درسی', icon: 'book' },
  { href: '/alerts', label: 'مرکز هشدارها', icon: 'bell' },
  { href: '/reports', label: 'گزارش‌ها و کارنامه‌ها', icon: 'file' },
  { href: '/imports', label: 'ورود اطلاعات', icon: 'upload', roles: broadEducationRoles },
  { href: '/manual-entry', label: 'ثبت و ویرایش دستی', icon: 'edit', roles: teacherWriteRoles },
  { href: '/users', label: 'کاربران', icon: 'user', roles: administrativeRoles },
  { href: '/roles', label: 'نقش‌ها و دسترسی', icon: 'settings', roles: administrativeRoles },
  { href: '/settings', label: 'تنظیمات سامانه', icon: 'settings' },
];

function shouldHandleNavigation(event: MouseEvent): boolean {
  const anchor = event.currentTarget as HTMLAnchorElement;
  return !event.defaultPrevented
    && event.button === 0
    && !event.metaKey
    && !event.ctrlKey
    && !event.shiftKey
    && !event.altKey
    && !anchor.target
    && !anchor.hasAttribute('download')
    && anchor.origin === location.origin;
}

function isNavigationItemActive(item: NavigationItem, pathname = location.pathname): boolean {
  return item.href === '/' ? pathname === '/' : pathname.startsWith(item.href);
}

export function createShell(content: HTMLElement): HTMLElement {
  const user = store.state.user;
  const fullName = `${user?.first_name ?? ''} ${user?.last_name ?? ''}`.trim() || user?.username || 'کاربر';
  const roles = activeRoles();
  let appMain: HTMLElement | null = null;
  let mobileToggle: HTMLButtonElement | null = null;
  let pendingNavigation = 0;
  const visibleNavigation = navigation.filter(item => !item.roles || item.roles.some(role => roles.includes(role)));
  const navLinks: HTMLAnchorElement[] = [];
  const closeButton = h('button', { className: 'icon-button sidebar__close', type: 'button', 'aria-label': 'بستن منوی اصلی' }, icon('close')) as HTMLButtonElement;
  const navigationList = h('nav', { className: 'sidebar__nav', 'aria-label': 'بخش‌های سامانه' },
    ...visibleNavigation.map(item => {
      const active = isNavigationItemActive(item);
      const link = h('a', {
        className: `nav-link ${active ? 'is-active' : ''}`,
        href: item.href,
        'aria-current': active ? 'page' : undefined,
        onClick: (event: MouseEvent) => {
          if (!shouldHandleNavigation(event)) return;
          event.preventDefault();
          void activateNavigation(item, event.currentTarget as HTMLAnchorElement);
        },
      },
      h('span', { className: 'nav-link__icon' }, icon(item.icon)),
      h('span', { className: 'nav-link__label', text: item.label }),
      ) as HTMLAnchorElement;
      navLinks.push(link);
      return link;
    }),
  );
  const navigationViewport = h('div', { className: 'sidebar__menu-viewport', tabindex: '-1' }, navigationList);
  const sidebar = h('aside', { className: 'sidebar', id: 'primary-navigation', 'aria-label': 'ناوبری اصلی', tabindex: '-1' },
    h('div', { className: 'sidebar__header' },
      h('div', { className: 'brand' }, h('span', { className: 'brand__mark' }, icon('book')), h('div', {}, h('strong', { text: 'هم‌آموز' }), h('small', { text: 'مدیریت هوشمند مدرسه' }))),
      closeButton,
    ),
    navigationViewport,
    h('div', { className: 'sidebar__footer' },
      h('button', { className: 'nav-link nav-link--button sidebar__logout', type: 'button', onClick: () => void import('../app/auth.js').then(module => module.logout()) },
        h('span', { className: 'nav-link__icon' }, icon('logout')),
        h('span', { className: 'nav-link__label', text: 'خروج از حساب' }),
      ),
      h('div', { className: 'role-card' }, h('span', { className: 'avatar avatar--accent', text: initials(fullName) }), h('div', {}, h('small', { text: 'نقش فعال' }), h('strong', { text: roles[0] ? roleLabel(roles[0]) : 'کاربر' }))),
    ),
  );
  const backdrop = h('div', { className: 'sidebar-backdrop', 'aria-hidden': 'true', onClick: () => {
    cancelPendingNavigation();
    setDrawerState(false);
  } });

  const isMobileLayout = (): boolean => window.matchMedia('(max-width: 980px)').matches;
  const focusableSelector = 'a[href], button:not([disabled]), select:not([disabled]), input:not([disabled]), [tabindex]:not([tabindex="-1"])';
  const reducedMotion = (): boolean => window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  function navigationScrollTop(link: HTMLElement): number {
    return Math.max(0, link.offsetTop - ((navigationViewport.clientHeight - link.offsetHeight) / 2));
  }

  function centerNavigationLink(link: HTMLElement, behavior: ScrollBehavior): void {
    const top = navigationScrollTop(link);
    if (behavior === 'auto') {
      navigationViewport.style.scrollBehavior = 'auto';
      navigationViewport.scrollTop = top;
      navigationViewport.style.removeProperty('scroll-behavior');
      return;
    }
    navigationViewport.scrollTo({ top, behavior });
  }

  let curveFrame = 0;
  function updateNavigationCurve(): void {
    curveFrame = 0;
    const currentLink = navLinks.find(link => link.getAttribute('aria-current') === 'page');
    navLinks.forEach(link => link.style.setProperty('--nav-spotlight-lock', '0px'));
    if (currentLink && !sidebar.hasAttribute('data-navigation-state')) {
      const lockOffset = navigationViewport.scrollTop - navigationScrollTop(currentLink);
      currentLink.style.setProperty('--nav-spotlight-lock', `${lockOffset.toFixed(1)}px`);
    }
    if (isMobileLayout()) {
      navLinks.forEach(link => link.style.setProperty('--nav-curve-inset', '0px'));
      return;
    }
    const viewportBounds = navigationViewport.getBoundingClientRect();
    const ellipseStyle = getComputedStyle(sidebar, '::before');
    const ellipseRadiusInline = Number.parseFloat(ellipseStyle.width) / 2;
    const ellipseRadiusBlock = Number.parseFloat(ellipseStyle.height) / 2;
    const viewportCenter = viewportBounds.top + (viewportBounds.height / 2);
    navLinks.forEach(link => {
      const isSpotlight = link.classList.contains('is-pending')
        || (!sidebar.hasAttribute('data-navigation-state') && link.getAttribute('aria-current') === 'page');
      if (isSpotlight || !Number.isFinite(ellipseRadiusInline) || !Number.isFinite(ellipseRadiusBlock)) {
        link.style.setProperty('--nav-curve-inset', '0px');
        return;
      }
      const bounds = link.getBoundingClientRect();
      const distance = Math.abs((bounds.top + (bounds.height / 2)) - viewportCenter);
      const ratio = Math.min(.985, distance / ellipseRadiusBlock);
      const ellipseInset = ellipseRadiusInline * (1 - Math.sqrt(1 - (ratio * ratio)));
      link.style.setProperty('--nav-curve-inset', `${Math.max(0, ellipseInset - 4).toFixed(1)}px`);
    });
  }

  function scheduleNavigationCurve(): void {
    if (curveFrame) return;
    curveFrame = window.requestAnimationFrame(updateNavigationCurve);
  }

  function cancelPendingNavigation(): void {
    pendingNavigation += 1;
    sidebar.removeAttribute('data-navigation-state');
    navLinks.forEach(link => link.classList.remove('is-pending'));
    appMain?.classList.remove('is-page-leaving');
    scheduleNavigationCurve();
  }

  async function activateNavigation(item: NavigationItem, link: HTMLAnchorElement): Promise<void> {
    const activation = ++pendingNavigation;
    const instant = reducedMotion();
    navLinks.forEach(candidate => candidate.classList.toggle('is-pending', candidate === link));
    sidebar.setAttribute('data-navigation-state', 'centering');
    centerNavigationLink(link, instant ? 'auto' : 'smooth');
    scheduleNavigationCurve();

    const exactPath = location.pathname.replace(/\/+$/, '') || '/';
    const targetPath = item.href.replace(/\/+$/, '') || '/';
    if (exactPath === targetPath) {
      if (!instant) await new Promise(resolve => window.setTimeout(resolve, 360));
      if (activation === pendingNavigation) cancelPendingNavigation();
      return;
    }

    appMain?.classList.add('is-page-leaving');
    if (!instant) await new Promise(resolve => window.setTimeout(resolve, 360));
    if (activation !== pendingNavigation) return;
    sidebar.setAttribute('data-navigation-state', 'navigating');
    setDrawerState(false, false);
    navigate(item.href);
  }

  function setDrawerState(open: boolean, restoreFocus = true): void {
    const mobile = isMobileLayout();
    const nextOpen = mobile && open;
    store.patch({ sidebarOpen: nextOpen });
    sidebar.classList.toggle('is-open', nextOpen);
    backdrop.classList.toggle('is-visible', nextOpen);
    document.body.classList.toggle('drawer-open', nextOpen);
    sidebar.toggleAttribute('inert', mobile && !nextOpen);
    if (mobile && !nextOpen) sidebar.setAttribute('aria-hidden', 'true');
    else sidebar.removeAttribute('aria-hidden');
    mobileToggle?.setAttribute('aria-expanded', String(nextOpen));
    mobileToggle?.setAttribute('aria-label', nextOpen ? 'بستن منوی اصلی' : 'بازکردن منوی اصلی');
    if (appMain) appMain.toggleAttribute('inert', nextOpen);
    if (nextOpen) queueMicrotask(() => closeButton.focus());
    else if (restoreFocus && mobile) queueMicrotask(() => mobileToggle?.focus());
  }

  closeButton.addEventListener('click', () => {
    cancelPendingNavigation();
    setDrawerState(false);
  });
  navigationViewport.addEventListener('scroll', scheduleNavigationCurve, { passive: true });
  sidebar.addEventListener('wheel', event => {
    if (isMobileLayout() && !sidebar.classList.contains('is-open')) return;
    event.preventDefault();
    event.stopPropagation();
    if (sidebar.getAttribute('data-navigation-state') === 'centering') cancelPendingNavigation();
    const multiplier = event.deltaMode === WheelEvent.DOM_DELTA_LINE
      ? 18
      : event.deltaMode === WheelEvent.DOM_DELTA_PAGE
        ? navigationViewport.clientHeight
        : 1;
    navigationViewport.scrollTop += event.deltaY * multiplier;
    scheduleNavigationCurve();
  }, { passive: false });
  sidebar.addEventListener('keydown', event => {
    if (!sidebar.classList.contains('is-open')) return;
    if (event.key === 'Escape') {
      event.preventDefault();
      cancelPendingNavigation();
      setDrawerState(false);
      return;
    }
    if (event.key !== 'Tab') return;
    const focusable = [...sidebar.querySelectorAll<HTMLElement>(focusableSelector)].filter(element => !element.hidden);
    const first = focusable[0];
    const last = focusable.at(-1);
    if (!first || !last) return;
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  });

  const organizationSelect = h('select', { className: 'scope-select', 'aria-label': 'انتخاب مجموعه' }) as HTMLSelectElement;
  const schoolSelect = h('select', { className: 'scope-select', 'aria-label': 'انتخاب شعبه' }) as HTMLSelectElement;
  let currentSchools: NamedItem[] = [];

  const loadSchools = async (organizationId: string): Promise<boolean> => {
    const response = await apiRequest<Pagination<NamedItem>>(endpoints.schools, { query: { page_size: 200, organization: organizationId || undefined } });
    currentSchools = response.results;
    schoolSelect.replaceChildren(h('option', { value: '', text: 'همه شعب مجاز' }), ...currentSchools.map(item => h('option', { value: item.id, text: item.name ?? item.title ?? item.id })));
    const savedSchool = store.state.scope.schoolId;
    if (savedSchool && !currentSchools.some(item => item.id === savedSchool)) {
      store.setScope({ organizationId: organizationId || null, schoolId: null });
      schoolSelect.value = '';
      return true;
    }
    schoolSelect.value = savedSchool ?? '';
    return false;
  };

  const loadScopes = async (): Promise<void> => {
    try {
      const orgResponse = await apiRequest<Pagination<NamedItem>>(endpoints.organizations, { query: { page_size: 200 } });
      const organizations = orgResponse.results;
      organizationSelect.replaceChildren(h('option', { value: '', text: 'همه مجموعه‌های مجاز' }), ...organizations.map(item => h('option', { value: item.id, text: item.name ?? item.title ?? item.id })));
      let organizationId = store.state.scope.organizationId ?? '';
      let corrected = false;
      if (organizationId && !organizations.some(item => item.id === organizationId)) {
        organizationId = '';
        store.setScope({ organizationId: null, schoolId: null });
        corrected = true;
      }
      organizationSelect.value = organizationId;
      corrected = await loadSchools(organizationId) || corrected;
      if (corrected && organizationSelect.isConnected) navigate(`${location.pathname}${location.search}`, true);
    } catch (error) {
      organizationSelect.disabled = true;
      schoolSelect.disabled = true;
      toast('دریافت حوزه‌های دسترسی ناموفق بود', 'error', error instanceof Error ? error.message : undefined);
    }
  };

  organizationSelect.addEventListener('change', () => {
    store.setScope({ organizationId: organizationSelect.value || null, schoolId: null });
    navigate(`${location.pathname}${location.search}`, true);
  });
  schoolSelect.addEventListener('change', () => {
    const selected = currentSchools.find(item => item.id === schoolSelect.value);
    const organizationId = selected?.organization ?? (organizationSelect.value || null);
    store.setScope({ organizationId, schoolId: schoolSelect.value || null });
    navigate(`${location.pathname}${location.search}`, true);
  });

  mobileToggle = h('button', {
    className: 'icon-button mobile-menu',
    type: 'button',
    'aria-label': 'بازکردن منوی اصلی',
    'aria-controls': 'primary-navigation',
    'aria-expanded': 'false',
    onClick: () => setDrawerState(!sidebar.classList.contains('is-open')),
  }, icon('menu')) as HTMLButtonElement;
  const header = h('header', { className: 'topbar' },
    mobileToggle,
    h('div', { className: 'scope-controls' }, organizationSelect, schoolSelect),
    h('label', { className: 'global-search' }, icon('search'), h('input', { type: 'search', placeholder: 'جست‌وجو در دانش‌آموزان…', 'aria-label': 'جست‌وجوی سراسری', onKeydown: (event: KeyboardEvent) => { if (event.key === 'Enter') { const input = event.currentTarget as HTMLInputElement; navigate(`/students?search=${encodeURIComponent(input.value)}`); } } })),
    h('button', { className: 'icon-button', type: 'button', 'aria-label': 'هشدارها', onClick: () => navigate('/alerts') }, icon('bell')),
    h('button', { className: 'user-menu', type: 'button', onClick: () => navigate('/profile') }, h('span', { className: 'avatar', text: initials(fullName) }), h('span', {}, h('strong', { text: fullName }), h('small', { text: roles[0] ? roleLabel(roles[0]) : '' }))),
  );
  appMain = h('div', { className: 'app-main' }, header, h('main', { className: 'page-container', id: 'page-content', tabindex: '-1' }, content));
  const shell = h('div', { className: 'app-shell' }, sidebar, backdrop, appMain);
  setDrawerState(Boolean(store.state.sidebarOpen), false);
  queueMicrotask(() => {
    const activeLink = navLinks.find(link => link.getAttribute('aria-current') === 'page');
    if (activeLink) centerNavigationLink(activeLink, 'auto');
    updateNavigationCurve();
    navigationViewport.classList.add('is-ready');
  });
  onWindowEventWhileConnected(shell, 'resize', () => {
    if (!isMobileLayout()) setDrawerState(false, false);
    else if (!sidebar.classList.contains('is-open')) setDrawerState(false, false);
    scheduleNavigationCurve();
  });
  void loadScopes();
  return shell;
}