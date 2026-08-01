'use client';

import Link from 'next/link';
import { BookOpen, Loader2, Search, Shield } from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';
import ResourceCard, { type LibraryItem } from '@/components/ResourceCard';
import { api } from '@/lib/api';

interface LibraryPage {
  items: LibraryItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  has_next: boolean;
  has_prev: boolean;
}

interface LibraryFilters {
  categories: string[];
  resource_types: string[];
  difficulties: string[];
}

export default function LibraryPage() {
  const [items, setItems] = useState<LibraryItem[]>([]);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(0);
  const [filters, setFilters] = useState<LibraryFilters>({ categories: [], resource_types: [], difficulties: [] });
  const [search, setSearch] = useState('');
  const [category, setCategory] = useState('');
  const [resourceType, setResourceType] = useState('');
  const [difficulty, setDifficulty] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    api
      .get<{ data: LibraryFilters }>('/library/filters')
      .then((res) => setFilters(res.data))
      .catch(() => undefined);
  }, []);

  const load = useCallback(() => {
    setLoading(true);
    const params = new URLSearchParams({ page: String(page), page_size: '12' });
    if (search) params.set('search', search);
    if (category) params.set('category', category);
    if (resourceType) params.set('resource_type', resourceType);
    if (difficulty) params.set('difficulty', difficulty);

    api
      .get<{ data: LibraryPage }>(`/library/?${params.toString()}`)
      .then((res) => {
        setItems(res.data.items);
        setTotalPages(res.data.total_pages);
        setError('');
      })
      .catch(() => setError('Failed to load the library — are you logged in?'))
      .finally(() => setLoading(false));
  }, [page, search, category, resourceType, difficulty]);

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
            &gt; // learning library · curated free resources
          </p>
          <h1 className="flex items-center gap-3 text-3xl font-bold">
            <BookOpen className="h-8 w-8 text-cyber-primary" />
            Learning <span className="glow-text text-cyber-primary">Library</span>
          </h1>
          <p className="mt-2 max-w-3xl text-sm text-cyber-muted">
            Courses, labs, articles, and tools from the best free security education providers —
            all in one place. Every resource is free to start and safe to use.
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
              placeholder="search title, tags, description…"
              className="w-full rounded border border-cyber-border bg-cyber-bg py-2 pl-9 pr-3 text-sm text-cyber-foreground outline-none placeholder:text-cyber-muted focus:border-cyber-primary"
            />
          </div>
          <select value={category} onChange={(e) => { setCategory(e.target.value); setPage(1); }} className={selectCls}>
            <option value="">all categories</option>
            {filters.categories.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
          <select value={resourceType} onChange={(e) => { setResourceType(e.target.value); setPage(1); }} className={selectCls}>
            <option value="">all types</option>
            {filters.resource_types.map((t) => (
              <option key={t} value={t}>{t}</option>
            ))}
          </select>
          <select value={difficulty} onChange={(e) => { setDifficulty(e.target.value); setPage(1); }} className={selectCls}>
            <option value="">all levels</option>
            {filters.difficulties.map((d) => (
              <option key={d} value={d}>{d}</option>
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
        ) : items.length === 0 ? (
          <p className="rounded border border-cyber-border bg-cyber-surface/50 p-10 text-center font-mono text-sm text-cyber-muted">
            no resources match those filters
          </p>
        ) : (
          <>
            <div className="grid gap-5 md:grid-cols-2 lg:grid-cols-3">
              {items.map((resource) => (
                <ResourceCard key={resource.id} resource={resource} />
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
