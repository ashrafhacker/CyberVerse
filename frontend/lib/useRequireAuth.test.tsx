import { renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { ReactNode } from 'react';

const navMock = vi.hoisted(() => {
  const replace = vi.fn();
  return { replace, router: { replace }, pathname: '/courses/course-1' };
});

const apiMock = vi.hoisted(() => ({
  api: { get: vi.fn(), post: vi.fn() },
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

vi.mock('next/navigation', () => ({
  usePathname: () => navMock.pathname,
  useRouter: () => navMock.router,
}));

import { AuthProvider, useRequireAuth } from './auth';
import type { User } from './types';

const TEST_USER: User = {
  id: 'user-1',
  email: 'neo@cyberverse.io',
  full_name: 'Neo Anderson',
  role: 'student',
  status: 'active',
  is_verified: true,
  is_2fa_enabled: false,
  provider: 'google',
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
};

function wrapper({ children }: { children: ReactNode }) {
  return <AuthProvider>{children}</AuthProvider>;
}

beforeEach(() => {
  vi.clearAllMocks();
  sessionStorage.clear();
  navMock.pathname = '/courses/course-1';
});

describe('useRequireAuth', () => {
  it('redirects to /login with the current URL saved when unauthenticated', async () => {
    apiMock.api.get.mockRejectedValue(Object.assign(new Error('nope'), { status: 401 }));

    const { result } = renderHook(() => useRequireAuth(), { wrapper });
    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(navMock.replace).toHaveBeenCalledWith(
      `/login?redirect=${encodeURIComponent('/courses/course-1')}`,
    );
    // The intended destination is persisted so the login page can restore it.
    expect(sessionStorage.getItem('cyberverse_redirect_after_login')).toBe('/courses/course-1');
  });

  it('does NOT redirect while the session is still loading', async () => {
    // /auth/me never resolves -> the status stays "initializing".
    apiMock.api.get.mockImplementation(() => new Promise(() => {}));

    const { result } = renderHook(() => useRequireAuth(), { wrapper });
    await waitFor(() => expect(result.current.loading).toBe(true));
    expect(navMock.replace).not.toHaveBeenCalled();
  });

  it('does NOT redirect when a valid session is restored', async () => {
    apiMock.api.get.mockResolvedValue({ data: TEST_USER });

    const { result } = renderHook(() => useRequireAuth(), { wrapper });
    await waitFor(() => expect(result.current.user).toEqual(TEST_USER));
    expect(navMock.replace).not.toHaveBeenCalled();
  });

  it('redirects at most once, even when the effect re-runs', async () => {
    apiMock.api.get.mockRejectedValue(Object.assign(new Error('nope'), { status: 401 }));

    const { result, rerender } = renderHook(() => useRequireAuth(), { wrapper });
    await waitFor(() => expect(result.current.loading).toBe(false));

    rerender();
    rerender();
    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(navMock.replace).toHaveBeenCalledTimes(1);
  });

  it('does NOT redirect when the session could not be checked', async () => {
    // A network fault is not a missing session: the user must not be bounced
    // to the login screen, they get a retry instead.
    apiMock.api.get.mockRejectedValue(Object.assign(new Error('offline'), { status: 0 }));

    const { result } = renderHook(() => useRequireAuth(), { wrapper });
    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(result.current.status).toBe('error');
    expect(navMock.replace).not.toHaveBeenCalled();
  });

  it('never redirects to the auth pages themselves', async () => {
    navMock.pathname = '/login';
    apiMock.api.get.mockRejectedValue(Object.assign(new Error('nope'), { status: 401 }));

    const { result } = renderHook(() => useRequireAuth(), { wrapper });
    await waitFor(() => expect(result.current.loading).toBe(false));

    const target = navMock.replace.mock.calls[0]?.[0] as string;
    expect(target).toBeDefined();
    // The destination must never point back at /login or /register.
    expect(target).not.toContain(encodeURIComponent('/login'));
    expect(target).not.toContain(encodeURIComponent('/register'));
  });

  it('sanitises an external redirect target', async () => {
    navMock.pathname = '/dashboard';
    window.history.pushState({}, '', '/dashboard?redirect=//evil.example/x');
    apiMock.api.get.mockRejectedValue(Object.assign(new Error('nope'), { status: 401 }));

    const { result } = renderHook(() => useRequireAuth(), { wrapper });
    await waitFor(() => expect(result.current.loading).toBe(false));

    const target = navMock.replace.mock.calls[0]?.[0] as string;
    expect(target).not.toContain('evil.example');
    expect(sessionStorage.getItem('cyberverse_redirect_after_login')).toBe('/dashboard');
  });
});
