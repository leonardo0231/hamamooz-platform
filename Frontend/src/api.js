const API_ROOT = (import.meta.env.VITE_API_BASE_URL || "/api/v1").replace(/\/$/, "");

const TOKEN_KEY = "hamamooz.tokens";
const SCHOOL_KEY = "hamamooz.school";

export class ApiError extends Error {
  constructor(message, status, data) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.data = data;
  }
}

export function getTokens() {
  try {
    return JSON.parse(localStorage.getItem(TOKEN_KEY)) || null;
  } catch {
    return null;
  }
}

export function setTokens(tokens) {
  localStorage.setItem(TOKEN_KEY, JSON.stringify(tokens));
}

export function clearSession() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(SCHOOL_KEY);
}

export function getSelectedSchool() {
  return localStorage.getItem(SCHOOL_KEY) || "";
}

export function setSelectedSchool(id) {
  if (id) localStorage.setItem(SCHOOL_KEY, id);
  else localStorage.removeItem(SCHOOL_KEY);
}

async function readBody(response) {
  if (response.status === 204) return null;
  const contentType = response.headers.get("content-type") || "";
  return contentType.includes("application/json") ? response.json() : response.text();
}

export function formatApiError(error) {
  const data = error?.data;
  if (!data) return error?.message || "ارتباط با سرور برقرار نشد.";
  if (typeof data === "string") return data;
  if (data.detail) return Array.isArray(data.detail) ? data.detail.join("، ") : data.detail;
  return Object.entries(data)
    .map(([key, value]) => `${key}: ${Array.isArray(value) ? value.join("، ") : value}`)
    .join(" | ");
}

async function refreshAccessToken() {
  const tokens = getTokens();
  if (!tokens?.refresh) return false;
  const response = await fetch(`${API_ROOT}/auth/token/refresh/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh: tokens.refresh }),
  });
  if (!response.ok) {
    clearSession();
    return false;
  }
  const data = await response.json();
  setTokens({ access: data.access, refresh: data.refresh || tokens.refresh });
  return true;
}

export async function api(path, options = {}, retry = true) {
  const tokens = getTokens();
  const headers = new Headers(options.headers || {});
  headers.set("Accept", "application/json");
  if (!(options.body instanceof FormData) && options.body != null) {
    headers.set("Content-Type", "application/json");
  }
  if (tokens?.access) headers.set("Authorization", `Bearer ${tokens.access}`);
  const school = getSelectedSchool();
  if (school) headers.set("X-School-ID", school);

  let response;
  try {
    response = await fetch(`${API_ROOT}${path}`, { ...options, headers });
  } catch {
    throw new ApiError("Backend در دسترس نیست. سرویس API را بررسی کنید.", 0, null);
  }
  if (response.status === 401 && retry && !path.startsWith("/auth/token")) {
    if (await refreshAccessToken()) return api(path, options, false);
  }
  const data = await readBody(response);
  if (!response.ok) {
    throw new ApiError(
      typeof data === "object" && data?.detail ? data.detail : "درخواست ناموفق بود.",
      response.status,
      data,
    );
  }
  return data;
}

export async function login(username, password) {
  let response;
  try {
    response = await fetch(`${API_ROOT}/auth/token/`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify({ username, password }),
    });
  } catch {
    throw new ApiError("Backend در دسترس نیست. سرویس API را بررسی کنید.", 0, null);
  }
  const data = await readBody(response);
  if (!response.ok) throw new ApiError("ورود ناموفق بود.", response.status, data);
  setTokens({ access: data.access, refresh: data.refresh });
  return data.user;
}

export async function logout() {
  const tokens = getTokens();
  try {
    if (tokens?.refresh) {
      await api("/auth/logout/", {
        method: "POST",
        body: JSON.stringify({ refresh: tokens.refresh }),
      });
    }
  } finally {
    clearSession();
  }
}

export async function download(path, filename) {
  const tokens = getTokens();
  const headers = new Headers();
  if (tokens?.access) headers.set("Authorization", `Bearer ${tokens.access}`);
  const school = getSelectedSchool();
  if (school) headers.set("X-School-ID", school);
  const response = await fetch(`${API_ROOT}${path}`, { headers });
  if (!response.ok) {
    const data = await readBody(response);
    throw new ApiError("دریافت فایل ناموفق بود.", response.status, data);
  }
  const url = URL.createObjectURL(await response.blob());
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

export { API_ROOT };
