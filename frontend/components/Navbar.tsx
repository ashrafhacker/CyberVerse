'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Shield, LayoutDashboard, BookOpen, Swords, Trophy, User, LogOut, Settings, FlaskConical, Wrench, Award, Globe, Gamepad2, Flag } from 'lucide-react';
import { useAuth } from '@/lib/auth';
import { cn } from '@/lib/utils';
import type { UserRole } from '@/lib/types';

const ADMIN_ROLES: UserRole[] = ['administrator', 'developer', 'super_admin'];
const INSTRUCTOR_ROLES: UserRole[] = ['instructor', ...ADMIN_ROLES];

export default function Navbar() {
  const { user, logout } = useAuth();
  const pathname = usePathname();

  if (!user) {
    return (
      <header className="sticky top-0 z-50 border-b border-cyber-border bg-cyber-bg/80 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-3">
          <Link href="/" className="flex items-center gap-2">
            <Shield className="h-6 w-6 text-cyber-primary" />
            <span className="font-mono font-bold text-cyber-primary">CyberVerse</span>
          </Link>
          <nav className="flex items-center gap-3">
            <Link href="/courses" className="flex items-center gap-2 rounded-md px-3 py-2 text-sm text-cyber-muted hover:text-cyber-primary transition-colors">
              <BookOpen className="h-4 w-4" />
              <span className="hidden md:inline">Learn</span>
            </Link>
            <Link href="/game" className="flex items-center gap-2 rounded-md px-3 py-2 text-sm text-cyber-muted hover:text-cyber-primary transition-colors">
              <Gamepad2 className="h-4 w-4" />
              <span className="hidden md:inline">Cyber Game</span>
            </Link>
            <Link href="/global-arena" className="flex items-center gap-2 rounded-md px-3 py-2 text-sm text-cyber-muted hover:text-cyber-primary transition-colors">
              <Flag className="h-4 w-4" />
              <span className="hidden md:inline">Global Arena</span>
            </Link>
            <Link href="/external-labs" className="flex items-center gap-2 rounded-md px-3 py-2 text-sm text-cyber-muted hover:text-cyber-primary transition-colors">
              <Globe className="h-4 w-4" />
              <span className="hidden md:inline">External Labs</span>
            </Link>
            <Link href="/tools" className="flex items-center gap-2 rounded-md px-3 py-2 text-sm text-cyber-muted hover:text-cyber-primary transition-colors">
              <Wrench className="h-4 w-4" />
              <span className="hidden md:inline">Tools</span>
            </Link>
            <Link href="/login" className="terminal-button-ghost px-4 py-2 text-sm">Log in</Link>
            <Link href="/register" className="terminal-button px-4 py-2 text-sm">Get Started</Link>
          </nav>
        </div>
      </header>
    );
  }

  const links = [
    { href: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { href: '/courses', label: 'Learn', icon: BookOpen },
    { href: '/missions', label: 'Missions', icon: Swords },
    { href: '/labs', label: 'Labs', icon: FlaskConical },
    { href: '/game', label: 'Cyber Game', icon: Gamepad2 },
    { href: '/global-arena', label: 'Global Arena', icon: Flag },
    { href: '/external-labs', label: 'External Labs', icon: Globe },
    { href: '/tools', label: 'Tools', icon: Wrench },
    { href: '/leaderboard', label: 'Leaderboard', icon: Trophy },
    { href: '/certificates', label: 'Certificates', icon: Award },
    { href: '/profile', label: 'Profile', icon: User },
    ...(user.role && INSTRUCTOR_ROLES.includes(user.role)
      ? [{ href: '/instructor', label: 'Instructor', icon: Settings }]
      : []),
    ...(user.role && ADMIN_ROLES.includes(user.role)
      ? [{ href: '/admin', label: 'Admin', icon: Settings }]
      : []),
  ];

  return (
    <header className="sticky top-0 z-50 border-b border-cyber-border bg-cyber-bg/80 backdrop-blur">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-3">
        <Link href="/" className="flex items-center gap-2">
          <Shield className="h-6 w-6 text-cyber-primary" />
          <span className="font-mono font-bold text-cyber-primary">CyberVerse</span>
        </Link>

        <nav className="flex items-center gap-1">
          {links.map(({ href, label, icon: Icon }) => (
            <Link
              key={href}
              href={href}
              className={cn(
                'flex items-center gap-2 rounded-md px-3 py-2 text-sm text-cyber-muted transition-colors hover:text-cyber-primary',
                pathname === href && 'bg-cyber-surface text-cyber-primary',
              )}
            >
              <Icon className="h-4 w-4" />
              <span className="hidden md:inline">{label}</span>
            </Link>
          ))}
          <button
            onClick={() => void logout()}
            className="ml-2 flex items-center gap-2 rounded-md px-3 py-2 text-sm text-cyber-muted transition-colors hover:text-cyber-danger"
            aria-label="Log out"
          >
            <LogOut className="h-4 w-4" />
            <span className="hidden md:inline">Logout</span>
          </button>
        </nav>
      </div>
    </header>
  );
}
