import type { ScopeState, User } from '../api/types.js';

export interface AppState {
  accessToken: string | null;
  refreshToken: string | null;
  rememberSession: boolean;
  user: User | null;
  scope: ScopeState;
  bootstrapping: boolean;
  sidebarOpen: boolean;
}

type Listener = (state: Readonly<AppState>) => void;
const REFRESH_SESSION_KEY = 'hamamooz.refresh.session';
const REFRESH_LOCAL_KEY = 'hamamooz.refresh.remembered';
const SCOPE_KEY = 'hamamooz.scope';

function browserStorage(kind: 'local' | 'session'): Storage | null {
  try { return kind === 'local' ? window.localStorage : window.sessionStorage; } catch { return null; }
}

function safeGet(storage: Storage | null, key: string): string | null {
  try { return storage?.getItem(key) ?? null; } catch { return null; }
}

function loadJson<T>(storage: Storage | null, key: string): T | null {
  try {
    const value = safeGet(storage, key);
    return value ? JSON.parse(value) as T : null;
  } catch {
    return null;
  }
}

const local = browserStorage('local');
const session = browserStorage('session');
const rememberedToken = safeGet(local, REFRESH_LOCAL_KEY);
const sessionToken = safeGet(session, REFRESH_SESSION_KEY);
const savedScope = loadJson<ScopeState>(local, SCOPE_KEY);

class AppStore {
  #state: AppState = {
    accessToken: null,
    refreshToken: rememberedToken ?? sessionToken,
    rememberSession: Boolean(rememberedToken),
    user: null,
    scope: savedScope ?? { organizationId: null, schoolId: null },
    bootstrapping: true,
    sidebarOpen: false,
  };

  #listeners = new Set<Listener>();

  get state(): Readonly<AppState> {
    return this.#state;
  }

  subscribe(listener: Listener): () => void {
    this.#listeners.add(listener);
    return () => this.#listeners.delete(listener);
  }

  patch(update: Partial<AppState>): void {
    this.#state = { ...this.#state, ...update };
    this.#listeners.forEach(listener => listener(this.#state));
  }

  setTokens(accessToken: string, refreshToken: string, remember: boolean): void {
    try { local?.removeItem(REFRESH_LOCAL_KEY); } catch {}
    try { session?.removeItem(REFRESH_SESSION_KEY); } catch {}
    try { (remember ? local : session)?.setItem(remember ? REFRESH_LOCAL_KEY : REFRESH_SESSION_KEY, refreshToken); } catch {}
    this.patch({ accessToken, refreshToken, rememberSession: remember });
  }

  updateAccess(accessToken: string, refreshToken?: string): void {
    if (refreshToken) {
      this.setTokens(accessToken, refreshToken, this.#state.rememberSession);
      return;
    }
    this.patch({ accessToken });
  }

  setScope(scope: ScopeState): void {
    try { local?.setItem(SCOPE_KEY, JSON.stringify(scope)); } catch {}
    this.patch({ scope });
  }

  clearSession(): void {
    try { local?.removeItem(REFRESH_LOCAL_KEY); } catch {}
    try { session?.removeItem(REFRESH_SESSION_KEY); } catch {}
    try { local?.removeItem(SCOPE_KEY); } catch {}
    this.patch({ accessToken: null, refreshToken: null, user: null, rememberSession: false, scope: { organizationId: null, schoolId: null }, sidebarOpen: false });
  }
}

export const store = new AppStore();
