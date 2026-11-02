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

/** Routes that must never be used as a post-login destination. */
const AUTH_ROUTES = ['/login', '/register'];

/** The default in-app destination after a successful sign-in. */
export const DEFAULT_AUTH_REDIRECT = '/dashboard';

/**
 * Validate a redirect path.
 *
 * Only same-origin, absolute *paths* are allowed. Everything that could send
 * the user to an untrusted origin is rejected: absolute URLs, protocol-relative
 * URLs (`//host`), backslash variants (`/\host` — some browsers normalise it to
 * `//host`), non-HTTP schemes, control characters, and the API namespace.
 *
 * A nested `redirect` parameter is stripped so a crafted target cannot smuggle
 * a second redirect through the login flow.
 */
export function sanitizeRedirect(path: string | null | undefined): string | null {
  if (typeof path !== 'string') return null;

  const raw = path.trim();
  if (!raw) return null;

  // Control characters (including newlines/tabs) can be used to smuggle a
  // second header or confuse downstream parsers.
  // eslint-disable-next-line no-control-regex
  if (/[\u0000-\u001f\u007f]/.test(raw)) return null;

  // Must be an absolute in-app path.
  if (!raw.startsWith('/')) return null;
  // Protocol-relative ("//evil.com") and backslash-normalised variants leave
  // the origin even though they start with a slash.
  if (raw.startsWith('//') || raw.startsWith('/\\')) return null;
  // "/javascript:alert(1)" style payloads.
  if (/^\/[a-z][a-z0-9+.-]*:/i.test(raw)) return null;

  const splitAt = raw.search(/[?#]/);
  const pathname = splitAt === -1 ? raw : raw.slice(0, splitAt);
  const suffix = splitAt === -1 ? '' : raw.slice(splitAt);

  if (!pathname.startsWith('/')) return null;
  if (pathname === '/api' || pathname.startsWith('/api/')) return null;
  if (AUTH_ROUTES.some((route) => pathname === route || pathname.startsWith(`${route}/`))) return null;

  // Drop any nested redirect parameter — a redirect inside a redirect is how
  // redirect cycles are built.
  const queryStart = suffix.indexOf('?');
  if (queryStart !== -1) {
    const hashAt = suffix.indexOf('#', queryStart);
    const query = suffix.slice(queryStart + 1, hashAt === -1 ? undefined : hashAt);
    const hash = hashAt === -1 ? '' : suffix.slice(hashAt);
    const params = new URLSearchParams(query);
    params.delete('redirect');
    const cleaned = params.toString();
    return pathname + (cleaned ? `?${cleaned}` : '') + hash;
  }

  return pathname + suffix;
}

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
 * Resolve where to send the user after a successful login, in priority order:
 *   1. `?redirect=` query param on the current URL
 *   2. the previously stored redirect target
 *   3. the fallback (dashboard)
 *
 * The stored target is always consumed (cleared) to avoid stale reuse.
 */
export function resolveLoginRedirect(fallback = DEFAULT_AUTH_REDIRECT): string {
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
  // The fallback must itself be a safe in-app path, otherwise a misconfigured
  // caller could turn the post-login navigation into an open redirect.
  return sanitizeRedirect(fallback) ?? DEFAULT_AUTH_REDIRECT;
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
