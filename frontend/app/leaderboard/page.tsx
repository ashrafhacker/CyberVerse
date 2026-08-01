'use client';

import { useEffect, useState } from 'react';
import { Trophy, Medal } from 'lucide-react';
import Navbar from '@/components/Navbar';
import { TerminalCard, LoadingScreen } from '@/components/TerminalCard';
import { useAuth } from '@/lib/auth';
import { api } from '@/lib/api';
import type { LeaderboardEntry } from '@/lib/types';

interface LeaderboardData {
  board_id: string;
  name: string;
  type: string;
  period_start: string | null;
  period_end: string | null;
  total_players: number;
  my_rank: { rank: number; score: number } | null;
  entries: LeaderboardEntry[];
}

const rankStyles: Record<number, string> = {
  1: 'text-cyber-warning border-cyber-warning/50',
  2: 'text-cyber-muted border-cyber-muted/50',
  3: 'text-amber-600 border-amber-700/50',
};

export default function LeaderboardPage() {
  const { user, loading } = useAuth();
  const [data, setData] = useState<LeaderboardData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!user) return;
    api
      .get<{ data: LeaderboardData }>('/leaderboard?limit=50')
      .then((res) => setData(res.data))
      .catch((err) => setError(err instanceof Error ? err.message : 'Failed to load leaderboard'));
  }, [user]);

  if (loading || !user) return <LoadingScreen />;

  return (
    <>
      <Navbar />
      <main className="mx-auto max-w-3xl px-6 py-8">
        <div className="mb-6 text-center">
          <Trophy className="mx-auto mb-2 h-10 w-10 text-cyber-warning" />
          <h1 className="text-2xl font-bold">Global <span className="text-cyber-primary">Leaderboard</span></h1>
          <p className="mt-1 text-sm text-cyber-muted">{data?.name ?? 'Weekly rankings'}</p>
          {data?.my_rank && (
            <p className="mt-2 font-mono text-xs text-cyber-muted">
              your rank: #{data.my_rank.rank} · {data.my_rank.score} XP
            </p>
          )}
        </div>

        {error && <div className="mb-6 text-cyber-danger">{error}</div>}

        <TerminalCard title="rankings.sql" className="p-0">
          {!data || data.entries.length === 0 ? (
            <p className="p-5 text-sm text-cyber-muted">
              No ranked agents yet. Complete missions to be the first!
            </p>
          ) : (
            <ol className="divide-y divide-cyber-border">
              {data.entries.map((entry) => (
                <li key={entry.user_id} className="flex items-center gap-4 px-5 py-3">
                  <span
                    className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-md border font-mono text-sm font-bold ${
                      rankStyles[entry.rank] ?? 'border-cyber-border text-cyber-muted'
                    }`}
                  >
                    {entry.rank <= 3 ? <Medal className="h-5 w-5" /> : entry.rank}
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="truncate font-medium">{entry.username}</p>
                    <p className="truncate font-mono text-xs text-cyber-muted">{entry.full_name}</p>
                  </div>
                  <span className="font-mono text-sm font-semibold text-cyber-primary">
                    {entry.score.toLocaleString()} XP
                  </span>
                </li>
              ))}
            </ol>
          )}
        </TerminalCard>
      </main>
    </>
  );
}
