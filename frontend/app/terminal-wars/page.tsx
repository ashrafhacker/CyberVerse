'use client';

import Link from 'next/link';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { Crosshair, Loader2, ShieldCheck, Swords, Trophy } from 'lucide-react';
import { api } from '@/lib/api';
import VirtualTerminal, { type ShellChallenge, type SubmitResult } from '@/components/terminal-wars/VirtualTerminal';

interface Challenge extends ShellChallenge {
  id: string;
  category: string;
  difficulty: string;
  tags: string[];
  solved: boolean;
}

interface Submission {
  correct: boolean;
  points_earned: number;
  attempts: number;
  first_blood: boolean;
  message: string;
}

const DIFFICULTIES = ['', 'beginner', 'intermediate', 'advanced'];

function errorMessage(err: unknown, fallback: string): string {
  return err instanceof Error && err.message ? err.message : fallback;
}

export default function TerminalWarsPage() {
  const [challenges, setChallenges] = useState<Challenge[]>([]);
  const [difficulty, setDifficulty] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [selectedSlug, setSelectedSlug] = useState<string | null>(null);
  const [solvedSet, setSolvedSet] = useState<Set<string>>(new Set());

  const load = useCallback(() => {
    setLoading(true);
    setError('');
    const params = difficulty ? `?difficulty=${difficulty}` : '';
    api
      .get<{ data: Challenge[] }>(`/ctf/challenges${params}`)
      .then((res) => {
        setChallenges(res.data);
        setSolvedSet(new Set(res.data.filter((c) => c.solved).map((c) => c.slug)));
      })
      .catch((e) => setError(errorMessage(e, 'Failed to load ops roster.')))
      .finally(() => setLoading(false));
  }, [difficulty]);

  useEffect(() => {
    load();
  }, [load]);

  const selected = useMemo(
    () => challenges.find((c) => c.slug === selectedSlug) ?? null,
    [challenges, selectedSlug],
  );

  const clearedCount = challenges.filter((c) => solvedSet.has(c.slug)).length;

  const submitFlag = useCallback(
    async (value: string): Promise<SubmitResult> => {
      if (!selectedSlug) return { ok: false, msg: 'No active op.' };
      const res = await api.post<{ data: Submission }>(
        `/ctf/challenges/${selectedSlug}/submit`,
        { flag: value },
      );
      const sub = res.data;
      if (sub.correct) {
        setSolvedSet((prev) => new Set(prev).add(selectedSlug));
        load();
      }
      return { ok: sub.correct, msg: sub.message };
    },
    [selectedSlug, load],
  );

  const shellChallenge: ShellChallenge | null = selected
    ? {
        slug: selected.slug,
        title: selected.title,
        story: selected.story,
        hint: selected.hint,
        flag_hint_prefix: selected.flag_hint_prefix,
        points: selected.points,
      }
    : null;

  return (
    <div className="min-h-screen bg-cyber-bg">
      <main className="mx-auto max-w-7xl px-4 py-10 sm:px-6 lg:px-8">
        {/* Header */}
        <header className="mb-8 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
          <div>
            <p className="mb-2 flex items-center gap-2 font-mono text-xs uppercase tracking-[0.25em] text-cyber-muted">
              <Swords className="h-3.5 w-3.5" /> District 02 · Offense
            </p>
            <h1 className="font-mono text-4xl font-bold text-emerald-400 drop-shadow-[0_0_18px_rgba(52,211,153,0.4)] sm:text-5xl">
              TERMINAL WARS
            </h1>
            <p className="mt-2 max-w-2xl text-sm text-cyber-muted">
              Fight ops entirely from the command line. Read the brief, explore the op directory,
              and deliver the flag — the command center validates every submission server-side.
            </p>
          </div>

          <div className="terminal-card flex items-center gap-6 p-4">
            <div className="text-center">
              <p className="font-mono text-2xl font-bold text-emerald-400">
                {clearedCount}
                <span className="text-cyber-muted">/{challenges.length}</span>
              </p>
              <p className="font-mono text-[10px] uppercase tracking-wider text-cyber-muted">Cleared</p>
            </div>
            <div className="h-10 w-px bg-cyber-border" aria-hidden />
            <div className="text-center">
              <p className="font-mono text-2xl font-bold text-cyber-primary">
                {challenges.reduce((sum, c) => sum + (solvedSet.has(c.slug) ? c.points : 0), 0)}
              </p>
              <p className="font-mono text-[10px] uppercase tracking-wider text-cyber-muted">XP from ops</p>
            </div>
          </div>
        </header>

        {/* Difficulty chips */}
        <div className="mb-4 flex flex-wrap items-center gap-2" role="group" aria-label="Filter ops by difficulty">
          <span className="font-mono text-[11px] uppercase tracking-wider text-cyber-muted">Channel:</span>
          {DIFFICULTIES.map((d) => (
            <button
              key={d || 'all'}
              type="button"
              onClick={() => setDifficulty(d)}
              aria-pressed={difficulty === d}
              className={`rounded-full border px-3 py-1 font-mono text-xs transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyber-primary ${
                difficulty === d
                  ? 'border-emerald-400/60 bg-emerald-400/15 text-emerald-400'
                  : 'border-cyber-border/60 text-cyber-muted hover:border-cyber-primary/50 hover:text-cyber-primary'
              }`}
            >
              {d || 'all ops'}
            </button>
          ))}
        </div>

        <div className="grid gap-6 lg:grid-cols-[300px_minmax(0,1fr)]">
          {/* Ops roster */}
          <aside aria-label="Ops roster" className="terminal-card max-h-[560px] overflow-y-auto p-3">
            <h2 className="mb-2 flex items-center gap-2 border-b border-cyber-border/60 px-1 pb-2 font-mono text-xs uppercase tracking-wider text-cyber-muted">
              <Crosshair className="h-3.5 w-3.5" /> Ops Roster
            </h2>

            {loading ? (
              <p className="flex items-center gap-2 px-1 py-4 text-sm text-cyber-muted">
                <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> Decrypting roster…
              </p>
            ) : error ? (
              <p className="rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-400" role="alert">
                {error}
              </p>
            ) : challenges.length === 0 ? (
              <div className="px-1 py-4 text-sm text-cyber-muted">
                <p className="mb-2">No active ops on this channel.</p>
                <Link href="/ctf" className="text-cyber-primary underline underline-offset-2 hover:text-cyber-secondary">
                  Visit the CTF Arena →
                </Link>
              </div>
            ) : (
              <ul className="space-y-1.5">
                {challenges.map((c) => {
                  const isSel = c.slug === selectedSlug;
                  const isSolved = solvedSet.has(c.slug);
                  return (
                    <li key={c.id}>
                      <button
                        type="button"
                        onClick={() => setSelectedSlug(c.slug)}
                        aria-pressed={isSel}
                        className={`w-full rounded-lg border px-3 py-2.5 text-left transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyber-primary ${
                          isSel
                            ? 'border-emerald-400/60 bg-emerald-400/10 shadow-[0_0_14px_rgba(52,211,153,0.25)]'
                            : 'border-cyber-border/50 bg-cyber-bg/40 hover:border-emerald-400/40 hover:bg-cyber-surface/60'
                        }`}
                      >
                        <span className="flex items-start justify-between gap-2">
                          <span className="font-mono text-sm font-semibold text-cyber-text">{c.title}</span>
                          {isSolved && <ShieldCheck className="h-4 w-4 shrink-0 text-emerald-400" aria-label="Cleared" />}
                        </span>
                        <span className="mt-1 flex items-center gap-2 font-mono text-[10px] uppercase tracking-wider text-cyber-muted">
                          <span>{c.difficulty}</span>
                          <span aria-hidden>·</span>
                          <span>+{c.points} XP</span>
                        </span>
                      </button>
                    </li>
                  );
                })}
              </ul>
            )}
          </aside>

          {/* Terminal */}
          <section aria-label="Operational terminal" className="flex min-w-0 flex-col gap-3">
            {selected ? (
              <div className="terminal-card flex flex-wrap items-center justify-between gap-2 p-3">
                <div className="min-w-0">
                  <p className="truncate font-mono text-sm font-semibold text-cyber-text">
                    {selected.title}
                  </p>
                  <p className="font-mono text-[10px] uppercase tracking-wider text-cyber-muted">
                    {selected.category} · {selected.difficulty} · +{selected.points} XP
                    {selected.flag_hint_prefix ? ` · token prefix: ${selected.flag_hint_prefix}` : ''}
                  </p>
                </div>
                <span
                  className={`rounded-full border px-3 py-1 font-mono text-[10px] uppercase tracking-wider ${
                    solvedSet.has(selected.slug)
                      ? 'border-emerald-400/50 bg-emerald-400/10 text-emerald-400'
                      : 'border-cyber-border/60 text-cyber-muted'
                  }`}
                >
                  {solvedSet.has(selected.slug) ? 'cleared' : 'in progress'}
                </span>
              </div>
            ) : null}

            {selected && (
              <VirtualTerminal
                key={selected.slug}
                challenge={shellChallenge}
                solved={solvedSet.has(selected.slug)}
                submitFlag={submitFlag}
              />
            )}

            {!selected && !loading && (
              <div className="terminal-card flex min-h-[420px] flex-col items-center justify-center gap-3 p-8 text-center">
                <Trophy className="h-10 w-10 text-emerald-400/60" aria-hidden />
                <p className="font-mono text-lg font-bold text-cyber-text">Awaiting op selection</p>
                <p className="max-w-md text-sm text-cyber-muted">
                  Pick an op from the roster to boot your secure shell. Clear ops to earn XP and
                  climb the district rankings.
                </p>
              </div>
            )}

            <p className="font-mono text-[11px] text-cyber-muted">
              Commands: <span className="text-cyber-primary">help</span> · ls · cat · hint · flag · clear
              · history — Ctrl+L clears the screen, ↑/↓ walks command history.
            </p>
          </section>
        </div>
      </main>
    </div>
  );
}
