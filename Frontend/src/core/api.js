import { config } from './config.js';
import { store } from './store.js';
import { alerts, dashboardData, studentProfile, students } from './mock-data.js';

export class ApiError extends Error {
  constructor({ status = 0, code = 'error', message = 'در پردازش درخواست خطایی رخ داد.', detail, requestId, fieldErrors = {} } = {}) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.detail = detail;
    this.requestId = requestId;
    this.fieldErrors = fieldErrors;
  }
}

const messages = {
  400: 'اطلاعات ارسال‌شده معتبر نیست.', 401: 'نشست شما منقضی شده است. دوباره وارد شوید.',
  403: 'برای این عملیات دسترسی کافی ندارید.', 404: 'داده موردنظر پیدا نشد.',
  409: 'این عملیات با وضعیت فعلی داده تعارض دارد.', 429: 'تعداد درخواست‌ها زیاد است. کمی بعد تلاش کنید.',
  503: 'سرویس موقتاً آماده نیست. دوباره تلاش کنید.',
};

let refreshPromise;

function url(path, query) {
  if (/^https?:\/\//.test(path)) return path;
  const clean = path.replace(/^\/+/, '').replace(/^api\/v1\//, '');
  const result = new URL(clean, new URL(config.apiBaseUrl, location.origin));
  for (const [key, value] of Object.entries(query ?? {})) {
    if (value !== undefined && value !== null && value !== '') result.searchParams.set(key, String(value));
  }
  return result.toString();
}

async function parsedError(response) {
  let body;
  try { body = await response.json(); } catch { body = {}; }
  const wrapped = body?.error ?? {};
  const detail = wrapped.detail ?? body.detail ?? body;
  const fieldErrors = detail && typeof detail === 'object' && !Array.isArray(detail)
    ? Object.fromEntries(Object.entries(detail).map(([key, value]) => [key, Array.isArray(value) ? value.map(String) : [String(value)]])) : {};
  const first = Object.values(fieldErrors)[0]?.[0];
  return new ApiError({ status: response.status, code: wrapped.code ?? `http_${response.status}`, message: first ?? messages[response.status], detail, requestId: wrapped.request_id, fieldErrors });
}

async function refreshAccess() {
  if (!store.state.refreshToken) throw new ApiError({ status: 401, message: messages[401] });
  if (!refreshPromise) {
    refreshPromise = fetch(url('auth/token/refresh/'), {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh: store.state.refreshToken }),
    }).then(async response => {
      if (!response.ok) throw await parsedError(response);
      const body = await response.json();
      store.updateAccess(body.access, body.refresh);
      return body.access;
    }).finally(() => { refreshPromise = null; });
  }
  return refreshPromise;
}

export async function apiRequest(path, options = {}) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), options.timeoutMs ?? config.requestTimeoutMs);
  const headers = new Headers(options.headers);
  headers.set('Accept', options.responseType === 'blob' ? '*/*' : 'application/json');
  headers.set('X-Request-ID', crypto.randomUUID?.() ?? `${Date.now()}-${Math.random()}`);
  const auth = options.auth !== false;
  if (auth && store.state.accessToken) headers.set('Authorization', `Bearer ${store.state.accessToken}`);
  if (store.state.scope.schoolId) headers.set('X-School-ID', store.state.scope.schoolId);
  else if (store.state.scope.organizationId) headers.set('X-Organization-ID', store.state.scope.organizationId);
  const form = options.body instanceof FormData;
  if (options.body !== undefined && !form) headers.set('Content-Type', 'application/json');
  try {
    const response = await fetch(url(path, options.query), {
      method: options.method ?? 'GET', headers, signal: options.signal ?? controller.signal,
      body: options.body === undefined ? undefined : form ? options.body : JSON.stringify(options.body),
    });
    if (response.status === 401 && auth && options.retryAuth !== false && store.state.refreshToken) {
      const access = await refreshAccess();
      return apiRequest(path, { ...options, headers: { ...Object.fromEntries(headers), Authorization: `Bearer ${access}` }, retryAuth: false });
    }
    if (!response.ok) throw await parsedError(response);
    if (options.responseType === 'blob') return response.blob();
    if (options.responseType === 'text') return response.text();
    if (options.responseType === 'void' || response.status === 204) return undefined;
    const text = await response.text();
    return text ? JSON.parse(text) : undefined;
  } catch (error) {
    if (error instanceof ApiError) throw error;
    if (error instanceof DOMException && error.name === 'AbortError') throw new ApiError({ code: 'timeout', message: 'مهلت درخواست به پایان رسید.' });
    throw new ApiError({ code: 'network_error', message: 'ارتباط با سرور برقرار نشد. اتصال شبکه را بررسی کنید.', detail: error });
  } finally { clearTimeout(timer); }
}

export async function login(identifier, password, remember) {
  if (config.demoMode) {
    store.patch({ user: { id: 1, username: identifier || 'manager.demo', first_name: 'مریم', last_name: 'نادری', role_assignments: [{ id: 'demo', role: 'school_manager', is_active: true }] }, bootstrapping: false });
    return;
  }
  const tokens = await apiRequest('auth/token/', { method: 'POST', auth: false, retryAuth: false, body: { username: identifier, password } });
  store.setTokens(tokens.access, tokens.refresh, remember);
  const user = await apiRequest('auth/me/');
  store.patch({ user, bootstrapping: false });
}

export async function restoreSession() {
  if (config.demoMode || store.state.user) { store.patch({ bootstrapping: false }); return true; }
  if (!store.state.refreshToken) { store.patch({ bootstrapping: false }); return false; }
  try {
    await refreshAccess();
    const user = await apiRequest('auth/me/');
    store.patch({ user, bootstrapping: false });
    return true;
  } catch { store.clearSession(); store.patch({ bootstrapping: false }); return false; }
}

export async function logout() {
  const refresh = store.state.refreshToken;
  try { if (refresh && !config.demoMode) await apiRequest('auth/logout/', { method: 'POST', body: { refresh }, responseType: 'void', retryAuth: false }); } catch {}
  store.clearSession();
}

function results(value) { return Array.isArray(value) ? value : value?.results ?? []; }

function faNumber(value) {
  return new Intl.NumberFormat('fa-IR', { maximumFractionDigits: 2 }).format(Number(value) || 0);
}

export function normalizeStudent(item) {
  return {
    id: item.id,
    name: item.name ?? item.full_name ?? (`${item.first_name ?? ''} ${item.last_name ?? ''}`.trim() || 'دانش‌آموز'),
    code: item.code ?? item.national_id ?? '—',
    grade: item.grade ?? 'بدون ثبت پایه',
    className: item.className ?? item.class_title ?? '—',
    average: item.average ?? '—',
    attendance: Number(item.attendance ?? 0),
    status: item.status ?? 'active',
    risk: item.risk ?? 'none',
    photo: item.photo ?? null,
  };
}

export function normalizeAlert(item) {
  const absenceCount = Number(item.absence_count ?? 0);
  const severity = item.severity === 'critical' ? 'critical' : item.severity === 'review' ? 'review' : 'important';
  return {
    id: item.id,
    studentId: item.student_id ?? item.student,
    student: item.student_name ?? item.student ?? 'دانش‌آموز',
    meta: item.meta ?? ([item.class_title, item.school_name].filter(Boolean).join(' · ') || 'حضور و غیاب'),
    title: item.title ?? `${absenceCount ? `${faNumber(absenceCount)} مورد ` : ''}غیبت در بازه اخیر`,
    type: item.type ?? (item.scope === 'period' ? 'غیبت کلاسی' : 'حضور و غیاب'),
    severity,
    time: item.time ?? (item.created_at ? new Intl.DateTimeFormat('fa-IR', { dateStyle: 'short', timeStyle: 'short' }).format(new Date(item.created_at)) : '—'),
    evidence: item.evidence ?? [
      `${faNumber(absenceCount)} غیبت از ${faNumber(item.total_sessions)} جلسه`,
      `نرخ غیبت ${faNumber(item.absence_percent)}٪`,
      `وضعیت: ${item.status === 'resolved' ? 'حل‌شده' : item.status === 'acknowledged' ? 'مشاهده‌شده' : 'باز'}`,
    ],
  };
}

export const dataApi = {
  dashboard: async signal => {
    if (config.demoMode) return dashboardData;
    const summary = await apiRequest('dashboard/manager/', { signal });
    const metrics = summary.metrics ?? {};
    return {
      ...dashboardData,
      school: 'مدرسه فعال', academicYear: 'سال تحصیلی جاری', metrics, raw: summary,
      kpis: [
        { label: 'کل دانش‌آموزان فعال', value: faNumber(metrics.active_students), delta: 'بر اساس ثبت‌نام فعال', tone: 'purple', icon: 'users' },
        { label: 'نیازمند پیگیری', value: faNumber(metrics.high_risk_signals), delta: 'سیگنال پرریسک فعال', tone: 'pink', icon: 'alert' },
        { label: 'هشدارهای باز', value: faNumber(metrics.open_operational_alerts), delta: 'نیازمند اقدام', tone: 'orange', icon: 'attendance' },
        { label: 'گزارش‌های ارسال‌شده', value: faNumber(metrics.submitted_report_drafts), delta: 'پیش‌نویس ثبت‌شده', tone: 'green', icon: 'report' },
      ],
    };
  },
  students: async (query, signal) => config.demoMode ? students : results(await apiRequest('students/', { query, signal })).map(normalizeStudent),
  student: async (id, signal) => {
    if (config.demoMode) return { ...studentProfile, ...(students.find(item => item.id === id) ?? {}) };
    const [summary, academics, attendance, evaluations] = await Promise.all([
      apiRequest(`students/${id}/360/summary/`, { signal }), apiRequest(`students/${id}/360/academics/`, { signal }),
      apiRequest(`students/${id}/360/attendance/`, { signal }), apiRequest(`students/${id}/360/evaluations/`, { signal }),
    ]);
    return { summary, academics, attendance, evaluations };
  },
  alerts: async (query, signal) => config.demoMode ? alerts : results(await apiRequest('attendance-alerts/', { query, signal })).map(normalizeAlert),
  resource: async (tag, query, signal) => results(await apiRequest(`${tag}/`, { query, signal })),
};
