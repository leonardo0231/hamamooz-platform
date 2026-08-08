import { config } from '../app/config.js';
import { store } from '../app/store.js';
import { humanizeApiError, networkError } from './errors.js';
import { ApiError, type ApiErrorPayload, type RefreshResponse, type RequestOptions } from './types.js';
import { endpoints } from './endpoints.js';

let refreshPromise: Promise<string> | null = null;
let unauthorizedHandler: (() => void) | null = null;

export function onUnauthorized(handler: () => void): void {
  unauthorizedHandler = handler;
}

function requestId(): string {
  return globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export function normalizeApiPath(path: string): string {
  if (/^https?:\/\//i.test(path)) return path;
  const clean = path.replace(/^\//, '').replace(/^api\/v1\//, '');
  const baseUrl = new URL(config.apiBaseUrl, globalThis.location.origin);
  return new URL(clean, baseUrl).toString();
}

function withQuery(url: string, query: RequestOptions['query']): string {
  const result = new URL(url);
  if (!query) return result.toString();
  for (const [key, value] of Object.entries(query)) {
    if (value !== null && value !== undefined && value !== '') result.searchParams.set(key, String(value));
  }
  return result.toString();
}

function invalidResponse(status: number, detail: unknown): ApiError {
  return new ApiError({
    status,
    code: 'invalid_response',
    message: 'پاسخ دریافتی از سرور ساختار معتبر ندارد.',
    detail,
  });
}

async function parseError(response: Response): Promise<ApiError> {
  let payload: ApiErrorPayload | null = null;
  try { payload = await response.json() as ApiErrorPayload; } catch { payload = null; }
  return humanizeApiError(response.status, payload);
}

async function refreshAccessToken(): Promise<string> {
  const refresh = store.state.refreshToken;
  if (!refresh) throw new ApiError({ status: 401, message: 'نشست قابل بازیابی نیست.' });
  if (!refreshPromise) {
    refreshPromise = (async () => {
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), config.requestTimeoutMs);
      try {
        const response = await fetch(normalizeApiPath(endpoints.auth.refresh), {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'X-Request-ID': requestId() },
          body: JSON.stringify({ refresh }),
          signal: controller.signal,
        });
        if (!response.ok) throw await parseError(response);
        let body: RefreshResponse;
        try { body = await response.json() as RefreshResponse; }
        catch (error) { throw invalidResponse(response.status, error); }
        if (!body.access) throw invalidResponse(response.status, body);
        store.updateAccess(body.access, body.refresh);
        return body.access;
      } catch (error) {
        if (error instanceof ApiError) throw error;
        if (error instanceof DOMException && error.name === 'AbortError') {
          throw new ApiError({ status: 0, code: 'timeout', message: 'مهلت تمدید نشست به پایان رسید.' });
        }
        throw networkError(error);
      } finally {
        clearTimeout(timeout);
      }
    })().finally(() => { refreshPromise = null; });
  }
  return refreshPromise;
}

async function xhrUpload<T>(url: string, options: RequestOptions, headers: Headers): Promise<T> {
  return await new Promise<T>((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    let settled = false;
    const abortUpload = (): void => xhr.abort();
    const cleanup = (): void => options.signal?.removeEventListener('abort', abortUpload);
    const succeed = (value: T): void => {
      if (settled) return;
      settled = true;
      cleanup();
      resolve(value);
    };
    const fail = (error: unknown): void => {
      if (settled) return;
      settled = true;
      cleanup();
      reject(error);
    };

    xhr.open(options.method ?? 'POST', url);
    headers.forEach((value, key) => xhr.setRequestHeader(key, value));
    xhr.timeout = options.timeoutMs ?? config.requestTimeoutMs;
    xhr.upload.onprogress = event => {
      if (event.lengthComputable) options.onUploadProgress?.(Math.round((event.loaded / event.total) * 100));
    };
    xhr.onerror = () => fail(networkError(new Error('XMLHttpRequest network failure')));
    xhr.ontimeout = () => fail(new ApiError({ status: 0, code: 'timeout', message: 'مهلت درخواست به پایان رسید.' }));
    xhr.onabort = () => fail(new ApiError({ status: 0, code: 'request_cancelled', message: 'درخواست لغو شد.' }));
    xhr.onload = () => {
      const contentType = xhr.getResponseHeader('Content-Type') ?? '';
      let parsed: unknown = xhr.status === 204 || !xhr.responseText ? undefined : xhr.responseText;
      if (contentType.includes('application/json') && xhr.responseText) {
        try { parsed = JSON.parse(xhr.responseText) as unknown; }
        catch (error) { fail(invalidResponse(xhr.status, error)); return; }
      }
      if (xhr.status >= 200 && xhr.status < 300) succeed(parsed as T);
      else fail(humanizeApiError(xhr.status, parsed as ApiErrorPayload));
    };
    if (options.signal?.aborted) {
      fail(new ApiError({ status: 0, code: 'request_cancelled', message: 'درخواست لغو شد.' }));
      return;
    }
    options.signal?.addEventListener('abort', abortUpload, { once: true });
    xhr.send(options.body instanceof FormData ? options.body : JSON.stringify(options.body ?? null));
  });
}

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const method = options.method ?? 'GET';
  const needsAuth = options.auth ?? (!path.includes('auth/token/') && !path.includes('health/'));
  const headers = new Headers(options.headers);
  headers.set('Accept', options.responseType === 'blob' ? '*/*' : 'application/json');
  headers.set('X-Request-ID', requestId());
  const { organizationId, schoolId } = store.state.scope;
  if (schoolId) headers.set('X-School-ID', schoolId);
  else if (organizationId) headers.set('X-Organization-ID', organizationId);
  if (needsAuth && store.state.accessToken) headers.set('Authorization', `Bearer ${store.state.accessToken}`);
  const isForm = options.body instanceof FormData;
  if (options.body !== undefined && !isForm) headers.set('Content-Type', 'application/json');
  const url = withQuery(normalizeApiPath(path), options.query);

  if (isForm && options.onUploadProgress) {
    try {
      return await xhrUpload<T>(url, { ...options, method }, headers);
    } catch (error) {
      if (error instanceof ApiError && error.status === 401 && needsAuth && options.retryAuth !== false && store.state.refreshToken) {
        try {
          const access = await refreshAccessToken();
          headers.set('Authorization', `Bearer ${access}`);
          return await apiRequest<T>(path, { ...options, headers: Object.fromEntries(headers), retryAuth: false });
        } catch (refreshError) {
          store.clearSession();
          unauthorizedHandler?.();
          throw refreshError;
        }
      }
      throw error;
    }
  }

  const controller = new AbortController();
  let timedOut = false;
  const timeout = setTimeout(() => { timedOut = true; controller.abort(); }, options.timeoutMs ?? config.requestTimeoutMs);
  const relayAbort = (): void => controller.abort();
  if (options.signal?.aborted) controller.abort();
  else options.signal?.addEventListener('abort', relayAbort, { once: true });
  try {
    const init: RequestInit = { method, headers, signal: controller.signal };
    if (options.body !== undefined) init.body = isForm ? options.body as FormData : JSON.stringify(options.body);
    const response = await fetch(url, init);
    if (response.status === 401 && needsAuth && options.retryAuth !== false && store.state.refreshToken) {
      try {
        const access = await refreshAccessToken();
        headers.set('Authorization', `Bearer ${access}`);
        return await apiRequest<T>(path, { ...options, headers: Object.fromEntries(headers), retryAuth: false });
      } catch (error) {
        store.clearSession();
        unauthorizedHandler?.();
        throw error;
      }
    }
    if (!response.ok) throw await parseError(response);
    if (options.responseType === 'void' || response.status === 204) return undefined as T;
    if (options.responseType === 'blob') return await response.blob() as T;
    if (options.responseType === 'text') return await response.text() as T;
    const text = await response.text();
    if (!text) return undefined as T;
    try { return JSON.parse(text) as T; }
    catch (error) { throw invalidResponse(response.status, error); }
  } catch (error) {
    if (error instanceof ApiError) throw error;
    if (timedOut && error instanceof DOMException && error.name === 'AbortError') {
      throw new ApiError({ status: 0, code: 'timeout', message: 'مهلت درخواست به پایان رسید.' });
    }
    throw networkError(error);
  } finally {
    clearTimeout(timeout);
    options.signal?.removeEventListener('abort', relayAbort);
  }
}
