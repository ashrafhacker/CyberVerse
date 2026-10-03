'use client';

import Link from 'next/link';
import { FileSearch, Shield, ShieldAlert } from 'lucide-react';
import DorkerTool from '@/components/DorkerTool';

export default function DorkerPage() {
  return (
    <div className="min-h-screen bg-cyber-bg px-6 py-6">
      <header className="mx-auto flex max-w-6xl items-center justify-between">
        <Link href="/" className="flex items-center gap-2">
          <Shield className="h-7 w-7 text-cyber-primary" />
          <span className="font-mono text-lg font-bold glow-text text-cyber-primary">CyberVerse</span>
        </Link>
        <nav className="flex items-center gap-3">
          <Link href="/game" className="terminal-button-ghost px-4 py-1.5 text-sm">
            sandbox game →
          </Link>
          <Link href="/" className="terminal-button-ghost px-4 py-1.5 text-sm">
            ← back
          </Link>
        </nav>
      </header>

      <main className="mx-auto mt-8 max-w-6xl">
        <div className="mb-6">
          <p className="mb-2 font-mono text-xs text-cyber-secondary">
            &gt; // osint tool · query builder · authorized use only
          </p>
          <h1 className="text-3xl font-bold">
            Open Directory <span className="glow-text text-cyber-primary">Dorker</span>
          </h1>
          <p className="mt-2 max-w-3xl text-sm text-cyber-muted">
            Pick a filetype and a search engine, then run an indexed search-query dork to hunt for
            open directory listings. Learn how classic OSINT queries are assembled before applying
            them — strictly on sources you are authorized to inspect.
          </p>
        </div>

        <div className="mb-6 flex items-center gap-2 text-xs text-amber-400 bg-amber-500/10 border border-amber-500/30 rounded px-3 py-2">
          <ShieldAlert className="h-4 w-4 flex-shrink-0" />
          <span>Educational technique only — build queries for fictional targets and sources you own or are authorized to test. Not for probing real third-party systems.</span>
        </div>

        <DorkerTool />

        <p className="mt-6 text-center font-mono text-xs text-cyber-muted">
          <FileSearch className="mr-1 inline h-3.5 w-3.5" />
          intitle:index.of · osint for education · stay authorized
        </p>
      </main>
    </div>
  );
}
