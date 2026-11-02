import { act, renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { ReactNode } from 'react';

const apiMock = vi.hoisted(() => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
  },
  clearTokens: vi.fn(),
  setTokens: vi.fn(),
  invalidateSession: vi.fn(),
}));

vi.mock('@/lib/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/lib/api')>();
  return {
    ...actual,
    api: apiMock.api,
    clearTokens: apiMock.clearTokens,
    setTokens: apiMock.setTokens,
    invalidateSession: apiMock.invalidateSession,
  };
});

import { AuthProvider, useAuth } from './auth';
import type { User } from './types';

const TEST_USER: User = {
  id: 'user-1',
  email: 'neo@cyberverse.io',
  full_name: 'Neo Anderson',
  role: 'student',
  status: 'active',
  is_verified: true,
  is_2fa_enabled: false,
  provider: 'local',
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
};

function wrapper({ children }: { children: ReactNode }) {
  return <AuthProvider>{children}</AuthProvider>;
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe('useAuth', () => {
  it('throws when used outside AuthProvider', () => {
    expect(() => renderHook(() => useAuth())).toThrow('useAuth must be used within AuthProvider');
  });

  it('restores the session on mount even when no bearer token is stored', async () => {
    // The session lives in an HttpOnly cookie: it is ambient and must always
    // be probed. Gating this on a localStorage token meant the session was
    // never restored after a reload.
    apiMock.api.get.mockResolvedValue({ data: TEST_USER });

    const { result } = renderHook(() => useAuth(), { wrapper });

    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(apiMock.api.get).toHaveBeenCalledWith('/auth/me', expect.objectContaining({ cache: 'no-store' }));
    expect(result.current.user).toEqual(TEST_USER);
    expect(result.current.status).toBe('authenticated');
  });

  it('marks the session unauthenticated when /auth/me returns 401', async () => {
    apiMock.api.get.mockRejectedValue(Object.assign(new Error('nope'), { status: 401 }));

    const { result } = renderHook(() => useAuth(), { wrapper });

    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.status).toBe('unauthenticated');
    expect(result.current.user).toBeNull();
  });

  it('reports an error (and keeps the user signed in) when the server is unreachable', async () => {
    apiMock.api.get.mockRejectedValue(Object.assign(new Error('offline'), { status: 0 }));

    const { result } = renderHook(() => useAuth(), { wrapper });

    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.status).toBe('error');
    expect(result.current.user).toBeNull();
    expect(result.current.error).toBeTruthy();
  });

  it('does not let a stale session check overwrite a newer one', async () => {
    let resolveFirst: (v: unknown) => void = () => {};
    apiMock.api.get
      .mockImplementationOnce(() => new Promise((r) => { resolveFirst = r; }))
      .mockResolvedValueOnce({ data: TEST_USER });

    const { result } = renderHook(() => useAuth(), { wrapper });

    // A second, newer check resolves first.
    await act(async () => {
      await result.current.refreshUser();
    });
    expect(result.current.user).toEqual(TEST_USER);

    // The older check resolves afterwards and must be ignored.
    await act(async () => {
      resolveFirst({ data: { ...TEST_USER, email: 'stale@cyberverse.io' } });
      await Promise.resolve();
    });
    expect(result.current.user).toEqual(TEST_USER);
  });

  it('login establishes a cookie session without persisting a null token', async () => {
    // The backend answers with HttpOnly cookies and no body tokens.
    apiMock.api.post.mockResolvedValue({
      data: { access_token: null, refresh_token: null, user: TEST_USER },
    });
    apiMock.api.get.mockResolvedValue({ data: TEST_USER });

    const { result } = renderHook(() => useAuth(), { wrapper });

    let returned: User | undefined;
    await act(async () => {
      returned = await result.current.login('neo@cyberverse.io', 'password123');
    });

    expect(apiMock.api.post).toHaveBeenCalledWith(
      '/auth/login',
      { email: 'neo@cyberverse.io', password: 'password123' },
      { auth: false },
    );
    // A null token must never be written to storage.
    expect(apiMock.setTokens).not.toHaveBeenCalled();
    expect(apiMock.invalidateSession).toHaveBeenCalled();
    // The session is confirmed through the authoritative endpoint.
    expect(apiMock.api.get).toHaveBeenCalledWith('/auth/me', expect.objectContaining({ cache: 'no-store' }));
    expect(result.current.user).toEqual(TEST_USER);
    expect(result.current.status).toBe('authenticated');
    expect(returned).toEqual(TEST_USER);
  });

  it('login stores a bearer token when the server opts in', async () => {
    apiMock.api.post.mockResolvedValue({
      data: { access_token: 'acc-token', refresh_token: 'ref-token', user: TEST_USER },
    });
    apiMock.api.get.mockResolvedValue({ data: TEST_USER });

    const { result } = renderHook(() => useAuth(), { wrapper });

    await act(async () => {
      await result.current.login('neo@cyberverse.io', 'password123');
    });

    expect(apiMock.setTokens).toHaveBeenCalledWith('acc-token', 'ref-token');
  });

  it('fails loudly when the session cannot be confirmed after login', async () => {
    apiMock.api.post.mockResolvedValue({
      data: { access_token: null, refresh_token: null, user: TEST_USER },
    });
    apiMock.api.get.mockRejectedValue(Object.assign(new Error('unauthorized'), { status: 401 }));

    const { result } = renderHook(() => useAuth(), { wrapper });

    await act(async () => {
      await expect(
        result.current.login('neo@cyberverse.io', 'password123'),
      ).rejects.toThrow(/session could not be established/i);
    });
    expect(result.current.user).toBeNull();
    expect(result.current.status).toBe('unauthenticated');
  });

  it('registration establishes a session through /auth/me', async () => {
    apiMock.api.post.mockResolvedValue({
      data: { access_token: null, refresh_token: null, user: TEST_USER },
    });
    apiMock.api.get.mockResolvedValue({ data: TEST_USER });

    const { result } = renderHook(() => useAuth(), { wrapper });

    await act(async () => {
      await result.current.register('neo@cyberverse.io', 'password123', 'Neo Anderson', 'neo');
    });

    expect(apiMock.api.post).toHaveBeenCalledWith(
      '/auth/register',
      { email: 'neo@cyberverse.io', password: 'password123', confirm_password: 'password123', full_name: 'Neo Anderson', username: 'neo' },
      { auth: false },
    );
    expect(result.current.status).toBe('authenticated');
  });

  it('google login establishes a session through /auth/me', async () => {
    apiMock.api.post.mockResolvedValue({
      data: { access_token: null, refresh_token: null, user: TEST_USER },
    });
    apiMock.api.get.mockResolvedValue({ data: TEST_USER });

    const { result } = renderHook(() => useAuth(), { wrapper });

    await act(async () => {
      await result.current.googleLogin('google-credential');
    });

    expect(apiMock.api.post).toHaveBeenCalledWith(
      '/auth/google',
      { credential: 'google-credential' },
      { auth: false },
    );
    expect(result.current.status).toBe('authenticated');
  });

  it('logout clears tokens and user even when the API call fails', async () => {
    apiMock.api.post.mockRejectedValue(new Error('network down'));
    apiMock.api.get.mockResolvedValue({ data: TEST_USER });

    const { result } = renderHook(() => useAuth(), { wrapper });
    await waitFor(() => expect(result.current.user).toEqual(TEST_USER));

    await act(async () => {
      await result.current.logout();
    });

    expect(apiMock.clearTokens).toHaveBeenCalled();
    expect(apiMock.invalidateSession).toHaveBeenCalled();
    expect(result.current.user).toBeNull();
    expect(result.current.status).toBe('unauthenticated');
  });

  it('logout only calls the API once when invoked concurrently', async () => {
    apiMock.api.post.mockResolvedValue({ message: 'Logged out successfully' });
    apiMock.api.get.mockResolvedValue({ data: TEST_USER });

    const { result } = renderHook(() => useAuth(), { wrapper });
    await waitFor(() => expect(result.current.user).toEqual(TEST_USER));

    await act(async () => {
      await Promise.all([result.current.logout(), result.current.logout(), result.current.logout()]);
    });

    const logoutCalls = apiMock.api.post.mock.calls.filter(
      ([path]) => path === '/auth/logout',
    );
    expect(logoutCalls.length).toBe(1);
  });
});
