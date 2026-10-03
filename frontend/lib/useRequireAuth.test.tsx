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
  getTokens: vi.fn(),
  setTokens: vi.fn(),
}));

vi.mock('@/lib/api', () => apiMock);
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
  apiMock.getTokens.mockReturnValue({ access: null, refresh: null });
});

describe('useRequireAuth', () => {
  it('redirects to /login with the current URL saved when unauthenticated', async () => {
    const { result } = renderHook(() => useRequireAuth(), { wrapper });
    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(navMock.replace).toHaveBeenCalledWith(
      `/login?redirect=${encodeURIComponent('/courses/course-1')}`,
    );
    // The intended destination is persisted so the login page can restore it.
    expect(sessionStorage.getItem('cyberverse_redirect_after_login')).toBe('/courses/course-1');
  });

  it('does NOT redirect while the session is still loading', async () => {
    // Tokens exist but /auth/me never resolves -> loading stays true.
    apiMock.getTokens.mockReturnValue({ access: 'acc', refresh: 'ref' });
    apiMock.api.get.mockImplementation(() => new Promise(() => {}));

    const { result } = renderHook(() => useRequireAuth(), { wrapper });
    await waitFor(() => expect(result.current.loading).toBe(true));
    expect(navMock.replace).not.toHaveBeenCalled();
  });

  it('does NOT redirect when a valid session is restored', async () => {
    apiMock.getTokens.mockReturnValue({ access: 'acc', refresh: 'ref' });
    apiMock.api.get.mockResolvedValue({ data: TEST_USER });

    const { result } = renderHook(() => useRequireAuth(), { wrapper });
    await waitFor(() => expect(result.current.user).toEqual(TEST_USER));
    expect(navMock.replace).not.toHaveBeenCalled();
  });
});
