'use client';

import { Globe, Trophy, Zap, Users, Flag, Star, ChevronLeft, ChevronRight, Play, Shield, Sword, ShieldAlert } from 'lucide-react';
import Link from 'next/link';
import { api } from '@/lib/api';

interface ArenaStats {
  activeChallenges: number;
  totalPlayers: number;
  activeEnvironments: number;
  currentSeason: { name: string; endsAt: string };
}

export default function ArenaPage() {
  const [stats, setStats] = useState<ArenaStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchStats();
  }, []);

  async function fetchStats() {
    try {
      const res = await api.get<ArenaStats>('/game/arena/stats');
      setStats(res.data);
    } catch {
      setStats(null);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-cyber-bg text-cyber-text">
      <div className="mx-auto max-w-7xl px-6 py-12">
        <header className="mb-12">
          <h1 className="mb-4 text-4xl font-bold tracking-tight md:text-5xl">
            CYBERVERSE <span className="text-cyber-primary">GLOBAL ARENA</span>
          </h1>
          <p className="mx-auto max-w-2xl text-lg text-cyber-muted">
            Enter the arena. Compete in real-time challenges, join tournaments, and climb the global rankings.
          </p>
        </header>

        {/* Stats Cards */}
        <div className="mb-12 grid gap-4 md:grid-cols-4">
          {stats ? (
            <>
              <article className="rounded-xl border border-cyber-border bg-cyber-surface/60 p-6">
                <div className="flex items-center gap-4">
                  <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-cyber-primary/20">
                    <Sword className="h-7 w-7 text-cyber-primary" />
                  </div>
                  <div>
                    <p className="text-3xl font-bold text-cyber-primary">{stats.activeChallenges}</p>
                    <p className="text-sm text-cyber-muted">Active Challenges</p>
                  </div>
                </div>
              </article>
              <article className="rounded-xl border border-cyber-border bg-cyber-surface/60 p-6">
                <div className="flex items-center gap-4">
                  <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-emerald-500/20">
                    <Users className="h-7 w-7 text-emerald-400" />
                  </div>
                  <div>
                    <p className="text-3xl font-bold text-emerald-400">{stats.totalPlayers.toLocaleString()}</p>
                    <p className="text-sm text-cyber-muted">Active Players</p>
                  </div>
                </div>
              </article>
              <article className="rounded-xl border border-cyber-border bg-cyber-surface/60 p-6">
                <div className="flex items-center gap-4">
                  <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-violet-500/20">
                    <Shield className="h-7 w-7 text-violet-400" />
                  </div>
                  <div>
                    <p className="text-3xl font-bold text-violet-400">{stats.activeEnvironments}</p>
                    <p className="text-sm text-cyber-muted">Live Environments</p>
                  </div>
                </div>
              </article>
              <article className="rounded-xl border border-cyber-border bg-cyber-surface/60 p-6">
                <div className="flex items-center gap-4">
                  <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-amber-500/20">
                    <Trophy className="h-7 w-7 text-amber-400" />
                  </div>
                  <div>
                    <p className="text-3xl font-bold text-amber-400">{stats.currentSeason?.name || 'Season 1'}</p>
                    <p className="text-sm text-cyber-muted">Current Season</p>
                  </div>
                </div>
              </article>
            </>
          ) : (
            Array.from({ length: 4 }).map((_, i) => (
              <article key={i} className="animate-pulse rounded-xl border border-cyber-border bg-cyber-surface/60 p-6">
                <div className="h-6 w-24 bg-cyber-border rounded" />
                <div className="mt-2 h-4 w-16 bg-cyber-border rounded" />
              </article>
            ))
          )}
        </div>

        {/* Main Grid */}
        <div className="grid gap-6 lg:grid-cols-3">
          {/* PLAY NOW */}
          <article className="lg:col-span-2 space-y-6">
            <section className="rounded-2xl border border-cyber-primary/30 bg-gradient-to-br from-cyber-primary/10 via-violet-500/10 to-cyan-500/10 p-8">
              <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-6">
                <div>
                  <h2 className="mb-2 text-2xl font-bold text-cyber-primary">CYBERVERSE ARENA</h2>
                  <p className="text-cyber-muted">
                    Jump into live challenges. Spin up isolated environments. Capture flags. Earn XP.
                    Real-time scoring, global leaderboards, seasonal rewards.
                  </p>
                </div>
                <Link
                  href="/game"
                  className="flex h-14 min-w-[180px] items-center justify-center rounded-lg border-2 border-cyber-primary bg-cyber-primary/10 px-8 font-bold text-cyber-primary hover:bg-cyber-primary/20 transition-all"
                >
                  <Play className="h-6 w-6 mr-2" />
                  PLAY NOW
                </Link>
              </div>
            </section>

            {/* Quick Access Cards */}
            <div className="grid gap-4 md:grid-cols-3">
              <Link
                href="/game"
                className="group rounded-xl border border-cyber-border bg-cyber-surface/60 p-6 transition-all hover:border-cyber-primary/60 hover:shadow-[0_0_24px_rgba(0,229,255,0.15)]"
              >
                <div className="mb-4 flex items-center gap-3">
                  <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-cyber-primary/20">
                    <Sword className="h-7 w-7 text-cyber-primary" />
                  </div>
                  <div>
                    <h3 className="font-bold group-hover:text-cyber-primary transition-colors">Challenges</h3>
                    <p className="text-sm text-cyber-muted">Browse all challenges</p>
                  </div>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-cyber-primary">Browse →</span>
                  <span className="text-2xl text-cyber-primary">→</span>
                </div>
              </Link>

              <Link
                href="/game/tournaments"
                className="group rounded-xl border border-cyber-border bg-cyber-surface/60 p-6 transition-all hover:border-cyber-primary/60 hover:shadow-[0_0_24px_rgba(0,229,255,0.15)]"
              >
                <div className="mb-4 flex items-center gap-3">
                  <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-amber-500/20">
                    <Trophy className="h-7 w-7 text-amber-400" />
                  </div>
                  <div>
                    <h3 className="font-bold group-hover:text-cyber-primary transition-colors">Tournaments</h3>
                    <p className="text-sm text-cyber-muted">Competitive events</p>
                  </div>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-cyber-primary">View →</span>
                  <span className="text-2xl text-cyber-primary">→</span>
                </div>
              </Link>

              <Link
                href="/game/teams"
                className="group rounded-xl border border-cyber-border bg-cyber-surface/60 p-6 transition-all hover:border-cyber-primary/60 hover:shadow-[0_0_24px_rgba(0,229,255,0.15)]"
              >
                <div className="mb-4 flex items-center gap-3">
                  <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-emerald-500/20">
                    <Users className="h-7 w-7 text-emerald-400" />
                  </div>
                  <div>
                    <h3 className="font-bold group-hover:text-cyber-primary transition-colors">Teams</h3>
                    <p className="text-sm text-cyber-muted">Join or create a team</p>
                  </div>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-cyber-primary">Explore →</span>
                  <span className="text-2xl text-cyber-primary">→</span>
                </div>
              </Link>
            </div>
          </article>

          {/* SIDEBAR */}
          <aside className="space-y-6">
            <section className="rounded-xl border border-cyber-border bg-cyber-surface/60 p-6">
              <h3 className="mb-4 flex items-center gap-2 text-lg font-semibold text-cyber-primary">
                <Flag className="h-5 w-5" />
                Current Season
              </h3>
              <div className="space-y-3">
                <div className="rounded-lg border border-cyber-border bg-cyber-bg p-4">
                  <p className="mb-1 text-sm font-medium text-cyber-text">{stats?.currentSeason?.name || 'CYBERVERSE SEASON 01'}</p>
                  <p className="mb-2 text-sm text-cyber-muted">OPERATION BLACKOUT</p>
                  <div className="flex items-center justify-between text-xs text-cyber-muted">
                    <span>Ends: {stats?.currentSeason?.endsAt ? new Date(stats.currentSeason.endsAt).toLocaleDateString() : 'TBD'}</span>
                    <span className="text-amber-400">Active</span>
                  </div>
                </div>
              </div>
            </section>

            <section className="rounded-xl border border-cyber-border bg-cyber-surface/60 p-6">
              <h3 className="mb-4 flex items-center gap-2 text-lg font-semibold">
                <Zap className="h-5 w-5 text-amber-400" />
                Quick Actions
              </h3>
              <div className="space-y-2">
                <Link
                  href="/game"
                  className="flex items-center gap-3 rounded-lg border border-cyber-border bg-cyber-surface px-4 py-3 text-left transition-all hover:border-cyber-primary/60 hover:bg-cyber-primary/10"
                >
                  <Sword className="h-5 w-5 text-cyber-primary" />
                  <span>Browse Challenges</span>
                </Link>
                <Link
                  href="/game/tournaments"
                  className="flex items-center gap-3 rounded-lg border border-cyber-border bg-cyber-surface px-4 py-3 text-left transition-all hover:border-cyber-primary/60 hover:bg-cyber-primary/10"
                >
                  <Trophy className="h-5 w-5 text-amber-400" />
                  <span>Join Tournament</span>
                </Link>
                <Link
                  href="/game/teams"
                  className="flex items-center gap-3 rounded-lg border border-cyber-border bg-cyber-surface px-4 py-3 text-left transition-all hover:border-cyber-primary/60 hover:bg-cyber-primary/10"
                >
                  <Users className="h-5 w-5 text-emerald-400" />
                  <span>Find a Team</span>
                </Link>
                <Link
                  href="/global-arena"
                  className="flex items-center gap-3 rounded-lg border border-cyber-border bg-cyber-surface px-4 py-3 text-left transition-all hover:border-cyber-primary/60 hover:bg-cyber-primary/10"
                >
                  <Flag className="h-5 w-5 text-cyber-primary" />
                  <span>View Leaderboard</span>
                </Link>
              </div>
            </section>

            <section className="rounded-xl border border-cyber-border bg-cyber-surface/60 p-6">
              <h3 className="mb-4 flex items-center gap-2 text-lg font-semibold">
                <ShieldAlert className="h-5 w-5 text-amber-400" />
                Safety Notice
              </h3>
              <p className="text-sm text-cyber-muted">
                All CyberVerse challenges run in isolated, controlled environments. No real-world systems
                are targeted. All organizations, identities, and infrastructure are fictional.
              </p>
            </section>
          </aside>
        </div>
      </div>
    </div>
  );
}