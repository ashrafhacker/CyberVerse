'use client';

import Link from 'next/link';
import { Globe2, Loader2, Search, Shield, ShieldAlert } from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';
import { api } from '@/lib/api';

interface CVESummary {
  cve_id: string;
  description: string;
  severity: string;
  cvss_score: number | null;
  cwe_id: string | null;
  attack_vector: string | null;
  published_date: string | null;
  source: string;
}

interface PageData {
  items: string[];
  total: number;
  page: number;
  total_pages: number;
  has_next: boolean;
  has_prev: boolean;
}

const SEV_COLORS: Record<string, string> = {
  critical: 'bg-red-500/20 text-red-400 border-red-500/40',
  high: 'bg-orange-500/20 text-orange-400 border-orange-500/40',
  medium: 'bg-amber-500/20 text-amber-400 border-amber-500/40',
  low: 'bg-green-500/20 text-green-400 border-green-500/40',
  unknown: 'bg-cyber-surface text-cyber-muted border-cyber-border',
};

export default function ThreatIntelPage() {
  const [cves, setCves] = useState<CVESummary[]>([]);
  const [search, setSearch] = useState('');
  const [debounced, setDebounced] = useState('');
  const [severity, setSeverity] = useState('');
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const t = setTimeout(() => {
      setDebounced(search);
      setPage(1);
    }, 400);
    return () => clearTimeout(t);
  }, [search]);

  const load = useCallback(() => {
    setLoading(true);
    const params = new URLSearchParams({ page: String(page), page_size: '10' });
    if (debounced) params.set('search', debounced);
    if (severity) params.set('severity', severity);
    api
      .get<{ data: PageData }>(`/threat-intel/cves?${params.toString()}`)
      .then(async (res) => {
        setTotalPages(res.data.total_pages);
        setError('');
        const details = await Promise.all(
          res.data.items.map((id) =>
            api.get<{ data: CVESummary }>(`/threat-intel/cves/${encodeURIComponent(id)}`).then((r) => r.data).catch(() => null),
          ),
        );
        setCves(details.filter(Boolean) as CVESummary[]);
      })
      .catch(() => setError('Failed to load CVEs.'))
      .finally(() => setLoading(false));
  }, [page, debounced, severity]);

  useEffect(() => {
    load();
  }, [load]);

  const selectCls =
    'rounded border border-cyber-border bg-cyber-bg px-3 py-1.5 text-sm text-cyber-muted outline-none focus:border-cyber-primary';

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
            &gt; // threat intelligence · cve & mitre knowledge
          </p>
          <h1 className="flex items-center gap-3 text-3xl font-bold">
            <Globe2 className="h-8 w-8 text-cyber-primary" />
            Threat <span className="glow-text text-cyber-primary">Intelligence</span>
          </h1>
          <p className="mt-2 max-w-3xl text-sm text-cyber-muted">
            Search curated CVEs sourced from NVD/CISA. Data shown is for education and offline-first
            reference; always verify mitigations against the official advisory.
          </p>
        </div>

        <div className="mb-6 flex flex-wrap items-center gap-3 rounded border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs text-amber-400">
          <ShieldAlert className="h-4 w-4 flex-shrink-0" />
          <span>Reference data only. Do not use to target systems — these entries describe real vulnerabilities for learning context.</span>
        </div>

        <div className="mb-6 flex flex-wrap items-center gap-3">
          <div className="relative flex-1 min-w-[220px]">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-cyber-muted" />
            <input
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setPage(1);
              }}
              placeholder="search CVE id or description…"
              className="w-full rounded border border-cyber-border bg-cyber-bg py-2 pl-9 pr-3 text-sm text-cyber-foreground outline-none placeholder:text-cyber-muted focus:border-cyber-primary"
            />
          </div>
          <select value={severity} onChange={(e) => { setSeverity(e.target.value); setPage(1); }} className={selectCls}>
            <option value="">all severities</option>
            <option value="critical">critical</option>
            <option value="high">high</option>
            <option value="medium">medium</option>
            <option value="low">low</option>
          </select>
        </div>

        {loading ? (
          <div className="flex justify-center py-20">
            <Loader2 className="h-8 w-8 animate-spin text-cyber-primary" />
          </div>
        ) : error ? (
          <p className="rounded border border-red-500/40 bg-red-500/10 p-4 text-center font-mono text-sm text-red-400">{error}</p>
        ) : cves.length === 0 ? (
          <p className="rounded border border-cyber-border bg-cyber-surface/50 p-10 text-center font-mono text-sm text-cyber-muted">
            no CVEs match those filters
          </p>
        ) : (
          <>
            <div className="space-y-4">
              {cves.map((c) => (
                <div key={c.cve_id} className="terminal-card p-5">
                  <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                    <span className="font-mono font-bold text-cyber-primary">{c.cve_id}</span>
                    <div className="flex items-center gap-2">
                      <span className={`rounded border px-2 py-0.5 font-mono text-xs capitalize ${SEV_COLORS[c.severity] ?? SEV_COLORS.unknown}`}>
                        {c.severity}
                      </span>
                      {c.cvss_score != null && (
                        <span className="rounded bg-cyber-surface px-2 py-0.5 font-mono text-xs text-cyber-muted">
                          CVSS {c.cvss_score}
                        </span>
                      )}
                    </div>
                  </div>
                  <p className="text-sm text-cyber-muted">{c.description}</p>
                  <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 font-mono text-[11px] text-cyber-muted">
                    {c.cwe_id && <span>CWE: {c.cwe_id}</span>}
                    {c.attack_vector && <span>Vector: {c.attack_vector}</span>}
                    {c.published_date && <span>{c.published_date.slice(0, 10)}</span>}
                    <span>Source: {c.source}</span>
                  </div>
                </div>
              ))}
            </div>
            {totalPages > 1 && (
              <div className="mt-8 flex items-center justify-center gap-4">
                <button className="terminal-button-ghost px-4 py-1.5 text-sm disabled:opacity-40" disabled={page <= 1} onClick={() => setPage((p) => Math.max(1, p - 1))}>
                  ← prev
                </button>
                <span className="font-mono text-sm text-cyber-muted">page {page} / {totalPages}</span>
                <button className="terminal-button-ghost px-4 py-1.5 text-sm disabled:opacity-40" disabled={page >= totalPages} onClick={() => setPage((p) => Math.min(totalPages, p + 1))}>
                  next →
                </button>
              </div>
            )}
          </>
        )}
      </main>
    </div>
  );
}
