'use client';
import React, { useCallback, useEffect, useState } from 'react';
import { DollarSign, CreditCard, RefreshCcw } from 'lucide-react';
import { useRequireAuth } from '@/lib/auth';
import { isAdmin } from '@/lib/roles';
import { api } from '@/lib/api';
import { LoadingState, EmptyState, RetryButton } from '@/components/AdminUI';

interface PaymentRow {
  id: string; user_id: string | null; user_email: string | null;
  payment_intent_id: string | null; status: string; amount: number; currency: string;
  payment_method: string; provider: string; description: string | null;
  failure_reason: string | null; paid_at: string | null; refunded_at: string | null;
  created_at: string;
}

interface PaymentsPayload {
  stats: { total: number; by_status: Record<string, number>; gross_completed: number; refunded: number; currency: string };
  payments: PaymentRow[];
}

function fmtMoney(amount: number, currency: string) {
  try { return new Intl.NumberFormat('en-US', { style: 'currency', currency }).format(amount); } catch { return `${currency} ${amount}`; }
}
function fmtWhen(iso?: string | null) {
  if (!iso) return '—';
  try { return new Date(iso).toLocaleString(); } catch { return iso; }
}

const STATUS_STYLES: Record<string, string> = {
  completed: 'bg-emerald-900/30 text-emerald-300',
  pending: 'bg-amber-900/30 text-amber-300',
  failed: 'bg-rose-900/30 text-rose-300',
  refunded: 'bg-violet-900/30 text-violet-300',
  cancelled: 'bg-zinc-800 text-zinc-400',
};

export default function AdminPaymentsPage() {
  const { user } = useRequireAuth();
  const [payload, setPayload] = useState<PaymentsPayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true); setError(null);
    try {
      const json = await api.get<{ data: PaymentsPayload }>('/admin/payments', { cache: 'no-store' });
      setPayload(json?.data ?? null);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to load payments');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  if (!user || !isAdmin(user.role)) return <div className="p-8"><h2 className="text-red-400 font-semibold">Access denied</h2></div>;

  const stats = payload?.stats;
  const currency = stats?.currency ?? 'USD';

  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <h1 className="text-2xl font-bold">Payments</h1>
        <button onClick={load} className="rounded bg-blue-600 px-3 py-2 text-sm hover:bg-blue-500 flex items-center gap-1"><RefreshCcw className="h-3.5 w-3.5" /> Refresh</button>
      </div>
      {loading ? <LoadingState /> : error ? <div className="rounded border border-red-900 bg-red-950/20 p-4"><p className="text-sm text-red-300">{error}</p><RetryButton onRetry={load} /></div> : (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-5">
            <div className="rounded border border-zinc-800 bg-zinc-900/60 p-4">
              <div className="flex items-center gap-2 text-xs text-zinc-400"><CreditCard className="h-4 w-4" /> Total payments</div>
              <div className="mt-1 text-2xl font-bold">{stats?.total ?? 0}</div>
            </div>
            <div className="rounded border border-zinc-800 bg-zinc-900/60 p-4">
              <div className="flex items-center gap-2 text-xs text-zinc-400"><DollarSign className="h-4 w-4" /> Revenue (completed)</div>
              <div className="mt-1 text-2xl font-bold text-emerald-300">{fmtMoney(stats?.gross_completed ?? 0, currency)}</div>
            </div>
            <div className="rounded border border-zinc-800 bg-zinc-900/60 p-4">
              <div className="flex items-center gap-2 text-xs text-zinc-400"><RefreshCcw className="h-4 w-4" /> Refunded</div>
              <div className="mt-1 text-2xl font-bold text-violet-300">{fmtMoney(stats?.refunded ?? 0, currency)}</div>
            </div>
            <div className="rounded border border-zinc-800 bg-zinc-900/60 p-4">
              <div className="flex items-center gap-2 text-xs text-zinc-400"><CreditCard className="h-4 w-4" /> By status</div>
              <div className="mt-1 flex flex-wrap gap-1">
                {Object.entries(stats?.by_status ?? {}).length === 0 && <span className="text-sm text-zinc-500">—</span>}
                {Object.entries(stats?.by_status ?? {}).map(([st, n]) => (
                  <span key={st} className={`text-xs rounded px-1.5 py-0.5 ${STATUS_STYLES[st] ?? 'bg-zinc-800 text-zinc-300'}`}>{st}: {n}</span>
                ))}
              </div>
            </div>
          </div>
          {(payload?.payments?.length ?? 0) === 0 ? (
            <EmptyState title="No payments yet" message="Payments appear here as soon as users subscribe through checkout." />
          ) : (
            <div className="overflow-auto rounded border border-zinc-800">
              <table className="w-full text-sm"><thead className="bg-zinc-900 text-zinc-300"><tr><th className="text-left px-3 py-2">User</th><th>Amount</th><th>Status</th><th>Method</th><th>Paid at</th><th>Created</th></tr></thead>
              <tbody>
                {payload!.payments.map((p) => (
                  <tr key={p.id} className="border-t border-zinc-800 hover:bg-zinc-900/40">
                    <td className="px-3 py-2">{p.user_email || p.user_id || '—'}</td>
                    <td className="px-3 py-2 font-medium">{fmtMoney(p.amount, p.currency)}</td>
                    <td className="px-3 py-2"><span className={`text-xs rounded px-1 ${STATUS_STYLES[p.status] ?? 'bg-zinc-800 text-zinc-300'}`}>{p.status}</span>{p.failure_reason ? <div className="text-xs text-rose-400">{p.failure_reason}</div> : null}</td>
                    <td className="px-3 py-2 text-zinc-400 text-xs">{p.payment_method} · {p.provider}</td>
                    <td className="px-3 py-2 text-xs text-zinc-400">{fmtWhen(p.paid_at)}</td>
                    <td className="px-3 py-2 text-xs text-zinc-500">{fmtWhen(p.created_at)}</td>
                  </tr>
                ))}
              </tbody></table>
            </div>
          )}
        </>
      )}
    </div>
  );
}
