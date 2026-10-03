'use client';

import { useState, useEffect } from 'react';
import { Trophy, Calendar, Users, Clock, Flag, Star, ChevronLeft, ChevronRight, Lock, ArrowRight } from 'lucide-react';
import Link from 'next/link';
import { api } from '@/lib/api';

interface Tournament {
  id: string;
  name: string;
  description: string;
  startAt: string;
  endAt: string;
  maxPlayers: number;
  maxTeams: number;
  status: 'upcoming' | 'active' | 'completed' | 'cancelled';
  rules: string;
  seasonId: string;
  registeredPlayers: number;
  registeredTeams: number;
}

interface TournamentsResponse {
  tournaments: Tournament[];
  total: number;
  page: number;
  pageSize: number;
}

const STATUS_COLORS = {
  upcoming: 'bg-sky-500/20 text-sky-400 border-sky-500/30',
  active: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
  completed: 'bg-violet-500/20 text-violet-400 border-violet-500/30',
  cancelled: 'bg-cyber-border text-cyber-muted',
};

const TABS = [
  { id: 'all', label: 'ALL' },
  { id: 'upcoming', label: 'UPCOMING' },
  { id: 'active', label: 'LIVE' },
  { id: 'completed', label: 'COMPLETED' },
] as const;

export default function TournamentsPage() {
  const [activeTab, setActiveTab] = useState('all');
  const [tournaments, setTournaments] = useState<Tournament[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const pageSize = 12;

  useEffect(() => {
    fetchTournaments();
  }, [activeTab, page]);

  async function fetchTournaments() {
    setLoading(true);
    try {
      const res = await api.get<TournamentsResponse>('/game/tournaments', {
        params: { status: activeTab === 'all' ? undefined : activeTab, page, pageSize },
      });
      setTournaments(res.data.tournaments);
      setTotal(res.data.total);
    } catch {
      setTournaments([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  }

  function formatDate(dateStr: string) {
    return new Date(dateStr).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  }

  function getStatusClass(status: string) {
    return STATUS_COLORS[status as keyof typeof STATUS_COLORS] || 'bg-cyber-border text-cyber-muted';
  }

  return (
    <div className="min-h-screen bg-cyber-bg text-cyber-text">
      <div className="mx-auto max-w-7xl px-6 py-12">
        <header className="mb-8">
          <h1 className="mb-4 text-4xl font-bold tracking-tight md:text-5xl">
            CYBERVERSE <span className="text-cyber-primary">TOURNAMENTS</span>
          </h1>
          <p className="mx-auto max-w-2xl text-lg text-cyber-muted">
            Compete in structured events. Solo, team, college, or global — climb the brackets.
          </p>
        </header>

        <nav className="mb-6 overflow-x-auto" aria-label="Tournament filters">
          <ul className="flex gap-2 min-w-max" role="tablist">
            {TABS.map(({ id, label }) => (
              <li key={id} role="presentation">
                <button
                  onClick={() => setActiveTab(id)}
                  className={`rounded-lg px-4 py-2 text-sm font-medium transition-all whitespace-nowrap ${
                    activeTab === id
                      ? 'bg-cyber-primary/20 border border-cyber-primary text-cyber-primary'
                      : 'bg-cyber-surface/60 border border-cyber-border text-cyber-muted hover:border-cyber-primary/60 hover:text-cyber-text'
                  }`}
                  role="tab"
                  aria-selected={activeTab === id}
                >
                  {label}
                </button>
              </li>
            ))}
          </ul>
        </nav>

        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {loading ? (
            Array.from({ length: 6 }).map((_, i) => (
              <article key={i} className="animate-pulse rounded-xl border border-cyber-border bg-cyber-surface/60 p-6">
                <div className="h-6 w-3/4 bg-cyber-border rounded" />
                <div className="mt-2 h-4 w-full bg-cyber-border rounded" />
                <div className="mt-4 flex gap-2">
                  <div className="h-6 w-20 bg-cyber-border rounded-full" />
                  <div className="h-6 w-24 bg-cyber-border rounded-full" />
                </div>
              </article>
            ))
          ) : tournaments.length === 0 ? (
            <div className="col-span-full text-center py-12">
              <Trophy className="mx-auto mb-4 h-12 w-12 text-cyber-muted" />
              <h3 className="mb-2 text-xl font-semibold">No tournaments found</h3>
              <p className="text-cyber-muted">Check back soon for upcoming events.</p>
            </div>
          ) : (
            tournaments.map((tournament) => (
              <article
                key={tournament.id}
                className="group relative overflow-hidden rounded-xl border border-cyber-border bg-cyber-surface/60 p-6 transition-all hover:border-cyber-primary/60 hover:shadow-[0_0_24px_rgba(0,229,255,0.15)]"
              >
                <div className="mb-4 flex items-start justify-between">
                  <div>
                    <h3 className="font-bold text-lg group-hover:text-cyber-primary transition-colors">
                      {tournament.name}
                    </h3>
                    <p className="text-sm text-cyber-muted">{tournament.description}</p>
                  </div>
                  <span className={`rounded-full border px-2 py-0.5 text-xs font-medium ${getStatusClass(tournament.status)}`}>
                    {tournament.status.toUpperCase()}
                  </span>
                </div>

                <div className="mb-4 flex flex-wrap gap-3 text-xs text-cyber-muted">
                  <span className="flex items-center gap-1">
                    <Calendar className="h-3.5 w-3.5" />
                    {formatDate(tournament.startAt)} - {formatDate(tournament.endAt)}
                  </span>
                  <span className="flex items-center gap-1">
                    <Users className="h-3.5 w-3.5" />
                    {tournament.registeredPlayers}/{tournament.maxPlayers} players
                  </span>
                  <span className="flex items-center gap-1">
                    <Flag className="h-3.5 w-3.5" />
                    {tournament.registeredTeams}/{tournament.maxTeams} teams
                  </span>
                </div>

                <div className="mb-4 pt-4 border-t border-cyber-border">
                  <p className="text-sm text-cyber-muted line-clamp-2">{tournament.rules}</p>
                </div>

                <div className="flex items-center justify-between">
                  <Link
                    href={`/game/tournaments/${tournament.id}`}
                    className="flex items-center gap-1.5 rounded-lg border border-cyber-primary/60 bg-cyber-primary/10 px-4 py-2 text-sm font-medium text-cyber-primary hover:bg-cyber-primary/20 transition-all"
                  >
                    VIEW
                    <ArrowRight className="h-4 w-4" />
                  </Link>
                  {tournament.status === 'upcoming' && (
                    <button className="rounded-lg border border-cyber-border bg-cyber-surface px-4 py-2 text-sm hover:border-cyber-primary/60 transition-all">
                      REGISTER
                    </button>
                  )}
                  {tournament.status === 'active' && (
                    <Link
                      href={`/game/tournaments/${tournament.id}`}
                      className="flex items-center gap-1.5 rounded-lg border border-emerald-500/60 bg-emerald-500/10 px-4 py-2 text-sm font-medium text-emerald-400 hover:bg-emerald-500/20 transition-all"
                    >
                      <Flag className="h-4 w-4" />
                      JOIN LIVE
                    </Link>
                  )}
                  {tournament.status === 'completed' && (
                    <span className="rounded-lg border border-cyber-border bg-cyber-surface px-4 py-2 text-sm text-cyber-muted">
                      COMPLETED
                    </span>
                  )}
                </div>
              </article>
            ))
          )}
        </div>

        {total > pageSize && (
          <div className="mt-8 flex items-center justify-center gap-2">
            <button
              onClick={() => setPage(p => Math.max(1, p - 1))}
              disabled={page === 1 || loading}
              className="rounded border border-cyber-border bg-cyber-bg px-3 py-1.5 hover:border-cyber-primary/60 disabled:opacity-50"
            >
              <ChevronLeft className="h-4 w-4" />
            </button>
            <span className="px-2 text-sm font-mono">
              Page {page} of {Math.ceil(total / pageSize)}
            </span>
            <button
              onClick={() => setPage(p => Math.min(Math.ceil(total / pageSize), p + 1))}
              disabled={page === Math.ceil(total / pageSize) || loading}
              className="rounded border border-cyber-border bg-cyber-bg px-3 py-1.5 hover:border-cyber-primary/60 disabled:opacity-50"
            >
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        )}
      </div>
    </div>
  );
}