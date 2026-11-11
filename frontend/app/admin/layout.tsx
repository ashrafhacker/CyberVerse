'use client';

import React from 'react';
import { Shield, Users, ShieldCheck, Megaphone, Wrench, Settings, CreditCard, BadgeCheck } from 'lucide-react';
import { useAuth } from '@/lib/auth';
import { isAdmin, SUPER_ROLES } from '@/lib/roles';
import { ErrorBoundary } from '@/components/AdminUI';

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const { user, loading, status, error, retry } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen bg-zinc-950 text-zinc-100 p-8">
        <div className="max-w-7xl mx-auto">
          <h1 className="text-2xl font-bold">Admin</h1>
          <div className="mt-6 rounded bg-zinc-900 border border-zinc-800 p-6 animate-pulse">
            <div className="h-4 w-32 bg-zinc-800 rounded" />
          </div>
        </div>
      </div>
    );
  }

  if (!user || !isAdmin(user.role)) {
    return (
      <div className="min-h-screen bg-zinc-950 text-zinc-100 p-8">
        <div className="max-w-3xl mx-auto rounded border border-red-900 bg-red-950/20 p-8 text-center">
          <Shield className="mx-auto h-10 w-10 text-red-400" />
          <h2 className="mt-4 text-xl font-semibold text-red-200">Access Denied</h2>
          <p className="text-sm text-zinc-400 mt-2">Admin access requires administrator, developer, or super_admin role.</p>
        </div>
      </div>
    );
  }

  const isSuper = SUPER_ROLES.includes(user.role);
  const nav = [
    { label: 'Overview', href: '/admin', icon: ShieldCheck },
    { label: 'Users', href: '/admin/users', icon: Users },
    { label: 'Payments', href: '/admin/payments', icon: CreditCard },
    { label: 'Subscriptions', href: '/admin/subscriptions', icon: BadgeCheck },
    { label: 'Tickets', href: '/admin/tickets', icon: Megaphone },
    { label: 'Audit', href: '/admin/audit', icon: Shield },
    { label: 'Feature Flags', href: '/admin/flags', icon: Wrench },
    { label: 'Settings', href: '/admin/settings', icon: Settings },
  ];

  return (
    <ErrorBoundary>
      <div className="min-h-screen bg-zinc-950 text-zinc-100">
        <header className="border-b border-zinc-800 bg-zinc-900/60 backdrop-blur-sm sticky top-0 z-50">
          <div className="max-w-7xl mx-auto px-4 h-14 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <ShieldCheck className="h-5 w-5 text-blue-400" />
              <span className="font-bold tracking-tight">Admin</span>
              {isSuper && <span className="text-[10px] rounded bg-amber-600/20 text-amber-300 px-1.5 py-0.5 font-mono">SUPER</span>}
            </div>
            <div className="text-xs text-zinc-400">{user.email}</div>
          </div>
        </header>
        <div className="max-w-7xl mx-auto px-4 flex gap-6">
          <nav className="w-48 shrink-0 pt-6 space-y-1">
            {nav.map((item) => (
              <a key={item.href} href={item.href} className="flex items-center gap-2 rounded px-3 py-2 text-sm text-zinc-300 hover:bg-zinc-900 hover:text-white transition-colors">
                <item.icon className="h-4 w-4 text-zinc-500" />
                {item.label}
              </a>
            ))}
          </nav>
          <main className="flex-1 pt-6">{children}</main>
        </div>
      </div>
    </ErrorBoundary>
  );
}
