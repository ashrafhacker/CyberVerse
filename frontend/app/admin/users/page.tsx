'use client';
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Search, Filter, Shield, ChevronLeft, ChevronRight } from 'lucide-react';
import { useRequireAuth } from '@/lib/auth';
import { isAdmin, canModify } from '@/lib/roles';
import { LoadingState, EmptyState, RetryButton } from '@/components/AdminUI';
import { useAdminWs } from '@/lib/adminWs';

interface AdminUser {
  id: string; email: string; full_name: string; role: string; status: string;
  is_verified: boolean; is_2fa_enabled: boolean; created_at: string;
}

export default function AdminUsersPage() {
  const { user } = useRequireAuth();
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [page, setPage] = useState(1);
  const perPage = 20;
  const { lastEvent, connected } = useAdminWs();

  const load = useCallback(async () => {
    setLoading(true); setError(null);
    try {
      const url = new URL((process.env.NEXT_PUBLIC_API_URL ?? '/api/v1') + '/admin/users', typeof window !== 'undefined' ? window.location.origin : 'http://localhost');
      url.searchParams.set('page', String(page));
      url.searchParams.set('limit', String(perPage));
      if (search) url.searchParams.set('search', search);
      if (statusFilter !== 'all') url.searchParams.set('status', statusFilter);
      const res = await fetch(url.toString(), { credentials: 'include', headers: { Accept: 'application/json' } });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const json = await res.json();
      setUsers(json.data?.users ?? json.data ?? []);
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

  const visible = useMemo(() => {
    return users.filter((u) => {
      const matchSearch = !search || u.email.toLowerCase().includes(search.toLowerCase()) || (u.full_name || '').toLowerCase().includes(search.toLowerCase());
      const matchStatus = statusFilter === 'all' || u.status === statusFilter;
      return matchSearch && matchStatus;
    });
  }, [users, search, statusFilter]);

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
      <div className="text-xs text-zinc-500 mb-2">WS: {connected ? 'connected' : 'offline'} | Events delivered: {visible.length}</div>
      {loading ? <LoadingState /> : error ? <div className="rounded border border-red-900 bg-red-950/20 p-4"><p className="text-sm text-red-300">{error}</p><RetryButton onRetry={load} /></div> : visible.length === 0 ? <EmptyState title="No users" message="No users match filters." /> : (
        <div className="overflow-auto rounded border border-zinc-800">
          <table className="w-full text-sm"><thead className="bg-zinc-900 text-zinc-300"><tr><th className="text-left px-3 py-2">User</th><th>Role</th><th>Status</th><th>2FA</th><th>Verified</th></tr></thead>
          <tbody>
            {visible.map((u) => (
              <tr key={u.id} className="border-t border-zinc-800 hover:bg-zinc-900/40"><td className="px-3 py-2">{u.full_name || u.email}</td><td className="px-3 py-2 text-zinc-400">{u.role}</td><td className="px-3 py-2"><span className={`text-xs rounded px-1 ${u.status === 'active' ? 'bg-emerald-900/30 text-emerald-300' : u.status === 'pending' ? 'bg-amber-900/30 text-amber-300' : 'bg-rose-900/30 text-rose-300'}`}>{u.status}</span></td><td className="px-3 py-2">{u.is_2fa_enabled ? 'Yes' : 'No'}</td><td className="px-3 py-2">{u.is_verified ? 'Yes' : 'No'}</td></tr>
            ))}
          </tbody></table>
        </div>
      )}
      <div className="flex gap-2 mt-3"><button onClick={() => setPage(p => Math.max(1, p-1))} disabled={page <= 1} className="rounded bg-zinc-900 border border-zinc-800 px-2 py-1 text-sm"><ChevronLeft className="h-3 w-3" /></button><span className="self-center text-xs text-zinc-400">Page {page}</span><button onClick={() => setPage(p => p+1)} className="rounded bg-zinc-900 border border-zinc-800 px-2 py-1 text-sm"><ChevronRight className="h-3 w-3" /></button></div>
    </div>
  );
}
