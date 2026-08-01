'use client';

import Link from 'next/link';
import { Shield } from 'lucide-react';
import CyberNetworkGame from '@/components/CyberNetworkGame';

export default function GamePage() {
  return (
    <div className="min-h-screen bg-cyber-bg px-6 py-6">
      <header className="mx-auto flex max-w-6xl items-center justify-between">
        <Link href="/" className="flex items-center gap-2">
          <Shield className="h-7 w-7 text-cyber-primary" />
          <span className="font-mono text-lg font-bold glow-text text-cyber-primary">CyberVerse</span>
        </Link>
        <Link href="/" className="terminal-button-ghost px-4 py-1.5 text-sm">
          ← back
        </Link>
      </header>

      <main className="mx-auto mt-8 max-w-6xl">
        <div className="mb-6">
          <p className="mb-2 font-mono text-xs text-cyber-secondary">
            &gt; // sandbox game · fictional network · authorized assessment only
          </p>
          <h1 className="text-3xl font-bold">
            Cyber <span className="glow-text text-cyber-primary">Network Raid</span>
          </h1>
          <p className="mt-2 max-w-3xl text-sm text-cyber-muted">
            Recon the simulated topology, scan hosts to reveal services and weaknesses, then exploit
            your way from the edge to the core. Everything here is fictional — no real systems are
            involved, exactly like the sandbox missions.
          </p>
        </div>

        <CyberNetworkGame />

        <p className="mt-6 text-center font-mono text-xs text-cyber-muted">
          educational simulation · scan then exploit · energy is finite · time is ticking
        </p>
      </main>
    </div>
  );
}
