import { act, renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { ReactNode } from 'react';

const apiMock = vi.hoisted(() => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
  },
  clearTokens: vi.fn(),
  getTokens: vi.fn(),
  setTokens: vi.fn(),
}));

vi.mock('@/lib/api', () => apiMock);

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
  apiMock.getTokens.mockReturnValue({ access: null, refresh: null });
});

describe('useAuth', () => {
  it('throws when used outside AuthProvider', () => {
    expect(() => renderHook(() => useAuth())).toThrow('useAuth must be used within AuthProvider');
  });

  it('resolves loading false with user null when no tokens exist', async () => {
    const { result } = renderHook(() => useAuth(), { wrapper });
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.user).toBeNull();
  });

  it('fetches the current user on mount when tokens exist', async () => {
    apiMock.getTokens.mockReturnValue({ access: 'acc', refresh: 'ref' });
    apiMock.api.get.mockResolvedValue({ data: TEST_USER });

    const { result } = renderHook(() => useAuth(), { wrapper });

    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(apiMock.api.get).toHaveBeenCalledWith('/auth/me');
    expect(result.current.user).toEqual(TEST_USER);
  });

  it('login stores tokens and sets the user', async () => {
    apiMock.api.post.mockResolvedValue({
      data: {
        access_token: 'acc-token',
        refresh_token: 'ref-token',
        user: TEST_USER,
      },
    });

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
    expect(apiMock.setTokens).toHaveBeenCalledWith('acc-token', 'ref-token');
    expect(result.current.user).toEqual(TEST_USER);
    expect(returned).toEqual(TEST_USER);
  });

  it('logout clears tokens and user even when API call fails', async () => {
    apiMock.api.post.mockRejectedValue(new Error('network down'));
    apiMock.getTokens.mockReturnValue({ access: 'acc', refresh: 'ref' });
    apiMock.api.get.mockResolvedValue({ data: TEST_USER });

    const { result } = renderHook(() => useAuth(), { wrapper });
    await waitFor(() => expect(result.current.user).toEqual(TEST_USER));

    await act(async () => {
      await result.current.logout();
    });

    expect(apiMock.clearTokens).toHaveBeenCalled();
    expect(result.current.user).toBeNull();
  });
});
