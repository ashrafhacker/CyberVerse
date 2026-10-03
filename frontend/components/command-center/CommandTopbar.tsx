'use client';

import Link from 'next/link';
import { useEffect, useRef, useState } from 'react';
import {
  Bell,
  ChevronDown,
  Flame,
  LogOut,
  Menu,
  RefreshCw,
  Search,
  Terminal,
  X,
  Zap,
} from 'lucide-react';
import { useAuth } from '@/lib/auth';
import { cn } from '@/lib/utils';
import { formatNumber } from '@/lib/command-center';
import type { CCNotification } from '@/lib/command-center';

export interface SearchTarget {
  id: string;
  label: string;
  group: string;
  href: string;
  hint?: string;
}

export default function CommandTopbar({
  xp,
  level,
  streak,
  unread,
  notifications,
  initials,
  refreshing,
  onRefresh,
  onOpenPalette,
  onToggleNav,
  targets,
}: {
  xp: number;
  level: number;
  streak: number;
  unread: number;
  notifications: CCNotification[];
  initials: string;
  refreshing: boolean;
  onRefresh: () => void;
  onOpenPalette: () => void;
  onToggleNav: () => void;
  targets: SearchTarget[];
}) {
  const { user, logout } = useAuth();
  const [showBell, setShowBell] = useState(false);
  const bellRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!showBell) return;
    const onDocClick = (e: MouseEvent) => {
      if (bellRef.current && !bellRef.current.contains(e.target as Node)) setShowBell(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setShowBell(false);
    };
    document.addEventListener('mousedown', onDocClick);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onDocClick);
      document.removeEventListener('keydown', onKey);
    };
  }, [showBell]);

  return (
    <header className="fixed left-0 right-0 top-0 z-30 flex h-16 items-center gap-3 border-b border-cyber-border/60 bg-cyber-bg/80 px-4 backdrop-blur-xl lg:left-64 lg:px-6">
      <button
        type="button"
        onClick={onToggleNav}
        aria-label="Open navigation"
        className="flex h-9 w-9 items-center justify-center rounded-xl border border-cyber-border/60 text-cyber-muted transition-colors hover:text-cyber-primary lg:hidden"
      >
        <Menu className="h-[18px] w-[18px]" />
      </button>

      <div className="hidden items-center gap-2 rounded-full border border-cyber-primary/30 bg-cyber-surface px-3 py-1.5 xl:flex">
        <span className="h-2 w-2 animate-ping rounded-full bg-cyber-success" />
        <span className="font-mono text-[10px] font-semibold uppercase tracking-wider text-cyber-primary">
          System Active
        </span>
      </div>

      <button
        type="button"
        onClick={onOpenPalette}
        className="group mx-auto flex w-full max-w-xl items-center gap-2 rounded-xl border border-cyber-border/70 bg-cyber-surface/70 px-3 py-2 text-left transition-all hover:border-cyber-primary/50 focus:border-cyber-primary focus:shadow-[0_0_16px_rgba(0,229,255,0.2)] focus:outline-none"
      >
        <Search className="h-4 w-4 shrink-0 text-cyber-muted" />
        <span className="flex-1 truncate font-mono text-xs text-cyber-muted">
          Query courses, labs, CTF challenges, tools…
        </span>
        <kbd className="hidden rounded-lg border border-cyber-border/60 bg-cyber-bg px-2 py-0.5 font-mono text-[10px] text-cyber-muted sm:inline">
          ⌘K
        </kbd>
      </button>

      <div className="flex shrink-0 items-center gap-2">
        <div className="hidden items-center gap-1.5 rounded-full border border-cyber-primary/30 bg-gradient-to-r from-cyber-primary/10 to-cyber-surface px-3 py-1.5 lg:flex">
          <Zap className="h-4 w-4 text-cyber-primary" />
          <span className="font-mono text-[11px] font-bold text-cyber-primary">{formatNumber(xp)} XP</span>
          <span className="text-cyber-muted">•</span>
          <span className="font-mono text-[11px] text-cyber-secondary">LVL {level}</span>
        </div>

        <div className="hidden items-center gap-1.5 rounded-full border border-cyber-border/60 bg-cyber-surface px-3 py-1.5 md:flex">
          <Flame className="h-4 w-4 text-cyber-warning" />
          <span className="font-mono text-[11px] font-semibold">{streak}D Streak</span>
        </div>

        <button
          type="button"
          onClick={onRefresh}
          aria-label="Refresh telemetry"
          title="Telemetry stream"
          className="flex h-9 w-9 items-center justify-center rounded-xl border border-cyber-border/60 bg-cyber-surface text-cyber-muted transition-colors hover:border-cyber-primary hover:text-cyber-primary"
        >
          <RefreshCw className={cn('h-[18px] w-[18px]', refreshing && 'animate-spin')} />
        </button>

        <Link
          href="/labs"
          title="Active terminal console"
          aria-label="Active terminal console"
          className="hidden h-9 w-9 items-center justify-center rounded-xl border border-cyber-border/60 bg-cyber-surface text-cyber-muted transition-colors hover:border-cyber-primary hover:text-cyber-primary sm:flex"
        >
          <Terminal className="h-[18px] w-[18px]" />
        </Link>

        <div className="relative" ref={bellRef}>
          <button
            type="button"
            onClick={() => setShowBell((v) => !v)}
            aria-label={`System notifications${unread > 0 ? ` (${unread} unread)` : ''}`}
            aria-expanded={showBell}
            className="relative flex h-9 w-9 items-center justify-center rounded-xl border border-cyber-border/60 bg-cyber-surface text-cyber-muted transition-colors hover:text-cyber-text"
          >
            <Bell className="h-[18px] w-[18px]" />
            {unread > 0 && (
              <span className="absolute right-2 top-2 h-2 w-2 rounded-full bg-cyber-primary" />
            )}
          </button>

          {showBell && (
            <div className="absolute right-0 top-12 z-50 w-80 rounded-xl border border-cyber-border bg-cyber-surface p-3 shadow-2xl">
              <div className="mb-2 flex items-center justify-between">
                <p className="font-mono text-[10px] uppercase tracking-wider text-cyber-muted">Alerts</p>
                <span className="font-mono text-[10px] text-cyber-muted">
                  {unread} unread
                </span>
              </div>
              {notifications.length === 0 ? (
                <p className="py-4 text-center font-mono text-xs text-cyber-muted">No alerts on this channel.</p>
              ) : (
                <ul className="max-h-72 space-y-2 overflow-y-auto">
                  {notifications.map((n) => (
                    <li key={n.id}>
                      <Link
                        href={n.link ?? '/notifications'}
                        onClick={() => setShowBell(false)}
                        className={cn(
                          'block rounded-lg border border-cyber-border/60 px-3 py-2 transition-colors hover:border-cyber-primary/50',
                          !n.isRead && 'bg-cyber-primary/5',
                        )}
                      >
                        <p className="text-xs font-semibold">{n.title}</p>
                        {n.body && <p className="mt-0.5 line-clamp-2 text-[11px] text-cyber-muted">{n.body}</p>}
                      </Link>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </div>

        <div className="flex items-center gap-2 border-l border-cyber-border/60 pl-2">
          <div className="flex h-9 w-9 items-center justify-center rounded-full bg-gradient-to-tr from-cyber-primary to-cyber-secondary font-mono text-xs font-bold text-cyber-bg">
            {initials}
          </div>
          <div className="hidden flex-col text-left xl:flex">
            <span className="text-xs font-bold leading-none">{user?.full_name ?? 'Operator'}</span>
            <span className="mt-1 font-mono text-[10px] leading-none text-cyber-muted">{user?.role}</span>
          </div>
          <button
            type="button"
            onClick={() => void logout()}
            aria-label="Log out"
            className="hidden h-9 w-9 items-center justify-center rounded-xl border border-cyber-border/60 bg-cyber-surface text-cyber-muted transition-colors hover:text-cyber-danger md:flex"
          >
            <LogOut className="h-[18px] w-[18px]" />
          </button>
        </div>
      </div>
    </header>
  );
}

export function MobileNavSheet({
  open,
  onClose,
  targets,
}: {
  open: boolean;
  onClose: () => void;
  targets: SearchTarget[];
}) {
  if (!open) return null;
  const groups = new Map<string, SearchTarget[]>();
  for (const t of targets) {
    const list = groups.get(t.group) ?? [];
    list.push(t);
    groups.set(t.group, list);
  }

  return (
    <div className="fixed inset-0 z-50 flex lg:hidden" role="dialog" aria-modal="true" aria-label="Navigation">
      <div className="absolute inset-0 bg-black/70" onClick={onClose} />
      <nav className="relative ml-auto flex h-full w-72 flex-col gap-4 overflow-y-auto border-l border-cyber-border bg-cyber-surface p-5">
        <div className="flex items-center justify-between">
          <span className="font-mono text-xs uppercase tracking-wider text-cyber-muted">Navigate</span>
          <button type="button" onClick={onClose} aria-label="Close navigation" className="text-cyber-muted">
            <X className="h-5 w-5" />
          </button>
        </div>
        {[...groups.entries()].map(([group, items]) => (
          <div key={group}>
            <p className="mb-2 font-mono text-[10px] uppercase tracking-[0.15em] text-cyber-muted">{group}</p>
            <ul className="flex flex-col gap-1">
              {items.map((t) => (
                <li key={t.id}>
                  <Link
                    href={t.href}
                    onClick={onClose}
                    className="flex items-center justify-between rounded-lg px-3 py-2 text-sm text-cyber-muted transition-colors hover:bg-cyber-bg hover:text-cyber-primary"
                  >
                    {t.label}
                    <ChevronDown className="h-3.5 w-3.5 -rotate-90 opacity-40" />
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </nav>
    </div>
  );
}