'use client';

import Link from 'next/link';
import { Shield } from 'lucide-react';
import { SignUp } from '@clerk/nextjs';
import { resolveLoginRedirect } from '@/lib/auth-utils';

/**
 * Sign-up page — powered by Clerk.
 *
 * Clerk handles account creation (email/password, social, MFA). The backend
 * provisions the local `users` row via the Clerk webhook or lazy sync on the
 * first authenticated request.
 */
export default function RegisterPage() {
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
            &gt; create account
          </h1>
          <SignUp
            path="/register"
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
          Already have an account?{' '}
          <Link href="/login" className="text-cyber-primary hover:underline">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}
