'use client';

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from 'react';
import { usePathname, useRouter } from 'next/navigation';
import { api, clearTokens, getTokens, setTokens } from './api';
import { saveRedirectTarget } from './auth-utils';
import type { User } from './types';

interface AuthContextValue {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<User>;
  googleLogin: (credential: string) => Promise<User>;
  register: (email: string, password: string, fullName: string, username: string) => Promise<User>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const refreshUser = useCallback(async () => {
    try {
      const data = await api.get<{ data: User }>('/auth/me', { cache: 'swr', cacheTtlMs: 60_000, cacheStaleMs: 30_000 });
      setUser(data.data);
    } catch {
      setUser(null);
    }
  }, []);

  useEffect(() => {
    const tokens = getTokens();
    if (tokens.access) {
      refreshUser().finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, [refreshUser]);

  const login = useCallback(async (email: string, password: string) => {
    const data = await api.post<{
      data: {
        access_token: string;
        refresh_token: string;
        user: User;
      };
    }>('/auth/login', { email, password }, { auth: false });
    const tokens = data.data;
    setTokens(tokens.access_token, tokens.refresh_token);
    setUser(tokens.user);
    return tokens.user;
  }, []);

  const googleLogin = useCallback(async (credential: string) => {
    const data = await api.post<{
      data: {
        access_token: string;
        refresh_token: string;
        user: User;
      };
    }>('/auth/google', { credential }, { auth: false });
    const tokens = data.data;
    setTokens(tokens.access_token, tokens.refresh_token);
    setUser(tokens.user);
    return tokens.user;
  }, []);

  const register = useCallback(
    async (email: string, password: string, fullName: string, username: string) => {
      const data = await api.post<{
        data: {
          access_token: string;
          refresh_token: string;
          user: User;
        };
      }>(
        '/auth/register',
        { email, password, confirm_password: password, full_name: fullName, username },
        { auth: false },
      );
      const tokens = data.data;
      setTokens(tokens.access_token, tokens.refresh_token);
      setUser(tokens.user);
      return tokens.user;
    },
    [],
  );

  const logout = useCallback(async () => {
    try {
      await api.post('/auth/logout');
    } catch {
      // ignore network errors on logout
    }
    clearTokens();
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, login, googleLogin, register, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}

/**
 * Route-protection hook for protected pages.
 *
 * - Waits for the session to be restored (loading) before deciding anything,
 *   so a valid persisted session is never mistaken for "logged out". This is
 *   the guard against the login loop: a brief null-user state while tokens are
 *   still being validated will NOT trigger a redirect.
 * - If, after restoring, there is still no user, the current URL (path + query)
 *   is saved as the intended destination and the user is redirected to
 *   /login?redirect=<that URL>. After sign-in the login page returns the user
 *   here, so the requested course/page opens automatically — no second click.
 */
export function useRequireAuth() {
  const { user, loading } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (loading) return;
    if (!user) {
      const search = typeof window !== 'undefined' ? window.location.search : '';
      const target = `${pathname}${search}`;
      saveRedirectTarget(target);
      router.replace(`/login?redirect=${encodeURIComponent(target)}`);
    }
  }, [loading, user, pathname, router]);

  return { user, loading };
}
