'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import {
  Activity, AlertTriangle, ArrowDownRight, ArrowUpRight, Ban, BookOpen,
  CheckCircle2, ChevronRight, Clock3, Command, Database, Download, Gauge,
  LayoutDashboard, LifeBuoy, LockKeyhole, LogOut, Menu, RefreshCw, Search,
  Server, Settings2, Shield, ShieldAlert, ShieldCheck, Users, X,
} from 'lucide-react';
import Navbar from '@/components/Navbar';
import { LoadingScreen } from '@/components/TerminalCard';
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
type Section = 'overview' | 'users' | 'security' | 'content' | 'system';

const navItems: { id: Section; label: string; icon: typeof LayoutDashboard; detail: string }[] = [
  { id: 'overview', label: 'Overview', icon: LayoutDashboard, detail: 'Live platform summary' },
  { id: 'users', label: 'Identity & users', icon: Users, detail: 'Accounts and access' },
  { id: 'security', label: 'Security center', icon: ShieldCheck, detail: 'Security posture' },
  { id: 'content', label: 'Learning content', icon: BookOpen, detail: 'Courses and missions' },
  { id: 'system', label: 'System health', icon: Server, detail: 'Services and diagnostics' },
];

function statusTone(status?: string) {
  const s = (status ?? '').toLowerCase();
  if (['ok', 'healthy', 'up', 'active', 'published'].includes(s)) return 'good';
  if (['degraded', 'pending', 'warning'].includes(s)) return 'warn';
  if (['down', 'error', 'unhealthy', 'suspended', 'failed'].includes(s)) return 'bad';
  return 'neutral';
}
function Badge({ children, tone = 'neutral' }: { children: React.ReactNode; tone?: string }) {
  return <span className={`nx-badge nx-${tone}`}><span className="nx-dot" />{children}</span>;
}
function Metric({ label, value, icon: Icon, hint, trend, tone = 'cyan' }: {
  label: string; value: string | number; icon: typeof Users; hint: string; trend?: 'up' | 'down'; tone?: string;
}) {
  return (
    <article className="nx-metric">
      <div className="flex items-start justify-between gap-3">
        <div><p className="nx-muted text-xs">{label}</p><p className="mt-2 text-3xl font-semibold tracking-tight">{value}</p></div>
        <span className={`nx-metric-icon nx-${tone}`}><Icon size={19} /></span>
      </div>
      <div className="mt-4 flex items-center gap-2 text-xs nx-muted">
        {trend === 'up' && <ArrowUpRight size={14} className="text-emerald-400" />}
        {trend === 'down' && <ArrowDownRight size={14} className="text-amber-300" />}
        <span>{hint}</span>
      </div>
    </article>
  );
}

export default function AdminPage() {
  const { user, loading } = useRequireAuth();
  const router = useRouter();
  const [section, setSection] = useState<Section>('overview');
  const [overview, setOverview] = useState<AdminOverview | null>(null);
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [totalUsers, setTotalUsers] = useState(0);
  const [query, setQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busyUser, setBusyUser] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [mobileNav, setMobileNav] = useState(false);

  const loadDashboard = useCallback(async (quiet = false) => {
    if (!quiet) setRefreshing(true);
    setError(null);
    try {
      const [o, u] = await Promise.all([
        api.get<{ data: AdminOverview }>('/admin/overview'),
        api.get<{ data: AdminUsersData }>('/admin/users?page=1&page_size=50'),
      ]);
      setOverview(o.data);
      setUsers(u.data.users ?? []);
      setTotalUsers(u.data.total ?? o.data.total_users ?? 0);
      setLastUpdated(new Date());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to load admin data.');
    } finally {
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    if (!user) return;
    if (!user.role || !ADMIN_ROLES.includes(user.role)) {
      router.replace('/dashboard');
      return;
    }
    void loadDashboard();
  }, [user, router, loadDashboard]);

  const filteredUsers = useMemo(() => users.filter((u) => {
    const q = query.trim().toLowerCase();
    const matchesQuery = !q || [u.full_name, u.email, u.role, u.id].some((v) => (v ?? '').toLowerCase().includes(q));
    return matchesQuery && (statusFilter === 'all' || u.status.toLowerCase() === statusFilter);
  }), [users, query, statusFilter]);

  const updateStatus = async (target: AdminUser) => {
    const nextStatus = target.status === 'active' ? 'suspended' : 'active';
    const action = nextStatus === 'suspended' ? 'suspend' : 'restore';
    if (!window.confirm(`Are you sure you want to ${action} ${target.full_name || target.email}?`)) return;
    setBusyUser(target.id);
    setError(null);
    setNotice(null);
    try {
      await api.patch(`/admin/users/${target.id}/status`, { status: nextStatus });
      setUsers((list) => list.map((u) => u.id === target.id ? { ...u, status: nextStatus } : u));
      setNotice(`${target.email} was ${nextStatus === 'active' ? 'restored' : 'suspended'}.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : `Unable to ${action} account.`);
    } finally {
      setBusyUser(null);
    }
  };

  const exportUsers = () => {
    const rows = [
      ['Name', 'Email', 'Role', 'Status', 'Verified', '2FA', 'Created'],
      ...filteredUsers.map((u) => [u.full_name, u.email, u.role, u.status, String(u.is_verified), String(u.is_2fa_enabled), u.created_at]),
    ];
    const csv = rows.map((row) => row.map((cell) => `"${String(cell ?? '').replace(/"/g, '""')}"`).join(',')).join('\r\n');
    const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8;' }));
    const a = document.createElement('a');
    a.href = url; a.download = 'cyberverse-admin-users.csv'; a.click();
    URL.revokeObjectURL(url);
  };

  if (loading || !user) return <LoadingScreen />;

  const services = overview?.system_health?.services ?? {};
  const health = overview?.system_health?.status ?? 'unknown';

  return (
    <>
      <Navbar />
      <style jsx global>{`
        .nx-shell{min-height:calc(100vh - 64px);color:#e6f1ff;background:radial-gradient(ellipse at 75% -15%,rgba(0,217,255,.10),transparent 38%),#070b12}
        .nx-panel{background:linear-gradient(145deg,rgba(16,25,39,.94),rgba(9,15,25,.96));border:1px solid rgba(121,158,190,.16);border-radius:16px;box-shadow:0 12px 35px rgba(0,0,0,.12)}
        .nx-muted{color:#8294a9}.nx-eyebrow{font-size:10px;letter-spacing:.18em;text-transform:uppercase;color:#64dff2;font-weight:700}
        .nx-metric{border:1px solid rgba(121,158,190,.16);background:linear-gradient(145deg,rgba(18,29,44,.95),rgba(10,17,27,.95));border-radius:15px;padding:19px;min-width:0}
        .nx-metric-icon{display:grid;place-items:center;width:40px;height:40px;border-radius:12px;background:rgba(49,212,240,.10);color:#51dff5}
        .nx-violet{background:rgba(167,139,250,.12);color:#b8a2ff}.nx-emerald{background:rgba(52,211,153,.12);color:#55e3ad}.nx-amber{background:rgba(251,191,36,.12);color:#facc68}
        .nx-btn{display:inline-flex;align-items:center;justify-content:center;gap:8px;border:1px solid rgba(121,158,190,.22);background:rgba(18,29,44,.75);border-radius:10px;padding:9px 12px;font-size:12px;font-weight:600;transition:.18s}
        .nx-btn:hover{border-color:rgba(65,220,245,.55);background:rgba(24,45,62,.95)}.nx-btn:disabled{opacity:.5;cursor:wait}
        .nx-input{width:100%;background:#09111c;border:1px solid rgba(121,158,190,.22);border-radius:10px;padding:10px 12px;color:#e6f1ff;outline:none;font-size:13px}
        .nx-input:focus{border-color:#41d9f1;box-shadow:0 0 0 3px rgba(65,217,241,.08)}
        .nx-nav{display:flex;align-items:center;gap:10px;width:100%;padding:10px 12px;border-radius:10px;color:#91a4ba;text-align:left;font-size:13px;transition:.18s}
        .nx-nav:hover{background:rgba(80,110,145,.1);color:#e6f1ff}.nx-nav.active{background:linear-gradient(90deg,rgba(0,217,255,.14),rgba(0,217,255,.03));color:#70e7f8;border:1px solid rgba(65,217,241,.17)}
        .nx-badge{display:inline-flex;align-items:center;gap:6px;padding:4px 8px;border-radius:99px;font-size:10px;font-weight:700;letter-spacing:.03em;border:1px solid rgba(121,158,190,.15);white-space:nowrap}
        .nx-dot{width:5px;height:5px;border-radius:99px;background:currentColor}.nx-good{color:#55e3ad;background:rgba(52,211,153,.07)}.nx-warn{color:#facc68;background:rgba(251,191,36,.07)}.nx-bad{color:#ff7b8d;background:rgba(251,113,133,.07)}.nx-neutral{color:#9badc2;background:rgba(148,163,184,.06)}
        .nx-table-wrap{overflow-x:auto}.nx-table{width:100%;border-collapse:collapse;min-width:700px}.nx-table th{text-align:left;font-size:10px;text-transform:uppercase;letter-spacing:.12em;color:#72869d;font-weight:700;padding:12px 16px;border-bottom:1px solid rgba(121,158,190,.13)}.nx-table td{padding:14px 16px;border-bottom:1px solid rgba(121,158,190,.09);font-size:12px}.nx-table tr:last-child td{border-bottom:0}.nx-table tbody tr:hover{background:rgba(90,135,170,.045)}
        .nx-grid-bg{background-image:linear-gradient(rgba(105,143,173,.035) 1px,transparent 1px),linear-gradient(90deg,rgba(105,143,173,.035) 1px,transparent 1px);background-size:28px 28px}
        @media(max-width:800px){.nx-sidebar{display:none}.nx-sidebar.mobile-open{display:block;position:absolute;z-index:30;left:12px;right:12px;top:72px;box-shadow:0 20px 60px #000}.nx-content{padding:18px!important}}
      `}</style>
      <main className="nx-shell nx-grid-bg">
        <div className="mx-auto max-w-[1600px] px-4 py-5 lg:px-7">
          <div className="mb-5 flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <button className="nx-btn lg:hidden" aria-label="Toggle navigation" onClick={() => setMobileNav(!mobileNav)}>{mobileNav ? <X size={16}/> : <Menu size={16}/>}</button>
              <div className="grid h-11 w-11 place-items-center rounded-xl border border-cyan-300/20 bg-cyan-300/10 text-cyan-200"><Shield size={22}/></div>
              <div>
                <div className="flex flex-wrap items-center gap-2"><h1 className="text-lg font-semibold tracking-tight">CyberVerse <span className="text-cyan-300">NEXUS</span></h1><Badge tone="good">OWNER CONSOLE</Badge></div>
                <p className="nx-muted mt-0.5 text-[11px]">Privileged platform control plane</p>
              </div>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <div className="hidden items-center gap-2 rounded-lg border border-white/10 px-3 py-2 text-[11px] text-slate-400 sm:flex"><span className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-400"/>{health === 'unknown' ? 'Checking services' : `System ${health}`}</div>
              <button className="nx-btn" onClick={() => void loadDashboard()} disabled={refreshing}><RefreshCw size={14} className={refreshing ? 'animate-spin' : ''}/>{refreshing ? 'Refreshing' : 'Refresh data'}</button>
              <div className="hidden h-9 w-9 place-items-center rounded-full border border-cyan-300/25 bg-cyan-300/10 text-xs font-bold text-cyan-100 sm:grid">{(user.full_name || user.email || 'A').slice(0,1).toUpperCase()}</div>
            </div>
          </div>

          <div className="grid gap-5 lg:grid-cols-[220px_minmax(0,1fr)]">
            <aside className={`nx-panel nx-sidebar h-fit p-3 ${mobileNav ? 'mobile-open' : ''}`}>
              <p className="nx-eyebrow px-3 pb-3 pt-2">Control plane</p>
              <nav className="space-y-1">
                {navItems.map((item) => {
                  const Icon = item.icon;
                  return <button key={item.id} className={`nx-nav ${section === item.id ? 'active' : ''}`} onClick={() => { setSection(item.id); setMobileNav(false); }}>
                    <Icon size={16}/><span className="flex-1">{item.label}</span>{section === item.id && <ChevronRight size={14}/>}
                  </button>;
                })}
              </nav>
              <div className="my-4 border-t border-white/10"/>
              <p className="nx-eyebrow px-3 pb-3">Platform</p>
              <a className="nx-nav" href="/dashboard"><LayoutDashboard size={16}/>Student experience<ChevronRight size={14} className="ml-auto"/></a>
              <a className="nx-nav" href="/instructor"><BookOpen size={16}/>Instructor studio<ChevronRight size={14} className="ml-auto"/></a>
              <div className="mt-5 rounded-xl border border-cyan-300/10 bg-cyan-300/[.04] p-3">
                <div className="mb-2 flex items-center gap-2 text-cyan-200"><LockKeyhole size={14}/><span className="text-xs font-semibold">Privileged session</span></div>
                <p className="nx-muted text-[10px] leading-relaxed">Actions are checked by the API. UI access alone does not grant server permissions.</p>
              </div>
              <div className="mt-4 flex items-center gap-2 px-3 text-[10px] nx-muted"><Command size={12}/>NEXUS CONTROL / v1</div>
            </aside>

            <section className="nx-content min-w-0 p-1">
              <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
                <div><p className="nx-eyebrow">CyberVerse / Admin / {section}</p><h2 className="mt-2 text-2xl font-semibold tracking-tight">{navItems.find(n => n.id === section)?.label}</h2><p className="nx-muted mt-1 text-xs">{navItems.find(n => n.id === section)?.detail}</p></div>
                <p className="nx-muted text-[10px]">{lastUpdated ? `Updated ${lastUpdated.toLocaleTimeString()}` : 'Awaiting first data sync'}</p>
              </div>

              {error && <div role="alert" className="mb-4 flex items-start gap-3 rounded-xl border border-rose-400/20 bg-rose-400/[.06] p-4 text-sm text-rose-200"><AlertTriangle size={17} className="mt-0.5 shrink-0"/><div className="flex-1">{error}</div><button aria-label="Dismiss error" onClick={() => setError(null)}><X size={15}/></button></div>}
              {notice && <div role="status" className="mb-4 flex items-center gap-3 rounded-xl border border-emerald-400/20 bg-emerald-400/[.06] p-3 text-xs text-emerald-200"><CheckCircle2 size={16}/><span className="flex-1">{notice}</span><button onClick={() => setNotice(null)} aria-label="Dismiss notice"><X size={14}/></button></div>}

              {section === 'overview' && <>
                <div className="mb-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                  <Metric label="Registered users" value={overview?.total_users ?? '—'} icon={Users} hint="Total accounts reported by API" tone="cyan"/>
                  <Metric label="Pending support" value={overview?.pending_tickets ?? '—'} icon={LifeBuoy} hint="Tickets requiring attention" tone="amber"/>
                  <Metric label="Active subscriptions" value={overview?.active_subscriptions ?? '—'} icon={Activity} hint="Current subscription count" tone="violet"/>
                  <Metric label="Announcements" value={overview?.published_announcements ?? '—'} icon={BookOpen} hint="Published platform notices" tone="emerald"/>
                </div>
                <div className="grid gap-4 xl:grid-cols-[1.35fr_1fr]">
                  <article className="nx-panel p-5">
                    <div className="mb-4 flex items-center justify-between gap-3"><div><h3 className="text-sm font-semibold">Service health</h3><p className="nx-muted mt-1 text-[11px]">Status reported by the existing admin API</p></div><Badge tone={statusTone(health)}>{health.toUpperCase()}</Badge></div>
                    <div className="space-y-2">
                      {Object.entries(services).length ? Object.entries(services).map(([name, value]) => <div key={name} className="flex items-center justify-between rounded-lg border border-white/[.06] bg-white/[.015] px-3 py-3"><div className="flex items-center gap-3"><span className="grid h-8 w-8 place-items-center rounded-lg bg-white/[.04] text-cyan-200"><Server size={15}/></span><div><p className="text-xs font-medium capitalize">{name.replace(/_/g, ' ')}</p><p className="nx-muted mt-0.5 text-[10px]">Health probe</p></div></div><Badge tone={statusTone(value)}>{String(value).toUpperCase()}</Badge></div>) : <p className="nx-muted rounded-lg border border-dashed border-white/10 p-4 text-xs">Service-level health details are not currently returned by the API.</p>}
                    </div>
                  </article>
                  <article className="nx-panel p-5">
                    <div className="mb-4 flex items-center gap-2"><ShieldCheck size={17} className="text-cyan-200"/><h3 className="text-sm font-semibold">Security posture</h3></div>
                    <div className="space-y-3">
                      <div className="flex gap-3"><div className="mt-0.5 text-emerald-300"><CheckCircle2 size={16}/></div><div><p className="text-xs font-medium">Role-gated admin page</p><p className="nx-muted mt-1 text-[11px]">Frontend redirects users without an approved admin role.</p></div></div>
                      <div className="flex gap-3"><div className="mt-0.5 text-cyan-200"><LockKeyhole size={16}/></div><div><p className="text-xs font-medium">API authorization required</p><p className="nx-muted mt-1 text-[11px]">Privileged endpoints must enforce permissions independently.</p></div></div>
                      <div className="flex gap-3"><div className="mt-0.5 text-amber-200"><AlertTriangle size={16}/></div><div><p className="text-xs font-medium">Review MFA coverage</p><p className="nx-muted mt-1 text-[11px]">Use Identity & users to inspect the 2FA status returned for accounts.</p></div></div>
                    </div>
                    <button className="nx-btn mt-5 w-full" onClick={() => setSection('security')}>Open security center <ChevronRight size={14}/></button>
                  </article>
                </div>
                <article className="nx-panel mt-4 p-5">
                  <div className="mb-4 flex items-center justify-between"><div><h3 className="text-sm font-semibold">Recent account registrations</h3><p className="nx-muted mt-1 text-[11px]">Latest accounts returned by the admin users endpoint</p></div><button className="nx-btn" onClick={() => setSection('users')}>Manage users <ChevronRight size={14}/></button></div>
                  <UserTable users={users.slice(0, 6)} busyUser={busyUser} onStatus={updateStatus}/>
                </article>
              </>}

              {section === 'users' && <article className="nx-panel p-5">
                <div className="mb-4 flex flex-wrap items-center justify-between gap-3"><div><h3 className="text-sm font-semibold">Identity & access</h3><p className="nx-muted mt-1 text-[11px]">{totalUsers} total accounts · {filteredUsers.length} shown in loaded page</p></div><button className="nx-btn" onClick={exportUsers}><Download size={14}/>Export CSV</button></div>
                <div className="mb-4 grid gap-3 sm:grid-cols-[minmax(0,1fr)_170px]">
                  <div className="relative"><Search size={15} className="nx-muted absolute left-3 top-1/2 -translate-y-1/2"/><input className="nx-input pl-9" aria-label="Search users" placeholder="Search name, email, role, or ID..." value={query} onChange={(e) => setQuery(e.target.value)}/></div>
                  <select className="nx-input" aria-label="Filter by status" value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}><option value="all">All statuses</option><option value="active">Active</option><option value="pending">Pending</option><option value="suspended">Suspended</option></select>
                </div>
                <UserTable users={filteredUsers} busyUser={busyUser} onStatus={updateStatus}/>
              </article>}

              {section === 'security' && <div className="grid gap-4 xl:grid-cols-2">
                <article className="nx-panel p-5"><div className="mb-4 flex items-center gap-2"><ShieldAlert size={17} className="text-cyan-200"/><h3 className="text-sm font-semibold">Access controls</h3></div>
                  {[['Admin role gate','The page checks administrator, developer, and super_admin roles.'],['Server-side enforcement','Every sensitive API route must independently validate role and permission.'],['Session protection','Keep access tokens short-lived and refresh tokens rotated and revocable.'],['Step-up verification','Require fresh authentication or MFA for high-impact changes.']].map(([title,desc])=><div key={title} className="border-b border-white/[.07] py-3 last:border-0"><p className="text-xs font-medium">{title}</p><p className="nx-muted mt-1 text-[11px] leading-relaxed">{desc}</p></div>)}
                </article>
                <article className="nx-panel p-5"><div className="mb-4 flex items-center gap-2"><Gauge size={17} className="text-amber-200"/><h3 className="text-sm font-semibold">Account hygiene</h3></div>
                  <div className="grid grid-cols-2 gap-3"><div className="rounded-xl border border-white/[.07] p-4"><p className="nx-muted text-[11px]">Verified accounts</p><p className="mt-2 text-2xl font-semibold">{users.filter(u=>u.is_verified).length}</p></div><div className="rounded-xl border border-white/[.07] p-4"><p className="nx-muted text-[11px]">2FA enabled</p><p className="mt-2 text-2xl font-semibold">{users.filter(u=>u.is_2fa_enabled).length}</p></div><div className="rounded-xl border border-white/[.07] p-4"><p className="nx-muted text-[11px]">Suspended</p><p className="mt-2 text-2xl font-semibold">{users.filter(u=>u.status==='suspended').length}</p></div><div className="rounded-xl border border-white/[.07] p-4"><p className="nx-muted text-[11px]">Loaded accounts</p><p className="mt-2 text-2xl font-semibold">{users.length}</p></div></div>
                  <p className="nx-muted mt-4 text-[10px] leading-relaxed">Counts are calculated from the currently loaded account page, not a complete database-wide security audit.</p>
                </article>
              </div>}

              {section === 'content' && <div className="grid gap-4 md:grid-cols-2">
                {[{title:'Courses & learning paths',desc:'Open the existing course experience to review what learners see.',href:'/courses',icon:BookOpen},{title:'Missions & challenges',desc:'Review the mission experience and safe training activities.',href:'/missions',icon:Shield},{title:'Instructor studio',desc:'Manage learning content through the instructor area.',href:'/instructor',icon:Settings2},{title:'CyberVerse labs',desc:'Review the platform’s existing lab experience.',href:'/labs',icon:Database}].map(item=>{const Icon=item.icon;return <a key={item.title} href={item.href} className="nx-panel p-5 transition hover:border-cyan-300/30"><div className="mb-4 flex items-center justify-between"><span className="grid h-10 w-10 place-items-center rounded-xl bg-cyan-300/10 text-cyan-200"><Icon size={18}/></span><ChevronRight size={16} className="nx-muted"/></div><h3 className="text-sm font-semibold">{item.title}</h3><p className="nx-muted mt-2 text-xs leading-relaxed">{item.desc}</p><p className="mt-4 text-[10px] font-semibold uppercase tracking-wider text-cyan-200">Open module ↗</p></a>})}
              </div>}

              {section === 'system' && <div className="grid gap-4 xl:grid-cols-2">
                <article className="nx-panel p-5"><div className="mb-4 flex items-center gap-2"><Server size={17} className="text-cyan-200"/><h3 className="text-sm font-semibold">Runtime health</h3></div><div className="mb-3 flex items-center justify-between rounded-xl border border-white/[.07] p-4"><div><p className="text-xs font-medium">Platform health</p><p className="nx-muted mt-1 text-[10px]">Reported by /admin/overview</p></div><Badge tone={statusTone(health)}>{health.toUpperCase()}</Badge></div>{Object.entries(services).map(([name,value])=><div key={name} className="flex items-center justify-between border-b border-white/[.06] py-3 last:border-0"><span className="text-xs capitalize">{name.replace(/_/g,' ')}</span><Badge tone={statusTone(value)}>{String(value)}</Badge></div>)}<button className="nx-btn mt-4 w-full" onClick={() => void loadDashboard()} disabled={refreshing}><RefreshCw size={14}/>Run health refresh</button></article>
                <article className="nx-panel p-5"><div className="mb-4 flex items-center gap-2"><Database size={17} className="text-violet-200"/><h3 className="text-sm font-semibold">Operations guardrails</h3></div><p className="nx-muted text-xs leading-relaxed">This console intentionally does not expose arbitrary shell execution, raw database credentials, or one-click destructive infrastructure actions in the browser.</p><div className="mt-4 space-y-2">{['Use audited server-side jobs for maintenance','Restrict database access to least-privilege service accounts','Keep backups encrypted and test restores','Require confirmation and audit records for high-impact actions'].map(t=><div key={t} className="flex gap-2 rounded-lg border border-white/[.06] p-3 text-[11px]"><CheckCircle2 size={14} className="shrink-0 text-emerald-300"/><span>{t}</span></div>)}</div></article>
              </div>}
              <footer className="nx-muted mt-5 flex flex-wrap items-center justify-between gap-2 px-1 text-[10px]"><span>CyberVerse Nexus · Owner control plane</span><span className="flex items-center gap-2"><Clock3 size={11}/>Data is live only where the backend API confirms it</span></footer>
            </section>
          </div>
        </div>
      </main>
    </>
  );
}

function UserTable({ users, busyUser, onStatus }: {
  users: AdminUser[];
  busyUser: string | null;
  onStatus: (user: AdminUser) => void;
}) {
  if (!users.length) return <div className="nx-muted rounded-xl border border-dashed border-white/10 p-8 text-center text-xs">No accounts match this view.</div>;
  return <div className="nx-table-wrap"><table className="nx-table"><thead><tr><th>Account</th><th>Role</th><th>Status</th><th>Security</th><th>Joined</th><th>Action</th></tr></thead><tbody>
    {users.map((u) => <tr key={u.id}>
      <td><div className="flex items-center gap-3"><span className="grid h-8 w-8 shrink-0 place-items-center rounded-full border border-white/10 bg-white/[.04] text-[10px] font-bold text-cyan-100">{(u.full_name || u.email || '?').slice(0,1).toUpperCase()}</span><div className="min-w-0"><p className="max-w-[190px] truncate font-medium">{u.full_name || 'Unnamed user'}</p><p className="nx-muted mt-1 max-w-[220px] truncate text-[10px]">{u.email}</p></div></div></td>
      <td><span className="rounded-md border border-white/10 px-2 py-1 text-[10px]">{u.role}</span></td>
      <td><Badge tone={statusTone(u.status)}>{u.status}</Badge></td>
      <td><div className="flex flex-wrap gap-1">{u.is_verified && <Badge tone="good">Verified</Badge>}{u.is_2fa_enabled && <Badge tone="good">2FA</Badge>}{!u.is_2fa_enabled && <Badge tone="warn">No 2FA</Badge>}</div></td>
      <td className="nx-muted whitespace-nowrap">{u.created_at ? new Date(u.created_at).toLocaleDateString() : '—'}</td>
      <td>{u.status === 'active' || u.status === 'suspended' ? <button disabled={busyUser === u.id} onClick={() => onStatus(u)} className="nx-btn py-1.5 text-[10px] disabled:opacity-50">{busyUser === u.id ? <RefreshCw size={12} className="animate-spin"/> : u.status === 'active' ? <Ban size={12}/> : <CheckCircle2 size={12} />}{u.status === 'active' ? 'Suspend' : 'Restore'}</button> : <span className="nx-muted text-[10px]">No action</span>}</td>
    </tr>)}
  </tbody></table></div>;
}
