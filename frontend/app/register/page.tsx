'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { Shield, AlertTriangle } from 'lucide-react';
import { useAuth } from '@/lib/auth';

export default function RegisterPage() {
  const { register } = useAuth();
  const router = useRouter();
  const [form, setForm] = useState({ fullName: '', username: '', email: '', password: '' });
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await register(form.email, form.password, form.fullName, form.username);
      router.push('/dashboard');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Registration failed');
    } finally {
      setLoading(false);
    }
  };

  const update = (key: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm((f) => ({ ...f, [key]: e.target.value }));

  return (
    <div className="flex min-h-screen items-center justify-center bg-grid-pattern [background-size:40px_40px] bg-cyber-bg px-4 py-10">
      <div className="w-full max-w-md">
        <div className="mb-8 flex items-center justify-center gap-2">
          <Shield className="h-10 w-10 text-cyber-primary" />
          <span className="font-mono text-2xl font-bold glow-text text-cyber-primary">CyberVerse</span>
        </div>

        <form onSubmit={handleSubmit} className="terminal-card p-8">
          <h1 className="mb-6 text-center font-mono text-xl font-bold text-cyber-primary">
            &gt; new agent registration
          </h1>

          {error && (
            <div className="mb-4 flex items-center gap-2 rounded-md border border-cyber-danger/40 bg-cyber-danger/10 px-3 py-2 text-sm text-cyber-danger">
              <AlertTriangle className="h-4 w-4 shrink-0" />
              {error}
            </div>
          )}

          <div className="mb-4">
            <label htmlFor="fullName" className="terminal-label">Full name</label>
            <input id="fullName" required value={form.fullName} onChange={update('fullName')} className="terminal-input" placeholder="Alex Rivera" />
          </div>

          <div className="mb-4">
            <label htmlFor="username" className="terminal-label">Username</label>
            <input id="username" required minLength={3} value={form.username} onChange={update('username')} className="terminal-input font-mono" placeholder="alex_rivera" />
          </div>

          <div className="mb-4">
            <label htmlFor="email" className="terminal-label">Email</label>
            <input id="email" type="email" required value={form.email} onChange={update('email')} className="terminal-input" placeholder="agent@cyberverse.io" autoComplete="email" />
          </div>

          <div className="mb-6">
            <label htmlFor="password" className="terminal-label">Password</label>
            <input id="password" type="password" required minLength={8} value={form.password} onChange={update('password')} className="terminal-input" placeholder="min. 8 characters" autoComplete="new-password" />
          </div>

          <button type="submit" disabled={loading} className="terminal-button w-full py-2.5">
            {loading ? 'Creating profile...' : 'Join CyberVerse'}
          </button>

          <p className="mt-4 text-center text-sm text-cyber-muted">
            Already have an account?{' '}
            <Link href="/login" className="text-cyber-primary hover:underline">
              Log in
            </Link>
          </p>
        </form>
      </div>
    </div>
  );
}
