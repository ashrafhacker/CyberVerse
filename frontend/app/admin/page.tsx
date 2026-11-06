'use client';
import React, { useCallback, useEffect, useState } from 'react';
import { ShieldCheck, Activity, Database } from 'lucide-react';
import { useRequireAuth } from '@/lib/auth';
import { isAdmin } from '@/lib/roles';
import { LoadingState, EmptyState, RetryButton } from '@/components/AdminUI';
import { AlertFeed, ThreatMap, VulnerabilityChart, ToolStatusGrid, ComplianceOverview } from '@/components/AdminDashboardComponents';

export default function AdminOverviewPage() {
  const { user } = useRequireAuth();
  const [overview, setOverview] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true); setError(null);
    try {
      const url = (process.env.NEXT_PUBLIC_API_URL ?? '/api/v1') + '/admin/overview';
      const res = await fetch(url, { credentials: 'include', headers: { Accept: 'application/json' } });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const json = await res.json();
      setOverview(json.data ?? json);
    } catch (e: unknown) { setError(e instanceof Error ? e.message : 'Failed'); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);
  if (!user || !isAdmin(user.role)) return <div className="p-8"><h2 className="text-red-400 font-semibold">Access denied</h2></div>;

  return (
    <div>
      <h1 className="text-2xl font-bold mb-2">Overview</h1>
      <p className="text-sm text-zinc-400 mb-4">Real-time platform health from verified backend endpoints.</p>
      <button onClick={load} className="rounded bg-blue-600 px-3 py-2 text-sm hover:bg-blue-500 mb-4">Refresh</button>
      {loading ? <LoadingState label="Loading overview..." /> : error ? <div className="rounded border border-red-900 bg-red-950/20 p-4"><p className="text-sm text-red-300">{error}</p><RetryButton onRetry={load} /></div> : (
        <div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
            <AlertFeed /> <ThreatMap /> <VulnerabilityChart /> <ToolStatusGrid />
          </div>
          <ComplianceOverview />
        </div>
      )}
    </div>
  );
}
