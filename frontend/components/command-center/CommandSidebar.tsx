'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  Award,
  BookOpen,
  ChevronLeft,
  Compass,
  Flag,
  LayoutDashboard,
  Network,
  Radar,
  Shield,
  ShieldCheck,
  Swords,
  Terminal,
  TrendingUp,
  Trophy,
  Wrench,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useAuth } from '@/lib/auth';
import type { UserRole } from '@/lib/types';

const ADMIN_ROLES: UserRole[] = ['administrator', 'developer', 'super_admin'];

interface NavItem {
  href: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
}

const PRIMARY: NavItem[] = [
  { href: '/dashboard-v2', label: 'Command Center', icon: LayoutDashboard },
  { href: '/courses', label: 'Learn', icon: BookOpen },
  { href: '/missions', label: 'Missions', icon: Swords },
  { href: '/labs', label: 'Cyber Labs', icon: Terminal },
  { href: '/ctf', label: 'CTF Arena', icon: Flag },
  { href: '/soc', label: 'SOC Center', icon: Radar },
  { href: '/threat-intel', label: 'Threat Intel', icon: Compass },
  { href: '/tools', label: 'Cyber Tools', icon: Wrench },
];

const TACTICAL: NavItem[] = [
  { href: '/game', label: 'Global Arena', icon: Network },
  { href: '/leaderboard', label: 'Global Leaderboard', icon: Trophy },
  { href: '/certificates', label: 'Achievements', icon: Award },
  { href: '/progression', label: 'Progression', icon: TrendingUp },
];

export default function CommandSidebar({
  level,
  rank,
  streak,
  xp,
  xpPercent,
  unread,
  onNavigate,
}: {
  level: number;
  rank: string;
  streak: number;
  xp: number;
  xpPercent: number;
  unread: number;
  onNavigate?: () => void;
}) {
  const pathname = usePathname();
  const { user } = useAuth();

  const tactical = ADMIN_ROLES.includes(user?.role as UserRole)
    ? [...TACTICAL, { href: '/admin', label: 'Security Center', icon: ShieldCheck } satisfies NavItem]
    : TACTICAL;

  const isActive = (href: string) =>
    pathname === href || (href !== '/dashboard-v2' && pathname.startsWith(`${href}/`));

  return (
    <aside className="fixed inset-y-0 left-0 z-40 hidden w-64 flex-col justify-between overflow-y-auto border-r border-cyber-border/60 bg-cyber-surface/40 lg:flex">
      <div className="flex flex-col">
        <div className="flex h-16 items-center gap-3 border-b border-cyber-border/40 bg-cyber-bg/40 px-5">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl border border-cyber-primary/40 bg-gradient-to-br from-cyber-primary/20 to-cyber-secondary/20 shadow-[0_0_16px_rgba(0,229,255,0.25)]">
            <Shield className="h-5 w-5 text-cyber-primary" />
          </div>
          <div className="flex flex-col leading-none">
            <span className="text-sm font-bold tracking-wider text-cyber-primary">CYBERVERSE</span>
            <span className="mt-1 font-mono text-[10px] uppercase tracking-[0.2em] text-cyber-muted">
              Academy OS
            </span>
          </div>
        </div>

        <SectionLabel>Primary Command</SectionLabel>
        <nav className="flex flex-col gap-1 px-3">
          {PRIMARY.map((item) => (
            <NavLink key={item.href} item={item} active={isActive(item.href)} onNavigate={onNavigate} />
          ))}
        </nav>

        <SectionLabel>Tactical Intel</SectionLabel>
        <nav className="flex flex-col gap-1 px-3">
          {tactical.map((item) => (
            <NavLink key={item.href} item={item} active={isActive(item.href)} onNavigate={onNavigate} />
          ))}
        </nav>

        <div className="px-5 pb-2 pt-5">
          <Link
            href="/dashboard"
            onClick={onNavigate}
            className="flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-wider text-cyber-muted transition-colors hover:text-cyber-primary"
          >
            <ChevronLeft className="h-3.5 w-3.5" /> Classic dashboard
          </Link>
        </div>
      </div>

      <div className="m-3 rounded-xl border border-cyber-border/60 bg-cyber-bg/60 p-3">
        <div className="flex items-center justify-between font-mono text-[10px] uppercase tracking-wider text-cyber-muted">
          <span>Operator Status</span>
          <span className="font-bold text-cyber-primary">LVL {level}</span>
        </div>
        <div className="mt-2 h-2 overflow-hidden rounded-full bg-cyber-border">
          <div
            className="h-full rounded-full bg-gradient-to-r from-cyber-primary to-cyber-secondary shadow-[0_0_10px_rgba(0,229,255,0.45)]"
            style={{ width: `${xpPercent}%` }}
          />
        </div>
        <div className="mt-2 flex items-center justify-between font-mono text-[10px] text-cyber-muted">
          <span className="truncate">{rank}</span>
          <span>{xp.toLocaleString('en-US')} XP</span>
        </div>
        <div className="mt-2 flex items-center justify-between border-t border-cyber-border/40 pt-2 font-mono text-[10px] text-cyber-muted">
          <span>Streak</span>
          <span className="text-cyber-warning">{streak}d</span>
        </div>
        {unread > 0 && (
          <p className="mt-2 font-mono text-[10px] text-cyber-primary">
            {unread} unread alert{unread === 1 ? '' : 's'}
          </p>
        )}
        <p className="mt-3 font-mono text-[9px] leading-tight text-cyber-muted/70">
          SIMULATION ENVIRONMENT • STRICT EDUCATIONAL USE ONLY
        </p>
      </div>
    </aside>
  );
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <p className="px-6 pb-1 pt-5 font-mono text-[10px] uppercase tracking-[0.15em] text-cyber-muted">
      {children}
    </p>
  );
}

function NavLink({
  item,
  active,
  onNavigate,
}: {
  item: NavItem;
  active: boolean;
  onNavigate?: () => void;
}) {
  const Icon = item.icon;
  return (
    <Link
      href={item.href}
      onClick={onNavigate}
      aria-current={active ? 'page' : undefined}
      className={cn(
        'flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm transition-all',
        active
          ? 'border-l-4 border-cyber-primary bg-gradient-to-r from-cyber-primary/15 to-cyber-surface font-semibold text-cyber-primary shadow-sm'
          : 'text-cyber-muted hover:bg-cyber-surface/70 hover:text-cyber-text',
      )}
    >
      <Icon className="h-[18px] w-[18px] shrink-0" />
      <span className="truncate">{item.label}</span>
    </Link>
  );
}