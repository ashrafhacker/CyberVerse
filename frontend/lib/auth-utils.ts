import { ApiError } from './api';

/**
 * Redirect-back utilities for the authentication flow.
 *
 * When an unauthenticated user attempts to reach a protected page, the intended
 * destination is captured so that — after a successful sign-in — we can return
 * the user to exactly where they wanted to go, instead of dumping them on the
 * dashboard. This is what eliminates the "log in again" loop.
 */

const REDIRECT_KEY = 'cyberverse_redirect_after_login';

/**
 * Persist the URL the user intended to visit. Stored in sessionStorage so it
 * survives the in-tab navigation to /login but does not outlive the tab.
 */
export function saveRedirectTarget(path: string) {
  if (typeof window === 'undefined') return;
  const safe = sanitizeRedirect(path);
  if (safe) window.sessionStorage.setItem(REDIRECT_KEY, safe);
}

/**
 * Return and clear the stored redirect target (one-shot).
 */
export function consumeRedirectTarget(): string | null {
  if (typeof window === 'undefined') return null;
  const stored = window.sessionStorage.getItem(REDIRECT_KEY);
  window.sessionStorage.removeItem(REDIRECT_KEY);
  return sanitizeRedirect(stored);
}

/**
 * Validate a redirect path. Must be a relative app path and must never point
 * back at the auth pages themselves (otherwise we recreate a redirect loop).
 */
function sanitizeRedirect(path: string | null | undefined): string | null {
  if (!path) return null;
  if (!path.startsWith('/') || path.startsWith('//')) return null;
  if (path === '/login' || path === '/register') return null;
  if (path.startsWith('/login?') || path.startsWith('/register?')) return null;
  if (path.startsWith('/api/')) return null;
  return path;
}

/**
 * Resolve where to send the user after a successful login, in priority order:
 *   1. `?redirect=` query param on the current URL
 *   2. the previously stored redirect target
 *   3. the fallback (dashboard)
 *
 * The stored target is always consumed (cleared) to avoid stale reuse.
 */
export function resolveLoginRedirect(fallback = '/dashboard'): string {
  if (typeof window !== 'undefined') {
    const fromUrl = new URLSearchParams(window.location.search).get('redirect');
    const validated = sanitizeRedirect(fromUrl);
    if (validated) {
      // Clear any stale stored target; the URL is authoritative.
      window.sessionStorage.removeItem(REDIRECT_KEY);
      return validated;
    }
  }
  const stored = consumeRedirectTarget();
  if (stored) return stored;
  return fallback;
}

/**
 * Map an auth error to a clear, actionable user-facing message.
 */
export function authErrorMessage(err: unknown, fallback: string): string {
  if (err instanceof ApiError) {
    if (err.details?.network || err.status === 0) {
      return 'Unable to reach the CyberVerse server. Check your connection and try again.';
    }
    // Include DB-degraded message if backend reports it (503 with Database detail)
    if (err.status === 503 && err.message.toLowerCase().includes('database')) {
      return 'Database temporarily unavailable — please wait 30 seconds and try again.';
    }
    switch (err.status) {
      case 400:
        return err.message || 'Invalid credentials or authentication token.';
      case 401:
        return 'Session invalid or expired. Please sign in again.';
      case 403:
        return err.message || 'Your account does not have access. Contact support.';
      case 404:
        return 'Account not found. Please register first.';
      case 409:
        return err.message || 'An account with these details already exists.';
      case 422: {
        // Validation: try to surface field-level message
        const msg = err.message || '';
        if (msg.includes('email')) return 'Please enter a valid email address (e.g., agent@cyberverse.io).';
        if (msg.includes('password')) return 'Password must be at least 8 characters.';
        return msg || 'Please check your input and try again.';
      }
      case 429:
        return 'Too many attempts. Please wait a moment and try again.';
      default:
        if (err.status >= 500) return 'The CyberVerse server is temporarily unavailable — most likely the database is starting. Please wait 30 seconds and try again. If it persists, contact support.';
        return err.message || fallback;
    }
  }
  return err instanceof Error ? err.message : fallback;
}
