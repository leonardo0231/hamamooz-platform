import { useEffect, useState } from './view.js';
import { config } from './config.js';

const REFRESH_SESSION = 'hamamooz.refresh.session';
const REFRESH_REMEMBERED = 'hamamooz.refresh.remembered';
const SCOPE = 'hamamooz.scope';

function read(storage, key) {
  try { return storage.getItem(key); } catch { return null; }
}

function readJson(storage, key, fallback) {
  try { return JSON.parse(read(storage, key)) ?? fallback; } catch { return fallback; }
}

const demoUser = {
  id: 1,
  username: 'manager.demo',
  first_name: 'مریم',
  last_name: 'نادری',
  email: 'manager@hamamooz.local',
  role_assignments: [{ id: 'demo-role', role: 'school_manager', is_active: true }],
};

let state = {
  accessToken: null,
  refreshToken: read(localStorage, REFRESH_REMEMBERED) ?? read(sessionStorage, REFRESH_SESSION),
  rememberSession: Boolean(read(localStorage, REFRESH_REMEMBERED)),
  user: config.demoMode ? demoUser : null,
  scope: readJson(localStorage, SCOPE, { organizationId: null, schoolId: null }),
  bootstrapping: !config.demoMode,
  sidebarOpen: false,
};

const listeners = new Set();
function emit() { listeners.forEach(listener => listener(state)); }

export const store = {
  get state() { return state; },
  subscribe(listener) { listeners.add(listener); return () => listeners.delete(listener); },
  patch(update) { state = { ...state, ...update }; emit(); },
  setTokens(accessToken, refreshToken, remember) {
    try {
      localStorage.removeItem(REFRESH_REMEMBERED);
      sessionStorage.removeItem(REFRESH_SESSION);
      (remember ? localStorage : sessionStorage).setItem(remember ? REFRESH_REMEMBERED : REFRESH_SESSION, refreshToken);
    } catch {}
    state = { ...state, accessToken, refreshToken, rememberSession: remember };
    emit();
  },
  updateAccess(accessToken, refreshToken) {
    if (refreshToken) return this.setTokens(accessToken, refreshToken, state.rememberSession);
    state = { ...state, accessToken };
    emit();
  },
  setScope(scope) {
    try { localStorage.setItem(SCOPE, JSON.stringify(scope)); } catch {}
    state = { ...state, scope };
    emit();
  },
  clearSession() {
    try {
      localStorage.removeItem(REFRESH_REMEMBERED);
      sessionStorage.removeItem(REFRESH_SESSION);
      localStorage.removeItem(SCOPE);
    } catch {}
    state = { ...state, accessToken: null, refreshToken: null, user: null, scope: { organizationId: null, schoolId: null }, sidebarOpen: false };
    emit();
  },
};

export function useStore(selector = value => value) {
  const [selected, setSelected] = useState(() => selector(state));
  useEffect(() => store.subscribe(next => setSelected(selector(next))), [selector]);
  return selected;
}

export function activeRoles() {
  return [...new Set((store.state.user?.role_assignments ?? []).filter(item => item.is_active).map(item => item.role))];
}

export function hasRole(roles) {
  if (!roles?.length) return true;
  const active = activeRoles();
  return active.includes('system_admin') || roles.some(role => active.includes(role));
}

export const roleLabels = {
  system_admin: 'مدیر کل سامانه', organization_admin: 'مدیر مجموعه', school_manager: 'مدیر مدرسه',
  educational_deputy: 'معاون آموزشی', student_affairs_deputy: 'معاون دانش‌آموزی', operator: 'اپراتور',
  teacher: 'دبیر', counselor: 'مشاور', guide_teacher: 'معلم راهنما',
};
