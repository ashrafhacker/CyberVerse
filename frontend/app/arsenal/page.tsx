'use client';

import Link from 'next/link';
import {
  ExternalLink,
  FileText,
  GraduationCap,
  Loader2,
  Search,
  Shield,
  Wrench,
} from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';
import { api } from '@/lib/api';

interface ArsenalTool {
  id: string;
  category_slug: string;
  slug: string;
  name: string;
  description: string;
  license_name: string;
  open_source: boolean;
  free_tier: boolean;
  supported_os: string[];
  difficulty: string;
  official_url: string;
  docs_url: string | null;
  tutorial_url: string | null;
  tags: string[];
  view_count: number;
}

interface Category {
  id: string;
  slug: string;
  name: string;
}

interface FilterSet {
  categories: Category[];
  licenses: string[];
  os: string[];
  difficulties: string[];
}

interface PageData {
  items: ArsenalTool[];
  total: number;
  page: number;
  total_pages: number;
}

export default function ArsenalPage() {
  const [tools, setTools] = useState<ArsenalTool[]>([]);
  const [filters, setFilters] = useState<FilterSet | null>(null);
  const [search, setSearch] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [category, setCategory] = useState('');
  const [difficulty, setDifficulty] = useState('');
  const [os, setOs] = useState('');
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const t = setTimeout(() => {
      setDebouncedSearch(search);
      setPage(1);
    }, 400);
    return () => clearTimeout(t);
  }, [search]);

  useEffect(() => {
    api
      .get<{ data: FilterSet }>('/cyber-arsenal/filters')
      .then((res) => setFilters(res.data))
      .catch(() => undefined);
  }, []);

  const load = useCallback(() => {
    setLoading(true);
    const params = new URLSearchParams({ page: String(page), page_size: '12' });
    if (debouncedSearch) params.set('search', debouncedSearch);
    if (category) params.set('category', category);
    if (difficulty) params.set('difficulty', difficulty);
    if (os) params.set('os', os);

    api
      .get<{ data: PageData }>(`/cyber-arsenal/tools?${params.toString()}`)
      .then((res) => {
        setTools(res.data.items);
        setTotalPages(res.data.total_pages);
        setError('');
      })
      .catch((e) => setError(e?.message ?? 'Failed to load the arsenal.'))
      .finally(() => setLoading(false));
  }, [page, debouncedSearch, category, difficulty, os]);

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
            &gt; // cyber arsenal · curated defense tooling
          </p>
          <h1 className="flex items-center gap-3 text-3xl font-bold">
            <Wrench className="h-8 w-8 text-cyber-primary" />
            Cyber <span className="glow-text text-cyber-primary">Arsenal</span>
          </h1>
          <p className="mt-2 max-w-3xl text-sm text-cyber-muted">
            Free and open-source security tools curated for learning and defensive operations.
            Every entry is verified and points to its official source.
          </p>
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
              placeholder="search name, tag, description…"
              className="w-full rounded border border-cyber-border bg-cyber-bg py-2 pl-9 pr-3 text-sm text-cyber-foreground outline-none placeholder:text-cyber-muted focus:border-cyber-primary"
            />
          </div>
          <select value={category} onChange={(e) => { setCategory(e.target.value); setPage(1); }} className={selectCls}>
            <option value="">all categories</option>
            {(filters?.categories ?? []).map((c) => (
              <option key={c.slug} value={c.slug}>{c.name}</option>
            ))}
          </select>
          <select value={difficulty} onChange={(e) => { setDifficulty(e.target.value); setPage(1); }} className={selectCls}>
            <option value="">all levels</option>
            {(filters?.difficulties ?? []).map((d) => (
              <option key={d} value={d}>{d}</option>
            ))}
          </select>
          <select value={os} onChange={(e) => { setOs(e.target.value); setPage(1); }} className={selectCls}>
            <option value="">all OS</option>
            {(filters?.os ?? []).map((o) => (
              <option key={o} value={o}>{o}</option>
            ))}
          </select>
        </div>

        {loading ? (
          <div className="flex justify-center py-20">
            <Loader2 className="h-8 w-8 animate-spin text-cyber-primary" />
          </div>
        ) : error ? (
          <p className="rounded border border-red-500/40 bg-red-500/10 p-4 text-center font-mono text-sm text-red-400">
            {error}
          </p>
        ) : tools.length === 0 ? (
          <p className="rounded border border-cyber-border bg-cyber-surface/50 p-10 text-center font-mono text-sm text-cyber-muted">
            no tools match those filters
          </p>
        ) : (
          <>
            <div className="grid gap-5 md:grid-cols-2 lg:grid-cols-3">
              {tools.map((tool) => (
                <div key={tool.id} className="terminal-card flex flex-col p-5">
                  <div className="mb-2 flex items-start justify-between gap-2">
                    <h3 className="font-bold">{tool.name}</h3>
                    <span className="shrink-0 rounded bg-cyber-primary/10 px-2 py-0.5 font-mono text-[10px] uppercase text-cyber-primary">
                      {tool.difficulty}
                    </span>
                  </div>
                  <p className="mb-3 flex-grow text-sm text-cyber-muted">{tool.description}</p>
                  <div className="mb-3 flex flex-wrap gap-1.5">
                    {tool.tags.slice(0, 4).map((tag) => (
                      <span key={tag} className="rounded bg-cyber-surface px-1.5 py-0.5 font-mono text-[10px] text-cyber-secondary">
                        {tag}
                      </span>
                    ))}
                  </div>
                  <div className="mb-3 flex flex-wrap gap-x-4 gap-y-1 border-t border-cyber-border pt-3 text-[11px] text-cyber-muted">
                    <span>License: {tool.license_name}</span>
                    <span>{tool.open_source ? 'Open source' : 'Proprietary'}</span>
                    {tool.free_tier && <span className="text-green-400">Free tier</span>}
                    <span>{(tool.supported_os ?? []).join(', ')}</span>
                  </div>
                  <div className="mt-auto flex items-center gap-2">
                    <a href={tool.official_url} target="_blank" rel="noopener noreferrer" className="terminal-button flex-1 px-3 py-1.5 text-center text-xs">
                      <ExternalLink className="mr-1 inline h-3.5 w-3.5" /> Official
                    </a>
                    {tool.docs_url && (
                      <a href={tool.docs_url} target="_blank" rel="noopener noreferrer" className="terminal-button-ghost px-3 py-1.5 text-xs">
                        <FileText className="h-4 w-4" />
                      </a>
                    )}
                    {tool.tutorial_url && (
                      <a href={tool.tutorial_url} target="_blank" rel="noopener noreferrer" className="terminal-button-ghost px-3 py-1.5 text-xs">
                        <GraduationCap className="h-4 w-4" />
                      </a>
                    )}
                  </div>
                </div>
              ))}
            </div>
            {totalPages > 1 && (
              <div className="mt-8 flex items-center justify-center gap-4">
                <button
                  className="terminal-button-ghost px-4 py-1.5 text-sm disabled:opacity-40"
                  disabled={page <= 1}
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                >
                  ← prev
                </button>
                <span className="font-mono text-sm text-cyber-muted">
                  page {page} / {totalPages}
                </span>
                <button
                  className="terminal-button-ghost px-4 py-1.5 text-sm disabled:opacity-40"
                  disabled={page >= totalPages}
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                >
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
