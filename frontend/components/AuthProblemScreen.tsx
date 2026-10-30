'use client';

import Link from 'next/link';
import type { AuthStatus } from '@/lib/auth';

/**
 * Terminal-styled screen for the non-loading auth failure states.
 *
 * Rendered by protected pages (dashboard first) when the user is signed in
 * with Clerk but the backend profile could not be loaded. Replaces the old
 * behaviour of showing the loading spinner forever.
 *
 * Every state offers a working Retry (re-runs the bounded backend fetch) and
 * a safe sign-out that clears local tokens even if Clerk sign-out fails.
 * Never renders tokens or raw error objects.
 */
interface AuthProblemScreenProps {
  status: AuthStatus;
  error: string | null;
  onRetry: () => void;
  onSignOut: () => void;
}

const COPY: Record<
  Exclude<AuthStatus, 'loading' | 'authenticated'>,
  { title: string; hint: string; showRetry: boolean }
> = {
  'logged-out': {
    title: 'SESSION ENDED',
    hint: 'You are signed out. Sign in to continue.',
    showRetry: false,
  },
  'session-expired': {
    title: 'SESSION EXPIRED',
    hint: 'Your session has expired. Retry to resume it, or sign in again.',
    showRetry: true,
  },
  'backend-unavailable': {
    title: 'BACKEND UNREACHABLE',
    hint: 'Cannot reach the CyberVerse backend right now.',
    showRetry: true,
  },
  'profile-failed': {
    title: 'PROFILE UNAVAILABLE',
    hint: 'Signed in, but your profile could not be loaded.',
    showRetry: true,
  },
  'auth-error': {
    title: 'AUTH ERROR',
    hint: 'Could not establish a secure session. Sign in again to continue.',
    showRetry: false,
  },
};

export default function AuthProblemScreen({
  status,
  error,
  onRetry,
  onSignOut,
}: AuthProblemScreenProps) {
  if (status === 'loading' || status === 'authenticated') return null;
  const copy = COPY[status];

  return (
    <div className="flex min-h-screen items-center justify-center px-4">
      <div className="terminal-card w-full max-w-md p-6" role="alert" aria-live="polite">
        <p className="font-mono text-sm text-red-400">&gt; {copy.title}</p>
        <p className="mt-3 text-sm text-cyber-text">{copy.hint}</p>
        {error ? <p className="mt-2 font-mono text-xs text-cyber-muted">{error}</p> : null}

        <div className="mt-6 flex flex-wrap gap-3">
          {copy.showRetry ? (
            <button type="button" onClick={onRetry} className="terminal-button">
              Retry
            </button>
          ) : null}
          <Link href="/login" className="terminal-button">
            Sign in
          </Link>
          <button type="button" onClick={onSignOut} className="terminal-button-ghost">
            Sign out
          </button>
        </div>
      </div>
    </div>
  );
}
