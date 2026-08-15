import { useEffect, useState } from './view.js';

export const routes = [
  { id: 'dashboard', pattern: /^\/$/, title: 'داشبورد' },
  { id: 'students', pattern: /^\/students\/?$/, title: 'دانش‌آموزان' },
  { id: 'student', pattern: /^\/students\/(?<id>[^/]+)\/?$/, title: 'پرونده ۳۶۰ درجه' },
  { id: 'performance', pattern: /^\/performance\/?$/, title: 'عملکرد آموزشی' },
  { id: 'attendance', pattern: /^\/attendance\/?$/, title: 'حضور و غیاب' },
  { id: 'alerts', pattern: /^\/alerts\/?$/, title: 'مرکز هشدارها' },
  { id: 'suggestions', pattern: /^\/suggestions\/?$/, title: 'پیشنهادهای هوشمند' },
  { id: 'reports', pattern: /^\/reports\/?$/, title: 'گزارش‌ها' },
  { id: 'portal', pattern: /^\/portal\/?$/, title: 'پورتال خانواده' },
  { id: 'imports', pattern: /^\/imports\/?$/, title: 'ورود اطلاعات', roles: ['system_admin', 'organization_admin', 'school_manager', 'educational_deputy', 'operator'] },
  { id: 'manual-entry', pattern: /^\/manual-entry\/?$/, title: 'ثبت دستی' },
  { id: 'users', pattern: /^\/users\/?$/, title: 'کاربران', roles: ['system_admin', 'organization_admin', 'school_manager'] },
  { id: 'roles', pattern: /^\/roles\/?$/, title: 'نقش‌ها', roles: ['system_admin', 'organization_admin', 'school_manager'] },
  { id: 'profile', pattern: /^\/profile\/?$/, title: 'پروفایل' },
  { id: 'settings', pattern: /^\/settings\/?$/, title: 'تنظیمات' },
  { id: 'resource', pattern: /^\/resources\/(?<tag>[a-z0-9-]+)\/?$/, title: 'مدیریت اطلاعات' },
  { id: 'forbidden', pattern: /^\/forbidden\/?$/, title: 'عدم دسترسی' },
  { id: 'login', pattern: /^\/login\/?$/, title: 'ورود', public: true },
];

export function matchRoute(pathname) {
  for (const route of routes) {
    const match = route.pattern.exec(pathname);
    if (match) return { ...route, params: match.groups ?? {} };
  }
  return { id: 'not-found', title: 'صفحه پیدا نشد', params: {} };
}

export function navigate(path, replace = false) {
  if (replace) history.replaceState({}, '', path);
  else history.pushState({}, '', path);
  window.dispatchEvent(new PopStateEvent('popstate'));
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

export function useRoute() {
  const [route, setRoute] = useState(() => matchRoute(location.pathname));
  useEffect(() => {
    const listener = () => setRoute(matchRoute(location.pathname));
    addEventListener('popstate', listener);
    return () => removeEventListener('popstate', listener);
  }, []);
  return route;
}
