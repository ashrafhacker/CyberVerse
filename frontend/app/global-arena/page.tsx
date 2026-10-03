'use client';

import { useState, useEffect } from 'react';
import { Globe, Trophy, Flag, User, Star, ChevronLeft, ChevronRight } from 'lucide-react';
import { api } from '@/lib/api';
import Link from 'next/link';

interface LeaderboardEntry {
  rank: number;
  username: string;
  country: string;
  xp: number;
  challenges: number;
  wins: number;
  score: number;
  avatar?: string;
}

interface LeaderboardResponse {
  entries: LeaderboardEntry[];
  total: number;
  page: number;
  pageSize: number;
}

const TABS = [
  { id: 'global', label: 'GLOBAL', icon: Globe },
  { id: 'country', label: 'COUNTRY', icon: Flag },
  { id: 'college', label: 'COLLEGE', icon: Trophy },
  { id: 'team', label: 'TEAM', icon: User },
  { id: 'weekly', label: 'WEEKLY', icon: Star },
  { id: 'monthly', label: 'MONTHLY', icon: Trophy },
  { id: 'season', label: 'SEASON', icon: Star },
] as const;

export default function GlobalArenaPage() {
  const [activeTab, setActiveTab] = useState('global');
  const [leaderboard, setLeaderboard] = useState<LeaderboardEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const pageSize = 50;

  useEffect(() => {
    fetchLeaderboard();
  }, [activeTab, page]);

  async function fetchLeaderboard() {
    setLoading(true);
    try {
      const res = await api.get<LeaderboardResponse>(
        `/leaderboard/${activeTab}`,
        { params: { page, pageSize } }
      );
      setLeaderboard(res.data.entries);
      setTotal(res.data.total);
    } catch {
      setLeaderboard([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  }

  function getRankClass(rank: number) {
    if (rank === 1) return 'text-amber-400';
    if (rank === 2) return 'text-gray-300';
    if (rank === 3) return 'text-amber-600';
    return 'text-cyber-muted';
  }

  return (
    <div className="min-h-screen bg-cyber-bg text-cyber-text">
      <div className="mx-auto max-w-7xl px-6 py-12">
        <header className="mb-8 text-center">
          <h1 className="mb-4 text-4xl font-bold tracking-tight md:text-5xl">
            CYBERVERSE <span className="text-cyber-primary">GLOBAL ARENA</span>
          </h1>
          <p className="mx-auto max-w-2xl text-lg text-cyber-muted">
            Worldwide rankings. Compete globally, nationally, or with your team.
          </p>
        </header>

        <nav className="mb-6 overflow-x-auto" aria-label="Leaderboard tabs">
          <ul className="flex gap-2 min-w-max" role="tablist">
            {TABS.map(({ id, label, icon: Icon }) => (
              <li key={id} role="presentation">
                <button
                  onClick={() => setActiveTab(id)}
                  className={`flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-all whitespace-nowrap ${
                    activeTab === id
                      ? 'bg-cyber-primary/20 border border-cyber-primary text-cyber-primary'
                      : 'bg-cyber-surface/60 border border-cyber-border text-cyber-muted hover:border-cyber-primary/60 hover:text-cyber-text'
                  }`}
                  role="tab"
                  aria-selected={activeTab === id}
                >
                  <Icon className="h-4 w-4" />
                  {label}
                </button>
              </li>
            ))}
          </ul>
        </nav>

        <div className="rounded-xl border border-cyber-border bg-cyber-surface/40 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full" role="table">
              <thead>
                <tr className="border-b border-cyber-border bg-cyber-bg/80">
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-cyber-muted">RANK</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-cyber-muted">PLAYER</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-cyber-muted">COUNTRY</th>
                  <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-cyber-muted">XP</th>
                  <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-cyber-muted">CHALLENGES</th>
                  <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-cyber-muted">WINS</th>
                  <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-cyber-muted">SCORE</th>
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  Array.from({ length: 5 }).map((_, i) => (
                    <tr key={i} className="border-b border-cyber-border/50 animate-pulse">
                      <td className="px-4 py-4"><div className="h-4 w-12 bg-cyber-border rounded" /></td>
                      <td className="px-4 py-4"><div className="h-4 w-32 bg-cyber-border rounded" /></td>
                      <td className="px-4 py-4"><div className="h-4 w-20 bg-cyber-border rounded" /></td>
                      <td className="px-4 py-4"><div className="h-4 w-24 bg-cyber-border rounded" /></td>
                      <td className="px-4 py-4"><div className="h-4 w-16 bg-cyber-border rounded" /></td>
                      <td className="px-4 py-4"><div className="h-4 w-16 bg-cyber-border rounded" /></td>
                      <td className="px-4 py-4"><div className="h-4 w-24 bg-cyber-border rounded" /></td>
                    </tr>
                  ))
                ) : leaderboard.length === 0 ? (
                  <tr>
                    <td className="px-4 py-12 text-center text-cyber-muted" colSpan={7}>
                      No entries found for this leaderboard.
                    </td>
                  </tr>
                ) : (
                  leaderboard.map((entry) => (
                    <tr key={entry.username} className="border-b border-cyber-border/50 hover:bg-cyber-primary/5 transition-colors">
                      <td className="px-4 py-4">
                        <span className={`font-mono font-bold ${getRankClass(entry.rank)}`}>
                          #{entry.rank}
                        </span>
                        {entry.rank <= 3 && (
                          <Trophy className={`inline h-4 w-4 ml-1 ${getRankClass(entry.rank)}`} />
                        )}
                      </td>
                      <td className="px-4 py-4">
                        <Link
                          href={`/profile/${entry.username}`}
                          className="flex items-center gap-2 font-medium hover:text-cyber-primary transition-colors"
                        >
                          {entry.avatar && (
                            <img
                              src={entry.avatar}
                              alt=""
                              className="h-8 w-8 rounded-full bg-cyber-bg"
                            />
                          )}
                          <span>{entry.username}</span>
                        </Link>
                      </td>
                      <td className="px-4 py-4">
                        <span className="flex items-center gap-1 text-cyber-muted">
                          <Flag className="h-3.5 w-3.5" />
                          {entry.country}
                        </span>
                      </td>
                      <td className="px-4 py-4 text-right font-mono text-cyber-primary">
                        {entry.xp.toLocaleString()}
                      </td>
                      <td className="px-4 py-4 text-right font-mono">
                        {entry.challenges}
                      </td>
                      <td className="px-4 py-4 text-right font-mono text-green-400">
                        {entry.wins}
                      </td>
                      <td className="px-4 py-4 text-right font-mono font-bold text-cyber-text">
                        {entry.score.toLocaleString()}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {total > pageSize && (
            <div className="flex items-center justify-between px-4 py-4 border-t border-cyber-border">
              <p className="text-sm text-cyber-muted">
                Showing {Math.min(page * pageSize, total)} of {total} entries
              </p>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setPage(p => Math.max(1, p - 1))}
                  disabled={page === 1 || loading}
                  className="rounded border border-cyber-border bg-cyber-bg px-3 py-1.5 text-sm hover:border-cyber-primary/60 disabled:opacity-50"
                >
                  <ChevronLeft className="h-4 w-4" />
                </button>
                <span className="px-2 text-sm font-mono">
                  Page {page} of {Math.ceil(total / pageSize)}
                </span>
                <button
                  onClick={() => setPage(p => Math.min(Math.ceil(total / pageSize), p + 1))}
                  disabled={page === Math.ceil(total / pageSize) || loading}
                  className="rounded border border-cyber-border bg-cyber-bg px-3 py-1.5 text-sm hover:border-cyber-primary/60 disabled:opacity-50"
                >
                  <ChevronRight className="h-4 w-4" />
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}