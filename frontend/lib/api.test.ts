import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiError, apiRequest, clearTokens, getTokens, setTokens } from './api';

const TOKEN_KEY = 'cyberverse_access_token';
const REFRESH_KEY = 'cyberverse_refresh_token';

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

describe('token storage', () => {
  beforeEach(() => {
    localStorage.clear();
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
});

describe('apiRequest', () => {
  beforeEach(() => {
    localStorage.clear();
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

  it('refreshes the access token once and retries on 401', async () => {
    setTokens('expired', 'refresh-me');
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(401, { detail: 'expired' }))
      .mockResolvedValueOnce(
        jsonResponse(200, { access_token: 'fresh', refresh_token: 'refresh-me' }),
      )
      .mockResolvedValueOnce(jsonResponse(200, { data: 'retried' }))
      .mockResolvedValueOnce(jsonResponse(200, { data: 'retried' }));
    vi.stubGlobal('fetch', fetchMock);

    const result = await apiRequest('/profile/');

    expect(result).toEqual({ data: 'retried' });
    expect(fetchMock).toHaveBeenCalledTimes(3);
    expect(localStorage.getItem(TOKEN_KEY)).toBe('fresh');
    const lastCall = fetchMock.mock.calls[2];
    expect(lastCall[1].headers.Authorization).toBe('Bearer fresh');
  });

  it('clears tokens and throws ApiError when refresh fails', async () => {
    setTokens('expired', 'bad-refresh');
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(401, { detail: 'expired' }))
      .mockResolvedValueOnce(jsonResponse(401, { detail: 'invalid token' }));
    vi.stubGlobal('fetch', fetchMock);

    await expect(apiRequest('/profile/')).rejects.toThrow(ApiError);
    expect(localStorage.getItem(TOKEN_KEY)).toBeNull();
    expect(localStorage.getItem(REFRESH_KEY)).toBeNull();
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
