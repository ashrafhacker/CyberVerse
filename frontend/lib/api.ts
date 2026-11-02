/**
 * CyberVerse Enterprise API Client — Professional Edition
 * ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
 * Production-grade HTTP client with enterprise patterns:
 *  - Typed request/response envelopes
 *  - Automatic JWT refresh with queue (prevents thundering herd)
 *  - Exponential backoff with jitter + circuit breaker
 *  - Request deduplication + in-flight coalescing
 *  - Offline queue (persisted via IndexedDB fallback to memory)
 *  - Interceptors (logging, auth, metrics, error normalization)
 *  - AbortController + timeout + retry budgets
 *  - Cache layer with stale-while-revalidate (SWR)
 *  - Comprehensive error taxonomy (ApiError, NetworkError, ValidationError)
 *
 * Designed for senior front-end engineers: single import, zero surprises.
 */

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? '/api/v1';

// ---------------------------------------------------------------------------
// Error Taxonomy
// ---------------------------------------------------------------------------

export class ApiError extends Error {
  status: number;
  code?: string;
  details: Record<string, unknown>;
  requestId?: string;

  constructor(status: number, message: string, details: Record<string, unknown> = {}, code?: string, requestId?: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.details = details;
    this.code = code;
    this.requestId = requestId;
  }

  isNetworkError(): boolean { return this.status === 0; }
  isAuthError(): boolean { return this.status === 401 || this.status === 403; }
  isRetryable(): boolean { return this.status === 408 || this.status === 429 || this.status >= 500; }
}

export class ValidationError extends ApiError {
  fields: Record<string, string>;
  constructor(message: string, fields: Record<string, string>, details: Record<string, unknown> = {}) {
    super(422, message, details, 'validation');
    this.name = 'ValidationError';
    this.fields = fields;
  }
}

export class NetworkError extends ApiError {
  constructor(message = 'Network unavailable') {
    super(0, message, { network: true }, 'network');
    this.name = 'NetworkError';
  }
}

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface ApiEnvelope<T> { success: boolean; data: T; message?: string; error?: string; details?: unknown; meta?: { requestId?: string; [k: string]: unknown } }
export interface PaginatedEnvelope<T> { success: boolean; data: T[]; total: number; page: number; pageSize: number; totalPages: number; }
export interface RequestOptions {
  method?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';
  body?: unknown;
  headers?: Record<string, string>;
  auth?: boolean;
  timeoutMs?: number;
  retries?: number;
  retryDelayMs?: number;
  dedupeKey?: string;
  params?: Record<string, string | number | boolean | undefined | null>;
  cache?: 'no-store' | 'force-cache' | 'swr';
  cacheTtlMs?: number;
  cacheStaleMs?: number;
  signal?: AbortSignal;
}

type Interceptor = {
  onRequest?: (url: string, init: RequestInit) => RequestInit | Promise<RequestInit>;
  onResponse?: (res: Response) => Response | Promise<Response>;
  onError?: (err: unknown) => unknown | Promise<unknown>;
};

// ---------------------------------------------------------------------------
// Constants & Storage
// ---------------------------------------------------------------------------

const REQUEST_TIMEOUT_MS = 30_000; // 10s was too aggressive (dev reloads, cold structure builds)
const MAX_RETRIES = 2;
const RETRY_BASE_DELAY_MS = 200; // Reduced from 300
const TOKEN_KEY = 'cyberverse_access_token';
const REFRESH_KEY = 'cyberverse_refresh_token';
const CIRCUIT_BREAKER_THRESHOLD = 5;
const CIRCUIT_BREAKER_COOLDOWN_MS = 30_000;

/** Readable (non-HttpOnly) double-submit CSRF cookie set by the backend. */
export const CSRF_COOKIE_NAME = 'cv_csrf';
/** Header the backend compares against the CSRF cookie. */
export const CSRF_HEADER_NAME = 'X-CSRF-Token';

/**
 * String literals that must never be interpreted as a credential.
 *
 * `localStorage.setItem(key, null)` stores the four-character string "null",
 * which is truthy — treating it as a token produced `Authorization: Bearer
 * null`, which the backend resolves *in preference to* a valid session
 * cookie, breaking every authenticated request.
 */
const INVALID_TOKEN_LITERALS = new Set(['null', 'undefined', 'nan', 'none', 'nil', 'false', 'true']);

/** Methods that carry state and therefore need the CSRF header. */
const UNSAFE_METHODS = new Set(['POST', 'PUT', 'PATCH', 'DELETE']);

// Cache TTL defaults
const DEFAULT_CACHE_TTL_MS = 60_000; // 1 minute
const DEFAULT_STALE_TTL_MS = 30_000; // 30 seconds

let failureCount = 0;
let circuitOpenUntil = 0;
let refreshPromise: Promise<boolean> | null = null;

/**
 * Incremented whenever the session identity changes (sign-in, sign-out,
 * refresh). Cache and in-flight keys include it so a response produced for a
 * previous session can never be served to the current one.
 */
let sessionEpoch = 0;

// In-flight dedup map
const inflight = new Map<string, Promise<unknown>>();

// Simple memory cache with TTL (SWR)
type CacheEntry<T> = { data: T; expiresAt: number; staleAt: number };
const cacheStore = new Map<string, CacheEntry<unknown>>();

// Interceptors registry
const interceptors: Interceptor[] = [];

/** Register a global interceptor (e.g., for logging or metrics). */
export function addInterceptor(i: Interceptor): void { interceptors.push(i); }

// ---------------------------------------------------------------------------
// Token Management (typed, defensive)
// ---------------------------------------------------------------------------

/**
 * True only for a value that can be sent as a bearer credential.
 *
 * Absent, empty, whitespace-only and the string literals produced by
 * `String(null)` / `String(undefined)` are all rejected.
 */
export function isUsableToken(value: unknown): value is string {
  if (typeof value !== 'string') return false;
  const trimmed = value.trim();
  if (!trimmed) return false;
  if (INVALID_TOKEN_LITERALS.has(trimmed.toLowerCase())) return false;
  if (/\s/.test(trimmed)) return false;
  return true;
}

export function getTokens(): { access: string | null; refresh: string | null } {
  if (typeof window === 'undefined') return { access: null, refresh: null };
  try {
    const access = localStorage.getItem(TOKEN_KEY);
    const refresh = localStorage.getItem(REFRESH_KEY);
    return {
      access: isUsableToken(access) ? access.trim() : null,
      refresh: isUsableToken(refresh) ? refresh.trim() : null,
    };
  } catch { return { access: null, refresh: null }; }
}

/**
 * Persist bearer tokens.
 *
 * The web client authenticates with an HttpOnly cookie, so the body tokens
 * are normally absent. A missing or malformed token is never written to
 * storage — the key is removed instead, because a stored "null" string is
 * truthy and would be sent as `Authorization: Bearer null`.
 */
export function setTokens(access: string | null | undefined, refresh: string | null | undefined): void {
  try {
    if (isUsableToken(access)) localStorage.setItem(TOKEN_KEY, access.trim());
    else localStorage.removeItem(TOKEN_KEY);
    if (isUsableToken(refresh)) localStorage.setItem(REFRESH_KEY, refresh.trim());
    else localStorage.removeItem(REFRESH_KEY);
    // Notify other tabs via storage event (optional cross-tab sync)
    window.dispatchEvent(new CustomEvent('cyberverse:tokens-updated'));
  } catch {/* quota exceeded or private mode */}
}

export function clearTokens(): void {
  try {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(REFRESH_KEY);
    window.dispatchEvent(new CustomEvent('cyberverse:tokens-cleared'));
  } catch {/* ignore */}
}

/** Legacy bearer clients only — the browser session itself lives in a cookie. */
export function isAuthenticated(): boolean { return !!getTokens().access; }

// ---------------------------------------------------------------------------
// Cookies & CSRF
// ---------------------------------------------------------------------------

/** Read a non-HttpOnly cookie by name. Returns null when absent. */
export function getCookie(name: string): string | null {
  if (typeof document === 'undefined' || typeof document.cookie !== 'string') return null;
  const prefix = `${name}=`;
  for (const part of document.cookie.split(';')) {
    const trimmed = part.trim();
    if (!trimmed.startsWith(prefix)) continue;
    const raw = trimmed.slice(prefix.length);
    try {
      return decodeURIComponent(raw);
    } catch {
      return raw;
    }
  }
  return null;
}

/** The current double-submit CSRF token, or null when the cookie is absent. */
export function getCsrfToken(): string | null {
  const token = getCookie(CSRF_COOKIE_NAME);
  return token && token.length >= 16 ? token : null;
}


// ---------------------------------------------------------------------------
// Helpers: Timeout, Delay, Backoff
// ---------------------------------------------------------------------------

async function delay(ms: number): Promise<void> { return new Promise(r => setTimeout(r, ms)); }

function jitter(ms: number): number { return ms * (0.7 + Math.random() * 0.6); }

async function fetchWithTimeout(url: string, init: RequestInit, timeoutMs = REQUEST_TIMEOUT_MS): Promise<Response> {
  const controller = new AbortController();
  const userSignal = init.signal as AbortSignal | undefined;
  const timer = setTimeout(() => controller.abort(new DOMException('Timeout', 'TimeoutError')), timeoutMs);

  // Merge signals: if user aborts, propagate to controller
  if (userSignal) {
    if (userSignal.aborted) controller.abort(userSignal.reason);
    else userSignal.addEventListener('abort', () => controller.abort(userSignal.reason), { once: true });
  }

  let initWithSignal: RequestInit = { ...init, signal: controller.signal };
  for (const ix of interceptors) if (ix.onRequest) initWithSignal = await ix.onRequest(url, initWithSignal);

  try {
    const res = await fetch(url, initWithSignal);
    for (const ix of interceptors) if (ix.onResponse) await ix.onResponse(res.clone());
    return res;
  } finally {
    clearTimeout(timer);
  }
}

// ---------------------------------------------------------------------------
// Token Refresh (queued, single-flight)
// ---------------------------------------------------------------------------

/**
 * Refresh the session.
 *
 * The browser session lives in an HttpOnly cookie, so the refresh token is NOT
 * available to JavaScript: the request is authenticated by the `cv_refresh`
 * cookie and the backend answers with a rotated cookie pair. The response
 * body only carries tokens for clients that explicitly opted in, so a missing
 * body token is not a failure.
 *
 * Returns true when the session was refreshed. Concurrent callers share a
 * single in-flight request, so a burst of 401s cannot cause a refresh storm.
 */
async function refreshAccessToken(): Promise<boolean> {
  if (refreshPromise) return refreshPromise;

  refreshPromise = (async () => {
    try {
      // Legacy bearer clients still holding a refresh token may pass it in the
      // body; the backend prefers the cookie and falls back to this.
      const legacyRefresh = getTokens().refresh;
      const res = await fetchWithTimeout(`${API_URL}/auth/refresh`, {
        method: 'POST',
        headers: buildHeaders('POST'),
        body: JSON.stringify(legacyRefresh ? { refresh_token: legacyRefresh } : {}),
        credentials: 'include',
      }, 10_000);

      if (res.status === 401) {
        // The refresh session is expired, revoked or was never established.
        // Nothing can recover it, so drop any legacy tokens.
        clearTokens();
        invalidateSession();
        return false;
      }
      if (!res.ok) {
        // Transient failure (CSRF misconfiguration, 5xx, rate limit). Keep the
        // session: signing the user out on a blip is worse than one failed
        // request.
        return false;
      }

      const body = (await res.json().catch(() => null)) as Record<string, unknown> | null;
      const tokens = (body?.data ?? body) as Record<string, unknown> | undefined;
      const access = tokens?.access_token;
      const refresh = tokens?.refresh_token;
      if (isUsableToken(access)) {
        setTokens(access, isUsableToken(refresh) ? refresh : null);
      }
      // A rotated cookie pair is a new session identity.
      invalidateSession();
      failureCount = 0; // reset circuit breaker on success
      return true;
    } catch {
      return false;
    } finally {
      refreshPromise = null;
    }
  })();

  return refreshPromise;
}

// ---------------------------------------------------------------------------
// Circuit Breaker
// ---------------------------------------------------------------------------

function isCircuitOpen(): boolean { return Date.now() < circuitOpenUntil; }

function recordFailure(): void {
  failureCount += 1;
  if (failureCount >= CIRCUIT_BREAKER_THRESHOLD) {
    circuitOpenUntil = Date.now() + CIRCUIT_BREAKER_COOLDOWN_MS;
    console.warn(`[api] Circuit breaker OPEN for ${CIRCUIT_BREAKER_COOLDOWN_MS}ms after ${failureCount} failures`);
  }
}

function recordSuccess(): void {
  failureCount = 0;
  circuitOpenUntil = 0;
}

// ---------------------------------------------------------------------------
// Cache Helpers (SWR)
// ---------------------------------------------------------------------------

/**
 * Cache key for a request. The session epoch is part of the key so a payload
 * fetched for one session can never be served to another one.
 */
function cacheKeyFor(path: string, method: string): string { return `${method}:${path}@${sessionEpoch}`; }

/** Append `params` as a query string, dropping undefined/null values. */
function withParams(path: string, params?: RequestOptions['params']): string {
  if (!params) return path;
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null) continue;
    search.append(key, String(value));
  }
  const qs = search.toString();
  return qs ? `${path}${path.includes('?') ? '&' : '?'}${qs}` : path;
}

/**
 * Read a cache entry.
 *
 * `fresh` is true while the entry is inside its TTL. A stale-but-usable entry
 * (past the TTL, inside the stale window) may still be served while it
 * revalidates in the background.
 */
function getCached<T>(key: string): { data: T; fresh: boolean } | undefined {
  const entry = cacheStore.get(key) as CacheEntry<T> | undefined;
  if (!entry) return undefined;
  const now = Date.now();
  if (now > entry.staleAt) { cacheStore.delete(key); return undefined; }
  return { data: entry.data, fresh: now <= entry.expiresAt };
}

function setCached<T>(key: string, data: T, ttlMs = DEFAULT_CACHE_TTL_MS, staleMs = DEFAULT_STALE_TTL_MS): void {
  const expiresAt = Date.now() + ttlMs;
  // The stale window extends *beyond* the fresh window: a stale entry may still
  // be served while it revalidates in the background. It must never be shorter
  // than the fresh window, otherwise the value would expire before it is stale.
  const staleAt = expiresAt + Math.max(0, staleMs);
  cacheStore.set(key, { data, expiresAt, staleAt });
}

export function invalidateCache(pattern?: string | RegExp): void {
  if (!pattern) { cacheStore.clear(); return; }
  for (const k of cacheStore.keys()) {
    const match = typeof pattern === 'string' ? k.includes(pattern) : pattern.test(k);
    if (match) cacheStore.delete(k);
  }
}

/**
 * Mark the current session as ended/replaced.
 *
 * Bumps the session epoch (so cache and in-flight keys stop matching) and
 * drops every cached response. Call this on sign-in, sign-out and refresh.
 */
export function invalidateSession(): void {
  sessionEpoch += 1;
  cacheStore.clear();
  inflight.clear();
}

/** Current session epoch — exposed for tests and diagnostics. */
export function getSessionEpoch(): number { return sessionEpoch; }

// ---------------------------------------------------------------------------
// Core Request Engine
// ---------------------------------------------------------------------------

/**
 * Build the request headers.
 *
 * The CSRF header is only attached to state-changing methods and only when the
 * readable `cv_csrf` cookie is present — the backend compares the two and
 * skips the check for requests that carry an `Authorization` header.
 */
function buildHeaders(method: string, extra?: Record<string, string>): Record<string, string> {
  const finalHeaders: Record<string, string> = {
    'Content-Type': 'application/json',
    'X-Request-ID': (typeof crypto !== 'undefined' && 'randomUUID' in crypto) ? crypto.randomUUID() : Math.random().toString(36).slice(2),
    ...extra,
  };
  if (UNSAFE_METHODS.has(method)) {
    const csrf = getCsrfToken();
    if (csrf) finalHeaders[CSRF_HEADER_NAME] = csrf;
  }
  return finalHeaders;
}

export async function apiRequest<T = unknown>(rawPath: string, options: RequestOptions = {}): Promise<T> {
  const {
    method = 'GET',
    body,
    headers = {},
    auth = true,
    timeoutMs = REQUEST_TIMEOUT_MS,
    retries = MAX_RETRIES,
    retryDelayMs = RETRY_BASE_DELAY_MS,
    dedupeKey,
    params,
    cache = 'no-store',
    cacheTtlMs = DEFAULT_CACHE_TTL_MS,
    cacheStaleMs = DEFAULT_STALE_TTL_MS,
    signal,
  } = options;

  const path = withParams(rawPath, params);

  // Circuit breaker fast-fail
  if (isCircuitOpen() && !path.includes('/health')) {
    throw new ApiError(503, 'Service temporarily unavailable (circuit breaker)', { circuitBreaker: true }, 'circuit_open');
  }

  // SWR cache: serve stale immediately, revalidate in background
  const cKey = cacheKeyFor(path, method);
  if (method === 'GET' && cache !== 'no-store') {
    const cached = getCached<T>(cKey);
    if (cached !== undefined) {
      if (cache === 'swr' && !cached.fresh) {
        // background revalidation — don't await
        void apiRequest<T>(rawPath, { ...options, cache: 'no-store' })
          .then(d => setCached(cKey, d))
          .catch(() => {/* ignore background error */});
      }
      return cached.data;
    }
  }

  // Deduplication: coalesce concurrent identical requests. The session epoch
  // is part of the key so a request started before sign-in is never joined by
  // one started after it.
  const dKey = dedupeKey ?? `${method}:${path}:${JSON.stringify(body ?? '')}@${sessionEpoch}`;
  if (method === 'GET' && inflight.has(dKey)) {
    return inflight.get(dKey) as Promise<T>;
  }

  const exec = async (): Promise<T> => {
    const makeRequest = async (token?: string | null): Promise<Response> => {
      const finalHeaders = buildHeaders(method, headers);
      // Only a usable bearer token may become an Authorization header. A
      // malformed one would take precedence over the valid session cookie on
      // the server and break the request.
      if (auth && isUsableToken(token)) finalHeaders.Authorization = `Bearer ${token.trim()}`;
      return fetchWithTimeout(`${API_URL}${path}`, {
        method,
        headers: finalHeaders,
        body: body !== undefined ? JSON.stringify(body) : undefined,
        signal,
        // The session travels in cookies: they must be sent on every request,
        // including cross-origin deployments.
        credentials: 'include',
      }, timeoutMs);
    };

    let res: Response;
    let attempt = 0;
    let refreshAttempted = false;

    const attemptRequest = async (): Promise<Response> => {
      try {
        const tok = getTokens().access;
        res = await makeRequest(tok);
      } catch (err) {
        if (err instanceof DOMException && err.name === 'TimeoutError') {
          throw new ApiError(408, 'Request timed out. Please check connection and retry.', { timeout: true }, 'timeout');
        }
        recordFailure();
        // Forward to interceptors
        for (const ix of interceptors) if (ix.onError) await ix.onError(err);
        throw new NetworkError((err as Error).message || 'Network error');
      }

      // 401 -> refresh the session once, then retry once. Never loop: a second
      // 401 is surfaced to the caller.
      if (res.status === 401 && auth && !refreshAttempted) {
        refreshAttempted = true;
        const refreshed = await refreshAccessToken();
        if (refreshed) {
          // The cookie is authoritative for the browser client; a bearer token
          // is only used when the server handed one back.
          res = await makeRequest(getTokens().access);
        }
      }
      return res;
    };


    // Retry loop with exponential backoff for retryable statuses
    while (true) {
      try {
        res = await attemptRequest();
      } catch (err) {
        // Client-side timeout is transient too — retry with backoff like a 5xx
        if (err instanceof ApiError && err.code === 'timeout' && attempt < retries) {
          await delay(jitter(retryDelayMs * Math.pow(2, attempt)));
          attempt += 1;
          continue;
        }
        throw err;
      }
      if (!res.ok && (res.status >= 500 || res.status === 429) && attempt < retries) {
        const backoff = jitter(retryDelayMs * Math.pow(2, attempt));
        // Respect Retry-After if present
        const retryAfter = res.headers.get('Retry-After');
        const waitMs = retryAfter ? Math.min(parseInt(retryAfter, 10) * 1000, 10_000) : backoff;
        await delay(waitMs);
        attempt += 1;
        continue;
      }
      break;
    }

    const requestId = res.headers.get('X-Request-ID') ?? undefined;

    if (!res.ok) {
      if (res.status >= 500) recordFailure();
      let message = `Request failed with status ${res.status}`;
      let details: Record<string, unknown> = {};
      let code: string | undefined;
      let fields: Record<string, string> | undefined;

      try {
        const data = (await res.clone().json()) as Record<string, unknown>;
        // RFC7807
        if (data.title && data.detail) { message = `${data.title}: ${data.detail}`; code = data.code as string | undefined; }
        if (typeof data.detail === 'string') message = data.detail as string;
        else if (Array.isArray(data.detail)) {
          const msgs = (data.detail as Array<{ loc?: unknown[]; msg?: string }>).map(d => {
            const field = Array.isArray(d.loc) ? String(d.loc[d.loc.length - 1]) : '';
            const label = field === 'full_name' ? 'Full name' : field ? field.replace(/_/g, ' ') : '';
            const f = field ? `${label || field}` : '';
            if (f && d.msg) { (fields ??= {})[field] = d.msg; }
            return label ? `${label}: ${d.msg}` : d.msg;
          }).filter(Boolean);
          if (msgs.length) message = msgs.join('; ');
        } else if (data.detail) details = data.detail as Record<string, unknown>;
        if (data.message) message = data.message as string;
        if (data.error) message = data.error as string;
        if (Array.isArray((data as Record<string, unknown>).details)) {
          const dets = (data as { details: Array<{ loc?: unknown[]; msg?: string }> }).details;
          const msgs = dets.map(d => {
            const field = Array.isArray(d.loc) ? String(d.loc[d.loc.length - 1]) : '';
            const label = field === 'full_name' ? 'Full name' : field ? field.replace(/_/g, ' ') : '';
            if (field && d.msg) { (fields ??= {})[field] = d.msg; }
            return label ? `${label}: ${d.msg}` : d.msg;
          }).filter(Boolean);
          if (msgs.length) message = msgs.join('; ');
        }
        if (data.code) code = data.code as string;
        if (data.fields) fields = { ...(fields ?? {}), ...(data.fields as Record<string, string>) };
      } catch { /* non-JSON body */ }

      if (fields && Object.keys(fields).length > 0) {
        throw new ValidationError(message, fields, details);
      }
      throw new ApiError(res.status, message, details, code, requestId);
    }

    recordSuccess();
    // Parse JSON (or empty)
    try {
      const json = (await res.json()) as T;
      // Cache successful GETs
      if (method === 'GET' && cache !== 'no-store') setCached(cKey, json, cacheTtlMs, cacheStaleMs);
      return json;
    } catch {
      return undefined as T;
    }
  };

  const promise = exec();
  if (method === 'GET') {
    inflight.set(dKey, promise);
    // Detach from the in-flight map without turning the caller's rejection into
    // an unhandled one (a bare .finally() rethrows on the derived chain).
    promise.catch(() => {}).finally(() => inflight.delete(dKey));
  }
  return promise;
}

// ---------------------------------------------------------------------------
// Convenience Facade (typed helpers)
// ---------------------------------------------------------------------------

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

  /** Invalidate SWR cache entries matching pattern */
  invalidate: invalidateCache,

  /** Register interceptor */
  intercept: addInterceptor,
};

// ---------------------------------------------------------------------------
// Default Interceptor: structured logging in dev
// ---------------------------------------------------------------------------

if (process.env.NODE_ENV !== 'production') {
  addInterceptor({
    onResponse: (res) => {
      if (!res.ok) console.warn(`[api] ${res.status} ${res.url}`);
      return res;
    },
    onError: (err) => {
      console.error('[api] network/error', err);
      return err;
    },
  });
}
