import { act, renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { ReactNode } from 'react';

const apiMock = vi.hoisted(() => {
  // Minimal ApiError mirror so auth.tsx error classification works under the
  // mocked api module (instanceof must resolve to the same class).
  class ApiError extends Error {
    status: number;
    code?: string;
    constructor(status: number, message: string, _details = {}, code?: string) {
      super(message);
      this.name = 'ApiError';
      this.status = status;
      this.code = code;
    }
  }
  return {
    api: {
      get: vi.fn(),
      post: vi.fn(),
    },
    ApiError,
    clearTokens: vi.fn(),
    getTokens: vi.fn(),
    setTokens: vi.fn(),
    setTokenRefresher: vi.fn(),
  };
});

const clerkMock = vi.hoisted(() => ({
  useAuth: vi.fn(),
}));

const navMock = vi.hoisted(() => {
  const replace = vi.fn();
  return { replace, router: { replace } };
});

vi.mock('@/lib/api', () => apiMock);
vi.mock('@clerk/nextjs', () => clerkMock);
vi.mock('next/navigation', () => ({
  usePathname: () => '/',
  useRouter: () => navMock.router,
}));

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
  provider: 'clerk',
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
};

function clerkSignedOut() {
  clerkMock.useAuth.mockReturnValue({
    isLoaded: true,
    isSignedIn: false,
    getToken: vi.fn().mockResolvedValue(null),
    signOut: vi.fn().mockResolvedValue(undefined),
  });
}

function clerkSignedIn(overrides: Record<string, unknown> = {}) {
  clerkMock.useAuth.mockReturnValue({
    isLoaded: true,
    isSignedIn: true,
    getToken: vi.fn().mockResolvedValue('clerk-session-jwt'),
    signOut: vi.fn().mockResolvedValue(undefined),
    ...overrides,
  });
}

function wrapper({ children }: { children: ReactNode }) {
  return <AuthProvider>{children}</AuthProvider>;
}

beforeEach(() => {
  vi.clearAllMocks();
  sessionStorage.clear();
  apiMock.getTokens.mockReturnValue({ access: null, refresh: null });
  clerkSignedOut();
});

describe('useAuth', () => {
  it('throws when used outside AuthProvider', () => {
    expect(() => renderHook(() => useAuth())).toThrow('useAuth must be used within AuthProvider');
  });

  it('resolves loading false with user null when signed out of Clerk', async () => {
    clerkSignedOut();
    const { result } = renderHook(() => useAuth(), { wrapper });
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.user).toBeNull();
    expect(apiMock.api.get).not.toHaveBeenCalled();
  });

  it('fetches the backend user on mount when the Clerk session is present', async () => {
    clerkSignedIn();
    apiMock.api.get.mockResolvedValue({ data: TEST_USER });

    const { result } = renderHook(() => useAuth(), { wrapper });

    await waitFor(() => expect(result.current.loading).toBe(false));
    // The Clerk session token is seeded so the API client attaches it.
    expect(apiMock.setTokens).toHaveBeenCalledWith('clerk-session-jwt', '');
    expect(apiMock.api.get).toHaveBeenCalledWith('/auth/me', { cache: 'no-store' });
    expect(result.current.user).toEqual(TEST_USER);
  });

  it('refreshUser re-fetches the backend user', async () => {
    clerkSignedIn();
    apiMock.api.get.mockResolvedValue({ data: TEST_USER });

    const { result } = renderHook(() => useAuth(), { wrapper });
    await waitFor(() => expect(result.current.user).toEqual(TEST_USER));

    await act(async () => {
      await result.current.refreshUser();
    });

    expect(apiMock.api.get).toHaveBeenCalledTimes(2);
    expect(result.current.user).toEqual(TEST_USER);
  });

  it('logout signs out of Clerk, clears tokens and the user', async () => {
    clerkSignedIn();
    apiMock.api.get.mockResolvedValue({ data: TEST_USER });

    const { result } = renderHook(() => useAuth(), { wrapper });
    await waitFor(() => expect(result.current.user).toEqual(TEST_USER));

    await act(async () => {
      await result.current.logout();
    });

    expect(apiMock.clearTokens).toHaveBeenCalled();
    expect(result.current.user).toBeNull();
    expect(navMock.replace).toHaveBeenCalledWith('/');
  });

  it('logout clears local state even when signOut fails', async () => {
    clerkSignedIn({ signOut: vi.fn().mockRejectedValue(new Error('network down')) });
    apiMock.api.get.mockResolvedValue({ data: TEST_USER });

    const { result } = renderHook(() => useAuth(), { wrapper });
    await waitFor(() => expect(result.current.user).toEqual(TEST_USER));

    await act(async () => {
      await result.current.logout();
    });

    expect(apiMock.clearTokens).toHaveBeenCalled();
    expect(result.current.user).toBeNull();
  });

  it('keeps the local user null when /auth/me fails for a signed-in session', async () => {
    clerkSignedIn();
    apiMock.api.get.mockRejectedValue(new Error('backend down'));

    const { result } = renderHook(() => useAuth(), { wrapper });
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.user).toBeNull();
  });
});

describe('distinct auth states (bounded retry, no infinite loop)', () => {
  it('reports backend-unavailable on network failure and stops retrying', async () => {
    vi.useFakeTimers();
    try {
      clerkSignedIn();
      apiMock.api.get.mockRejectedValue(new apiMock.ApiError(0, 'Network unavailable'));

      const { result } = renderHook(() => useAuth(), { wrapper });
      await act(async () => {
        await vi.advanceTimersByTimeAsync(0);
      });

      expect(result.current.status).toBe('backend-unavailable');
      expect(result.current.loading).toBe(false);
      expect(result.current.user).toBeNull();
      expect(result.current.error).toBeTruthy();
      // The error message must never contain the session token.
      expect(result.current.error).not.toContain('clerk-session-jwt');

      // Drain every backoff window: the retry budget must run out (bounded).
      await act(async () => {
        await vi.advanceTimersByTimeAsync(10 * 60 * 1000);
      });
      const settled = apiMock.api.get.mock.calls.length;
      expect(settled).toBeGreaterThanOrEqual(2); // it did auto-retry
      expect(settled).toBeLessThanOrEqual(6); // initial attempts + MAX_AUTO_RETRIES

      // And it must stay settled — no zombie timers keep firing.
      await act(async () => {
        await vi.advanceTimersByTimeAsync(10 * 60 * 1000);
      });
      expect(apiMock.api.get.mock.calls.length).toBe(settled);
      expect(result.current.status).toBe('backend-unavailable');
    } finally {
      vi.useRealTimers();
    }
  });

  it('reports session-expired on 401 without auto-retrying', async () => {
    vi.useFakeTimers();
    try {
      clerkSignedIn();
      apiMock.api.get.mockRejectedValue(new apiMock.ApiError(401, 'Token expired'));

      const { result } = renderHook(() => useAuth(), { wrapper });
      await act(async () => {
        await vi.advanceTimersByTimeAsync(0);
      });

      expect(result.current.status).toBe('session-expired');
      expect(result.current.user).toBeNull();

      await act(async () => {
        await vi.advanceTimersByTimeAsync(10 * 60 * 1000);
      });
      // Auth failures are terminal until the user acts — no auto-retry.
      expect(apiMock.api.get).toHaveBeenCalledTimes(1);
    } finally {
      vi.useRealTimers();
    }
  });

  it('retry() refetches after a failure and recovers to authenticated', async () => {
    clerkSignedIn();
    apiMock.api.get.mockRejectedValueOnce(new apiMock.ApiError(0, 'Network unavailable'));
    apiMock.api.get.mockResolvedValue({ data: TEST_USER });

    const { result } = renderHook(() => useAuth(), { wrapper });
    await waitFor(() => expect(result.current.status).toBe('backend-unavailable'));

    act(() => {
      result.current.retry();
    });

    await waitFor(() => expect(result.current.status).toBe('authenticated'));
    expect(result.current.user).toEqual(TEST_USER);
    expect(result.current.error).toBeNull();
  });

  it('logout() from an error state clears local tokens and reports logged-out', async () => {
    clerkSignedIn();
    apiMock.api.get.mockRejectedValue(new apiMock.ApiError(0, 'Network unavailable'));

    const { result } = renderHook(() => useAuth(), { wrapper });
    await waitFor(() => expect(result.current.status).toBe('backend-unavailable'));

    await act(async () => {
      await result.current.logout();
    });

    expect(apiMock.clearTokens).toHaveBeenCalled();
    expect(result.current.status).toBe('logged-out');
    expect(result.current.user).toBeNull();
    expect(result.current.error).toBeNull();
  });
});
