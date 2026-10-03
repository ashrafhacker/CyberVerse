'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Users, ShieldAlert, Activity, Flag, Ban, CheckCircle2 } from 'lucide-react';
import Navbar from '@/components/Navbar';
import { TerminalCard, StatCard, LoadingScreen } from '@/components/TerminalCard';
import { useRequireAuth } from '@/lib/auth';
import { api } from '@/lib/api';
import type { UserRole } from '@/lib/types';

const ADMIN_ROLES: UserRole[] = ['administrator', 'developer', 'super_admin'];

interface AdminOverview {
  total_users: number;
  pending_tickets: number;
  active_subscriptions: number;
  published_announcements: number;
  system_health: { status: string; services: Record<string, string> };
}

interface AdminUser {
  id: string;
  email: string;
  full_name: string;
  role: string;
  status: string;
  is_verified: boolean;
  is_2fa_enabled: boolean;
  last_login: string | null;
  created_at: string;
}

interface AdminUsersData {
  total: number;
  page: number;
  page_size: number;
  users: AdminUser[];
}

export default function AdminPage() {
  const { user, loading } = useRequireAuth();
  const router = useRouter();
  const [overview, setOverview] = useState<AdminOverview | null>(null);
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!user) return;
    if (!user.role || !ADMIN_ROLES.includes(user.role)) {
      router.replace('/dashboard');
      return;
    }
    Promise.all([
      api.get<{ data: AdminOverview }>('/admin/overview'),
      api.get<{ data: AdminUsersData }>('/admin/users?page_size=10'),
    ])
      .then(([o, u]) => {
        setOverview(o.data);
        setUsers(u.data.users);
      })
      .catch((err) => setError(err instanceof Error ? err.message : 'Failed to load admin data'));
  }, [user, router]);

  const updateStatus = async (userId: string, status: string) => {
    try {
      await api.patch(`/admin/users/${userId}/status`, { status });
      setUsers((list) => list.map((u) => (u.id === userId ? { ...u, status } : u)));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Status update failed');
    }
  };

  if (loading || !user) return <LoadingScreen />;

  if (error) {
    return (
      <>
        <Navbar />
        <div className="mx-auto max-w-7xl px-6 py-16 text-center text-cyber-danger">{error}</div>
      </>
    );
  }

  return (
    <>
      <Navbar />
      <main className="mx-auto max-w-7xl px-6 py-8">
        <div className="mb-8">
          <h1 className="flex items-center gap-2 text-2xl font-bold">
            <ShieldAlert className="h-6 w-6 text-cyber-danger" /> Admin Console
          </h1>
          <p className="mt-1 text-sm text-cyber-muted">Platform overview, user management, and moderation.</p>
          <p className="mt-1 font-mono text-xs text-cyber-success">
            system: {overview?.system_health.status ?? 'checking'} · api: {overview?.system_health.services.api ?? 'ok'} · db: {overview?.system_health.services.database ?? 'ok'} · redis: {overview?.system_health.services.redis ?? 'ok'}
          </p>
        </div>

        <div className="mb-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatCard label="Total Users" value={overview?.total_users ?? '—'} icon={Users} />
          <StatCard label="Open Tickets" value={overview?.pending_tickets ?? '—'} accent="text-cyber-warning" icon={Flag} />
          <StatCard label="Subscriptions" value={overview?.active_subscriptions ?? '—'} accent="text-cyber-secondary" icon={Activity} />
          <StatCard label="Announcements" value={overview?.published_announcements ?? '—'} accent="text-cyber-success" icon={CheckCircle2} />
        </div>

        <TerminalCard title="user_management.sh" className="p-0">
          <div className="border-b border-cyber-border px-5 py-3">
            <h2 className="font-semibold">Latest registrations</h2>
          </div>
          {users.length === 0 ? (
            <p className="p-5 text-sm text-cyber-muted">No users yet.</p>
          ) : (
            <ul className="divide-y divide-cyber-border">
              {users.map((u) => (
                <li key={u.id} className="flex flex-wrap items-center justify-between gap-3 px-5 py-3 text-sm">
                  <div className="min-w-0">
                    <span className="font-medium">{u.full_name}</span>
                    <span className="ml-2 font-mono text-xs text-cyber-muted">{u.email}</span>
                    <div className="mt-1 flex gap-1.5">
                      <span className="rounded bg-cyber-border px-1.5 py-0.5 text-xs text-cyber-muted">{u.role}</span>
                      <span className={`rounded px-1.5 py-0.5 text-xs ${
                        u.status === 'active'
                          ? 'bg-cyber-success/20 text-cyber-success'
                          : u.status === 'pending'
                            ? 'bg-cyber-warning/20 text-cyber-warning'
                            : 'bg-cyber-danger/20 text-cyber-danger'
                      }`}>
                        {u.status}
                      </span>
                      {u.is_2fa_enabled && (
                        <span className="rounded bg-cyber-primary/20 px-1.5 py-0.5 text-xs text-cyber-primary">2FA</span>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xs text-cyber-muted">
                      {u.created_at ? new Date(u.created_at).toLocaleDateString() : '—'}
                    </span>
                    {u.status === 'active' ? (
                      <button
                        onClick={() => void updateStatus(u.id, 'suspended')}
                        className="terminal-button-ghost flex items-center gap-1.5 py-1 text-xs text-cyber-danger"
                      >
                        <Ban className="h-3.5 w-3.5" /> Suspend
                      </button>
                    ) : (
                      <button
                        onClick={() => void updateStatus(u.id, 'active')}
                        className="terminal-button-ghost flex items-center gap-1.5 py-1 text-xs text-cyber-success"
                      >
                        <CheckCircle2 className="h-3.5 w-3.5" /> Restore
                      </button>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </TerminalCard>
      </main>
    </>
  );
}
