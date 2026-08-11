import { apiRequest } from '../api/client.js';
import { endpoints } from '../api/endpoints.js';
import type { Pagination } from '../api/types.js';
import { activeRoles, roleLabel } from '../app/permissions.js';
import { store } from '../app/store.js';
import { navigate } from '../app/router.js';
import { isStaffWorkspaceActive, staffNavigationForRoles, type StaffWorkspace } from '../app/workspaces.js';
import { primaryRole } from '../ui/role-experience.js';
import { h, initials, onWindowEventWhileConnected } from '../utils/dom.js';
import { icon } from './icons.js';
import { toast } from './feedback.js';

interface NamedItem { id: string; name?: string; title?: string; organization?: string; }
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

function isNavigationItemActive(item: StaffWorkspace, pathname = location.pathname): boolean {
  return isStaffWorkspaceActive(item, pathname);
}

export function createShell(content: HTMLElement): HTMLElement {
  const user = store.state.user;
  const fullName = `${user?.first_name ?? ''} ${user?.last_name ?? ''}`.trim() || user?.username || 'کاربر';
  const roles = activeRoles();
  const visibleNavigation = staffNavigationForRoles(roles);
  const visibleWorkspaceIds = new Set(visibleNavigation.map(workspace => workspace.id));
  const contextRole = roles.length ? primaryRole(roles) : null;
  const mobileQuery = window.matchMedia('(max-width: 1080px)');
  const focusableSelector = 'a[href], button:not([disabled]), select:not([disabled]), input:not([disabled]), [tabindex]:not([tabindex="-1"])';

  let appMain: HTMLElement | null = null;
  let mobileToggle: HTMLButtonElement | null = null;

  const closeButton = h('button', {
    className: 'icon-button sidebar__close',
    type: 'button',
    'aria-label': 'بستن منوی اصلی',
  }, icon('close')) as HTMLButtonElement;

  const navLinks = visibleNavigation.map(item => {
    const active = isNavigationItemActive(item);
    return h('a', {
      className: 'nav-link',
      href: item.href,
      'aria-current': active ? 'page' : undefined,
      onClick: (event: MouseEvent) => {
        if (!shouldHandleNavigation(event)) return;
        event.preventDefault();
        setDrawerState(false, false);
        navigate(item.href);
      },
    },
    h('span', { className: 'nav-link__icon', 'aria-hidden': 'true' }, icon(item.icon)),
    h('span', { className: 'nav-link__label', text: item.label }),
    );
  });

  const sidebar = h('aside', {
    className: 'sidebar',
    id: 'primary-navigation',
    'aria-label': 'ناوبری اصلی',
    tabindex: '-1',
  },
  h('div', { className: 'sidebar__header' },
    h('a', {
      className: 'brand',
      href: '/',
      'aria-label': 'هم‌آموز — صفحه اصلی',
      onClick: (event: MouseEvent) => {
        if (!shouldHandleNavigation(event)) return;
        event.preventDefault();
        setDrawerState(false, false);
        navigate('/');
      },
    },
    h('span', { className: 'brand__mark', 'aria-hidden': 'true' }, icon('book')),
    h('div', {}, h('strong', { text: 'هم‌آموز' }), h('small', { text: 'مدیریت مدرسه و یادگیری' })),
    ),
    closeButton,
  ),
  h('div', { className: 'sidebar__menu-viewport' },
    h('nav', { className: 'sidebar__nav', 'aria-label': 'بخش‌های سامانه' }, ...navLinks),
  ),
  h('div', { className: 'sidebar__footer' },
    h('button', {
      className: 'sidebar__profile',
      type: 'button',
      onClick: () => {
        setDrawerState(false, false);
        navigate('/profile');
      },
    },
    h('span', { className: 'avatar avatar--accent', text: initials(fullName) }),
    h('span', { className: 'sidebar__profile-copy' },
      h('strong', { text: fullName }),
      h('small', { text: contextRole ? roleLabel(contextRole) : 'کاربر' }),
    ),
    ),
    h('button', {
      className: 'icon-button sidebar__logout',
      type: 'button',
      title: 'خروج از حساب',
      'aria-label': 'خروج از حساب',
      onClick: () => void import('../app/auth.js').then(module => module.logout()),
    }, icon('logout')),
  ),
  );

  const backdrop = h('div', {
    className: 'sidebar-backdrop',
    'aria-hidden': 'true',
    onClick: () => setDrawerState(false),
  });

  function setDrawerState(open: boolean, restoreFocus = true): void {
    const mobile = mobileQuery.matches;
    const nextOpen = mobile && open;
    store.patch({ sidebarOpen: nextOpen });
    sidebar.classList.toggle('is-open', nextOpen);
    backdrop.classList.toggle('is-visible', nextOpen);
    document.body.classList.toggle('drawer-open', nextOpen);
    sidebar.toggleAttribute('inert', mobile && !nextOpen);
    sidebar.setAttribute('aria-hidden', mobile && !nextOpen ? 'true' : 'false');
    mobileToggle?.setAttribute('aria-expanded', String(nextOpen));
    mobileToggle?.setAttribute('aria-label', nextOpen ? 'بستن منوی اصلی' : 'بازکردن منوی اصلی');
    appMain?.toggleAttribute('inert', nextOpen);
    if (nextOpen) queueMicrotask(() => closeButton.focus());
    else if (restoreFocus && mobile) queueMicrotask(() => mobileToggle?.focus());
  }

  closeButton.addEventListener('click', () => setDrawerState(false));
  sidebar.addEventListener('keydown', event => {
    if (!sidebar.classList.contains('is-open')) return;
    if (event.key === 'Escape') {
      event.preventDefault();
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
    const response = await apiRequest<Pagination<NamedItem>>(endpoints.schools, {
      query: { page_size: 200, organization: organizationId || undefined },
    });
    currentSchools = response.results;
    schoolSelect.replaceChildren(
      h('option', { value: '', text: 'همه شعب مجاز' }),
      ...currentSchools.map(item => h('option', { value: item.id, text: item.name ?? item.title ?? item.id })),
    );
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
      organizationSelect.replaceChildren(
        h('option', { value: '', text: 'همه مجموعه‌های مجاز' }),
        ...organizations.map(item => h('option', { value: item.id, text: item.name ?? item.title ?? item.id })),
      );
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

  const searchInput = h('input', {
    type: 'search',
    placeholder: 'جست‌وجوی دانش‌آموز…',
    'aria-label': 'جست‌وجوی سراسری دانش‌آموز',
    onKeydown: (event: KeyboardEvent) => {
      if (event.key !== 'Enter') return;
      const input = event.currentTarget as HTMLInputElement;
      const value = input.value.trim();
      navigate(value ? `/students?search=${encodeURIComponent(value)}` : '/students');
    },
  });

  const studentSearch = visibleWorkspaceIds.has('students')
    ? h('label', { className: 'global-search' }, icon('search'), searchInput)
    : null;

  const header = h('header', { className: 'topbar' },
    h('div', { className: 'topbar__leading' },
      mobileToggle,
      h('div', { className: 'scope-controls' },
        h('span', { className: 'scope-controls__label', text: 'حوزه فعال' }),
        organizationSelect,
        schoolSelect,
      ),
    ),
    studentSearch,
    h('div', { className: 'topbar__actions' },
      visibleWorkspaceIds.has('attendance') && h('button', {
        className: 'icon-button',
        type: 'button',
        title: 'مرکز هشدارها',
        'aria-label': 'مرکز هشدارها',
        onClick: () => navigate('/attendance/alerts'),
      }, icon('bell')),
      h('button', {
        className: 'user-menu',
        type: 'button',
        onClick: () => navigate('/profile'),
      },
      h('span', { className: 'avatar', text: initials(fullName) }),
      h('span', { className: 'user-menu__copy' },
        h('strong', { text: fullName }),
        h('small', { text: contextRole ? roleLabel(contextRole) : '' }),
      ),
      ),
    ),
  );

  appMain = h('div', { className: 'app-main' },
    header,
    h('main', { className: 'page-container', id: 'page-content', tabindex: '-1' }, content),
  );
  const shell = h('div', { className: 'app-shell' }, sidebar, backdrop, appMain);

  setDrawerState(Boolean(store.state.sidebarOpen), false);
  onWindowEventWhileConnected(shell, 'resize', () => {
    if (!mobileQuery.matches) setDrawerState(false, false);
    else if (!sidebar.classList.contains('is-open')) setDrawerState(false, false);
  });
  void loadScopes();
  return shell;
}
