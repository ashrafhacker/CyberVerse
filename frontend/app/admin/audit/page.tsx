'use client';
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { FileSearch, ChevronLeft, ChevronRight } from 'lucide-react';
import { useRequireAuth } from '@/lib/auth';
import { isAdmin } from '@/lib/roles';
import { LoadingState, EmptyState, RetryButton } from '@/components/AdminUI';

export default function AdminAuditPage() {
  const { user } = useRequireAuth();
  const [logs, setLogs] = useState<Array<Record<string, unknown>>>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const perPage = 20;

  const load = useCallback(async () => {
    setLoading(true); setError(null);
    try {
      const url = new URL((process.env.NEXT_PUBLIC_API_URL ?? '/api/v1') + '/admin/audit', typeof window !== 'undefined' ? window.location.origin : 'http://localhost');
      url.searchParams.set('page', String(page));
      url.searchParams.set('limit', String(perPage));
      const res = await fetch(url.toString(), { credentials: 'include', headers: { Accept: 'application/json' } });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const json = await res.json();
      setLogs(json.data ?? []);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to load audit logs');
    } finally {
      setLoading(false);
    }
  }, [page]);

  useEffect(() => { load(); }, [load]);

  const visible = useMemo(() => logs, [logs]);

  if (!user || !isAdmin(user.role)) return <div className="p-8"><h2 className="text-red-400 font-semibold">Access denied</h2></div>;

  return (
    <div>
      <h1 className="text-2xl font-bold mb-2">Audit Logs</h1>
      <p className="text-sm text-zinc-400 mb-4">Sensitive actions are audit-logged. No external release.</p>
      <button onClick={load} className="rounded bg-blue-600 px-3 py-2 text-sm hover:bg-blue-500 mb-4">Refresh</button>
      {loading ? <LoadingState label="Loading audit logs..." /> : error ? <div className="rounded border border-red-900 bg-red-950/20 p-4"><p className="text-sm text-red-300">{error}</p><RetryButton onRetry={load} /></div> : visible.length === 0 ? <EmptyState title="No audit logs" message="No audit entries for this page." /> : (
        <div className="overflow-auto rounded border border-zinc-800">
          <table className="w-full text-sm"><thead className="bg-zinc-900 text-zinc-300"><tr><th className="text-left px-3 py-2">Action</th><th>User</th><th>Time</th></tr></thead>
          <tbody>{visible.map((log, i) => (
            <tr key={i} className="border-t border-zinc-800 hover:bg-zinc-900/40"><td className="px-3 py-2">{String(log.action ?? log.event ?? '-')}</td><td className="px-3 py-2 text-zinc-400">{String(log.user_id ?? log.user_email ?? '-')}</td><td className="px-3 py-2 text-zinc-500">{String(log.created_at ?? log.timestamp ?? '-')}</td></tr>
          ))}</tbody></table>
        </div>
      )}
      <div className="flex gap-2 mt-3"><button onClick={() => setPage(p => Math.max(1, p-1))} disabled={page <= 1} className="rounded bg-zinc-900 border border-zinc-800 px-2 py-1 text-sm"><ChevronLeft className="h-3 w-3" /></button><span className="self-center text-xs text-zinc-400">Page {page}</span><button onClick={() => setPage(p => p+1)} className="rounded bg-zinc-900 border border-zinc-800 px-2 py-1 text-sm"><ChevronRight className="h-3 w-3" /></button></div>
    </div>
  );
}
