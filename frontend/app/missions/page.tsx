'use client';

import { useEffect, useState } from 'react';
import { Swords, Play } from 'lucide-react';
import Navbar from '@/components/Navbar';
import { TerminalCard, LoadingScreen } from '@/components/TerminalCard';
import { useAuth } from '@/lib/auth';
import { api } from '@/lib/api';
import type { DailyChallenge, Mission } from '@/lib/types';

const difficultyColors: Record<string, string> = {
  easy: 'text-cyber-success border-cyber-success/40',
  medium: 'text-cyber-warning border-cyber-warning/40',
  hard: 'text-cyber-danger border-cyber-danger/40',
  expert: 'text-cyber-secondary border-cyber-secondary/40',
};

export default function MissionsPage() {
  const { user, loading } = useAuth();
  const [missions, setMissions] = useState<Mission[]>([]);
  const [daily, setDaily] = useState<DailyChallenge[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!user) return;
    Promise.all([
      api.get<{ data: { items: Mission[] } }>('/missions'),
      api.get<DailyChallenge[]>('/missions/daily'),
    ])
      .then(([m, d]) => {
        setMissions(m.data.items);
        setDaily(d);
      })
      .catch((err) => setError(err instanceof Error ? err.message : 'Failed to load missions'));
  }, [user]);

  if (loading || !user) return <LoadingScreen />;

  return (
    <>
      <Navbar />
      <main className="mx-auto max-w-5xl px-6 py-8">
        <div className="mb-6">
          <h1 className="text-2xl font-bold">Missions <span className="text-cyber-primary">Console</span></h1>
          <p className="mt-1 text-sm text-cyber-muted">
            Complete missions in our sandbox to earn XP, coins, and badges.
          </p>
        </div>

        {error && <div className="mb-6 text-cyber-danger">{error}</div>}

        {daily.length > 0 && (
          <TerminalCard title="daily_challenges.json" className="mb-8">
            <h2 className="mb-3 font-semibold">Today&apos;s challenges</h2>
            <ul className="space-y-2">
              {daily.map((c) => (
                <li key={c.id} className="flex items-center justify-between rounded-md border border-cyber-border px-3 py-2 text-sm">
                  <div>
                    <span className="font-medium">{c.title}</span>
                    <p className="text-xs text-cyber-muted">{c.description}</p>
                  </div>
                  <div className="flex shrink-0 gap-2 font-mono text-xs">
                    <span className="text-cyber-primary">+{c.xp_reward} XP</span>
                    <span className="text-cyber-warning">+{c.coins_reward} coins</span>
                  </div>
                </li>
              ))}
            </ul>
          </TerminalCard>
        )}

        {missions.length === 0 ? (
          <TerminalCard title="missions.log">
            <p className="text-sm text-cyber-muted">No missions available. The next rotation is scheduled automatically.</p>
          </TerminalCard>
        ) : (
          <div className="grid gap-4 md:grid-cols-2">
            {missions.map((mission) => (
              <TerminalCard key={mission.id} title={`mission://${mission.name.toLowerCase().replace(/\s+/g, '-')}`}>
                <div className="mb-2 flex items-start justify-between gap-2">
                  <Swords className="h-5 w-5 shrink-0 text-cyber-secondary" />
                  <div className="flex gap-2">
                    <span className={`rounded border px-2 py-0.5 text-xs ${difficultyColors[mission.difficulty] ?? 'text-cyber-muted border-cyber-border'}`}>
                      {mission.difficulty}
                    </span>
                    {mission.is_premium && (
                      <span className="rounded border border-cyber-warning/40 px-2 py-0.5 text-xs text-cyber-warning">premium</span>
                    )}
                  </div>
                </div>
                <h2 className="font-semibold">{mission.name}</h2>
                <p className="mt-1 text-sm text-cyber-muted">{mission.short_description}</p>
                <div className="mt-3 flex items-center justify-between">
                  <div className="flex gap-2 font-mono text-xs">
                    <span className="text-cyber-primary">+{mission.xp_reward} XP</span>
                    <span className="text-cyber-warning">+{mission.coins_reward} coins</span>
                    <span className="text-cyber-muted">{mission.estimated_minutes}m</span>
                  </div>
                  <button
                    onClick={() => void api.post(`/missions/${mission.id}/start`).catch(() => undefined)}
                    className="terminal-button-ghost flex items-center gap-1.5 py-1.5 text-xs"
                  >
                    <Play className="h-3.5 w-3.5" /> Start
                  </button>
                </div>
              </TerminalCard>
            ))}
          </div>
        )}
      </main>
    </>
  );
}
