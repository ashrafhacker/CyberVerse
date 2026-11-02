'use client';
import React, { useCallback, useEffect, useState } from 'react';
import { Wrench, ChevronLeft, ChevronRight } from 'lucide-react';
import { useRequireAuth } from '@/lib/auth';
import { isAdmin } from '@/lib/roles';
import { LoadingState, EmptyState, RetryButton } from '@/components/AdminUI';

export default function AdminFlagsPage() {
  const { user } = useRequireAuth();
  const [flags, setFlags] = useState<Array<Record<string, unknown>>>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const load = useCallback(async () => {
    setLoading(true); setError(null);
    try {
      const url = new URL((process.env.NEXT_PUBLIC_API_URL ?? '/api/v1') + '/admin/feature-flags', typeof window !== 'undefined' ? window.location.origin : 'http://localhost');
      url.searchParams.set('page', String(page));
      const res = await fetch(url.toString(), { credentials: 'include', headers: { Accept: 'application/json' } });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const json = await res.json();
      setFlags(json.data ?? []);
    } catch (e: unknown) { setError(e instanceof Error ? e.message : 'Failed'); } finally { setLoading(false); }
  }, [page]);
  useEffect(() => { load(); }, [load]);
  if (!user || !isAdmin(user.role)) return <div className="p-8"><h2 className="text-red-400 font-semibold">Access denied</h2></div>;
  return (
    <div>
      <h1 className="text-2xl font-bold mb-2">Feature Flags</h1>
      <button onClick={load} className="rounded bg-blue-600 px-3 py-2 text-sm hover:bg-blue-500 mb-4">Refresh</button>
      {loading ? <LoadingState label="Loading flags..." /> : error ? <div className="rounded border border-red-900 bg-red-950/20 p-4"><p className="text-sm text-red-300">{error}</p><RetryButton onRetry={load} /></div> : flags.length === 0 ? <EmptyState title="No flags" message="No feature flags configured." /> : (
        <div className="overflow-auto rounded border border-zinc-800"><table className="w-full text-sm"><thead className="bg-zinc-900 text-zinc-300"><tr><th className="text-left px-3 py-2">Name</th><th>State</th></tr></thead>
        <tbody>{flags.map((f, i) => (<tr key={i} className="border-t border-zinc-800"><td className="px-3 py-2">{String(f.name ?? f.key ?? '-')}</td><td className="px-3 py-2">{String(f.enabled ?? f.state ?? '-')}</td></tr>))}</tbody></table></div>
      )}
      <div className="flex gap-2 mt-3"><button onClick={() => setPage(p => Math.max(1, p-1))} disabled={page <= 1} className="rounded bg-zinc-900 border border-zinc-800 px-2 py-1 text-sm"><ChevronLeft className="h-3 w-3" /></button><span className="self-center text-xs text-zinc-400">Page {page}</span><button onClick={() => setPage(p => p+1)} className="rounded bg-zinc-900 border border-zinc-800 px-2 py-1 text-sm"><ChevronRight className="h-3 w-3" /></button></div>
    </div>
  );
}
