interface RuntimeConfig {
  apiBaseUrl: string;
  appName: string;
  requestTimeoutMs: number;
}

declare global {
  interface Window {
    __HAMAMOOZ_CONFIG__?: Partial<RuntimeConfig>;
  }
}

function normalizeBaseUrl(value: string): string {
  const trimmed = value.trim();
  const withSlash = trimmed.endsWith('/') ? trimmed : `${trimmed}/`;
  return withSlash;
}

function fromMeta(name: string): string | undefined {
  return document.querySelector<HTMLMetaElement>(`meta[name="${name}"]`)?.content || undefined;
}

const runtime = window.__HAMAMOOZ_CONFIG__ ?? {};

export const config: RuntimeConfig = Object.freeze({
  apiBaseUrl: normalizeBaseUrl(runtime.apiBaseUrl ?? fromMeta('hamamooz-api-base-url') ?? 'http://localhost:8000/api/v1/'),
  appName: runtime.appName ?? fromMeta('application-name') ?? 'هم‌آموز',
  requestTimeoutMs: runtime.requestTimeoutMs ?? Number(fromMeta('hamamooz-request-timeout-ms') ?? 20_000),
});
