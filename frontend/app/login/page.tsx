'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { Shield, AlertTriangle } from 'lucide-react';
import { useAuth } from '@/lib/auth';

export default function LoginPage() {
  const { login } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await login(email, password);
      router.push('/dashboard');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  return (
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

          <button type="submit" disabled={loading} className="terminal-button w-full py-2.5">
            {loading ? 'Connecting...' : 'Access Terminal'}
          </button>

          <p className="mt-4 text-center text-sm text-cyber-muted">
            No account yet?{' '}
            <Link href="/register" className="text-cyber-primary hover:underline">
              Create one
            </Link>
          </p>
        </form>
      </div>
    </div>
  );
}
