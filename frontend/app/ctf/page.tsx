'use client';

import Link from 'next/link';
import {
  Flag,
  Loader2,
  Lock,
  Shield,
  Sparkles,
  Trophy,
  X,
} from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';
import { api } from '@/lib/api';

interface Challenge {
  id: string;
  slug: string;
  title: string;
  story: string;
  category: string;
  difficulty: string;
  points: number;
  hint: string | null;
  flag_hint_prefix: string | null;
  tags: string[];
  solved: boolean;
}

interface LeaderboardRow {
  display_name: string;
  points: number;
  solved: number;
}

interface Submission {
  correct: boolean;
  points_earned: number;
  attempts: number;
  first_blood: boolean;
  message: string;
}

const CATEGORIES = ['crypto', 'web', 'forensics', 'reversing', 'osint', 'networking', 'defensive'];

export default function CtfPage() {
  const [challenges, setChallenges] = useState<Challenge[]>([]);
  const [category, setCategory] = useState('');
  const [difficulty, setDifficulty] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const [selected, setSelected] = useState<Challenge | null>(null);
  const [flag, setFlag] = useState('');
  const [submitResult, setSubmitResult] = useState<Submission | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [showHint, setShowHint] = useState(false);

  const [leaderboard, setLeaderboard] = useState<LeaderboardRow[]>([]);
  const [showLb, setShowLb] = useState(false);

  const load = useCallback(() => {
    setLoading(true);
    const params = new URLSearchParams();
    if (category) params.set('category', category);
    if (difficulty) params.set('difficulty', difficulty);
    api
      .get<{ data: Challenge[] }>(`/ctf/challenges?${params.toString()}`)
      .then((res) => setChallenges(res.data))
      .catch((e) => setError(e?.message ?? 'Failed to load challenges.'))
      .finally(() => setLoading(false));
  }, [category, difficulty]);

  useEffect(() => {
    load();
  }, [load]);

  const open = (c: Challenge) => {
    setSelected(c);
    setFlag('');
    setSubmitResult(null);
    setShowHint(false);
  };

  const submit = async () => {
    if (!selected || !flag.trim()) return;
    setSubmitting(true);
    try {
      const res = await api.post<{ data: Submission }>(`/ctf/challenges/${selected.slug}/submit`, { flag: flag.trim() });
      setSubmitResult(res.data);
      if (res.data.correct) load();
    } catch (e: unknown) {
      const msg = (e as { message?: string })?.message ?? 'Submission failed.';
      setSubmitResult({ correct: false, points_earned: 0, attempts: 1, first_blood: false, message: msg });
    } finally {
      setSubmitting(false);
    }
  };

  const loadLeaderboard = () => {
    api
      .get<{ data: LeaderboardRow[] }>('/ctf/leaderboard')
      .then((res) => {
        setLeaderboard(res.data);
        setShowLb(true);
      })
      .catch(() => undefined);
  };

  const selectCls =
    'rounded border border-cyber-border bg-cyber-bg px-3 py-1.5 text-sm text-cyber-muted outline-none focus:border-cyber-primary';

  const diffColor = (d: string) =>
    d === 'beginner' ? 'text-green-400' : d === 'intermediate' ? 'text-amber-400' : 'text-red-400';

  return (
    <div className="min-h-screen bg-cyber-bg px-6 py-6">
      <header className="mx-auto flex max-w-6xl items-center justify-between">
        <Link href="/" className="flex items-center gap-2">
          <Shield className="h-7 w-7 text-cyber-primary" />
          <span className="font-mono text-lg font-bold glow-text text-cyber-primary">CyberVerse</span>
        </Link>
        <Link href="/" className="terminal-button-ghost px-4 py-1.5 text-sm">
          ← back
        </Link>
      </header>

      <main className="mx-auto mt-8 max-w-6xl">
        <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="mb-2 font-mono text-xs text-cyber-secondary">
              &gt; // capture the flag · defensive challenges
            </p>
            <h1 className="flex items-center gap-3 text-3xl font-bold">
              <Flag className="h-8 w-8 text-cyber-primary" />
              Capture the <span className="glow-text text-cyber-primary">Flag</span>
            </h1>
            <p className="mt-2 max-w-3xl text-sm text-cyber-muted">
              Practice core skill categories through synthetic, solvable puzzles. Flags are
              stored only as hashes and every challenge is self-contained.
            </p>
          </div>
          <button onClick={loadLeaderboard} className="terminal-button-ghost flex items-center gap-2 px-4 py-2 text-sm">
            <Trophy className="h-4 w-4" /> Leaderboard
          </button>
        </div>

        <div className="mb-6 flex flex-wrap items-center gap-3">
          <select value={category} onChange={(e) => { setCategory(e.target.value); }} className={selectCls}>
            <option value="">all categories</option>
            {CATEGORIES.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
          <select value={difficulty} onChange={(e) => { setDifficulty(e.target.value); }} className={selectCls}>
            <option value="">all levels</option>
            <option value="beginner">beginner</option>
            <option value="intermediate">intermediate</option>
            <option value="advanced">advanced</option>
          </select>
        </div>

        {loading ? (
          <div className="flex justify-center py-20">
            <Loader2 className="h-8 w-8 animate-spin text-cyber-primary" />
          </div>
        ) : error ? (
          <p className="rounded border border-red-500/40 bg-red-500/10 p-4 text-center font-mono text-sm text-red-400">
            {error}
          </p>
        ) : challenges.length === 0 ? (
          <p className="rounded border border-cyber-border bg-cyber-surface/50 p-10 text-center font-mono text-sm text-cyber-muted">
            no challenges match those filters
          </p>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {challenges.map((c) => (
              <button
                key={c.id}
                onClick={() => open(c)}
                className="terminal-card flex flex-col p-5 text-left transition-colors hover:border-cyber-primary"
              >
                <div className="mb-2 flex items-center justify-between gap-2">
                  <span className="rounded bg-cyber-primary/10 px-2 py-0.5 font-mono text-[10px] uppercase text-cyber-primary">
                    {c.category}
                  </span>
                  <span className={`font-mono text-sm font-bold ${diffColor(c.difficulty)}`}>{c.points} pts</span>
                </div>
                <h3 className="flex items-center gap-2 font-bold">
                  {c.title}
                  {c.solved && <Lock className="h-4 w-4 text-green-400" />}
                </h3>
                <p className="mt-2 line-clamp-2 flex-grow text-sm text-cyber-muted">{c.story}</p>
                <div className="mt-3 flex items-center justify-between text-[11px] text-cyber-muted">
                  <span className="capitalize">{c.difficulty}</span>
                  {c.solved && <span className="text-green-400">solved</span>}
                </div>
              </button>
            ))}
          </div>
        )}
      </main>

      {selected && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4" onClick={() => setSelected(null)}>
          <div
            className="w-full max-w-lg rounded-lg border border-cyber-border bg-cyber-bg p-6 shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="mb-1 flex items-center justify-between">
              <span className="rounded bg-cyber-primary/10 px-2 py-0.5 font-mono text-xs uppercase text-cyber-primary">
                {selected.category} · {selected.points} pts
              </span>
              <button onClick={() => setSelected(null)} className="text-cyber-muted hover:text-cyber-primary">
                <X className="h-5 w-5" />
              </button>
            </div>
            <h2 className="mb-2 text-xl font-bold">{selected.title}</h2>
            <p className="mb-4 text-sm text-cyber-muted">{selected.story}</p>

            {selected.solved && (
              <p className="mb-4 rounded border border-green-500/30 bg-green-500/10 px-3 py-2 text-sm text-green-400">
                <Lock className="mr-1 inline h-4 w-4" /> You have already solved this challenge.
              </p>
            )}

            {selected.hint && (
              <button
                onClick={() => setShowHint((s) => !s)}
                className="terminal-button-ghost mb-3 flex items-center gap-2 px-3 py-1.5 text-xs"
              >
                <Sparkles className="h-4 w-4" /> {showHint ? 'Hide hint' : 'Show hint'}
              </button>
            )}
            {showHint && selected.hint && (
              <p className="mb-4 rounded border border-amber-500/30 bg-amber-500/10 px-3 py-2 font-mono text-xs text-amber-300">
                {selected.hint}
              </p>
            )}

            <div className="flex gap-2">
              <input
                value={flag}
                onChange={(e) => setFlag(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && submit()}
                placeholder={selected.flag_hint_prefix ? `flag... (${selected.flag_hint_prefix})` : 'enter flag...'}
                className="flex-1 rounded border border-cyber-border bg-cyber-surface px-3 py-2 font-mono text-sm text-cyber-foreground outline-none placeholder:text-cyber-muted focus:border-cyber-primary"
              />
              <button onClick={submit} disabled={submitting || !flag.trim() || selected.solved} className="terminal-button px-4 py-2 text-sm disabled:opacity-50">
                {submitting ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Submit'}
              </button>
            </div>

            {submitResult && (
              <p
                className={`mt-3 rounded border px-3 py-2 font-mono text-sm ${
                  submitResult.correct
                    ? 'border-green-500/30 bg-green-500/10 text-green-400'
                    : 'border-red-500/30 bg-red-500/10 text-red-400'
                }`}
              >
                {submitResult.message}
                {submitResult.first_blood && ' · First blood!'}
                {submitResult.attempts > 1 && ` · attempt ${submitResult.attempts}`}
              </p>
            )}
          </div>
        </div>
      )}

      {showLb && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4" onClick={() => setShowLb(false)}>
          <div className="w-full max-w-md rounded-lg border border-cyber-border bg-cyber-bg p-6" onClick={(e) => e.stopPropagation()}>
            <div className="mb-4 flex items-center justify-between">
              <h2 className="flex items-center gap-2 text-lg font-bold">
                <Trophy className="h-5 w-5 text-amber-400" /> CTF Leaderboard
              </h2>
              <button onClick={() => setShowLb(false)} className="text-cyber-muted hover:text-cyber-primary">
                <X className="h-5 w-5" />
              </button>
            </div>
            {leaderboard.length === 0 ? (
              <p className="py-6 text-center font-mono text-sm text-cyber-muted">No scores yet — be the first to solve a flag.</p>
            ) : (
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-cyber-border font-mono text-xs text-cyber-muted">
                    <th className="pb-2 text-left">#</th>
                    <th className="pb-2 text-left">User</th>
                    <th className="pb-2 text-right">Solved</th>
                    <th className="pb-2 text-right">Points</th>
                  </tr>
                </thead>
                <tbody>
                  {leaderboard.map((row, idx) => (
                    <tr key={row.display_name ?? String(idx)} className="border-b border-cyber-border/30">
                      <td className="py-2 font-mono text-cyber-secondary">{idx + 1}</td>
                      <td className="py-2">{row.display_name ?? 'Unknown'}</td>
                      <td className="py-2 text-right">{row.solved}</td>
                      <td className="py-2 text-right font-mono font-bold text-cyber-primary">{row.points}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
