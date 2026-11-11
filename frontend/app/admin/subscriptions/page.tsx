'use client';
import React, { useCallback, useEffect, useState } from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { useRequireAuth } from '@/lib/auth';
import { isAdmin } from '@/lib/roles';
import { api } from '@/lib/api';
import { LoadingState, EmptyState, RetryButton } from '@/components/AdminUI';

interface SubRow {
  id: string; user_id: string; user_email: string | null; plan_name: string | null;
  status: string; current_period_start: string | null; current_period_end: string | null;
  created_at: string;
}

const STATUS_STYLES: Record<string, string> = {
  active: 'bg-emerald-900/30 text-emerald-300',
  trialing: 'bg-sky-900/30 text-sky-300',
  past_due: 'bg-amber-900/30 text-amber-300',
  canceled: 'bg-zinc-800 text-zinc-400',
  cancelled: 'bg-zinc-800 text-zinc-400',
  expired: 'bg-rose-900/30 text-rose-300',
};

function fmtWhen(iso?: string | null) {
  if (!iso) return '—';
  try { return new Date(iso).toLocaleString(); } catch { return iso; }
}

export default function AdminSubscriptionsPage() {
  const { user } = useRequireAuth();
  const [subs, setSubs] = useState<SubRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const load = useCallback(async () => {
    setLoading(true); setError(null);
    try {
      const json = await api.get<{ data: SubRow[] }>('/admin/subscriptions', { cache: 'no-store' });
      setSubs(json?.data ?? []);
    } catch (e: unknown) { setError(e instanceof Error ? e.message : 'Failed'); } finally { setLoading(false); }
  }, []);
  useEffect(() => { load(); }, [load]);
  if (!user || !isAdmin(user.role)) return <div className="p-8"><h2 className="text-red-400 font-semibold">Access denied</h2></div>;
  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-2xl font-bold">Subscriptions</h1>
        <button onClick={load} className="rounded bg-blue-600 px-3 py-2 text-sm hover:bg-blue-500">Refresh</button>
      </div>
      {loading ? <LoadingState label="Loading subscriptions..." /> : error ? <div className="rounded border border-red-900 bg-red-950/20 p-4"><p className="text-sm text-red-300">{error}</p><RetryButton onRetry={load} /></div> : subs.length === 0 ? <EmptyState title="No subscriptions" message="Subscriptions appear here once users subscribe." /> : (
        <div className="overflow-auto rounded border border-zinc-800"><table className="w-full text-sm"><thead className="bg-zinc-900 text-zinc-300"><tr><th className="text-left px-3 py-2">User</th><th>Plan</th><th>Status</th><th>Period</th></tr></thead>
        <tbody>{subs.map((s) => (
          <tr key={s.id} className="border-t border-zinc-800">
            <td className="px-3 py-2">{s.user_email || s.user_id}</td>
            <td className="px-3 py-2">{s.plan_name || '—'}</td>
            <td className="px-3 py-2"><span className={`text-xs rounded px-1 ${STATUS_STYLES[s.status] ?? 'bg-zinc-800 text-zinc-300'}`}>{s.status}</span></td>
            <td className="px-3 py-2 text-xs text-zinc-400">{fmtWhen(s.current_period_start)} → {fmtWhen(s.current_period_end)}</td>
          </tr>
        ))}</tbody></table></div>
      )}
      <div className="flex gap-2 mt-3"><span className="self-center text-xs text-zinc-400">Most recent 100 subscriptions</span></div>
    </div>
  );
}
