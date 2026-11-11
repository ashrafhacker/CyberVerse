'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { Award, Calendar, ShieldCheck, ShieldX, Loader2 } from 'lucide-react';
import Navbar from '@/components/Navbar';
import { API_URL } from '@/lib/api';

interface VerifiedCertificate {
  template_name: string;
  course_name: string | null;
  full_name: string;
  verification_code: string;
  issued_at: string | null;
  status: string;
  signature: string | null;
  signature_valid: boolean;
}

export default function CertificateVerifyPage() {
  const { code } = useParams<{ code: string }>();
  const [cert, setCert] = useState<VerifiedCertificate | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    fetch(`${API_URL}/certificates/verify/${encodeURIComponent(code ?? '')}`, { cache: 'no-store' })
      .then(async (res) => {
        if (!res.ok) {
          const body = await res.json().catch(() => null);
          throw new Error(body?.detail || (res.status === 404 ? 'Certificate not found' : 'Verification failed'));
        }
        return res.json();
      })
      .then((body) => {
        if (!cancelled) setCert(body?.data ?? null);
      })
      .catch((err: Error) => {
        if (!cancelled) setError(err.message || 'Verification failed');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [code]);

  return (
    <>
      <Navbar />
      <main className="flex min-h-screen flex-col items-center justify-center bg-cyber-bg px-6 py-16">
        {loading && (
          <div className="flex items-center gap-3 text-cyber-muted">
            <Loader2 className="h-5 w-5 animate-spin" />
            Verifying certificate…
          </div>
        )}

        {!loading && error && (
          <div className="terminal-card max-w-md p-8 text-center">
            <ShieldX className="mx-auto h-12 w-12 text-cyber-danger" aria-hidden="true" />
            <h1 className="mt-4 text-xl font-bold text-cyber-text">Certificate not found</h1>
            <p className="mt-2 text-sm text-cyber-muted">
              {error}. Check the verification code and try again.
            </p>
            <Link href="/contact" className="terminal-button mt-6 inline-block px-4 py-2 text-sm">
              Contact the site owner
            </Link>
          </div>
        )}

        {!loading && cert && (
          <div className="terminal-card w-full max-w-2xl overflow-hidden">
            <div className="border-b border-cyber-border bg-gradient-to-r from-cyber-primary/10 to-cyber-secondary/10 px-8 py-6 text-center">
              <Award className="mx-auto h-14 w-14 text-cyber-primary" aria-hidden="true" />
              <h1 className="mt-3 text-2xl font-bold text-cyber-text">Certificate of Completion</h1>
              <p className="mt-1 font-mono text-xs text-cyber-secondary">cyberverse.qd.je</p>
            </div>
            <div className="px-8 py-6 text-center">
              <p className="text-xs uppercase tracking-widest text-cyber-muted">Awarded to</p>
              <p className="mt-1 text-3xl font-bold text-cyber-text">{cert.full_name}</p>
              <p className="mt-4 text-xs uppercase tracking-widest text-cyber-muted">for completing</p>
              <p className="mt-1 text-lg font-semibold text-cyber-primary">
                {cert.course_name ?? cert.template_name}
              </p>
              <div className="mt-4 flex items-center justify-center gap-2 text-sm text-cyber-muted">
                <Calendar className="h-4 w-4" />
                {cert.issued_at ? new Date(cert.issued_at).toLocaleDateString(undefined, { year: 'numeric', month: 'long', day: 'numeric' }) : '—'}
              </div>

              <div
                className={`mt-6 rounded-md border px-4 py-3 text-left ${
                  cert.signature_valid
                    ? 'border-cyber-success/40 bg-cyber-success/10'
                    : 'border-cyber-danger/40 bg-cyber-danger/10'
                }`}
              >
                <p className={`flex items-center gap-2 text-sm font-semibold ${cert.signature_valid ? 'text-cyber-success' : 'text-cyber-danger'}`}>
                  {cert.signature_valid ? (
                    <>
                      <ShieldCheck className="h-4 w-4" /> Digitally signed &amp; verified
                    </>
                  ) : (
                    <>
                      <ShieldX className="h-4 w-4" /> Signature could not be verified
                    </>
                  )}
                </p>
                <dl className="mt-2 space-y-1 text-xs text-cyber-muted">
                  <div className="flex flex-wrap gap-1">
                    <dt className="font-semibold text-cyber-text">Verification ID:</dt>
                    <dd className="font-mono">{cert.verification_code}</dd>
                  </div>
                  {cert.signature && (
                    <div className="flex flex-wrap gap-1">
                      <dt className="font-semibold text-cyber-text">Signature (HMAC-SHA256):</dt>
                      <dd className="break-all font-mono">{cert.signature.slice(0, 32)}…</dd>
                    </div>
                  )}
                </dl>
              </div>

              <p className="mt-6 text-[11px] text-cyber-muted">
                This page is the authoritative record. Anyone holding this link can verify the
                certificate&apos;s authenticity and integrity.
              </p>
            </div>
          </div>
        )}
      </main>
    </>
  );
}
