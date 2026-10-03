'use client';

import Link from 'next/link';
import {
  Backpack,
  CalendarDays,
  CalendarRange,
  Loader2,
  Shield,
  Sparkles,
  Trophy,
} from 'lucide-react';
import { useEffect, useState } from 'react';
import { api } from '@/lib/api';

interface Branch {
  slug: string;
  name: string;
  level: number;
  max_level: number;
  xp_in_branch: number;
}

interface SkillProgress {
  total_xp: number;
  level: number;
  rank: string;
  next_rank: string | null;
  next_rank_level: number | null;
  branches: Branch[];
}

interface Quest {
  id: string;
  title: string;
  description: string;
  xp_reward: number;
  coins_reward: number;
  task_type?: string;
  task_requirement?: number;
}

interface InventoryItem {
  id: string;
  item_type: string;
  name: string;
  description: string;
  rarity: string;
  quantity: number;
  is_equipped: boolean;
}

export default function ProgressionPage() {
  const [progress, setProgress] = useState<SkillProgress | null>(null);
  const [daily, setDaily] = useState<Quest[]>([]);
  const [weekly, setWeekly] = useState<Quest[]>([]);
  const [inventory, setInventory] = useState<InventoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    setLoading(true);
    Promise.all([
      api.get<{ data: SkillProgress }>('/skills').then((r) => r.data).catch(() => null),
      api.get<{ data: Quest[] }>('/progression/quests/daily').then((r) => r.data).catch(() => []),
      api.get<{ data: Quest[] }>('/progression/quests/weekly').then((r) => r.data).catch(() => []),
      api.get<{ data: InventoryItem[] }>('/progression/inventory').then((r) => r.data).catch(() => []),
    ])
      .then(([p, d, w, inv]) => {
        setProgress(p);
        setDaily(d);
        setWeekly(w);
        setInventory(inv);
        setError('');
      })
      .catch(() => setError('Failed to load progression.'))
      .finally(() => setLoading(false));
  }, []);

  const rarityColor: Record<string, string> = {
    common: 'text-cyber-muted',
    rare: 'text-blue-400',
    epic: 'text-purple-400',
    legendary: 'text-amber-400',
  };

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-cyber-bg">
        <Loader2 className="h-8 w-8 animate-spin text-cyber-primary" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-cyber-bg px-6 py-6">
      <header className="mx-auto flex max-w-6xl items-center justify-between">
        <Link href="/" className="flex items-center gap-2">
          <Shield className="h-7 w-7 text-cyber-primary" />
          <span className="font-mono text-lg font-bold glow-text text-cyber-primary">CyberVerse</span>
        </Link>
        <Link href="/" className="terminal-button-ghost px-4 py-1.5 text-sm">← back</Link>
      </header>

      <main className="mx-auto mt-8 max-w-6xl">
        {error ? (
          <p className="rounded border border-red-500/40 bg-red-500/10 p-4 text-center font-mono text-sm text-red-400">{error}</p>
        ) : (
          <>
            <section className="terminal-card mb-8 p-6">
              <div className="flex flex-wrap items-center justify-between gap-4">
                <div>
                  <p className="mb-1 font-mono text-xs text-cyber-secondary">&gt; // career progression</p>
                  <h1 className="flex items-center gap-3 text-3xl font-bold">
                    <Trophy className="h-8 w-8 text-cyber-primary" />
                    {progress?.rank ?? 'Analyst'} <span className="glow-text text-cyber-primary">· Lv {progress?.level ?? 1}</span>
                  </h1>
                  <p className="mt-2 text-sm text-cyber-muted">
                    {progress?.next_rank
                      ? `Next rank "${progress.next_rank}" unlocks at level ${progress.next_rank_level}.`
                      : 'You have reached the top rank — CyberVerse Elite.'}
                  </p>
                </div>
                <div className="rounded border border-cyber-border bg-cyber-surface px-4 py-3 text-center">
                  <div className="font-mono text-2xl font-bold text-cyber-primary">{progress?.total_xp ?? 0}</div>
                  <div className="text-xs text-cyber-muted">total XP</div>
                </div>
              </div>

              <div className="mt-6">
                <h2 className="mb-3 flex items-center gap-2 font-semibold">
                  <Sparkles className="h-4 w-4 text-cyber-secondary" /> Skill Tree
                </h2>
                <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                  {(progress?.branches ?? []).map((b) => {
                    const pct = b.max_level ? Math.round((b.level / b.max_level) * 100) : 0;
                    return (
                      <div key={b.slug} className="rounded border border-cyber-border bg-cyber-surface/50 p-4">
                        <div className="mb-2 flex items-center justify-between">
                          <span className="font-medium capitalize">{b.name}</span>
                          <span className="font-mono text-xs text-cyber-secondary">{b.level}/{b.max_level}</span>
                        </div>
                        <div className="h-1.5 overflow-hidden rounded bg-cyber-border">
                          <div className="h-full rounded bg-cyber-primary transition-all" style={{ width: `${pct}%` }} />
                        </div>
                        <div className="mt-1 font-mono text-[10px] text-cyber-muted">{b.xp_in_branch} xp</div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </section>

            <div className="grid gap-8 lg:grid-cols-2">
              <section>
                <h2 className="mb-3 flex items-center gap-2 font-semibold">
                  <CalendarDays className="h-4 w-4 text-cyber-primary" /> Daily Quests
                </h2>
                {daily.length === 0 ? (
                  <p className="rounded border border-cyber-border bg-cyber-surface/50 p-6 text-center font-mono text-sm text-cyber-muted">no daily quests today</p>
                ) : (
                  <div className="space-y-3">
                    {daily.map((q) => (
                      <div key={q.id} className="terminal-card p-4">
                        <div className="mb-1 font-semibold">{q.title}</div>
                        <p className="mb-2 text-sm text-cyber-muted">{q.description}</p>
                        <div className="flex gap-4 font-mono text-xs text-cyber-muted">
                          <span className="text-cyber-primary">+{q.xp_reward} xp</span>
                          <span className="text-green-400">+{q.coins_reward} coins</span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </section>

              <section>
                <h2 className="mb-3 flex items-center gap-2 font-semibold">
                  <CalendarRange className="h-4 w-4 text-cyber-primary" /> Weekly Quests
                </h2>
                {weekly.length === 0 ? (
                  <p className="rounded border border-cyber-border bg-cyber-surface/50 p-6 text-center font-mono text-sm text-cyber-muted">no weekly quests this week</p>
                ) : (
                  <div className="space-y-3">
                    {weekly.map((q) => (
                      <div key={q.id} className="terminal-card p-4">
                        <div className="mb-1 font-semibold">{q.title}</div>
                        <p className="mb-2 text-sm text-cyber-muted">{q.description}</p>
                        <div className="flex gap-4 font-mono text-xs text-cyber-muted">
                          <span className="text-cyber-primary">+{q.xp_reward} xp</span>
                          <span className="text-green-400">+{q.coins_reward} coins</span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </section>
            </div>

            <section className="mt-8">
              <h2 className="mb-3 flex items-center gap-2 font-semibold">
                <Backpack className="h-4 w-4 text-cyber-primary" /> Inventory
              </h2>
              {inventory.length === 0 ? (
                <p className="rounded border border-cyber-border bg-cyber-surface/50 p-6 text-center font-mono text-sm text-cyber-muted">inventory empty</p>
              ) : (
                <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                  {inventory.map((it) => (
                    <div key={it.id} className="terminal-card flex items-start justify-between gap-2 p-4">
                      <div>
                        <div className="font-semibold">{it.name}</div>
                        <p className="mb-1 text-xs text-cyber-muted">{it.description}</p>
                        <span className={`font-mono text-[10px] uppercase ${rarityColor[it.rarity] ?? 'text-cyber-muted'}`}>{it.rarity}</span>
                        <span className="ml-2 font-mono text-[10px] text-cyber-muted">×{it.quantity}</span>
                      </div>
                      <div className="flex flex-col items-end gap-1">
                        <span className="rounded bg-cyber-surface px-1.5 py-0.5 font-mono text-[10px] text-cyber-muted">{it.item_type}</span>
                        {it.is_equipped && <span className="rounded bg-cyber-primary/15 px-1.5 py-0.5 font-mono text-[10px] text-cyber-primary">equipped</span>}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </section>
          </>
        )}
      </main>
    </div>
  );
}
