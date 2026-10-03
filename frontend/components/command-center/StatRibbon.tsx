'use client';

import Link from 'next/link';
import type { ReactNode } from 'react';
import { Award, Flame, Flag, Medal, Terminal, Zap } from 'lucide-react';
import { formatNumber } from '@/lib/command-center';

export interface RibbonCell {
  id: string;
  label: string;
  value: string;
  sub?: ReactNode;
  meter?: number;
  footer?: ReactNode;
  icon: React.ComponentType<{ className?: string }>;
  accent?: 'primary' | 'secondary' | 'success' | 'warning';
}

const ACCENT_TEXT: Record<NonNullable<RibbonCell['accent']>, string> = {
  primary: 'text-cyber-primary',
  secondary: 'text-cyber-secondary',
  success: 'text-cyber-success',
  warning: 'text-cyber-warning',
};

const METER_GRADIENT: Record<NonNullable<RibbonCell['accent']>, string> = {
  primary: 'from-cyber-primary to-cyber-secondary',
  secondary: 'from-cyber-secondary to-cyber-primary',
  success: 'from-cyber-success to-cyber-secondary',
  warning: 'from-cyber-warning to-cyber-danger',
};

export default function StatRibbon({ cells }: { cells: RibbonCell[] }) {
  return (
    <div className="grid grid-cols-2 gap-4 md:grid-cols-3 xl:grid-cols-6">
      {cells.map((cell) => (
        <Cell key={cell.id} cell={cell} />
      ))}
    </div>
  );
}

function Cell({ cell }: { cell: RibbonCell }) {
  const Icon = cell.icon;
  const accent = cell.accent ?? 'primary';
  return (
    <div className="group flex flex-col justify-between gap-3 rounded-2xl border border-cyber-border/60 bg-cyber-surface/60 p-4 shadow-lg backdrop-blur-md transition-colors hover:border-cyber-primary/40">
      <div className="flex items-center justify-between font-mono text-[10px] uppercase tracking-wider text-cyber-muted">
        <span>{cell.label}</span>
        <Icon className={`h-4 w-4 ${ACCENT_TEXT[accent]} transition-transform group-hover:scale-110`} />
      </div>

      <div>
        <p className={`font-mono text-lg font-bold ${ACCENT_TEXT[accent]}`}>{cell.value}</p>
        {cell.sub && <p className="mt-0.5 truncate text-[11px] text-cyber-muted">{cell.sub}</p>}
      </div>

      {typeof cell.meter === 'number' ? (
        <div>
          <div className="mb-1.5 flex justify-between font-mono text-[10px] text-cyber-muted">
            <span>Progress</span>
            <span className={ACCENT_TEXT[accent]}>{cell.meter}%</span>
          </div>
          <div className="h-1.5 overflow-hidden rounded-full bg-cyber-border">
            <div
              className={`h-full rounded-full bg-gradient-to-r ${METER_GRADIENT[accent]} shadow-[0_0_8px_rgba(0,229,255,0.4)]`}
              style={{ width: `${Math.max(0, Math.min(100, cell.meter))}%` }}
            />
          </div>
        </div>
      ) : (
        cell.footer && <div className="font-mono text-[10px] text-cyber-muted">{cell.footer}</div>
      )}
    </div>
  );
}

export function ribbonCells(input: {
  level: number;
  rank: string;
  levelPercent: number;
  totalXp: number;
  xpNeeded: number;
  coins: number;
  streak: number;
  longestStreak: number;
  labsCompleted: number;
  labShare: number;
  missionsCompleted: number;
  lessonsCompleted: number;
  quizzesPassed: number;
  hoursLogged: number;
  badges: string[];
  flagsSolved: number;
  flagsTotal: number;
  globalRank: number | null;
  hoursHref: string;
}): RibbonCell[] {
  const medals = input.badges.length;
  return [
    {
      id: 'rank',
      label: 'Rank tier',
      value: `Lvl ${input.level}`,
      sub: input.rank,
      meter: input.levelPercent,
      icon: Award,
    },
    {
      id: 'xp',
      label: 'Experience',
      value: formatNumber(input.totalXp),
      accent: 'primary',
      sub: <span className="text-cyber-primary">+{formatNumber(input.xpNeeded)} XP to next level</span>,
      footer: `${formatNumber(input.coins)} coins banked`,
      icon: Zap,
    },
    {
      id: 'streak',
      label: 'Defense streak',
      value: `${input.streak} Days`,
      sub: 'Active sentinel',
      accent: 'warning',
      footer: `Record: ${input.longestStreak} days`,
      icon: Flame,
    },
    {
      id: 'labs',
      label: 'Lab matrix',
      value: `${input.labsCompleted} labs`,
      sub: `${input.missionsCompleted} missions · ${input.lessonsCompleted} lessons`,
      accent: 'secondary',
      meter: input.labShare,
      icon: Terminal,
    },
    {
      id: 'flags',
      label: 'CTF flags',
      value: `${input.flagsSolved} solved`,
      sub: input.globalRank ? `Rank #${input.globalRank} weekly` : 'Unranked this week',
      accent: 'success',
      footer: `${input.flagsTotal} challenges live · ${input.quizzesPassed} quizzes passed`,
      icon: Flag,
    },
    {
      id: 'badges',
      label: 'Achievements',
      value: `${medals} badge${medals === 1 ? '' : 's'}`,
      sub: `${input.hoursLogged}h logged`,
      accent: 'primary',
      footer: (
        <Link href={input.hoursHref} className="text-cyber-primary hover:underline">
          Open progression
        </Link>
      ),
      icon: Medal,
    },
  ];
}