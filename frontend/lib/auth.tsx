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
import { useAuth as useClerkAuth, useUser } from '@clerk/nextjs';
import { api, clearTokens, setTokenRefresher, setTokens } from './api';
import { saveRedirectTarget } from './auth-utils';
import type { User } from './types';

/**
 * CyberVerse auth context, now backed by Clerk.
 *
 * Clerk is the identity authority (sign-in/sign-up/session tokens); the
 * CyberVerse backend remains the record authority. The local user (with role,
 * XP, …) is fetched from `/auth/me`, which lazy-provisions a `users` row from
 * the Clerk identity on first sight.
 *
 * The public surface keeps the fields the rest of the app depends on — `user`,
 * `loading`, `logout`, `refreshUser` — so the ~19 consuming pages are unchanged.
 */
interface AuthContextValue {
  user: User | null;
  loading: boolean;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const { isLoaded, isSignedIn, getToken, signOut } = useClerkAuth();
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  // Teach the API client to obtain a fresh Clerk session token on a 401.
  useEffect(() => {
    setTokenRefresher(async () => (isSignedIn ? await getToken() : null));
    return () => setTokenRefresher(null);
  }, [isSignedIn, getToken]);

  const refreshUser = useCallback(async () => {
    if (!isSignedIn) {
      setUser(null);
      return;
    }
    try {
      // Seed the access token so the API client attaches it, then load our
      // backend user (this also provisions the local row via lazy sync).
      const token = await getToken();
      if (token) setTokens(token, '');
      const data = await api.get<{ data: User }>('/auth/me', { cache: 'no-store' });
      setUser(data.data);
    } catch {
      setUser(null);
    }
  }, [isSignedIn, getToken]);

  useEffect(() => {
    if (!isLoaded) {
      setLoading(true);
      return;
    }
    if (!isSignedIn) {
      setUser(null);
      setLoading(false);
      return;
    }
    refreshUser().finally(() => setLoading(false));
  }, [isLoaded, isSignedIn, refreshUser]);

  const logout = useCallback(async () => {
    try {
      await signOut();
    } catch {
      // ignore network/sign-out errors — still clear local state
    }
    clearTokens();
    setUser(null);
    router.replace('/');
  }, [signOut, router]);

  return (
    <AuthContext.Provider value={{ user, loading, logout, refreshUser }}>
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
 * - Waits for the session to be restored (loading) before deciding, so a
 *   valid session mid-restore is never mistaken for "logged out" — the guard
 *   against the login redirect loop.
 * - If there is still no user after restore, the current URL is saved and the
 *   user is sent to /login?redirect=<that URL>; after sign-in Clerk returns
 *   them here.
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
