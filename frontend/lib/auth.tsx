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
import { api, clearTokens, invalidateSession, isUsableToken, setTokens } from './api';
import { DEFAULT_AUTH_REDIRECT, sanitizeRedirect, saveRedirectTarget } from './auth-utils';
import type { User } from './types';

/**
 * Authentication state.
 *
 * - `initializing`   the session is being checked (first load / after sign-in)
 * - `authenticated`  a live session exists
 * - `unauthenticated`no session: the guard sends the user to /login
 * - `error`          the session could not be determined (network/server fault)
 */
export type AuthStatus = 'initializing' | 'authenticated' | 'unauthenticated' | 'error';

interface AuthContextValue {
  user: User | null;
  status: AuthStatus;
  /** True while the session is still being determined. */
  loading: boolean;
  /** Human-readable reason for the `error` status. */
  error: string | null;
  login: (email: string, password: string) => Promise<User>;
  googleLogin: (credential: string) => Promise<User>;
  register: (email: string, password: string, fullName: string, username: string) => Promise<User>;
  logout: () => Promise<void>;
  /** Re-checks the session against the backend. Resolves to the user, or null. */
  refreshUser: () => Promise<User | null>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

/** Shape of the auth endpoints. The body tokens are only present for
 *  clients that explicitly asked for them (`include_tokens: true`); the
 *  browser session itself travels in HttpOnly cookies. */
interface AuthResponse {
  data: {
    access_token?: string | null;
    refresh_token?: string | null;
    user: User;
  };
}

const SESSION_ERROR_MESSAGE =
  'Your session could not be established. Please make sure cookies are enabled for this site and try again.';

/**
 * True when the failure means "there is no session" rather than "we could not
 * ask". Duck-typed on the status code so the check does not depend on the
 * concrete error class.
 */
function isUnauthenticatedError(err: unknown): boolean {
  const status = (err as { status?: unknown } | null | undefined)?.status;
  return status === 401 || status === 403;
}

/** Best-effort, already-sanitised message for a failed session check. */
function errorMessage(err: unknown, fallback: string): string {
  const message = (err as { message?: unknown } | null | undefined)?.message;
  return typeof message === 'string' && message ? message : fallback;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [status, setStatus] = useState<AuthStatus>('initializing');
  const [error, setError] = useState<string | null>(null);

  // Guards against an older, slower session check overwriting a newer one.
  const requestSeq = useRef(0);
  // De-duplicates concurrent logout calls.
  const logoutPromise = useRef<Promise<void> | null>(null);

  const refreshUser = useCallback(async (): Promise<User | null> => {
    const seq = ++requestSeq.current;
    try {
      // `no-store`: the session check must never be served from — or written
      // to — a cache that is shared across sessions.
      const data = await api.get<{ data: User }>('/auth/me', { cache: 'no-store' });
      if (seq !== requestSeq.current) return null; // a newer check won
      setUser(data.data);
      setStatus('authenticated');
      setError(null);
      return data.data;
    } catch (err) {
      if (seq !== requestSeq.current) return null; // a newer check won
      setUser(null);
      if (isUnauthenticatedError(err)) {
        setStatus('unauthenticated');
        setError(null);
      } else {
        // Network fault or server error: we do not know whether a session
        // exists, so we must not sign the user out.
        setStatus('error');
        setError(
          errorMessage(err, 'Unable to verify your session. Please check your connection.'),
        );
      }
      return null;
    }
  }, []);

  /**
   * Restore the session on mount.
   *
   * The session lives in an HttpOnly cookie, so it is ambient: it must always
   * be probed. Gating this on a localStorage token meant the session was never
   * restored after a page reload.
   */
  useEffect(() => {
    void refreshUser();
  }, [refreshUser]);

  /**
   * Complete a sign-in.
   *
   * The backend sets the session cookies; the body tokens are usually absent.
   * A token is only persisted when the server actually issued a usable one —
   * storing `null` would produce a truthy "null" string that is later sent as
   * `Authorization: Bearer null`.
   */
  const establishSession = useCallback(
    async (response: AuthResponse): Promise<User> => {
      const tokens = response.data;
      if (isUsableToken(tokens.access_token)) {
        setTokens(tokens.access_token, isUsableToken(tokens.refresh_token) ? tokens.refresh_token : null);
      }
      // A new session identity: drop anything cached for the previous one.
      invalidateSession();

      // Confirm the session through the authoritative endpoint. If the cookie
      // was not accepted (blocked, wrong domain, cross-site without
      // SameSite=None) we fail loudly instead of bouncing between /dashboard
      // and /login forever.
      setStatus('initializing');
      const confirmed = await refreshUser();
      if (!confirmed) {
        throw new Error(SESSION_ERROR_MESSAGE);
      }
      return confirmed;
    },
    [refreshUser],
  );

  const login = useCallback(
    async (email: string, password: string) => {
      const data = await api.post<AuthResponse>(
        '/auth/login',
        { email, password },
        { auth: false },
      );
      return establishSession(data);
    },
    [establishSession],
  );

  const googleLogin = useCallback(
    async (credential: string) => {
      const data = await api.post<AuthResponse>(
        '/auth/google',
        { credential },
        { auth: false },
      );
      return establishSession(data);
    },
    [establishSession],
  );

  const register = useCallback(
    async (email: string, password: string, fullName: string, username: string) => {
      const data = await api.post<AuthResponse>(
        '/auth/register',
        { email, password, confirm_password: password, full_name: fullName, username },
        { auth: false },
      );
      return establishSession(data);
    },
    [establishSession],
  );

  const logout = useCallback(async (): Promise<void> => {
    if (logoutPromise.current) return logoutPromise.current;

    logoutPromise.current = (async () => {
      try {
        await api.post('/auth/logout');
      } catch {
        // Ignore network errors on logout: the local session is still cleared
        // and the server-side session expires with its cookies.
      } finally {
        clearTokens();
        invalidateSession();
        // Invalidate any in-flight session check so it cannot re-authenticate
        // the user after sign-out.
        requestSeq.current += 1;
        setUser(null);
        setStatus('unauthenticated');
        setError(null);
      }
    })();

    try {
      await logoutPromise.current;
    } finally {
      logoutPromise.current = null;
    }
  }, []);

  const loading = status === 'initializing';

  return (
    <AuthContext.Provider
      value={{ user, status, loading, error, login, googleLogin, register, logout, refreshUser }}
    >
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
 * - Waits for the session to be restored before deciding anything, so a valid
 *   session is never mistaken for "logged out" (this is the guard against the
 *   login loop).
 * - If the session is invalid, the current URL is saved as the intended
 *   destination and the user is redirected to /login?redirect=<that URL>.
 *   The destination is validated by the shared `sanitizeRedirect` helper, so
 *   it can never point at an external origin or back at the auth pages.
 * - The redirect is issued at most once per mount, so a re-render or React
 *   Strict Mode's double effect cannot fire a navigation loop.
 * - A session that could not be checked (`error`) does NOT redirect: the page
 *   shows a retry instead of bouncing the user to the login screen.
 */
export function useRequireAuth() {
  const { user, status, loading, error, refreshUser } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const redirected = useRef(false);

  useEffect(() => {
    if (status !== 'unauthenticated') return;
    if (redirected.current) return;
    redirected.current = true;

    const search = typeof window !== 'undefined' ? window.location.search : '';
    const target = sanitizeRedirect(`${pathname}${search}`) ?? DEFAULT_AUTH_REDIRECT;
    saveRedirectTarget(target);
    router.replace(`/login?redirect=${encodeURIComponent(target)}`);
  }, [status, pathname, router]);

  return { user, status, loading, error, refreshUser };
}
