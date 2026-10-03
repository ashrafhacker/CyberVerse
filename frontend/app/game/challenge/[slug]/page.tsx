'use client';

import { useState, useEffect } from 'react';
import { Flag, Clock, Star, Target, Lock, Brain, ExternalLink, CheckCircle, AlertCircle, Loader2 } from 'lucide-react';
import { api } from '@/lib/api';

interface GameChallenge {
  id: string;
  title: string;
  slug: string;
  description: string;
  category: string;
  difficulty: 'Beginner' | 'Intermediate' | 'Advanced' | 'Expert';
  points: number;
  xp: number;
  timeLimit: number;
  status: 'draft' | 'published' | 'archived';
  isPublished: boolean;
  flagHash: string;
  hints: string[];
  environmentConfig: Record<string, unknown>;
  createdAt: string;
  author: { username: string; avatar?: string };
}

const DIFFICULTY_COLORS = {
  Beginner: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
  Intermediate: 'bg-sky-500/20 text-sky-400 border-sky-500/30',
  Advanced: 'bg-violet-500/20 text-violet-400 border-violet-500/30',
  Expert: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
};

export default function ChallengePage({ params }: { params: Promise<{ slug: string }> }) {
  const [challenge, setChallenge] = useState<GameChallenge | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [submittedFlag, setSubmittedFlag] = useState('');
  const [result, setResult] = useState<{ correct: boolean; message: string; xpAwarded?: number } | null>(null);
  const [hintIndex, setHintIndex] = useState(0);
  const [timerStarted, setTimerStarted] = useState(false);
  const [timeRemaining, setTimeRemaining] = useState(0);
  const [environmentReady, setEnvironmentReady] = useState(false);

  useEffect(() => {
    params.then(p => fetchChallenge(p.slug));
  }, [params]);

  async function fetchChallenge(slug: string) {
    setLoading(true);
    try {
      const res = await api.get<GameChallenge>(`/game/challenges/${slug}`);
      setChallenge(res.data);
      setTimeRemaining(res.data.timeLimit * 60);
    } catch {
      setError('Challenge not found');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (timerStarted && timeRemaining > 0) {
      const interval = setInterval(() => {
        setTimeRemaining(t => {
          if (t <= 1) {
            setTimerStarted(false);
            return 0;
          }
          return t - 1;
        });
      }, 1000);
      return () => clearInterval(interval);
    }
  }, [timerStarted, timeRemaining]);

  function formatTime(seconds: number) {
    const m = Math.floor(seconds / 60).toString().padStart(2, '0');
    const s = (seconds % 60).toString().padStart(2, '0');
    return `${m}:${s}`;
  }

  function getDifficultyClass(difficulty: string) {
    return DIFFICULTY_COLORS[difficulty as keyof typeof DIFFICULTY_COLORS] || 'bg-cyber-border text-cyber-muted';
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!submittedFlag.trim() || submitting) return;

    setSubmitting(true);
    setResult(null);

    try {
      const res = await api.post<{ correct: boolean; message: string; xpAwarded?: number }>(
        `/game/challenges/${challenge?.slug}/submit`,
        { flag: submittedFlag.trim() }
      );
      setResult(res.data);
      if (res.data.correct) {
        setSubmittedFlag('');
      }
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Submission failed';
      setResult({ correct: false, message });
    } finally {
      setSubmitting(false);
    }
  }

  async function startChallenge() {
    if (!challenge) return;
    setTimerStarted(true);
    try {
      await api.post(`/game/challenges/${challenge.slug}/start`);
      setEnvironmentReady(true);
    } catch {
      setEnvironmentReady(false);
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-cyber-bg text-cyber-text flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="mx-auto h-12 w-12 animate-spin text-cyber-primary" />
          <p className="mt-4 text-cyber-muted">Loading challenge...</p>
        </div>
      </div>
    );
  }

  if (error || !challenge) {
    return (
      <div className="min-h-screen bg-cyber-bg text-cyber-text flex items-center justify-center">
        <div className="text-center">
          <AlertCircle className="mx-auto h-12 w-12 text-cyber-danger" />
          <h2 className="mt-4 text-2xl font-bold">Challenge Not Found</h2>
          <p className="mt-2 text-cyber-muted">{error || 'The challenge you are looking for does not exist.'}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-cyber-bg text-cyber-text">
      <div className="mx-auto max-w-5xl px-6 py-8">
        <header className="mb-8">
          <Link
            href="/game"
            className="mb-4 inline-flex items-center gap-2 text-cyber-muted hover:text-cyber-primary transition-colors"
          >
            <Flag className="h-4 w-4" />
            Back to Challenges
          </Link>

          <div className="mb-4 flex flex-wrap items-center gap-3">
            <h1 className="text-3xl font-bold md:text-4xl">{challenge.title}</h1>
            <span className={`rounded-full border px-3 py-1 text-sm font-medium ${getDifficultyClass(challenge.difficulty)}`}>
              {challenge.difficulty}
            </span>
            <span className="rounded-full border border-cyber-border bg-cyber-surface px-3 py-1 text-sm font-medium text-cyber-primary">
              {challenge.category.toUpperCase()}
            </span>
          </div>

          <div className="flex flex-wrap items-center gap-4 text-sm text-cyber-muted">
            <span className="flex items-center gap-1.5">
              <Clock className="h-4 w-4" />
              {challenge.timeLimit} minutes
            </span>
            <span className="flex items-center gap-1.5 text-amber-400">
              <Star className="h-4 w-4" />
              +{challenge.xp} XP
            </span>
            <span className="flex items-center gap-1.5 text-green-400">
              <Flag className="h-4 w-4" />
              {challenge.points} points
            </span>
            <span className="flex items-center gap-1.5">
              <Target className="h-4 w-4" />
              By {challenge.author.username}
            </span>
          </div>
        </header>

        <div className="grid gap-6 lg:grid-cols-3">
          <div className="lg:col-span-2 space-y-6">
            <section className="rounded-xl border border-cyber-border bg-cyber-surface/60 p-6">
              <h2 className="mb-4 text-xl font-semibold">Description</h2>
              <div className="prose prose-invert max-w-none text-cyber-muted">
                <p>{challenge.description}</p>
              </div>
            </section>

            <section className="rounded-xl border border-cyber-border bg-cyber-surface/60 p-6">
              <h2 className="mb-4 text-xl font-semibold">Environment</h2>
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-cyber-muted">Status</span>
                  <span className={`flex items-center gap-2 rounded-full border px-3 py-1 text-sm font-medium ${
                    environmentReady
                      ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-400'
                      : timerStarted
                        ? 'border-amber-500/30 bg-amber-500/10 text-amber-400'
                        : 'border-cyber-border bg-cyber-surface text-cyber-muted'
                  }`}>
                    {environmentReady ? (
                      <>
                        <CheckCircle className="h-4 w-4" />
                        Ready
                      </>
                    ) : timerStarted ? (
                      <>
                        <Loader2 className="h-4 w-4 animate-spin" />
                        Starting...
                      </>
                    ) : (
                      <>
                        <span className="h-2 w-2 rounded-full bg-cyber-border" />
                        Not Started
                      </>
                    )}
                  </span>
                </div>

                {!timerStarted ? (
                  <button
                    onClick={startChallenge}
                    disabled={environmentReady}
                    className="w-full rounded-lg border border-cyber-primary bg-cyber-primary/10 px-6 py-3 font-medium text-cyber-primary hover:bg-cyber-primary/20 transition-all disabled:opacity-50"
                  >
                    <Flag className="inline h-5 w-5 mr-2" />
                    {environmentReady ? 'Environment Ready' : 'Start Challenge'}
                  </button>
                ) : (
                  <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-4 text-center">
                    <p className="mb-2 text-amber-400 font-mono text-2xl">{formatTime(timeRemaining)}</p>
                    <p className="text-sm text-cyber-muted">Timer running — environment initializing</p>
                  </div>
                )}

                {environmentReady && (
                  <div className="rounded-lg border border-cyber-border bg-cyber-bg p-4">
                    <p className="mb-2 text-sm text-cyber-muted">Challenge Environment</p>
                    <div className="font-mono text-xs text-cyber-primary">
                      {JSON.stringify(challenge.environmentConfig, null, 2)}
                    </div>
                  </div>
                )}
              </div>
            </section>

            {hintIndex < (challenge.hints?.length || 0) && (
              <section className="rounded-xl border border-cyber-border bg-cyber-surface/60 p-6">
                <div className="mb-4 flex items-center justify-between">
                  <h2 className="text-xl font-semibold">Hints</h2>
                  <button
                    onClick={() => setHintIndex(h => Math.min(h + 1, (challenge.hints?.length || 0) - 1))}
                    className="rounded-lg border border-cyber-border bg-cyber-surface px-4 py-2 text-sm hover:border-cyber-primary/60 transition-all"
                  >
                    Next Hint ({hintIndex + 1}/{challenge.hints?.length || 0})
                  </button>
                </div>
                <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-4 text-amber-300">
                  {challenge.hints[hintIndex]}
                </div>
              </section>
            )}

            <section className="rounded-xl border border-cyber-border bg-cyber-surface/60 p-6">
              <h2 className="mb-4 text-xl font-semibold">Submit Flag</h2>
              <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                  <label className="mb-2 block text-sm font-medium">Flag</label>
                  <input
                    type="text"
                    value={submittedFlag}
                    onChange={e => setSubmittedFlag(e.target.value)}
                    placeholder="CYBERVERSE{...}"
                    className="w-full rounded-lg border border-cyber-border bg-black/50 px-4 py-3 text-cyber-text placeholder:text-cyber-muted focus:border-cyber-primary focus:outline-none"
                    disabled={!environmentReady || submitting}
                  />
                  <p className="mt-1 text-xs text-cyber-muted">
                    Format: CYBERVERSE{{flag_content}}. Flags are case-sensitive.
                  </p>
                </div>
                <button
                  type="submit"
                  disabled={!environmentReady || submitting}
                  className="w-full rounded-lg border border-cyber-primary bg-cyber-primary/10 px-6 py-3 font-medium text-cyber-primary hover:bg-cyber-primary/20 transition-all disabled:opacity-50"
                >
                  {submitting ? (
                    <>
                      <Loader2 className="inline h-5 w-5 mr-2 animate-spin" />
                      Submitting...
                    </>
                  ) : (
                    <>
                      <Flag className="inline h-5 w-5 mr-2" />
                      SUBMIT FLAG
                    </>
                  )}
                </button>
              </form>

              {result && (
                <div className={`rounded-lg p-4 ${
                  result.correct
                    ? 'border-emerald-500/30 bg-emerald-500/10'
                    : 'border-cyber-danger/30 bg-cyber-danger/10'
                }`}>
                  <div className="flex items-center gap-3">
                    {result.correct ? (
                      <CheckCircle className="h-6 w-6 text-emerald-400" />
                    ) : (
                      <AlertCircle className="h-6 w-6 text-cyber-danger" />
                    )}
                    <div>
                      <p className="font-medium">{result.correct ? 'Correct!' : 'Incorrect'}</p>
                      <p className="text-sm text-cyber-muted">{result.message}</p>
                      {result.correct && result.xpAwarded && (
                        <p className="mt-1 text-sm text-amber-400">+{result.xpAwarded} XP awarded</p>
                      )}
                    </div>
                  </div>
                </div>
              )}
            </section>
          </div>

          <aside className="space-y-6">
            <div className="rounded-xl border border-cyber-border bg-cyber-surface/60 p-6">
              <h3 className="mb-4 text-lg font-semibold">Challenge Info</h3>
              <dl className="space-y-3 text-sm">
                <div className="flex justify-between">
                  <dt className="text-cyber-muted">Category</dt>
                  <dd className="font-medium text-cyber-text">{challenge.category.toUpperCase()}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-cyber-muted">Difficulty</dt>
                  <dd className={`font-medium ${getDifficultyClass(challenge.difficulty)}`}>
                    {challenge.difficulty}
                  </dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-cyber-muted">Time Limit</dt>
                  <dd className="font-medium">{challenge.timeLimit} minutes</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-cyber-muted">XP Reward</dt>
                  <dd className="font-medium text-amber-400">+{challenge.xp} XP</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-cyber-muted">Points</dt>
                  <dd className="font-medium text-green-400">{challenge.points} pts</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-cyber-muted">Created</dt>
                  <dd className="font-medium">{new Date(challenge.createdAt).toLocaleDateString()}</dd>
                </div>
              </dl>
            </div>

            <div className="rounded-xl border border-cyber-border bg-cyber-surface/60 p-6">
              <h3 className="mb-4 text-lg font-semibold">Rules</h3>
              <ul className="space-y-2 text-sm text-cyber-muted">
                <li className="flex items-center gap-2">
                  <CheckCircle className="h-4 w-4 text-emerald-400" />
                  Flags are submitted via the form above
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle className="h-4 w-4 text-emerald-400" />
                  Each challenge has a time limit
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle className="h-4 w-4 text-emerald-400" />
                  Hints are available but reduce XP
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle className="h-4 w-4 text-emerald-400" />
                  All environments are isolated and safe
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle className="h-4 w-4 text-emerald-400" />
                  No real-world targeting allowed
                </li>
              </ul>
            </div>
          </aside>
        </div>
      </div>
    </div>
  );
}