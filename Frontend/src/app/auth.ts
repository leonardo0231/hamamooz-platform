import { apiRequest } from '../api/client.js';
import { endpoints } from '../api/endpoints.js';
import { ApiError, type LoginResponse, type RefreshResponse, type User } from '../api/types.js';
import { store } from './store.js';
import { navigate } from './router.js';
import { toast } from '../components/feedback.js';

export async function login(identifier: string, password: string, remember: boolean): Promise<void> {
  const response = await apiRequest<LoginResponse>(endpoints.auth.token, { method: 'POST', body: { username: identifier, password }, auth: false, retryAuth: false });
  store.setTokens(response.access, response.refresh, remember);
  try {
    const user = await apiRequest<User>(endpoints.auth.me);
    store.patch({ user, bootstrapping: false });
  } catch (error) {
    store.clearSession();
    throw error;
  }
}

export async function restoreSession(): Promise<boolean> {
  const refresh = store.state.refreshToken;
  if (!refresh) {
    store.patch({ bootstrapping: false });
    return false;
  }
  try {
    const renewed = await apiRequest<RefreshResponse>(endpoints.auth.refresh, {
      method: 'POST',
      body: { refresh },
      auth: false,
      retryAuth: false,
    });
    store.updateAccess(renewed.access, renewed.refresh);
    const user = await apiRequest<User>(endpoints.auth.me);
    store.patch({ user, bootstrapping: false });
    return true;
  } catch {
    store.clearSession();
    store.patch({ bootstrapping: false });
    return false;
  }
}

export async function ensureUser(): Promise<boolean> {
  if (store.state.user) return true;
  if (!store.state.refreshToken && !store.state.accessToken) return false;
  try {
    if (!store.state.accessToken && store.state.refreshToken) {
      const renewed = await apiRequest<RefreshResponse>(endpoints.auth.refresh, {
        method: 'POST',
        body: { refresh: store.state.refreshToken },
        auth: false,
        retryAuth: false,
      });
      store.updateAccess(renewed.access, renewed.refresh);
    }
    const user = await apiRequest<User>(endpoints.auth.me);
    store.patch({ user, bootstrapping: false });
    return true;
  } catch {
    store.clearSession();
    return false;
  }
}

export async function logout(): Promise<void> {
  let refresh = store.state.refreshToken;
  try {
    if (refresh) {
      try {
        await apiRequest<void>(endpoints.auth.logout, { method: 'POST', body: { refresh }, responseType: 'void', retryAuth: false });
      } catch (error) {
        if (!(error instanceof ApiError) || error.status !== 401) throw error;
        const renewed = await apiRequest<RefreshResponse>(endpoints.auth.refresh, { method: 'POST', body: { refresh }, auth: false, retryAuth: false });
        refresh = renewed.refresh ?? refresh;
        store.updateAccess(renewed.access, renewed.refresh);
        await apiRequest<void>(endpoints.auth.logout, { method: 'POST', body: { refresh }, responseType: 'void', retryAuth: false });
      }
    }
  } catch {
    toast('خروج محلی انجام شد؛ ابطال نشست در سرور تأیید نشد.', 'info');
  } finally {
    store.clearSession();
    navigate('/login', true);
  }
}
