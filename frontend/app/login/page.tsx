'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { Shield, AlertTriangle } from 'lucide-react';
import { useAuth } from '@/lib/auth';
import { authErrorMessage, resolveLoginRedirect } from '@/lib/auth-utils';
import { GoogleOAuthProvider, GoogleLogin } from '@react-oauth/google';

const GOOGLE_CLIENT_ID =
  process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID ??
  '629472594859-dc64tio5cvcfq8g8f41igr1peu8mr2d6.apps.googleusercontent.com';

export default function LoginPage() {
  const { user, loading, login, googleLogin } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  // Once a valid session exists (either restored or just created by login),
  // send the user back to the page they originally requested — never to a
  // second login screen. This is the end of the redirect loop.
  useEffect(() => {
    if (loading || !user) return;
    router.replace(resolveLoginRedirect());
  }, [loading, user, router]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login(email, password);
      // Redirect handled by the effect above once `user` is set.
    } catch (err) {
      setError(authErrorMessage(err, 'Login failed'));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <GoogleOAuthProvider clientId={GOOGLE_CLIENT_ID}>
      <div className="flex min-h-screen items-center justify-center bg-grid-pattern [background-size:40px_40px] bg-cyber-bg px-4">
      <div className="w-full max-w-md">
        <div className="mb-8 flex items-center justify-center gap-2">
          <Shield className="h-10 w-10 text-cyber-primary" />
          <span className="font-mono text-2xl font-bold glow-text text-cyber-primary">CyberVerse</span>
        </div>

        <form onSubmit={handleSubmit} className="terminal-card p-8">
          <h1 className="mb-6 text-center font-mono text-xl font-bold text-cyber-primary">
            &gt; authenticate
          </h1>

          {error && (
            <div className="mb-4 flex items-center gap-2 rounded-md border border-cyber-danger/40 bg-cyber-danger/10 px-3 py-2 text-sm text-cyber-danger">
              <AlertTriangle className="h-4 w-4 shrink-0" />
              {error}
            </div>
          )}

          <div className="mb-4">
            <label htmlFor="email" className="terminal-label">Email</label>
            <input
              id="email"
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="terminal-input"
              placeholder="agent@cyberverse.io"
              autoComplete="email"
            />
          </div>

          <div className="mb-6">
            <label htmlFor="password" className="terminal-label">Password</label>
            <input
              id="password"
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="terminal-input"
              placeholder="••••••••"
              autoComplete="current-password"
            />
          </div>

          <button type="submit" disabled={submitting} className="terminal-button w-full py-2.5 mb-4">
            {submitting ? 'Connecting...' : 'Access Terminal'}
          </button>

          <div className="mb-4 flex flex-col items-center gap-3">
            <div className="flex w-full items-center gap-2">
              <div className="h-px flex-1 bg-cyber-border"></div>
              <span className="text-xs text-cyber-muted">OR</span>
              <div className="h-px flex-1 bg-cyber-border"></div>
            </div>
            <GoogleLogin
              onSuccess={async (credentialResponse) => {
                if (!credentialResponse.credential) return;
                setSubmitting(true);
                setError(null);
                try {
                  await googleLogin(credentialResponse.credential);
                  // Redirect handled by the effect above once `user` is set.
                } catch (err) {
                  setError(authErrorMessage(err, 'Google login failed'));
                } finally {
                  setSubmitting(false);
                }
              }}
              onError={() => setError('Google sign-in was cancelled or failed. Please try again.')}
              theme="filled_black"
              shape="rectangular"
              text="signin_with"
            />
          </div>

          <p className="mt-4 text-center text-sm text-cyber-muted">
            No account yet?{' '}
            <Link href="/register" className="text-cyber-primary hover:underline">
              Create one
            </Link>
          </p>
        </form>
      </div>
    </div>
    </GoogleOAuthProvider>
  );
}
