function meta(name) {
  return document.querySelector(`meta[name="${name}"]`)?.content;
}

function withTrailingSlash(value) {
  const clean = String(value || '').trim();
  return clean.endsWith('/') ? clean : `${clean}/`;
}

const params = new URLSearchParams(location.search);
const runtime = window.__HAMAMOOZ_CONFIG__ ?? {};

export const config = Object.freeze({
  appName: runtime.appName ?? meta('application-name') ?? 'هم‌آموز',
  apiBaseUrl: withTrailingSlash(runtime.apiBaseUrl ?? meta('hamamooz-api-base-url') ?? '/api/v1/'),
  requestTimeoutMs: Number(runtime.requestTimeoutMs ?? 20_000),
  demoMode: params.get('demo') === '1' || localStorage.getItem('hamamooz.demo') === '1',
});
