import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import {
  ApiError,
  apiRequest,
  clearTokens,
  getCsrfToken,
  getTokens,
  isUsableToken,
  setTokens,
} from './api';

const TOKEN_KEY = 'cyberverse_access_token';
const REFRESH_KEY = 'cyberverse_refresh_token';

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

function setCsrfCookie(value: string): void {
  document.cookie = `cv_csrf=${value}; path=/`;
}

describe('token storage', () => {
  beforeEach(() => {
    if (typeof localStorage !== 'undefined') localStorage.clear();
  });

  it('returns null tokens when storage is empty', () => {
    expect(getTokens()).toEqual({ access: null, refresh: null });
  });

  it('stores and retrieves tokens', () => {
    setTokens('acc-token', 'ref-token');
    expect(localStorage.getItem(TOKEN_KEY)).toBe('acc-token');
    expect(localStorage.getItem(REFRESH_KEY)).toBe('ref-token');
    expect(getTokens()).toEqual({ access: 'acc-token', refresh: 'ref-token' });
  });

  it('clears tokens', () => {
    setTokens('a', 'r');
    clearTokens();
    expect(getTokens()).toEqual({ access: null, refresh: null });
  });

  it('never stores the literal strings "null" or "undefined" as tokens', () => {
    // `localStorage.setItem(key, null)` produces the truthy string "null",
    // which used to be sent as `Authorization: Bearer null` and took
    // precedence over the valid session cookie on the server.
    setTokens(null, undefined);
    expect(localStorage.getItem(TOKEN_KEY)).toBeNull();
    expect(localStorage.getItem(REFRESH_KEY)).toBeNull();
    expect(getTokens()).toEqual({ access: null, refresh: null });
  });

  it('treats a pre-existing "null" string in storage as no token', () => {
    localStorage.setItem(TOKEN_KEY, 'null');
    localStorage.setItem(REFRESH_KEY, 'undefined');
    expect(getTokens()).toEqual({ access: null, refresh: null });
  });
});

describe('isUsableToken', () => {
  it('rejects absent, empty and sentinel values', () => {
    expect(isUsableToken(null)).toBe(false);
    expect(isUsableToken(undefined)).toBe(false);
    expect(isUsableToken('')).toBe(false);
    expect(isUsableToken('   ')).toBe(false);
    expect(isUsableToken('null')).toBe(false);
    expect(isUsableToken('NULL')).toBe(false);
    expect(isUsableToken('undefined')).toBe(false);
    expect(isUsableToken('NaN')).toBe(false);
    expect(isUsableToken('none')).toBe(false);
  });

  it('accepts a real token', () => {
    expect(isUsableToken('eyJhbGciOiJIUzI1NiJ9.abc.def')).toBe(true);
  });
});

describe('apiRequest', () => {
  beforeEach(() => {
    if (typeof localStorage !== 'undefined') localStorage.clear();
    document.cookie = 'cv_csrf=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT';
    vi.restoreAllMocks();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('sends auth header with stored access token', async () => {
    setTokens('acc', 'ref');
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(200, { data: 'ok' }));
    vi.stubGlobal('fetch', fetchMock);

    await apiRequest('/profile/');

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe('http://localhost:8000/api/v1/profile/');
    expect(init.headers.Authorization).toBe('Bearer acc');
  });

  it('never sends a Bearer null / Bearer undefined header', async () => {
    // A stored "null" (the old bug) must not become an Authorization header.
    localStorage.setItem(TOKEN_KEY, 'null');
    localStorage.setItem(REFRESH_KEY, 'undefined');
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(200, { data: 'ok' }));
    vi.stubGlobal('fetch', fetchMock);

    await apiRequest('/profile/');

    const [, init] = fetchMock.mock.calls[0];
    expect(init.headers.Authorization).toBeUndefined();
  });

  it('sends cookies with every request so the session travels with it', async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(200, { data: 'ok' }));
    vi.stubGlobal('fetch', fetchMock);

    await apiRequest('/profile/');

    const [, init] = fetchMock.mock.calls[0];
    expect(init.credentials).toBe('include');
  });

  it('sends the CSRF token on state-changing requests', async () => {
    setCsrfCookie('csrf-token-value-123456');
    expect(getCsrfToken()).toBe('csrf-token-value-123456');
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(200, { data: 'ok' }));
    vi.stubGlobal('fetch', fetchMock);

    await apiRequest('/progress/lessons/abc', { method: 'POST', body: { status: 'completed' } });

    const [, init] = fetchMock.mock.calls[0];
    expect(init.headers['X-CSRF-Token']).toBe('csrf-token-value-123456');
  });

  it('does not send a CSRF header on safe requests', async () => {
    setCsrfCookie('csrf-token-value-123456');
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(200, { data: 'ok' }));
    vi.stubGlobal('fetch', fetchMock);

    await apiRequest('/profile/');

    const [, init] = fetchMock.mock.calls[0];
    expect(init.headers['X-CSRF-Token']).toBeUndefined();
  });

  it('omits auth header when auth is false', async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(200, { data: 'ok' }));
    vi.stubGlobal('fetch', fetchMock);

    await apiRequest('/auth/login', { method: 'POST', body: { email: 'a@b.c' }, auth: false });

    const [, init] = fetchMock.mock.calls[0];
    expect(init.headers.Authorization).toBeUndefined();
    expect(JSON.parse(init.body)).toEqual({ email: 'a@b.c' });
  });

  it('returns parsed JSON on success', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(200, { success: true, data: 42 })));
    const result = await apiRequest<{ success: boolean; data: number }>('/x');
    expect(result).toEqual({ success: true, data: 42 });
  });

  it('refreshes the session once and retries on 401 (cookie flow)', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(401, { detail: 'expired' }))
      // The refresh endpoint rotates the cookies; the body carries no tokens.
      .mockResolvedValueOnce(jsonResponse(200, { data: { access_token: null, refresh_token: null } }))
      .mockResolvedValueOnce(jsonResponse(200, { data: 'retried' }));
    vi.stubGlobal('fetch', fetchMock);

    const result = await apiRequest('/profile/');

    expect(result).toEqual({ data: 'retried' });
    expect(fetchMock).toHaveBeenCalledTimes(3);

    // The refresh call is cookie-authenticated and sends no bearer token.
    const refreshCall = fetchMock.mock.calls[1];
    expect(refreshCall[0]).toBe('http://localhost:8000/api/v1/auth/refresh');
    expect(refreshCall[1].credentials).toBe('include');
    expect(refreshCall[1].headers.Authorization).toBeUndefined();

    // The retried request relies on the cookie: no fabricated bearer header.
    const lastCall = fetchMock.mock.calls[2];
    expect(lastCall[1].headers.Authorization).toBeUndefined();
  });

  it('stores the rotated token when the backend opts in with body tokens', async () => {
    setTokens('expired', 'refresh-me');
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(401, { detail: 'expired' }))
      .mockResolvedValueOnce(jsonResponse(200, { data: { access_token: 'fresh', refresh_token: 'refresh-me' } }))
      .mockResolvedValueOnce(jsonResponse(200, { data: 'retried' }));
    vi.stubGlobal('fetch', fetchMock);

    const result = await apiRequest('/profile/');

    expect(result).toEqual({ data: 'retried' });
    expect(localStorage.getItem(TOKEN_KEY)).toBe('fresh');
    const lastCall = fetchMock.mock.calls[2];
    expect(lastCall[1].headers.Authorization).toBe('Bearer fresh');
  });

  it('does not retry forever when the session cannot be refreshed', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(401, { detail: 'expired' }))
      .mockResolvedValue(jsonResponse(401, { detail: 'invalid token' }));
    vi.stubGlobal('fetch', fetchMock);

    await expect(apiRequest('/profile/')).rejects.toThrow(ApiError);
    // original request + one refresh attempt only
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it('clears legacy tokens when the refresh session is revoked', async () => {
    setTokens('expired', 'bad-refresh');
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(401, { detail: 'expired' }))
      .mockResolvedValueOnce(jsonResponse(401, { detail: 'refresh token has been revoked' }));
    vi.stubGlobal('fetch', fetchMock);

    await expect(apiRequest('/profile/')).rejects.toThrow(ApiError);
    expect(localStorage.getItem(TOKEN_KEY)).toBeNull();
    expect(localStorage.getItem(REFRESH_KEY)).toBeNull();
  });

  it('keeps the session when the refresh fails for a non-auth reason', async () => {
    setTokens('acc', 'ref');
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(401, { detail: 'expired' }))
      .mockResolvedValueOnce(jsonResponse(500, { detail: 'boom' }));
    vi.stubGlobal('fetch', fetchMock);

    await expect(apiRequest('/profile/')).rejects.toThrow(ApiError);
    // A server fault must not sign the user out.
    expect(localStorage.getItem(TOKEN_KEY)).toBe('acc');
  });

  it('does not create a refresh storm when several requests fail at once', async () => {
    const fetchMock = vi.fn().mockImplementation(async (url: string) => {
      if (url.endsWith('/auth/refresh')) {
        return jsonResponse(200, { data: { access_token: null, refresh_token: null } });
      }
      return jsonResponse(401, { detail: 'expired' });
    });
    vi.stubGlobal('fetch', fetchMock);

    await Promise.allSettled([
      apiRequest('/profile/'),
      apiRequest('/progress/overview'),
      apiRequest('/missions/daily'),
    ]);

    const refreshCalls = fetchMock.mock.calls.filter(([url]) => String(url).endsWith('/auth/refresh'));
    expect(refreshCalls.length).toBe(1);
  });

  it('throws ApiError with message from string detail', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(404, { detail: 'Not found' })));
    await expect(apiRequest('/missing')).rejects.toMatchObject({
      status: 404,
      message: 'Not found',
    });
  });

  it('throws ApiError with joined messages from array detail', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        jsonResponse(422, {
          detail: [{ msg: 'field required' }, { msg: 'too short' }],
        }),
      ),
    );
    await expect(apiRequest('/x')).rejects.toMatchObject({
      status: 422,
      message: 'field required; too short',
    });
  });

  it('falls back to generic message for non-JSON errors', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(new Response('boom', { status: 500 })),
    );
    await expect(apiRequest('/x')).rejects.toMatchObject({
      status: 500,
      message: 'Request failed with status 500',
    });
  });
});
