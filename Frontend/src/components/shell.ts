import { apiRequest } from '../api/client.js';
import { endpoints } from '../api/endpoints.js';
import type { Pagination, Role } from '../api/types.js';
import { activeRoles, administrativeRoles, broadEducationRoles, roleLabel } from '../app/permissions.js';
import { store } from '../app/store.js';
import { navigate } from '../app/router.js';
import { h, initials } from '../utils/dom.js';
import { icon } from './icons.js';
import { toast } from './feedback.js';

interface NamedItem { id: string; name?: string; title?: string; organization?: string; }

const navigation: Array<{ href: string; label: string; icon: string; roles?: Role[] }> = [
  { href: '/', label: 'داشبورد', icon: 'home' },
  { href: '/students', label: 'دانش‌آموزان', icon: 'users' },
  { href: '/resources/assessments', label: 'عملکرد آموزشی', icon: 'chart' },
  { href: '/attendance', label: 'حضور و غیاب', icon: 'calendar' },
  { href: '/alerts', label: 'مرکز هشدارها', icon: 'bell' },
  { href: '/resources/course-offerings', label: 'برنامه آموزشی', icon: 'book' },
  { href: '/reports', label: 'گزارش‌ها', icon: 'file' },
  { href: '/imports', label: 'ورود اطلاعات', icon: 'upload', roles: broadEducationRoles },
  { href: '/users', label: 'کاربران', icon: 'user', roles: administrativeRoles },
  { href: '/roles', label: 'نقش‌ها و دسترسی', icon: 'settings', roles: administrativeRoles },
];

export function createShell(content: HTMLElement): HTMLElement {
  const user = store.state.user;
  const fullName = `${user?.first_name ?? ''} ${user?.last_name ?? ''}`.trim() || user?.username || 'کاربر';
  const roles = activeRoles();
  const sidebar = h('aside', { className: `sidebar ${store.state.sidebarOpen ? 'is-open' : ''}`, 'aria-label': 'ناوبری اصلی' },
    h('div', { className: 'brand' }, h('span', { className: 'brand__mark' }, icon('book')), h('div', {}, h('strong', { text: 'هم‌آموز' }), h('small', { text: 'مدیریت هوشمند مدرسه' }))),
    h('nav', { className: 'sidebar__nav' }, ...navigation.filter(item => !item.roles || item.roles.some(role => roles.includes(role))).map(item => {
      const active = item.href === '/' ? location.pathname === '/' : location.pathname.startsWith(item.href);
      return h('a', { className: `nav-link ${active ? 'is-active' : ''}`, href: item.href, onClick: (event: MouseEvent) => { event.preventDefault(); navigate(item.href); } }, icon(item.icon), h('span', { text: item.label }));
    })),
    h('div', { className: 'sidebar__footer' },
      h('a', { className: 'nav-link', href: '/settings', onClick: (event: MouseEvent) => { event.preventDefault(); navigate('/settings'); } }, icon('settings'), 'تنظیمات'),
      h('button', { className: 'nav-link nav-link--button', type: 'button', onClick: () => void import('../app/auth.js').then(module => module.logout()) }, icon('logout'), 'خروج از حساب'),
      h('div', { className: 'role-card' }, h('span', { className: 'avatar avatar--accent', text: initials(fullName) }), h('div', {}, h('small', { text: 'نقش فعال' }), h('strong', { text: roles[0] ? roleLabel(roles[0]) : 'کاربر' }))),
    ),
  );

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

  const mobileToggle = h('button', { className: 'icon-button mobile-menu', type: 'button', 'aria-label': 'بازکردن منو', onClick: () => { store.patch({ sidebarOpen: !store.state.sidebarOpen }); sidebar.classList.toggle('is-open'); } }, icon('menu'));
  const header = h('header', { className: 'topbar' },
    mobileToggle,
    h('div', { className: 'scope-controls' }, organizationSelect, schoolSelect),
    h('label', { className: 'global-search' }, icon('search'), h('input', { type: 'search', placeholder: 'جست‌وجو در دانش‌آموزان…', 'aria-label': 'جست‌وجوی سراسری', onKeydown: (event: KeyboardEvent) => { if (event.key === 'Enter') { const input = event.currentTarget as HTMLInputElement; navigate(`/students?search=${encodeURIComponent(input.value)}`); } } })),
    h('button', { className: 'icon-button', type: 'button', 'aria-label': 'هشدارها', onClick: () => navigate('/alerts') }, icon('bell')),
    h('button', { className: 'user-menu', type: 'button', onClick: () => navigate('/profile') }, h('span', { className: 'avatar', text: initials(fullName) }), h('span', {}, h('strong', { text: fullName }), h('small', { text: roles[0] ? roleLabel(roles[0]) : '' }))),
  );
  void loadScopes();
  return h('div', { className: 'app-shell' }, sidebar, h('div', { className: 'app-main' }, header, h('main', { className: 'page-container', id: 'page-content', tabindex: '-1' }, content)));
}
