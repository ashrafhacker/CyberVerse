export const API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000/api/v1';

export class ApiError extends Error {
  status: number;
  details: Record<string, unknown>;

  constructor(status: number, message: string, details: Record<string, unknown> = {}) {
    super(message);
    this.status = status;
    this.details = details;
  }
}

interface RequestOptions {
  method?: string;
  body?: unknown;
  headers?: Record<string, string>;
  auth?: boolean;
}

const TOKEN_KEY = 'cyberverse_access_token';
const REFRESH_KEY = 'cyberverse_refresh_token';

export function getTokens(): { access: string | null; refresh: string | null } {
  if (typeof window === 'undefined') return { access: null, refresh: null };
  return {
    access: localStorage.getItem(TOKEN_KEY),
    refresh: localStorage.getItem(REFRESH_KEY),
  };
}

export function setTokens(access: string, refresh: string) {
  localStorage.setItem(TOKEN_KEY, access);
  localStorage.setItem(REFRESH_KEY, refresh);
}

export function clearTokens() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(REFRESH_KEY);
}

async function refreshAccessToken(): Promise<string | null> {
  const { refresh } = getTokens();
  if (!refresh) return null;

  try {
    const res = await fetch(`${API_URL}/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refresh }),
    });
    if (!res.ok) {
      clearTokens();
      return null;
    }
    const data = await res.json();
    setTokens(data.access_token, data.refresh_token ?? refresh);
    return data.access_token;
  } catch {
    clearTokens();
    return null;
  }
}

export async function apiRequest<T = unknown>(
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  const { method = 'GET', body, headers = {}, auth = true } = options;

  const makeRequest = async (token?: string): Promise<Response> => {
    const finalHeaders: Record<string, string> = {
      'Content-Type': 'application/json',
      ...headers,
    };
    if (auth && token) finalHeaders.Authorization = `Bearer ${token}`;

    return fetch(`${API_URL}${path}`, {
      method,
      headers: finalHeaders,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  };

  let res = await makeRequest(getTokens().access ?? undefined);

  if (res.status === 401 && auth) {
    const newToken = await refreshAccessToken();
    if (newToken) {
      res = await makeRequest(newToken);
    }
  }

  if (!res.ok) {
    let message = `Request failed with status ${res.status}`;
    let details: Record<string, unknown> = {};
    try {
      const data = await res.json();
      if (typeof data.detail === 'string') message = data.detail;
      else if (Array.isArray(data.detail))
        message = data.detail.map((d: { msg?: string }) => d.msg).filter(Boolean).join('; ');
      else if (data.detail) details = data.detail;
      else if (data.message) message = data.message;
    } catch {
      // non-JSON error body
    }
    throw new ApiError(res.status, message, details);
  }

  return (await res.json()) as T;
}

export const api = {
  get: <T = unknown>(path: string, opts?: Omit<RequestOptions, 'method' | 'body'>) =>
    apiRequest<T>(path, { ...opts, method: 'GET' }),
  post: <T = unknown>(path: string, body?: unknown, opts?: Omit<RequestOptions, 'method' | 'body'>) =>
    apiRequest<T>(path, { ...opts, method: 'POST', body }),
  put: <T = unknown>(path: string, body?: unknown, opts?: Omit<RequestOptions, 'method' | 'body'>) =>
    apiRequest<T>(path, { ...opts, method: 'PUT', body }),
  patch: <T = unknown>(path: string, body?: unknown, opts?: Omit<RequestOptions, 'method' | 'body'>) =>
    apiRequest<T>(path, { ...opts, method: 'PATCH', body }),
  delete: <T = unknown>(path: string, opts?: Omit<RequestOptions, 'method' | 'body'>) =>
    apiRequest<T>(path, { ...opts, method: 'DELETE' }),
};
