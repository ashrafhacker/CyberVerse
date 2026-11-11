'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { Loader2, Printer, ArrowLeft, AlertTriangle } from 'lucide-react';
import { api, ApiError } from '@/lib/api';
import { useRequireAuth } from '@/lib/auth';
import type { APIResponse } from '@/lib/types';

interface Certificate {
  id: string;
  template_name: string;
  course_name: string | null;
  full_name: string;
  verification_code: string;
  issued_at: string | null;
  status: string;
  signature: string | null;
  signature_valid: boolean;
  verify_path: string;
}

export default function CertificatePrintPage() {
  const { id } = useParams<{ id: string }>();
  const { loading: authLoading } = useRequireAuth();
  const [cert, setCert] = useState<Certificate | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (authLoading) return;
    api
      .get<APIResponse<Certificate>>(`/certificates/${id}`, { cache: 'no-store' })
      .then((res) => setCert(res.data ?? null))
      .catch((err) => {
        if (err instanceof ApiError && err.status === 404) {
          setError('Certificate not found.');
        } else {
          setError('Could not load this certificate. Try again in a moment.');
        }
      });
  }, [authLoading, id]);

  const verificationUrl =
    typeof window !== 'undefined' && cert
      ? `${window.location.origin}${cert.verify_path ?? `/certificates/verify/${cert.verification_code}`}`
      : cert
        ? `/certificates/verify/${cert.verification_code}`
        : '';

  return (
    <>
      <style>{`
        @page { size: landscape; margin: 0; }
        @media print {
          body { background: #050b1a !important; }
          .no-print { display: none !important; }
          .certificate-sheet {
            box-shadow: none !important;
            width: 100vw !important;
            height: 100vh !important;
            border-radius: 0 !important;
          }
        }
      `}</style>

      <div className="no-print sticky top-0 z-10 flex items-center justify-between gap-3 border-b border-cyber-border bg-cyber-bg/90 px-6 py-3 backdrop-blur">
        <Link href="/certificates" className="flex items-center gap-2 text-sm text-cyber-muted hover:text-cyber-text">
          <ArrowLeft className="h-4 w-4" /> Back to certificates
        </Link>
        <button
          onClick={() => window.print()}
          className="flex items-center gap-2 rounded-md bg-cyber-primary px-4 py-2 text-sm font-semibold text-black transition hover:bg-cyber-primary/90"
        >
          <Printer className="h-4 w-4" /> Print / Save as PDF
        </button>
      </div>

      <main className="flex min-h-screen items-center justify-center bg-cyber-bg p-4 sm:p-8">
        {!cert && !error && (
          <div className="flex items-center gap-3 text-cyber-muted">
            <Loader2 className="h-5 w-5 animate-spin" /> Loading certificate…
          </div>
        )}

        {error && (
          <div className="max-w-md text-center">
            <AlertTriangle className="mx-auto h-10 w-10 text-cyber-danger" />
            <p className="mt-3 text-cyber-muted">{error}</p>
          </div>
        )}

        {cert && (
          <div
            className="certificate-sheet relative flex w-full max-w-4xl flex-col items-center justify-between overflow-hidden rounded-xl border-2 border-cyber-primary/60 bg-[#0a1128] px-8 py-10 text-center shadow-[0_0_80px_rgba(0,255,255,0.08)] sm:px-16"
            role="document"
            aria-label={`Certificate of completion for ${cert.full_name}`}
          >
            {/* Corner accents */}
            <div aria-hidden="true" className="pointer-events-none absolute left-3 top-3 h-16 w-16 border-l-2 border-t-2 border-cyber-primary/50" />
            <div aria-hidden="true" className="pointer-events-none absolute right-3 top-3 h-16 w-16 border-r-2 border-t-2 border-cyber-primary/50" />
            <div aria-hidden="true" className="pointer-events-none absolute bottom-3 left-3 h-16 w-16 border-b-2 border-l-2 border-cyber-primary/50" />
            <div aria-hidden="true" className="pointer-events-none absolute bottom-3 right-3 h-16 w-16 border-b-2 border-r-2 border-cyber-primary/50" />

            <header>
              <p className="font-mono text-sm uppercase tracking-[0.35em] text-cyber-secondary">CyberVerse</p>
              <h1 className="mt-2 text-3xl font-bold text-cyber-text sm:text-4xl">Certificate of Completion</h1>
            </header>

            <section className="mt-4">
              <p className="text-[11px] uppercase tracking-widest text-cyber-muted">This certifies that</p>
              <p className="mt-2 border-b border-cyber-primary/40 px-6 pb-2 text-3xl font-bold italic text-cyber-primary sm:text-4xl">
                {cert.full_name}
              </p>
              <p className="mt-3 text-[11px] uppercase tracking-widest text-cyber-muted">has successfully completed</p>
              <p className="mt-1 text-xl font-semibold text-cyber-text sm:text-2xl">
                {cert.course_name ?? cert.template_name}
              </p>
              {cert.issued_at && (
                <p className="mt-2 text-sm text-cyber-muted">
                  Issued {new Date(cert.issued_at).toLocaleDateString(undefined, { year: 'numeric', month: 'long', day: 'numeric' })}
                </p>
              )}
            </section>

            <footer className="mt-6 w-full border-t border-cyber-border pt-5">
              <div className="flex flex-col items-center justify-between gap-4 sm:flex-row sm:text-left">
                <div className="text-left">
                  <p className="text-[10px] uppercase tracking-widest text-cyber-muted">Verification ID</p>
                  <p className="font-mono text-sm font-semibold text-cyber-text">{cert.verification_code}</p>
                  <p className="mt-1 break-all font-mono text-[10px] text-cyber-muted">{verificationUrl}</p>
                </div>
                <div className="max-w-[16rem]">
                  <p className="text-[10px] uppercase tracking-widest text-cyber-muted">Digital signature (HMAC-SHA256)</p>
                  <p className="break-all font-mono text-[10px] leading-snug text-cyber-muted">
                    {cert.signature ? `${cert.signature.slice(0, 40)}…` : 'Unsigned (legacy)'}
                  </p>
                  <p className={`mt-1 text-[10px] font-semibold uppercase tracking-wider ${cert.signature_valid ? 'text-cyber-success' : 'text-cyber-danger'}`}>
                    {cert.signature_valid ? '✓ Signature valid' : '✗ Signature invalid'}
                  </p>
                </div>
              </div>
            </footer>
          </div>
        )}
      </main>
    </>
  );
}
