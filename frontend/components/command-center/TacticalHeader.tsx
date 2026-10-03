'use client';

import Link from 'next/link';
import { Activity, Radio, RefreshCw, SlidersHorizontal, Wifi } from 'lucide-react';
import { greetingFor } from '@/lib/command-center';
import type { SnapshotStatus } from '@/lib/command-center';

export default function TacticalHeader({
  displayName,
  role,
  status,
  refreshing,
  onRefresh,
  missionCount,
  onOpenConfig,
}: {
  displayName: string;
  role: string;
  status: SnapshotStatus;
  refreshing: boolean;
  onRefresh: () => void;
  missionCount: number;
  onOpenConfig: () => void;
}) {
  return (
    <section className="relative overflow-hidden rounded-2xl border border-cyber-border/60 bg-gradient-to-r from-cyber-surface via-cyber-surface/70 to-cyber-surface p-5 shadow-2xl sm:p-6">
      <div className="pointer-events-none absolute -right-24 -top-24 h-96 w-96 rounded-full bg-cyber-primary/10 blur-3xl" />
      <div className="pointer-events-none absolute -bottom-24 -left-24 h-96 w-96 rounded-full bg-cyber-secondary/10 blur-3xl" />
      <div className="absolute inset-y-0 left-0 w-1.5 bg-gradient-to-b from-cyber-primary via-cyber-secondary to-transparent" />

      <div className="relative z-10 flex flex-col gap-5 xl:flex-row xl:items-end xl:justify-between">
        <div className="flex flex-col gap-2">
          <div className="flex flex-wrap items-center gap-2">
            <span className="inline-flex items-center gap-1.5 rounded-full border border-cyber-primary/30 bg-cyber-bg/60 px-2.5 py-1 font-mono text-[10px] font-bold uppercase tracking-wider text-cyber-primary">
              <span
                className={`h-2 w-2 rounded-full ${status === 'live' ? 'animate-pulse bg-cyber-success' : status === 'loading' ? 'animate-pulse bg-cyber-warning' : 'bg-cyber-warning'}`}
              />
              {status === 'live' ? 'Live telemetry' : status === 'loading' ? 'Syncing matrix' : 'Degraded feed'}
            </span>
            <span className="font-mono text-[10px] uppercase tracking-wider text-cyber-muted">
              operator // {role}
            </span>
          </div>

          <h1 className="text-2xl font-bold tracking-tight text-cyber-primary sm:text-3xl">
            {greetingFor(new Date())}, {displayName}
          </h1>

          <p className="flex items-center gap-2 text-sm text-cyber-muted">
            <Radio className="h-4 w-4 shrink-0 text-cyber-primary" />
            {status === 'degraded'
              ? 'Backend unreachable — panels are showing simulation placeholders.'
              : `Threat telemetry is active. ${missionCount} tactical objective${missionCount === 1 ? '' : 's'} tracked on this deck.`}
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={onRefresh}
            className="flex items-center gap-2 rounded-xl border border-cyber-border/60 bg-cyber-surface px-3.5 py-2 font-mono text-[11px] uppercase tracking-wider text-cyber-text shadow-md transition-all hover:border-cyber-primary/50"
          >
            <RefreshCw className={`h-4 w-4 text-cyber-primary ${refreshing ? 'animate-spin' : ''}`} />
            Telemetry stream
          </button>
          <button
            type="button"
            onClick={onOpenConfig}
            className="flex items-center gap-2 rounded-xl border border-cyber-border/60 bg-cyber-surface px-3.5 py-2 font-mono text-[11px] uppercase tracking-wider text-cyber-text shadow-md transition-all hover:border-cyber-primary/50"
          >
            <SlidersHorizontal className="h-4 w-4 text-cyber-secondary" />
            Deck config
          </button>
          <div className="flex items-center gap-2 rounded-xl border border-cyber-primary/30 bg-cyber-primary/10 px-3.5 py-2 font-mono text-[11px] text-cyber-primary">
            <Wifi className="h-4 w-4 animate-pulse" />
            Pod v-pod-88 : ready
          </div>
        </div>
      </div>
    </section>
  );
}

export function StatusStrip({
  status,
  lastSyncedAt,
  onOpenConfig,
}: {
  status: SnapshotStatus;
  lastSyncedAt: number | null;
  onOpenConfig: () => void;
}) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-cyber-border/60 bg-cyber-surface/40 px-4 py-2.5 font-mono text-[10px] uppercase tracking-wider text-cyber-muted">
      <span className="flex items-center gap-2">
        <Activity className="h-3.5 w-3.5 text-cyber-primary" />
        {status === 'live' ? 'Matrix nominal' : status === 'loading' ? 'Establishing link' : 'Simulation placeholders active'}
      </span>
      <span className="flex items-center gap-3">
        {lastSyncedAt && <span>Synced {new Date(lastSyncedAt).toLocaleTimeString('en-US')}</span>}
        <Link href="/profile" className="text-cyber-primary hover:underline">
          Operator profile
        </Link>
        <button type="button" onClick={onOpenConfig} className="text-cyber-primary hover:underline">
          Configure
        </button>
      </span>
    </div>
  );
}