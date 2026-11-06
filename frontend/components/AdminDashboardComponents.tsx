/**
 * Phase C platform dashboard components — real endpoint integration.
 * Each component hits a real backend endpoint and shows loading/error/empty/retry.
 */
import React from 'react';
import { Activity, ShieldAlert, Server, ShieldCheck, Database, BarChart3, LockKeyhole } from 'lucide-react';
import { LoadingState, EmptyState, RetryButton } from './AdminUI';

export function AlertFeed() {
  return <StatCard icon={Activity} title="Security Alerts" endpoint="/soc/alerts" />;
}

export function ThreatMap() {
  return <StatCard icon={ShieldAlert} title="Threat Indicators" endpoint="/threat-intel/indicators" />;
}

export function VulnerabilityChart() {
  return <StatCard icon={ShieldCheck} title="CVE Exposure" endpoint="/threat-intel/cves" />;
}

export function ToolStatusGrid() {
  return <StatCard icon={Server} title="Arsenal Tools" endpoint="/arsenal/tools" />;
}

export function ComplianceOverview() {
  return <StatCard icon={LockKeyhole} title="Compliance Score" endpoint="/analytics/compliance" />;
}

export function AdminStatCard({ icon: Icon, title, endpoint }: { icon: typeof Activity; title: string; endpoint: string }) {
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [data, setData] = React.useState<Record<string, unknown> | null>(null);

  const load = React.useCallback(async () => {
    setLoading(true); setError(null);
    try {
      const res = await fetch((process.env.NEXT_PUBLIC_API_URL ?? '/api/v1') + endpoint, { credentials: 'include', headers: { 'Accept': 'application/json' } });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const json = await res.json();
      setData(json.data ?? json);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }, [endpoint]);

  React.useEffect(() => { load(); }, [load]);

  if (loading) return <LoadingState label={`Loading ${title}...`} />;
  if (error) return <div className="rounded border border-red-900 bg-red-950/20 p-4"><p className="text-sm text-red-300">{title}: {error}</p><RetryButton onRetry={load} /></div>;
  if (!data || (Array.isArray(data) && data.length === 0)) return <EmptyState title={`${title} — No data`} message="No records returned from backend." />;

  return (
    <div className="rounded border border-zinc-800 bg-zinc-900/40 p-4 hover:border-zinc-700 transition-colors">
      <div className="flex items-center gap-3 mb-3">
        <div className="rounded-full bg-blue-900/30 p-2"><Icon className="h-4 w-4 text-blue-400" /></div>
        <h4 className="text-sm font-medium text-zinc-200">{title}</h4>
      </div>
      <pre className="text-xs text-zinc-500 overflow-auto max-h-48">{JSON.stringify(data, null, 2)}</pre>
    </div>
  );
}

function StatCard({ icon: Icon, title, endpoint }: { icon: typeof Activity; title: string; endpoint: string }) {
  return <AdminStatCard icon={Icon} title={title} endpoint={endpoint} />;
}
