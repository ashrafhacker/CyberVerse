'use client';

import { useState, useEffect } from 'react';
import { Users, Plus, Search, ChevronLeft, ChevronRight, Flag, Trophy, Star, Lock, Shield } from 'lucide-react';
import Link from 'next/link';
import { api } from '@/lib/api';

interface Team {
  id: string;
  name: string;
  tag: string;
  description: string;
  avatar?: string;
  memberCount: number;
  maxMembers: number;
  isPrivate: boolean;
  captainId: string;
  captainName: string;
  xp: number;
  rank: number;
  createdAt: string;
}

interface TeamsResponse {
  teams: Team[];
  total: number;
  page: number;
  pageSize: number;
}

export default function TeamsPage() {
  const [teams, setTeams] = useState<Team[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [search, setSearch] = useState('');
  const pageSize = 12;

  useEffect(() => {
    fetchTeams();
  }, [page, search]);

  async function fetchTeams() {
    setLoading(true);
    try {
      const res = await api.get<TeamsResponse>('/game/teams', {
        params: { page, pageSize, search: search || undefined },
      });
      setTeams(res.data.teams);
      setTotal(res.data.total);
    } catch {
      setTeams([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-cyber-bg text-cyber-text">
      <div className="mx-auto max-w-7xl px-6 py-12">
        <header className="mb-8 flex flex-col md:flex-row md:items-center md:justify-between gap-6">
          <div>
            <h1 className="mb-4 text-4xl font-bold tracking-tight md:text-5xl">
              CYBERVERSE <span className="text-cyber-primary">TEAMS</span>
            </h1>
            <p className="mx-auto max-w-2xl text-lg text-cyber-muted">
              Join forces. Compete together. Share knowledge. Build your crew.
            </p>
          </div>
          <Link
            href="/game/teams/create"
            className="flex h-12 min-w-[160px] items-center justify-center gap-2 rounded-lg border-2 border-cyber-primary bg-cyber-primary/10 px-6 font-bold text-cyber-primary hover:bg-cyber-primary/20 transition-all"
          >
            <Plus className="h-5 w-5" />
            CREATE TEAM
          </Link>
        </header>

        <div className="mb-6 flex items-center justify-between">
          <div className="relative max-w-md">
            <Search className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-cyber-muted" />
            <input
              type="text"
              value={search}
              onChange={e => { setSearch(e.target.value); setPage(1); }}
              placeholder="Search teams..."
              className="w-full rounded-lg border border-cyber-border bg-black/50 pl-10 pr-4 py-2 text-cyber-text placeholder:text-cyber-muted focus:border-cyber-primary focus:outline-none"
            />
          </div>
        </div>

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
          ) : teams.length === 0 ? (
            <div className="col-span-full text-center py-12">
              <Users className="mx-auto mb-4 h-12 w-12 text-cyber-muted" />
              <h3 className="mb-2 text-xl font-semibold">No teams found</h3>
              <p className="text-cyber-muted">Be the first to create a team!</p>
              <Link
                href="/game/teams/create"
                className="mt-4 inline-flex items-center gap-2 rounded-lg border-2 border-cyber-primary bg-cyber-primary/10 px-6 py-3 font-bold text-cyber-primary hover:bg-cyber-primary/20 transition-all"
              >
                <Plus className="h-5 w-5" />
                CREATE TEAM
              </Link>
            </div>
          ) : (
            teams.map((team) => (
              <article
                key={team.id}
                className="group relative overflow-hidden rounded-xl border border-cyber-border bg-cyber-surface/60 p-6 transition-all hover:border-cyber-primary/60 hover:shadow-[0_0_24px_rgba(0,229,255,0.15)]"
              >
                <div className="mb-4 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    {team.avatar ? (
                      <img src={team.avatar} alt={team.name} className="h-10 w-10 rounded-full" />
                    ) : (
                      <div className="flex h-10 w-10 items-center justify-center rounded-full bg-cyber-primary/20">
                        <Shield className="h-6 w-6 text-cyber-primary" />
                      </div>
                    )}
                    <div>
                      <h3 className="font-bold group-hover:text-cyber-primary transition-colors">
                        {team.name}
                      </h3>
                      <p className="text-sm text-cyber-muted">[{team.tag}]</p>
                    </div>
                  </div>
                  {team.isPrivate && <Lock className="h-5 w-5 text-cyber-muted" />}
                </div>

                <p className="mb-4 line-clamp-2 text-sm text-cyber-muted">{team.description}</p>

                <div className="mb-4 flex flex-wrap gap-3 text-xs text-cyber-muted">
                  <span className="flex items-center gap-1">
                    <Users className="h-3.5 w-3.5" />
                    {team.memberCount}/{team.maxMembers} members
                  </span>
                  <span className="flex items-center gap-1 text-amber-400">
                    <Star className="h-3.5 w-3.5" />
                    {team.xp.toLocaleString()} XP
                  </span>
                  <span className="flex items-center gap-1 text-cyber-primary">
                    <Flag className="h-3.5 w-3.5" />
                    Rank #{team.rank}
                  </span>
                </div>

                <div className="flex items-center justify-between pt-4 border-t border-cyber-border">
                  <div className="flex items-center gap-2 text-xs text-cyber-muted">
                    <img
                      src={`https://api.dicebear.com/7.x/avataaars/svg?seed=${team.captainName}`}
                      alt={team.captainName}
                      className="h-6 w-6 rounded-full"
                    />
                    <span>Captain: {team.captainName}</span>
                  </div>
                  <Link
                    href={`/game/teams/${team.id}`}
                    className="rounded-lg border border-cyber-primary/60 bg-cyber-primary/10 px-4 py-2 text-sm font-medium text-cyber-primary hover:bg-cyber-primary/20 transition-all"
                  >
                    VIEW
                  </Link>
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