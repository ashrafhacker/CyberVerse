'use client';
import React, { useCallback, useEffect, useState } from 'react';
import { Search, ChevronLeft, ChevronRight, KeyRound, History, X } from 'lucide-react';
import { useRequireAuth } from '@/lib/auth';
import { isAdmin, isSuper } from '@/lib/roles';
import { api } from '@/lib/api';
import { LoadingState, EmptyState, RetryButton } from '@/components/AdminUI';
import { useAdminWs } from '@/lib/adminWs';

interface AdminUser {
  id: string; email: string; full_name: string; role: string; status: string;
  is_verified: boolean; is_2fa_enabled: boolean; created_at: string;
  last_login?: string | null;
}

interface UserSession {
  id: string; ip_address: string | null; user_agent: string;
  location: string | null; created_at: string; expires_at: string;
}

interface LoginHistoryRow {
  id: string; success: boolean; ip_address: string | null;
  location: string | null; method: string; failure_reason: string | null; created_at: string;
}

const ROLES = ['guest', 'student', 'premium_student', 'instructor', 'moderator', 'administrator', 'developer', 'super_admin'];

function fmtWhen(iso?: string | null) {
  if (!iso) return '—';
  try { return new Date(iso).toLocaleString(); } catch { return iso; }
}

export default function AdminUsersPage() {
  const { user } = useRequireAuth();
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [page, setPage] = useState(1);
  const perPage = 20;
  const [busyId, setBusyId] = useState<string | null>(null);
  const [detail, setDetail] = useState<AdminUser | null>(null);
  const { lastEvent, connected } = useAdminWs();

  const load = useCallback(async () => {
    setLoading(true); setError(null);
    try {
      const params = new URLSearchParams({ page: String(page), page_size: String(perPage) });
      if (search) params.set('search', search);
      if (statusFilter !== 'all') params.set('status', statusFilter);
      const json = await api.get<{ data: { users: AdminUser[]; total: number } }>(`/admin/users?${params.toString()}`, { cache: 'no-store' });
      setUsers(json?.data?.users ?? []);
      setTotal(json?.data?.total ?? 0);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to load users');
    } finally {
      setLoading(false);
    }
  }, [page, search, statusFilter]);

  useEffect(() => { load(); }, [load]);
  useEffect(() => {
    if (lastEvent && (lastEvent.type === 'user_updated' || lastEvent.type === 'audit')) load();
  }, [lastEvent, load]);

  const setStatus = useCallback(async (u: AdminUser, status: string) => {
    setBusyId(u.id);
    try {
      await api.patch(`/admin/users/${u.id}/status`, { status });
      await load();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Status update failed');
    } finally {
      setBusyId(null);
    }
  }, [load]);

  const setRole = useCallback(async (u: AdminUser, role: string) => {
    setBusyId(u.id);
    try {
      await api.patch(`/admin/users/${u.id}/role`, { role });
      await load();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Role update failed');
    } finally {
      setBusyId(null);
    }
  }, [load]);

  const superUser = isSuper(user?.role);
  const pages = Math.max(1, Math.ceil(total / perPage));

  if (!user || !isAdmin(user.role)) return <div className="p-8"><h2 className="text-red-400 font-semibold">Access denied</h2></div>;

  return (
    <div>
      <h1 className="text-2xl font-bold mb-2">Users</h1>
      <div className="flex gap-3 mb-4">
        <div className="relative"><Search className="absolute left-2 top-2 h-4 w-4 text-zinc-500" /><input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search users..." className="rounded bg-zinc-900 border border-zinc-800 pl-8 pr-3 py-2 text-sm" /></div>
        <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)} className="rounded bg-zinc-900 border border-zinc-800 px-3 py-2 text-sm">
          <option value="all">All statuses</option><option>active</option><option>pending</option><option>suspended</option><option>banned</option>
        </select>
        <button onClick={load} className="rounded bg-blue-600 px-3 py-2 text-sm hover:bg-blue-500">Refresh</button>
      </div>
      <div className="text-xs text-zinc-500 mb-2">{total} user{total === 1 ? '' : 's'} | WS: {connected ? 'connected' : 'offline'}</div>
      {loading ? <LoadingState /> : error ? <div className="rounded border border-red-900 bg-red-950/20 p-4"><p className="text-sm text-red-300">{error}</p><RetryButton onRetry={load} /></div> : users.length === 0 ? <EmptyState title="No users" message="No users match filters." /> : (
        <div className="overflow-auto rounded border border-zinc-800">
          <table className="w-full text-sm"><thead className="bg-zinc-900 text-zinc-300"><tr><th className="text-left px-3 py-2">User</th><th>Role</th><th>Status</th><th>Verified</th><th>Last login</th><th>Actions</th></tr></thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.id} className="border-t border-zinc-800 hover:bg-zinc-900/40">
                <td className="px-3 py-2">
                  <div className="font-medium">{u.full_name || u.email}</div>
                  <div className="text-xs text-zinc-500">{u.email}</div>
                </td>
                <td className="px-3 py-2">
                  <select
                    value={u.role}
                    disabled={!superUser || u.id === user.id || busyId === u.id}
                    title={superUser ? 'Change role' : 'Role changes require super_admin'}
                    onChange={(e) => setRole(u, e.target.value)}
                    className="rounded bg-zinc-900 border border-zinc-800 px-1 py-1 text-xs disabled:opacity-40"
                  >
                    {[...new Set([u.role, ...ROLES])].map((r) => <option key={r} value={r}>{r}</option>)}
                  </select>
                </td>
                <td className="px-3 py-2"><span className={`text-xs rounded px-1 ${u.status === 'active' ? 'bg-emerald-900/30 text-emerald-300' : u.status === 'pending' ? 'bg-amber-900/30 text-amber-300' : 'bg-rose-900/30 text-rose-300'}`}>{u.status}</span></td>
                <td className="px-3 py-2">{u.is_verified ? 'Yes' : 'No'}</td>
                <td className="px-3 py-2 text-xs text-zinc-400">{fmtWhen(u.last_login)}</td>
                <td className="px-3 py-2">
                  <div className="flex gap-1 justify-center items-center">
                    {u.id !== user.id && (
                      <button
                        disabled={busyId === u.id}
                        onClick={() => setStatus(u, u.status === 'active' ? 'suspended' : 'active')}
                        className={`rounded px-2 py-1 text-xs disabled:opacity-40 ${u.status === 'active' ? 'bg-rose-700/60 hover:bg-rose-600 text-white' : 'bg-emerald-700/60 hover:bg-emerald-600 text-white'}`}
                      >
                        {u.status === 'active' ? 'Suspend' : 'Activate'}
                      </button>
                    )}
                    <button onClick={() => setDetail(u)} className="rounded bg-zinc-800 hover:bg-zinc-700 px-2 py-1 text-xs flex items-center gap-1"><KeyRound className="h-3 w-3" /> Sessions</button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody></table>
        </div>
      )}
      <div className="flex gap-2 mt-3 items-center">
        <button onClick={() => setPage(p => Math.max(1, p-1))} disabled={page <= 1} className="rounded bg-zinc-900 border border-zinc-800 px-2 py-1 text-sm disabled:opacity-40"><ChevronLeft className="h-3 w-3" /></button>
        <span className="text-xs text-zinc-400">Page {page} of {pages}</span>
        <button onClick={() => setPage(p => Math.min(pages, p+1))} disabled={page >= pages} className="rounded bg-zinc-900 border border-zinc-800 px-2 py-1 text-sm disabled:opacity-40"><ChevronRight className="h-3 w-3" /></button>
      </div>
      {detail && <SessionsDrawer target={detail} onClose={() => setDetail(null)} />}
    </div>
  );
}

function SessionsDrawer({ target, onClose }: { target: AdminUser; onClose: () => void }) {
  const [sessions, setSessions] = useState<UserSession[]>([]);
  const [history, setHistory] = useState<LoginHistoryRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true); setError(null);
    try {
      const [s, h] = await Promise.all([
        api.get<{ data: UserSession[] }>(`/admin/users/${target.id}/sessions`, { cache: 'no-store' }),
        api.get<{ data: LoginHistoryRow[] }>(`/admin/users/${target.id}/login-history?limit=15`, { cache: 'no-store' }),
      ]);
      setSessions(s?.data ?? []);
      setHistory(h?.data ?? []);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to load sessions');
    } finally {
      setLoading(false);
    }
  }, [target.id]);

  useEffect(() => { load(); }, [load]);

  const revoke = async (sessionId: string) => {
    setBusy(sessionId);
    try {
      await api.delete(`/admin/users/${target.id}/sessions/${sessionId}`);
      await load();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Revoke failed');
    } finally {
      setBusy(null);
    }
  };

  const revokeAll = async () => {
    setBusy('all');
    try {
      await api.post(`/admin/users/${target.id}/sessions/revoke-all`);
      await load();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Revoke all failed');
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className="fixed inset-0 z-[60] bg-black/70 flex items-center justify-center p-4" onClick={onClose}>
      <div className="w-full max-w-2xl rounded-lg border border-zinc-800 bg-zinc-950 p-5 max-h-[85vh] overflow-auto" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold flex items-center gap-2"><KeyRound className="h-5 w-5 text-blue-400" /> Logins — {target.full_name || target.email}</h2>
          <button onClick={onClose} className="rounded p-1 hover:bg-zinc-800"><X className="h-4 w-4" /></button>
        </div>
        {loading ? <LoadingState /> : error ? <div className="rounded border border-red-900 bg-red-950/20 p-3 mb-3"><p className="text-sm text-red-300">{error}</p><RetryButton onRetry={load} /></div> : (
          <>
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-sm font-semibold text-zinc-300">Active sessions ({sessions.length})</h3>
              <button onClick={revokeAll} disabled={busy === 'all' || sessions.length === 0} className="rounded bg-rose-700/60 hover:bg-rose-600 px-2 py-1 text-xs text-white disabled:opacity-40">Force logout everywhere</button>
            </div>
            {sessions.length === 0 ? <p className="text-xs text-zinc-500 mb-4">No active sessions.</p> : (
              <ul className="mb-4 space-y-2">
                {sessions.map((s) => (
                  <li key={s.id} className="rounded border border-zinc-800 bg-zinc-900/60 px-3 py-2 text-xs flex items-center justify-between gap-3">
                    <div>
                      <div className="text-zinc-300">{s.user_agent || 'Unknown device'}</div>
                      <div className="text-zinc-500">{s.ip_address || '—'} · started {fmtWhen(s.created_at)} · expires {fmtWhen(s.expires_at)}</div>
                    </div>
                    <button onClick={() => revoke(s.id)} disabled={busy === s.id} className="rounded bg-zinc-800 hover:bg-rose-700/70 px-2 py-1 disabled:opacity-40 shrink-0">Revoke</button>
                  </li>
                ))}
              </ul>
            )}
            <h3 className="text-sm font-semibold text-zinc-300 mb-2 flex items-center gap-1"><History className="h-4 w-4" /> Login history</h3>
            {history.length === 0 ? <p className="text-xs text-zinc-500">No login attempts recorded.</p> : (
              <table className="w-full text-xs"><thead className="bg-zinc-900 text-zinc-400"><tr><th className="text-left px-2 py-1">When</th><th className="text-left px-2 py-1">Method</th><th className="text-left px-2 py-1">IP</th><th className="text-left px-2 py-1">Result</th></tr></thead>
              <tbody>
                {history.map((h) => (
                  <tr key={h.id} className="border-t border-zinc-800">
                    <td className="px-2 py-1">{fmtWhen(h.created_at)}</td>
                    <td className="px-2 py-1">{h.method}</td>
                    <td className="px-2 py-1">{h.ip_address || '—'}</td>
                    <td className="px-2 py-1">{h.success ? <span className="text-emerald-300">success</span> : <span className="text-rose-300">failed{h.failure_reason ? ` — ${h.failure_reason}` : ''}</span>}</td>
                  </tr>
                ))}
              </tbody></table>
            )}
          </>
        )}
      </div>
    </div>
  );
}
