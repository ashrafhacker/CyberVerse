'use client';

import Link from 'next/link';
import {
  Activity,
  Loader2,
  Plus,
  Radio,
  Shield,
  ShieldAlert,
} from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';
import { api } from '@/lib/api';

interface Alert {
  id: string;
  title: string;
  description: string;
  severity: string;
  confidence: number;
  asset: string | null;
  source: string | null;
  status: string;
  mitre_technique_id: string | null;
  timestamp: string;
}

interface Incident {
  id: string;
  case_number: string;
  title: string;
  description: string;
  severity: string;
  priority: string;
  status: string;
  mitre_mapping: string[];
  affected_assets: string[];
  root_cause: string | null;
  containment_actions: string[];
  remediation_plan: string | null;
  opened_at: string;
  updated_at: string;
  alert_count: number;
}

interface PageData<T> {
  items: T[];
  total: number;
  page: number;
  total_pages: number;
}

const STATUS_FLOW = ['new', 'investigating', 'contained', 'recovering', 'resolved', 'closed'];

const SEV_COLORS: Record<string, string> = {
  critical: 'bg-red-500/20 text-red-400',
  high: 'bg-orange-500/20 text-orange-400',
  medium: 'bg-amber-500/20 text-amber-400',
  low: 'bg-green-500/20 text-green-400',
};

const STATUS_COLORS: Record<string, string> = {
  new: 'bg-cyber-surface text-cyber-muted',
  investigating: 'bg-blue-500/20 text-blue-400',
  contained: 'bg-amber-500/20 text-amber-400',
  recovering: 'bg-orange-500/20 text-orange-400',
  resolved: 'bg-green-500/20 text-green-400',
  closed: 'bg-cyber-surface text-cyber-muted',
};

export default function SocPage() {
  const [tab, setTab] = useState<'alerts' | 'incidents'>('alerts');
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [alertsPage, setAlertsPage] = useState(1);
  const [incidentsPage, setIncidentsPage] = useState(1);
  const [alertsTotal, setAlertsTotal] = useState(1);
  const [incidentsTotal, setIncidentsTotal] = useState(1);
  const [severity, setSeverity] = useState('');
  const [status, setStatus] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const loadAlerts = useCallback(() => {
    const params = new URLSearchParams({ page: String(alertsPage), page_size: '12' });
    if (severity) params.set('severity', severity);
    if (status) params.set('status', status);
    return api
      .get<{ data: PageData<Alert> }>(`/soc/alerts?${params.toString()}`)
      .then((res) => {
        setAlerts(res.data.items);
        setAlertsTotal(res.data.total_pages);
        setError('');
      })
      .catch(() => setError('Failed to load alerts.'));
  }, [alertsPage, severity, status]);

  const loadIncidents = useCallback(() => {
    return api
      .get<{ data: PageData<Incident> }>(`/soc/incidents?page=${incidentsPage}&page_size=10`)
      .then((res) => {
        setIncidents(res.data.items);
        setIncidentsTotal(res.data.total_pages);
        setError('');
      })
      .catch(() => setError('Failed to load incidents.'));
  }, [incidentsPage]);

  useEffect(() => {
    setLoading(true);
    (tab === 'alerts' ? loadAlerts() : loadIncidents()).finally(() => setLoading(false));
  }, [tab, loadAlerts, loadIncidents]);

  const severityCls = (s: string) => SEV_COLORS[s] ?? SEV_COLORS.medium;
  const statusCls = (s: string) => STATUS_COLORS[s] ?? STATUS_COLORS.new;
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
            &gt; // security operations center · alert triage & incident response
          </p>
          <h1 className="flex items-center gap-3 text-3xl font-bold">
            <Radio className="h-8 w-8 text-cyber-primary" />
            SOC <span className="glow-text text-cyber-primary">Simulator</span>
          </h1>
          <p className="mt-2 max-w-3xl text-sm text-cyber-muted">
            Triage simulated alerts, create incidents, and drive them through the full
            response lifecycle alongside the Neo analysis engine.
          </p>
        </div>

        <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
          <div className="flex rounded border border-cyber-border overflow-hidden">
            <button
              onClick={() => setTab('alerts')}
              className={`flex items-center gap-2 px-4 py-2 text-sm ${tab === 'alerts' ? 'bg-cyber-primary/15 text-cyber-primary' : 'text-cyber-muted hover:text-cyber-primary'}`}
            >
              <Activity className="h-4 w-4" /> Alert Queue
            </button>
            <button
              onClick={() => setTab('incidents')}
              className={`flex items-center gap-2 px-4 py-2 text-sm ${tab === 'incidents' ? 'bg-cyber-primary/15 text-cyber-primary' : 'text-cyber-muted hover:text-cyber-primary'}`}
            >
              <ShieldAlert className="h-4 w-4" /> Incidents
            </button>
          </div>
          <button
            onClick={() => setTab('incidents')}
            className="terminal-button flex items-center gap-2 px-4 py-2 text-sm"
          >
            <Plus className="h-4 w-4" /> New Incident
          </button>
        </div>

        {tab === 'alerts' && (
          <div className="mb-6 flex flex-wrap items-center gap-3">
            <select value={severity} onChange={(e) => { setSeverity(e.target.value); setAlertsPage(1); }} className={selectCls}>
              <option value="">all severities</option>
              <option value="critical">critical</option>
              <option value="high">high</option>
              <option value="medium">medium</option>
              <option value="low">low</option>
            </select>
            <select value={status} onChange={(e) => { setStatus(e.target.value); setAlertsPage(1); }} className={selectCls}>
              <option value="">all statuses</option>
              {['new', 'assigned', 'investigating', 'closed'].map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
          </div>
        )}

        {loading ? (
          <div className="flex justify-center py-20">
            <Loader2 className="h-8 w-8 animate-spin text-cyber-primary" />
          </div>
        ) : error ? (
          <p className="rounded border border-red-500/40 bg-red-500/10 p-4 text-center font-mono text-sm text-red-400">{error}</p>
        ) : tab === 'alerts' ? (
          <div className="space-y-3">
            {alerts.length === 0 ? (
              <p className="rounded border border-cyber-border bg-cyber-surface/50 p-10 text-center font-mono text-sm text-cyber-muted">
                no alerts match those filters
              </p>
            ) : (
              alerts.map((a) => (
                <div key={a.id} className="terminal-card p-4">
                  <div className="mb-1 flex flex-wrap items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <span className={`rounded px-2 py-0.5 font-mono text-xs ${severityCls(a.severity)}`}>{a.severity}</span>
                      <span className="font-semibold">{a.title}</span>
                    </div>
                    <span className={`rounded px-2 py-0.5 font-mono text-xs ${statusCls(a.status)}`}>{a.status}</span>
                  </div>
                  <p className="mb-2 text-sm text-cyber-muted">{a.description}</p>
                  <div className="flex flex-wrap gap-x-4 gap-y-1 font-mono text-[11px] text-cyber-muted">
                    <span>confidence {a.confidence}%</span>
                    {a.asset && <span>asset: {a.asset}</span>}
                    {a.mitre_technique_id && <span>MITRE: {a.mitre_technique_id}</span>}
                    {a.source && <span>source: {a.source}</span>}
                    <span>{new Date(a.timestamp).toLocaleString()}</span>
                  </div>
                </div>
              ))
            )}
            {alertsTotal > 1 && (
              <div className="flex justify-center gap-4 pt-4">
                <button className="terminal-button-ghost px-4 py-1.5 text-sm disabled:opacity-40" disabled={alertsPage <= 1} onClick={() => setAlertsPage((p) => Math.max(1, p - 1))}>
                  ← prev
                </button>
                <button className="terminal-button-ghost px-4 py-1.5 text-sm disabled:opacity-40" disabled={alertsPage >= alertsTotal} onClick={() => setAlertsPage((p) => Math.min(alertsTotal, p + 1))}>
                  next →
                </button>
              </div>
            )}
          </div>
        ) : (
          <div className="space-y-3">
            {incidents.length === 0 ? (
              <p className="rounded border border-cyber-border bg-cyber-surface/50 p-10 text-center font-mono text-sm text-cyber-muted">
                no incidents — open one from the alert queue
              </p>
            ) : (
              incidents.map((inc) => (
                <div key={inc.id} className="terminal-card p-4">
                  <div className="mb-1 flex flex-wrap items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs text-cyber-secondary">{inc.case_number}</span>
                      <span className="font-semibold">{inc.title}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className={`rounded px-2 py-0.5 font-mono text-xs ${severityCls(inc.severity)}`}>{inc.severity}</span>
                      <span className={`rounded px-2 py-0.5 font-mono text-xs ${statusCls(inc.status)}`}>{inc.status}</span>
                    </div>
                  </div>
                  <p className="mb-2 text-sm text-cyber-muted">{inc.description}</p>
                  <div className="flex flex-wrap items-center gap-2">
                    <label className="font-mono text-[11px] text-cyber-muted">Advance status:</label>
                    <select
                      className={selectCls + ' py-1 text-xs'}
                      defaultValue=""
                      onChange={(e) => {
                        if (!e.target.value) return;
                        api
                          .patch<{ data: Incident }>(`/soc/incidents/${inc.id}`, { status: e.target.value })
                          .then(() => loadIncidents())
                          .catch(() => undefined);
                      }}
                    >
                      <option value="">—</option>
                      {STATUS_FLOW.map((s) => (
                        <option key={s} value={s} disabled={s === inc.status}>{s}</option>
                      ))}
                    </select>
                    <span className="font-mono text-[11px] text-cyber-muted">{inc.alert_count} alerts · {inc.mitre_mapping.length} MITRE</span>
                  </div>
                </div>
              ))
            )}
            {incidentsTotal > 1 && (
              <div className="flex justify-center gap-4 pt-4">
                <button className="terminal-button-ghost px-4 py-1.5 text-sm disabled:opacity-40" disabled={incidentsPage <= 1} onClick={() => setIncidentsPage((p) => Math.max(1, p - 1))}>
                  ← prev
                </button>
                <button className="terminal-button-ghost px-4 py-1.5 text-sm disabled:opacity-40" disabled={incidentsPage >= incidentsTotal} onClick={() => setIncidentsPage((p) => Math.min(incidentsTotal, p + 1))}>
                  next →
                </button>
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
