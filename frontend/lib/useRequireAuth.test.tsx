import { renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { ReactNode } from 'react';

const navMock = vi.hoisted(() => {
  const replace = vi.fn();
  return { replace, router: { replace }, pathname: '/courses/course-1' };
});

const apiMock = vi.hoisted(() => {
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
    api: { get: vi.fn(), post: vi.fn() },
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

vi.mock('@/lib/api', () => apiMock);
vi.mock('@clerk/nextjs', () => clerkMock);
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
  provider: 'clerk',
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
};

function clerkSession(state: {
  isLoaded?: boolean;
  isSignedIn?: boolean;
  getToken?: unknown;
}) {
  clerkMock.useAuth.mockReturnValue({
    isLoaded: state.isLoaded ?? true,
    isSignedIn: state.isSignedIn ?? false,
    getToken: (state.getToken as never) ?? vi.fn().mockResolvedValue(null),
    signOut: vi.fn().mockResolvedValue(undefined),
  });
}

function wrapper({ children }: { children: ReactNode }) {
  return <AuthProvider>{children}</AuthProvider>;
}

beforeEach(() => {
  vi.clearAllMocks();
  sessionStorage.clear();
  apiMock.getTokens.mockReturnValue({ access: null, refresh: null });
  clerkSession({ isLoaded: true, isSignedIn: false });
});

describe('useRequireAuth', () => {
  it('redirects to /login with the current URL saved when unauthenticated', async () => {
    clerkSession({ isLoaded: true, isSignedIn: false });
    const { result } = renderHook(() => useRequireAuth(), { wrapper });
    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(navMock.replace).toHaveBeenCalledWith(
      `/login?redirect=${encodeURIComponent('/courses/course-1')}`,
    );
    // The intended destination is persisted so the login page can restore it.
    expect(sessionStorage.getItem('cyberverse_redirect_after_login')).toBe('/courses/course-1');
  });

  it('does NOT redirect while the session is still loading', async () => {
    // Clerk has not finished restoring the session yet -> loading stays true.
    clerkSession({ isLoaded: false, isSignedIn: false });

    const { result } = renderHook(() => useRequireAuth(), { wrapper });
    await waitFor(() => expect(result.current.loading).toBe(true));
    expect(navMock.replace).not.toHaveBeenCalled();
  });

  it('does NOT redirect when a valid session is restored', async () => {
    clerkSession({
      isLoaded: true,
      isSignedIn: true,
      getToken: vi.fn().mockResolvedValue('clerk-session-jwt'),
    });
    apiMock.api.get.mockResolvedValue({ data: TEST_USER });

    const { result } = renderHook(() => useRequireAuth(), { wrapper });
    await waitFor(() => expect(result.current.user).toEqual(TEST_USER));
    expect(navMock.replace).not.toHaveBeenCalled();
  });

  it('does NOT redirect when signed in but the backend is unavailable', async () => {
    // Regression guard: a backend/network failure must surface as a distinct
    // status with retry — never a login redirect (the old infinite loop).
    clerkSession({
      isLoaded: true,
      isSignedIn: true,
      getToken: vi.fn().mockResolvedValue('clerk-session-jwt'),
    });
    apiMock.api.get.mockRejectedValue(new apiMock.ApiError(0, 'Network unavailable'));

    const { result } = renderHook(() => useRequireAuth(), { wrapper });
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.user).toBeNull();
    expect(result.current.status).toBe('backend-unavailable');
    expect(result.current.error).toBeTruthy();
    expect(typeof result.current.retry).toBe('function');
    expect(navMock.replace).not.toHaveBeenCalled();
  });
});
