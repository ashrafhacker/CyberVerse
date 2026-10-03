'use client';

import Link from 'next/link';
import { ExternalLink, Shield, Lock, Zap, Brain, ChevronRight } from 'lucide-react';

export default function ExternalLabsPage() {
  return (
    <div className="min-h-screen bg-cyber-bg text-cyber-text">
      <div className="mx-auto max-w-5xl px-6 py-16">
        <header className="mb-12 text-center">
          <h1 className="mb-4 text-4xl font-bold tracking-tight md:text-5xl">
            CYBERVERSE <span className="text-cyber-primary">EXTERNAL LABS</span>
          </h1>
          <p className="mx-auto max-w-2xl text-lg text-cyber-muted">
            Connect your cybersecurity training ecosystem. Access official Hack The Box and TryHackMe
            integrations through authorized channels only.
          </p>
        </header>

        <div className="grid gap-6 md:grid-cols-2">
          {/* HACK THE BOX CARD */}
          <article className="relative overflow-hidden rounded-2xl border border-cyber-border bg-cyber-surface/60 p-8 transition-all hover:border-cyber-primary/60 hover:shadow-[0_0_24px_rgba(0,229,255,0.15)]">
            <div className="mb-6 flex items-center gap-3">
              <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-green-500/20">
                <Shield className="h-7 w-7 text-green-400" />
              </div>
              <div>
                <h2 className="text-2xl font-bold">HACK THE BOX</h2>
                <p className="text-sm text-cyber-muted">Official training platform</p>
              </div>
            </div>

            <p className="mb-6 text-cyber-muted">
              Access Hack The Box training, CTFs, and authorized integrations.
              Enterprise-grade labs, real-world scenarios, and competitive CTFs.
            </p>

            <div className="space-y-3">
              <Link
                href="https://account.hackthebox.com/"
                target="_blank"
                rel="noopener noreferrer"
                className="flex w-full items-center justify-between rounded-lg border border-cyber-border bg-cyber-bg px-4 py-3 text-left transition-all hover:border-cyber-primary/60 hover:bg-cyber-primary/10"
              >
                <div className="flex items-center gap-3">
                  <ExternalLink className="h-5 w-5 text-cyber-muted" />
                  <span className="font-medium">HTB Account</span>
                </div>
                <ChevronRight className="h-5 w-5 text-cyber-muted" />
              </Link>

              <Link
                href="https://app.hackthebox.com/"
                target="_blank"
                rel="noopener noreferrer"
                className="flex w-full items-center justify-between rounded-lg border border-cyber-border bg-cyber-bg px-4 py-3 text-left transition-all hover:border-cyber-primary/60 hover:bg-cyber-primary/10"
              >
                <div className="flex items-center gap-3">
                  <Zap className="h-5 w-5 text-cyber-muted" />
                  <span className="font-medium">HTB Labs</span>
                </div>
                <ChevronRight className="h-5 w-5 text-cyber-muted" />
              </Link>

              <Link
                href="https://academy.hackthebox.com/"
                target="_blank"
                rel="noopener noreferrer"
                className="flex w-full items-center justify-between rounded-lg border border-cyber-border bg-cyber-bg px-4 py-3 text-left transition-all hover:border-cyber-primary/60 hover:bg-cyber-primary/10"
              >
                <div className="flex items-center gap-3">
                  <Brain className="h-5 w-5 text-cyber-muted" />
                  <span className="font-medium">HTB Academy</span>
                </div>
                <ChevronRight className="h-5 w-5 text-cyber-muted" />
              </Link>

              <Link
                href="https://ctf.hackthebox.com/"
                target="_blank"
                rel="noopener noreferrer"
                className="flex w-full items-center justify-between rounded-lg border border-cyber-border bg-cyber-bg px-4 py-3 text-left transition-all hover:border-cyber-primary/60 hover:bg-cyber-primary/10"
              >
                <div className="flex items-center gap-3">
                  <Lock className="h-5 w-5 text-cyber-muted" />
                  <span className="font-medium">HTB CTF</span>
                </div>
                <ChevronRight className="h-5 w-5 text-cyber-muted" />
              </Link>
            </div>

            <div className="mt-6 pt-6 border-t border-cyber-border">
              <p className="text-xs text-cyber-muted/70">
                Official destinations only. CyberVerse does not scrape, proxy, or store HTB credentials.
              </p>
            </div>
          </article>

          {/* TRYHACKME CARD */}
          <article className="relative overflow-hidden rounded-2xl border border-cyber-border bg-cyber-surface/60 p-8 transition-all hover:border-cyber-primary/60 hover:shadow-[0_0_24px_rgba(0,229,255,0.15)]">
            <div className="mb-6 flex items-center gap-3">
              <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-red-500/20">
                <Lock className="h-7 w-7 text-red-400" />
              </div>
              <div>
                <h2 className="text-2xl font-bold">TRYHACKME</h2>
                <p className="text-sm text-cyber-muted">Interactive security rooms</p>
              </div>
            </div>

            <p className="mb-6 text-cyber-muted">
              Access TryHackMe rooms and learning paths through officially supported integrations.
              Guided, hands-on cybersecurity training for all skill levels.
            </p>

            <div className="space-y-3">
              <Link
                href="https://tryhackme.com/"
                target="_blank"
                rel="noopener noreferrer"
                className="flex w-full items-center justify-between rounded-lg border border-cyber-border bg-cyber-bg px-4 py-3 text-left transition-all hover:border-cyber-primary/60 hover:bg-cyber-primary/10"
              >
                <div className="flex items-center gap-3">
                  <ExternalLink className="h-5 w-5 text-cyber-muted" />
                  <span className="font-medium">Open TryHackMe</span>
                </div>
                <ChevronRight className="h-5 w-5 text-cyber-muted" />
              </Link>
            </div>

            <div className="mt-6 pt-6 border-t border-cyber-border">
              <p className="text-xs text-cyber-muted/70">
                No scraping. No credential storage. Official platform links only.
              </p>
            </div>
          </article>
        </div>

        <section className="mt-16 rounded-2xl border border-cyber-primary/30 bg-cyber-primary/10 p-6 text-center">
          <h3 className="mb-3 text-xl font-semibold text-cyber-primary">Official Integrations</h3>
          <p className="mx-auto max-w-2xl text-cyber-muted">
            CyberVerse supports official HTB and TryHackMe integrations where authorized APIs exist.
            When Enterprise/Education API access is configured, synchronized progress and achievements
            will appear in your CyberVerse profile. Otherwise, use the external links above.
          </p>
          <div className="mt-4 flex flex-wrap justify-center gap-3">
            <span className="rounded-full border border-cyber-border bg-cyber-surface px-3 py-1 text-xs text-cyber-muted">
              HTB_API_KEY: Not configured
            </span>
            <span className="rounded-full border border-cyber-border bg-cyber-surface px-3 py-1 text-xs text-cyber-muted">
              TRYHACKME_API_KEY: Not configured
            </span>
          </div>
        </section>
      </div>
    </div>
  );
}