'use client';

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from 'react';
import { usePathname, useRouter } from 'next/navigation';
import { useAuth as useClerkAuth } from '@clerk/nextjs';
import { ApiError, api, clearTokens, setTokenRefresher, setTokens } from './api';
import { saveRedirectTarget } from './auth-utils';
import type { User } from './types';

/**
 * CyberVerse auth context, backed by Clerk.
 *
 * Clerk is the identity authority (sign-in/sign-up/session tokens); the
 * CyberVerse backend remains the record authority. The local user (role, XP,
 * …) is fetched from `/auth/me`, which lazy-provisions a `users` row from the
 * Clerk identity on first sight.
 *
 * The public surface keeps the fields the rest of the app depends on — `user`,
 * `loading`, `logout`, `refreshUser` — so the ~19 consuming pages are
 * unchanged, and adds an explicit `status`/`error`/`retry` so pages can render
 * distinct, actionable states instead of an eternal loading spinner.
 */

/** Distinct auth states — one per real failure mode, no ambiguous "loading". */
export type AuthStatus =
  | 'loading' // Clerk restoring session, or the first /auth/me fetch in flight
  | 'authenticated' // backend user loaded
  | 'logged-out' // Clerk says signed out
  | 'session-expired' // signed in with Clerk but backend rejected the token (401)
  | 'backend-unavailable' // network failure / timeout / 5xx reaching the backend
  | 'profile-failed' // backend answered with a non-auth error (403/404/…)
  | 'auth-error'; // Clerk loaded but no usable session token

interface AuthContextValue {
  user: User | null;
  loading: boolean;
  status: AuthStatus;
  error: string | null;
  isSignedIn: boolean | undefined;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
  retry: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

// Bounded auto-retry: only transient backend/network failures are retried,
// capped, with exponential backoff. Auth/profile errors are terminal until the
// user acts (Retry button or sign-out).
const MAX_AUTO_RETRIES = 4;
const RETRY_BASE_DELAY_MS = 2000;

/**
 * Map a fetch failure to a distinct UI state plus a user-safe message.
 * Never includes tokens or headers — only status-derived text.
 */
function classifyAuthError(err: unknown): { status: AuthStatus; message: string } {
  // `typeof ApiError === 'function'` guards against test/module mocks that
  // stub the api module without an ApiError class.
  if (typeof ApiError === 'function' && err instanceof ApiError) {
    if (err.status === 401) {
      return {
        status: 'session-expired',
        message: 'Your session has expired. Retry to resume it, or sign in again.',
      };
    }
    if (err.status === 0) {
      return {
        status: 'backend-unavailable',
        message: 'Cannot reach the CyberVerse backend. Check your connection and retry.',
      };
    }
    if (err.status >= 500) {
      return {
        status: 'backend-unavailable',
        message: 'The CyberVerse backend is temporarily unavailable. Please retry shortly.',
      };
    }
    return {
      status: 'profile-failed',
      message: err.message || 'Could not load your profile.',
    };
  }
  return {
    status: 'backend-unavailable',
    message: 'Cannot reach the CyberVerse backend. Check your connection and retry.',
  };
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const { isLoaded, isSignedIn, getToken, signOut } = useClerkAuth();
  const [user, setUser] = useState<User | null>(null);
  const [status, setStatus] = useState<AuthStatus>('loading');
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

  // Guards against out-of-order async results (rapid session flips, unmount).
  const seqRef = useRef(0);
  const attemptsRef = useRef(0);
  const retryTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const isSignedInRef = useRef<boolean | undefined>(isSignedIn);
  isSignedInRef.current = isSignedIn;

  // Latest-refresh accessor so the retry timer never captures a stale closure.
  const refreshUserRef = useRef<() => Promise<void>>(async () => {});

  // Teach the API client to obtain a fresh Clerk session token on a 401.
  useEffect(() => {
    setTokenRefresher(async () => (isSignedIn ? await getToken() : null));
    return () => setTokenRefresher(null);
  }, [isSignedIn, getToken]);

  // Clear any pending auto-retry on unmount.
  useEffect(
    () => () => {
      if (retryTimerRef.current) clearTimeout(retryTimerRef.current);
    },
    []
  );

  const refreshUser = useCallback(async () => {
    if (isSignedInRef.current !== true) {
      setUser(null);
      setStatus('logged-out');
      setError(null);
      return;
    }
    const seq = ++seqRef.current;
    try {
      // Seed the access token so the API client attaches it, then load our
      // backend user (this also provisions the local row via lazy sync).
      const token = await getToken();
      if (
        token &&
        typeof token === 'string' &&
        token.trim() &&
        token.trim() !== 'null' &&
        token.trim() !== 'undefined'
      ) {
        setTokens(token.trim(), '');
      }
      const data = await api.get<{ data: User }>('/auth/me', { cache: 'no-store' });
      if (seq !== seqRef.current) return; // superseded by a newer load
      setUser(data.data);
      setStatus('authenticated');
      setError(null);
      attemptsRef.current = 0;
    } catch (err) {
      if (seq !== seqRef.current) return; // superseded — keep the newer result
      setUser(null);
      const { status: nextStatus, message } = classifyAuthError(err);
      setStatus(nextStatus);
      setError(message);
      // Bounded auto-retry, transient backend/network failures only.
      if (nextStatus === 'backend-unavailable' && attemptsRef.current < MAX_AUTO_RETRIES) {
        attemptsRef.current += 1;
        if (retryTimerRef.current) clearTimeout(retryTimerRef.current);
        retryTimerRef.current = setTimeout(() => {
          if (isSignedInRef.current === true) refreshUserRef.current().catch(() => {});
        }, RETRY_BASE_DELAY_MS * attemptsRef.current);
      }
    }
  }, [getToken]);

  refreshUserRef.current = refreshUser;

  // Manual retry: reset the budget and try again immediately.
  const retry = useCallback(() => {
    if (retryTimerRef.current) clearTimeout(retryTimerRef.current);
    attemptsRef.current = 0;
    if (isSignedInRef.current === true) {
      setStatus('loading');
      setError(null);
      refreshUserRef.current().catch(() => {});
    } else {
      setUser(null);
      setStatus('logged-out');
      setError(null);
    }
  }, []);

  // Initial load + reaction to Clerk session changes.
  useEffect(() => {
    if (!isLoaded) {
      setStatus('loading');
      return;
    }
    if (!isSignedIn) {
      seqRef.current += 1; // supersede any in-flight fetch
      if (retryTimerRef.current) clearTimeout(retryTimerRef.current);
      attemptsRef.current = 0;
      setUser(null);
      setStatus('logged-out');
      setError(null);
      return;
    }
    setStatus('loading');
    refreshUser().catch(() => {});
  }, [isLoaded, isSignedIn, refreshUser]);

  const logout = useCallback(async () => {
    seqRef.current += 1; // invalidate in-flight fetches
    if (retryTimerRef.current) clearTimeout(retryTimerRef.current);
    attemptsRef.current = 0;
    try {
      await signOut();
    } catch {
      // ignore network/sign-out errors — still clear local state
    }
    clearTokens();
    setUser(null);
    setStatus('logged-out');
    setError(null);
    router.replace('/');
  }, [signOut, router]);

  const value: AuthContextValue = {
    user,
    loading: status === 'loading',
    status,
    error,
    isSignedIn,
    logout,
    refreshUser,
    retry,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
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
 * - Redirects to /login only when Clerk definitively reports signed out.
 *   Backend/network failures never redirect: they surface as a distinct
 *   `status` with a manual `retry()` (auto-retry is bounded in the provider —
 *   this hook no longer loops forever).
 */
export function useRequireAuth() {
  const { user, loading, status, error, isSignedIn, retry } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const redirectedRef = useRef(false);

  useEffect(() => {
    if (loading) return;
    if (user) {
      redirectedRef.current = false;
      return;
    }
    // Only redirect if definitely signed out — a backend failure is NOT
    // "logged out" and must never trigger a login redirect loop.
    if (isSignedIn === false && !redirectedRef.current) {
      redirectedRef.current = true;
      const search = typeof window !== 'undefined' ? window.location.search : '';
      const target = `${pathname}${search}`;
      saveRedirectTarget(target);
      router.replace(`/login?redirect=${encodeURIComponent(target)}`);
    }
  }, [loading, user, isSignedIn, pathname, router]);

  return { user, loading, status, error, retry };
}
