'use client';

import Link from 'next/link';
import { Shield } from 'lucide-react';
import { SignIn } from '@clerk/nextjs';
import { resolveLoginRedirect } from '@/lib/auth-utils';

/**
 * Sign-in page — powered by Clerk.
 *
 * Clerk renders the full credential + MFA flow. After a successful sign-in it
 * returns the user to the page they originally requested (saved by
 * useRequireAuth), so a protected deep-link opens automatically.
 */
export default function LoginPage() {
  const redirect = resolveLoginRedirect();

  return (
    <div className="flex min-h-screen items-center justify-center bg-grid-pattern [background-size:40px_40px] bg-cyber-bg px-4">
      <div className="w-full max-w-md">
        <div className="mb-8 flex items-center justify-center gap-2">
          <Shield className="h-10 w-10 text-cyber-primary" />
          <span className="font-mono text-2xl font-bold glow-text text-cyber-primary">CyberVerse</span>
        </div>

        <div className="terminal-card p-4">
          <h1 className="mb-4 text-center font-mono text-xl font-bold text-cyber-primary">
            &gt; authenticate
          </h1>
          <SignIn
            path="/login"
            routing="path"
            fallbackRedirectUrl={redirect}
            appearance={{
              variables: {
                colorPrimary: '#00ff9c',
                colorBackground: '#0a0e14',
                colorText: '#c9d1d9',
                colorTextSecondary: '#8b949e',
                borderRadius: '6px',
              },
              elements: {
                card: { background: 'transparent', boxShadow: 'none' },
                headerTitle: { color: '#c9d1d9' },
                headerSubtitle: { color: '#8b949e' },
              },
            }}
          />
        </div>

        <p className="mt-4 text-center text-sm text-cyber-muted">
          No account yet?{' '}
          <Link href="/register" className="text-cyber-primary hover:underline">
            Create one
          </Link>
        </p>
      </div>
    </div>
  );
}
