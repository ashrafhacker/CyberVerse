'use client';

import { cn } from '@/lib/utils';

export function TerminalCard({
  className,
  title,
  children,
}: {
  className?: string;
  title?: string;
  children: React.ReactNode;
}) {
  return (
    <div className={cn('terminal-card overflow-hidden', className)}>
      {title && (
        <div className="flex items-center gap-2 border-b border-cyber-border bg-cyber-bg/60 px-4 py-2">
          <span className="h-2.5 w-2.5 rounded-full bg-cyber-danger/70" />
          <span className="h-2.5 w-2.5 rounded-full bg-cyber-warning/70" />
          <span className="h-2.5 w-2.5 rounded-full bg-cyber-success/70" />
          <span className="ml-2 font-mono text-xs text-cyber-muted">{title}</span>
        </div>
      )}
      <div className="p-5">{children}</div>
    </div>
  );
}

export function StatCard({
  label,
  value,
  accent = 'text-cyber-primary',
  icon: Icon,
}: {
  label: string;
  value: string | number;
  accent?: string;
  icon?: React.ComponentType<{ className?: string }>;
}) {
  return (
    <div className="terminal-card p-5">
      <div className="flex items-center justify-between">
        <p className="text-xs uppercase tracking-wider text-cyber-muted">{label}</p>
        {Icon && <Icon className={cn('h-5 w-5', accent)} />}
      </div>
      <p className={cn('mt-2 font-mono text-3xl font-bold', accent)}>{value}</p>
    </div>
  );
}

export function XPBar({ xp, level, xpForNext }: { xp: number; level: number; xpForNext: number }) {
  const pct = Math.min(100, Math.round((xp / xpForNext) * 100));
  return (
    <div className="terminal-card p-5">
      <div className="mb-2 flex items-center justify-between font-mono text-sm">
        <span className="text-cyber-primary">LEVEL {level}</span>
        <span className="text-cyber-muted">
          {xp} / {xpForNext} XP
        </span>
      </div>
      <div className="h-2.5 overflow-hidden rounded-full bg-cyber-border">
        <div
          className="h-full rounded-full bg-gradient-to-r from-cyber-primary to-cyber-secondary transition-all"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

export function LoadingScreen() {
  return (
    <div className="flex min-h-screen items-center justify-center">
      <div className="text-center">
        <p className="animate-pulse font-mono text-cyber-primary">&gt; establishing secure connection...</p>
      </div>
    </div>
  );
}
