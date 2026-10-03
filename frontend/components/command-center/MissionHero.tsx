'use client';

import Link from 'next/link';
import {
  BadgeCheck,
  CheckCircle2,
  FolderOpen,
  Loader2,
  Play,
  Radio,
  RotateCw,
  Terminal,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import type { CCMission } from '@/lib/command-center';

export default function MissionHero({
  mission,
  labHref,
  isMock,
}: {
  mission: CCMission;
  labHref: string;
  isMock: boolean;
}) {
  const metRatio = mission.objectivesTotal === 0 ? 0 : mission.objectivesMet / mission.objectivesTotal;

  return (
    <section className="relative flex flex-col gap-5 overflow-hidden rounded-2xl border border-cyber-border/60 bg-cyber-surface shadow-2xl">
      <div className="absolute inset-x-0 top-0 h-1.5 bg-gradient-to-r from-cyber-primary via-cyber-secondary to-cyber-border" />

      <div className="flex flex-wrap items-center justify-between gap-3 pt-5">
        <div className="flex flex-wrap items-center gap-2">
          <span className="rounded-full border border-cyber-border/60 bg-cyber-bg/60 px-3 py-1 font-mono text-[10px] font-bold uppercase tracking-wider text-cyber-primary">
            Tactical Ops // Priority-1
          </span>
          <span className="rounded-full bg-cyber-border/60 px-3 py-1 font-mono text-[10px] text-cyber-muted">
            {mission.difficulty}
          </span>
          {isMock && (
            <span className="rounded-full border border-cyber-warning/40 bg-cyber-warning/10 px-3 py-1 font-mono text-[10px] uppercase tracking-wider text-cyber-warning">
              Simulation placeholder
            </span>
          )}
        </div>

        <div className="inline-flex items-center gap-2 rounded-full border border-cyber-primary/30 bg-cyber-primary/10 px-3 py-1.5 font-mono text-[10px] font-semibold text-cyber-primary">
          <span className="h-2 w-2 animate-pulse rounded-full bg-cyber-primary" />
          {mission.status === 'completed'
            ? 'Mission complete'
            : `${mission.objectivesMet}/${mission.objectivesTotal} objectives met`}
        </div>
      </div>

      <div className="grid grid-cols-1 gap-5 px-5 md:grid-cols-3">
        <div className="flex flex-col justify-between gap-4 md:col-span-2">
          <div>
            <h2 className="text-xl font-bold tracking-tight text-cyber-primary sm:text-2xl">{mission.name}</h2>
            <p className="mt-2 text-sm leading-relaxed text-cyber-muted">{mission.brief}</p>
          </div>

          <div className="flex items-center gap-3 rounded-xl border border-cyber-border/60 bg-cyber-bg/60 p-3.5">
            <BadgeCheck className="h-6 w-6 shrink-0 text-cyber-secondary" />
            <div className="flex min-w-0 flex-col">
              <span className="font-mono text-[10px] uppercase tracking-wider text-cyber-muted">Mission bounty</span>
              <span className="truncate font-mono text-sm font-bold text-cyber-primary">
                +{mission.xpReward} XP • {mission.estimatedMinutes} min estimated
              </span>
            </div>
          </div>
        </div>

        <NodeTopology breached={metRatio < 1 && mission.status !== 'completed'} />
      </div>

      <div className="flex flex-col gap-2 px-5">
        <span className="font-mono text-[10px] uppercase tracking-wider text-cyber-muted">Mission objectives</span>
        <div className="space-y-2">
          {mission.objectives.length === 0 && (
            <p className="rounded-xl border border-cyber-border/60 bg-cyber-bg/40 px-3.5 py-3 text-sm text-cyber-muted">
              No objectives published for this mission yet.
            </p>
          )}
          {mission.objectives.map((objective, i) => (
            <div
              key={objective.id}
              className={cn(
                'flex flex-wrap items-center justify-between gap-3 rounded-xl border px-3.5 py-3 transition-colors',
                objective.state === 'active'
                  ? 'border-cyber-primary/40 bg-cyber-primary/10 shadow-sm'
                  : 'border-cyber-border/50 bg-cyber-bg/40 hover:border-cyber-border',
              )}
            >
              <div className="flex min-w-0 items-center gap-3">
                {objective.state === 'completed' ? (
                  <CheckCircle2 className="h-5 w-5 shrink-0 text-cyber-success" />
                ) : objective.state === 'active' ? (
                  <RotateCw className="h-5 w-5 shrink-0 animate-spin text-cyber-primary" />
                ) : (
                  <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full border border-cyber-border font-mono text-[10px] text-cyber-muted">
                    {i + 1}
                  </span>
                )}
                <span className={cn('min-w-0 text-sm', objective.state === 'active' && 'font-medium text-cyber-primary')}>
                  {i + 1}. {objective.name}
                </span>
              </div>

              <span
                className={cn(
                  'shrink-0 rounded-lg border px-2.5 py-1 font-mono text-[10px] uppercase tracking-wider',
                  objective.state === 'completed' && 'border-cyber-success/30 bg-cyber-success/10 text-cyber-success',
                  objective.state === 'active' && 'border-cyber-primary/40 bg-cyber-primary/15 font-bold text-cyber-primary',
                  objective.state === 'pending' && 'border-cyber-border/60 bg-cyber-bg text-cyber-muted',
                )}
              >
                {objective.state === 'completed' ? `+${objective.xpReward} XP` : objective.state === 'active' ? 'Active' : 'Pending'}
              </span>
            </div>
          ))}
        </div>
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3 px-5 pb-5 pt-1">
        <div className="flex flex-wrap items-center gap-2">
          <Link
            href={labHref}
            className="flex items-center gap-2 rounded-xl bg-gradient-to-r from-cyber-primary to-cyber-secondary px-5 py-3 font-mono text-xs font-bold uppercase tracking-wider text-cyber-bg shadow-lg transition-transform active:scale-95"
          >
            <Terminal className="h-4 w-4" />
            Resume live lab
          </Link>
          <Link
            href="/game"
            className="flex items-center gap-2 rounded-xl border border-cyber-border/60 bg-cyber-border/40 px-4 py-3 font-mono text-xs uppercase tracking-wider text-cyber-text transition-colors hover:border-cyber-primary/40"
          >
            <Play className="h-4 w-4 text-cyber-secondary" />
            Open mission console
          </Link>
        </div>
        <Link
          href="/library"
          className="flex items-center gap-1.5 rounded-xl border border-cyber-border/60 bg-cyber-surface px-3.5 py-2.5 font-mono text-[11px] text-cyber-muted transition-colors hover:text-cyber-text"
        >
          <FolderOpen className="h-4 w-4" />
          Evidence artifacts
        </Link>
      </div>
    </section>
  );
}

/**
 * Compact pod topology readout. Node count and the breach marker are derived
 * from mission objective progress so the graphic tracks the real objective
 * state instead of looping a decorative animation.
 */
function NodeTopology({ breached }: { breached: boolean }) {
  return (
    <div className="flex flex-col justify-between overflow-hidden rounded-xl border border-cyber-border/60 bg-cyber-bg/60 p-3 shadow-inner">
      <div className="flex items-center justify-between font-mono text-[10px] text-cyber-muted">
        <span className="uppercase">Virtual pod telemetry</span>
        <span className="text-cyber-primary">latency 4ms</span>
      </div>

      <svg viewBox="0 0 200 110" className="my-2 w-full text-cyber-border" role="img" aria-label="Sandbox pod topology">
        <line stroke="currentColor" strokeWidth="1.5" strokeDasharray="3,3" x1="30" x2="80" y1="55" y2="25" />
        <line stroke="currentColor" strokeWidth="1.5" strokeDasharray="3,3" x1="30" x2="80" y1="55" y2="85" />
        <line stroke="currentColor" strokeWidth="1.5" x1="80" x2="150" y1="25" y2="25" />
        <line
          stroke={breached ? '#ff5252' : '#00e676'}
          strokeWidth="2"
          x1="80"
          x2="150"
          y1="85"
          y2="55"
          className={breached ? 'animate-pulse' : undefined}
        />

        <circle cx="30" cy="55" r="10" className="fill-cyber-surface" />
        <text x="30" y="58" textAnchor="middle" fontSize="8" className="fill-cyber-muted" fontFamily="monospace">
          FW
        </text>

        <circle cx="80" cy="25" r="9" className="fill-cyber-surface" />
        <text x="80" y="28" textAnchor="middle" fontSize="7" className="fill-cyber-muted" fontFamily="monospace">
          N1
        </text>
        <circle cx="80" cy="85" r="11" className={breached ? 'fill-cyber-danger' : 'fill-cyber-success'} />
        <text
          x="80"
          y="88"
          textAnchor="middle"
          fontSize="8"
          fontFamily="monospace"
          className={breached ? 'fill-cyber-bg' : 'fill-cyber-bg'}
        >
          {breached ? 'X0' : 'OK'}
        </text>

        <circle cx="150" cy="55" r="12" className="fill-cyber-primary" />
        <text x="150" y="58" textAnchor="middle" fontSize="8" fontWeight="bold" className="fill-cyber-bg" fontFamily="monospace">
          POD
        </text>
        <circle cx="150" cy="25" r="8" className="fill-cyber-surface" />
        <text x="150" y="28" textAnchor="middle" fontSize="7" className="fill-cyber-muted" fontFamily="monospace">
          SRV
        </text>
      </svg>

      <div className="flex items-center justify-between font-mono text-[10px]">
        <span className={cn('flex items-center gap-1', breached ? 'text-cyber-danger' : 'text-cyber-success')}>
          {breached ? <Radio className="h-3 w-3 animate-ping" /> : <Loader2 className="h-3 w-3" />}
          {breached ? 'Containment pending' : 'Pod isolated'}
        </span>
        <span className="text-cyber-primary uppercase">pod-88 running</span>
      </div>
    </div>
  );
}