'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { Award, BadgeCheck, Calendar, Copy, Search, ShieldCheck } from 'lucide-react';
import Navbar from '@/components/Navbar';
import { LoadingScreen, TerminalCard } from '@/components/TerminalCard';
import { api } from '@/lib/api';
import { useRequireAuth } from '@/lib/auth';
import type { APIResponse } from '@/lib/types';

interface Certificate {
  id: string;
  template_slug: string;
  template_name: string;
  template_description: string;
  source_type: string;
  source_id: string | null;
  course_name: string | null;
  full_name: string;
  verification_code: string;
  status: string;
  pdf_url: string | null;
  issued_at: string | null;
  expires_at: string | null;
}

export default function CertificatesPage() {
  const { user, loading } = useRequireAuth();
  const [certificates, setCertificates] = useState<Certificate[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [verifyCode, setVerifyCode] = useState('');
  const [verifyResult, setVerifyResult] = useState<Certificate | null>(null);
  const [verifyError, setVerifyError] = useState<string | null>(null);
  const [verifying, setVerifying] = useState(false);

  useEffect(() => {
    if (!user) return;
    api
      .get<APIResponse<Certificate[]>>('/certificates/')
      .then((res) => setCertificates(res.data ?? []))
      .catch((err) => setError(err instanceof Error ? err.message : 'Failed to load certificates'));
  }, [user]);

  const copyCode = (code: string) => {
    void navigator.clipboard?.writeText(code);
  };

  const verify = async () => {
    const code = verifyCode.trim();
    if (!code || verifying) return;
    setVerifying(true);
    setVerifyResult(null);
    setVerifyError(null);
    try {
      const res = await api.get<APIResponse<Certificate>>(`/certificates/verify/${encodeURIComponent(code)}`);
      setVerifyResult(res.data ?? null);
    } catch (err) {
      setVerifyError(err instanceof Error ? err.message : 'Verification failed');
    } finally {
      setVerifying(false);
    }
  };

  if (loading || !user) return <LoadingScreen />;

  return (
    <>
      <Navbar />
      <main className="mx-auto max-w-7xl px-6 py-10">
        <div className="mb-10">
          <div className="mb-2 flex items-center gap-2 font-mono text-xs text-cyber-secondary">
            <Award className="h-3.5 w-3.5" />
            <span>Course completions are verified with unique codes</span>
          </div>
          <h1 className="text-3xl font-bold sm:text-4xl">
            My <span className="text-cyber-primary">Certificates</span>
          </h1>
          <p className="mt-2 max-w-2xl text-cyber-muted">
            Complete every lesson in a course to earn a CyberVerse certificate. Anyone can verify a
            certificate using its unique code.
          </p>
        </div>

        <div className="grid gap-8 lg:grid-cols-[1fr,380px]">
          {/* Certificate list */}
          <section>
            {error && (
              <div className="mb-6 rounded-md border border-cyber-danger/40 bg-cyber-danger/10 px-4 py-3 text-sm text-cyber-danger">
                {error}
              </div>
            )}

            {certificates.length === 0 ? (
              <TerminalCard title="certificates.list">
                <div className="flex flex-col items-center gap-3 py-8 text-center">
                  <BadgeCheck className="h-10 w-10 text-cyber-muted/50" />
                  <p className="text-sm text-cyber-muted">No certificates yet.</p>
                  <p className="text-xs text-cyber-muted">
                    Finish all lessons in a course to earn your first certificate.
                  </p>
                  <Link href="/courses" className="terminal-button mt-2 px-4 py-2 text-sm">
                    Browse Courses
                  </Link>
                </div>
              </TerminalCard>
            ) : (
              <div className="space-y-4">
                {certificates.map((cert) => (
                  <div
                    key={cert.id}
                    className="terminal-card relative overflow-hidden p-6"
                  >
                    <div className="absolute right-0 top-0 h-full w-1.5 bg-gradient-to-b from-cyber-primary to-cyber-secondary" />
                    <div className="flex flex-wrap items-start justify-between gap-4">
                      <div className="flex items-start gap-4">
                        <div className="rounded-lg bg-cyber-primary/10 p-3 text-cyber-primary">
                          <Award className="h-7 w-7" />
                        </div>
                        <div>
                          <h2 className="text-lg font-bold text-cyber-text">{cert.template_name}</h2>
                          <p className="mt-0.5 text-sm text-cyber-muted">
                            {cert.course_name ?? 'CyberVerse course'}
                          </p>
                          <div className="mt-2 flex flex-wrap items-center gap-3 text-xs text-cyber-muted">
                            <span className="flex items-center gap-1">
                              <Calendar className="h-3 w-3" />
                              {cert.issued_at ? new Date(cert.issued_at).toLocaleDateString() : '—'}
                            </span>
                            <span className="flex items-center gap-1 text-cyber-success">
                              <ShieldCheck className="h-3 w-3" />
                              {cert.full_name}
                            </span>
                          </div>
                        </div>
                      </div>
                      <button
                        onClick={() => copyCode(cert.verification_code)}
                        className="flex items-center gap-2 rounded border border-cyber-border px-3 py-1.5 font-mono text-xs text-cyber-secondary hover:border-cyber-primary transition-colors"
                        title="Copy verification code"
                      >
                        <Copy className="h-3 w-3" />
                        {cert.verification_code.slice(0, 10)}…
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>

          {/* Verify panel */}
          <aside>
            <TerminalCard title="verify.sh">
              <h2 className="mb-2 font-semibold">Verify a certificate</h2>
              <p className="mb-4 text-xs text-cyber-muted">
                Enter a certificate verification code to confirm it is genuine.
              </p>
              <input
                value={verifyCode}
                onChange={(e) => setVerifyCode(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && void verify()}
                placeholder="e.g. A1B2C3D4E5F6…"
                className="w-full rounded-md border border-cyber-border bg-cyber-bg px-3 py-2 font-mono text-sm text-cyber-text outline-none focus:border-cyber-primary"
              />
              <button
                onClick={() => void verify()}
                disabled={verifying || !verifyCode.trim()}
                className="terminal-button mt-3 flex w-full items-center justify-center gap-2 px-4 py-2 text-sm disabled:opacity-50"
              >
                <Search className="h-4 w-4" />
                {verifying ? 'Checking…' : 'Verify'}
              </button>

              {verifyError && (
                <p className="mt-3 text-xs text-cyber-danger">✕ {verifyError}</p>
              )}
              {verifyResult && (
                <div className="mt-3 rounded-md border border-cyber-success/40 bg-cyber-success/10 p-3">
                  <p className="flex items-center gap-2 text-sm font-semibold text-cyber-success">
                    <ShieldCheck className="h-4 w-4" /> Valid certificate
                  </p>
                  <p className="mt-1 text-xs text-cyber-muted">
                    {verifyResult.template_name} — {verifyResult.course_name ?? 'CyberVerse course'}
                  </p>
                  <p className="mt-0.5 text-xs text-cyber-muted">
                    Issued to {verifyResult.full_name}
                  </p>
                  <p className="mt-0.5 text-xs text-cyber-muted">
                    {verifyResult.issued_at ? new Date(verifyResult.issued_at).toLocaleDateString() : ''}
                  </p>
                </div>
              )}
            </TerminalCard>
          </aside>
        </div>
      </main>
    </>
  );
}
