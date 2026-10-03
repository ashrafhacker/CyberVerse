'use client';

import { useState, useEffect } from 'react';
import { Globe, Trophy, Flag, Users, Zap, Lock, Brain, Target, ChevronRight } from 'lucide-react';
import Link from 'next/link';
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
  createdAt: string;
}

interface ChallengesResponse {
  challenges: GameChallenge[];
  total: number;
}

const CATEGORIES = [
  { id: 'all', label: 'ALL', icon: Globe },
  { id: 'web', label: 'WEB', icon: Globe },
  { id: 'network', label: 'NETWORK', icon: Globe },
  { id: 'linux', label: 'LINUX', icon: Target },
  { id: 'crypto', label: 'CRYPTO', icon: Lock },
  { id: 'osint', label: 'OSINT', icon: Brain },
  { id: 'forensics', label: 'FORENSICS', icon: Trophy },
  { id: 'reversing', label: 'REVERSING', icon: Lock },
  { id: 'log-analysis', label: 'LOG ANALYSIS', icon: Trophy },
  { id: 'incident-response', label: 'INCIDENT RESPONSE', icon: Zap },
  { id: 'phishing', label: 'PHISHING', icon: Target },
  { id: 'secure-coding', label: 'SECURE CODING', icon: Brain },
  { id: 'cloud', label: 'CLOUD', icon: Globe },
  { id: 'malware', label: 'MALWARE', icon: Lock },
] as const;

const DIFFICULTY_COLORS = {
  Beginner: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
  Intermediate: 'bg-sky-500/20 text-sky-400 border-sky-500/30',
  Advanced: 'bg-violet-500/20 text-violet-400 border-violet-500/30',
  Expert: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
};

export default function GamePage() {
  const [activeCategory, setActiveCategory] = useState('all');
  const [challenges, setChallenges] = useState<GameChallenge[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedChallenge, setSelectedChallenge] = useState<GameChallenge | null>(null);

  useEffect(() => {
    fetchChallenges();
  }, [activeCategory]);

  async function fetchChallenges() {
    setLoading(true);
    try {
      const res = await api.get<ChallengesResponse>('/game/challenges', {
        params: { category: activeCategory === 'all' ? undefined : activeCategory, published: true },
      });
      setChallenges(res.data.challenges);
    } catch {
      setChallenges([]);
    } finally {
      setLoading(false);
    }
  }

  function getDifficultyClass(difficulty: string) {
    return DIFFICULTY_COLORS[difficulty as keyof typeof DIFFICULTY_COLORS] || 'bg-cyber-border text-cyber-muted';
  }

  return (
    <div className="min-h-screen bg-cyber-bg text-cyber-text">
      <div className="mx-auto max-w-7xl px-6 py-12">
        <header className="mb-8">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-6">
            <div>
              <h1 className="text-4xl font-bold tracking-tight md:text-5xl">
                CYBERVERSE <span className="text-cyber-primary">CYBER GAME</span>
              </h1>
              <p className="mt-2 text-lg text-cyber-muted">
                Native cybersecurity challenges. Play, learn, compete.
              </p>
            </div>
            <div className="flex flex-wrap gap-3">
              <Link
                href="/game/arena"
                className="rounded-lg border border-cyber-primary/60 bg-cyber-primary/10 px-6 py-3 font-medium text-cyber-primary hover:bg-cyber-primary/20 transition-all"
              >
                <Zap className="inline h-5 w-5 mr-2" />
                Enter Arena
              </Link>
              <Link
                href="/game/tournaments"
                className="rounded-lg border border-cyber-border bg-cyber-surface px-6 py-3 font-medium hover:border-cyber-primary/60 transition-all"
              >
                <Trophy className="inline h-5 w-5 mr-2" />
                Tournaments
              </Link>
              <Link
                href="/game/teams"
                className="rounded-lg border border-cyber-border bg-cyber-surface px-6 py-3 font-medium hover:border-cyber-primary/60 transition-all"
              >
                <Users className="inline h-5 w-5 mr-2" />
                Teams
              </Link>
              <Link
                href="/global-arena"
                className="rounded-lg border border-cyber-border bg-cyber-surface px-6 py-3 font-medium hover:border-cyber-primary/60 transition-all"
              >
                <Flag className="inline h-5 w-5 mr-2" />
                Leaderboard
              </Link>
            </div>
          </div>
        </header>

        <nav className="mb-6 overflow-x-auto" aria-label="Challenge categories">
          <ul className="flex gap-2 min-w-max" role="tablist">
            {CATEGORIES.map(({ id, label, icon: Icon }) => (
              <li key={id} role="presentation">
                <button
                  onClick={() => setActiveCategory(id)}
                  className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition-all whitespace-nowrap ${
                    activeCategory === id
                      ? 'bg-cyber-primary/20 border border-cyber-primary text-cyber-primary'
                      : 'bg-cyber-surface/60 border border-cyber-border text-cyber-muted hover:border-cyber-primary/60 hover:text-cyber-text'
                  }`}
                  role="tab"
                  aria-selected={activeCategory === id}
                >
                  <Icon className="h-3.5 w-3.5" />
                  {label}
                </button>
              </li>
            ))}
          </ul>
        </nav>

        {selectedChallenge && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4">
            <div className="w-full max-w-3xl max-h-[90vh] overflow-y-auto rounded-2xl border border-cyber-primary/60 bg-cyber-dark/95 p-6 shadow-[0_0_30px_rgba(0,229,255,0.25)]">
              <div className="mb-4 flex items-center justify-between">
                <h2 className="text-xl font-bold text-cyber-primary">{selectedChallenge.title}</h2>
                <button
                  onClick={() => setSelectedChallenge(null)}
                  className="text-cyber-muted hover:text-cyber-danger"
                >
                  ✕
                </button>
              </div>

              <div className="mb-4 flex flex-wrap gap-2">
                <span className={`rounded-full border px-3 py-1 text-xs font-medium ${getDifficultyClass(selectedChallenge.difficulty)}`}>
                  {selectedChallenge.difficulty}
                </span>
                <span className="rounded-full border border-cyber-border bg-cyber-surface px-3 py-1 text-xs font-medium text-cyber-primary">
                  {selectedChallenge.category.toUpperCase()}
                </span>
                <span className="rounded-full border border-cyber-border bg-cyber-surface px-3 py-1 text-xs font-medium text-cyber-muted">
                  {selectedChallenge.timeLimit} min
                </span>
                <span className="rounded-full border border-cyber-border bg-cyber-surface px-3 py-1 text-xs font-medium text-amber-400">
                  +{selectedChallenge.xp} XP
                </span>
              </div>

              <p className="mb-6 text-cyber-muted">{selectedChallenge.description}</p>

              <div className="flex gap-3">
                <Link
                  href={`/game/challenge/${selectedChallenge.slug}`}
                  className="flex-1 rounded-lg border border-cyber-primary bg-cyber-primary/10 px-6 py-3 font-medium text-cyber-primary text-center hover:bg-cyber-primary/20 transition-all"
                >
                  <Flag className="inline h-5 w-5 mr-2" />
                  START CHALLENGE
                </Link>
                <button
                  onClick={() => setSelectedChallenge(null)}
                  className="rounded-lg border border-cyber-border bg-cyber-surface px-6 py-3 font-medium hover:border-cyber-primary/60 transition-all"
                >
                  CLOSE
                </button>
              </div>
            </div>
          </div>
        )}

        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {loading ? (
            Array.from({ length: 6 }).map((_, i) => (
              <article key={i} className="animate-pulse rounded-xl border border-cyber-border bg-cyber-surface/60 p-6">
                <div className="mb-4 h-6 w-3/4 bg-cyber-border rounded" />
                <div className="h-4 w-full bg-cyber-border rounded" />
                <div className="mt-2 h-4 w-2/3 bg-cyber-border rounded" />
                <div className="mt-4 flex gap-2">
                  <div className="h-6 w-20 bg-cyber-border rounded-full" />
                  <div className="h-6 w-24 bg-cyber-border rounded-full" />
                </div>
              </article>
            ))
          ) : challenges.length === 0 ? (
            <div className="col-span-full text-center py-12">
              <p className="text-cyber-muted">No challenges found for this category.</p>
            </div>
          ) : (
            challenges.map((challenge) => (
              <article
                key={challenge.id}
                className="group relative overflow-hidden rounded-xl border border-cyber-border bg-cyber-surface/60 p-6 transition-all hover:border-cyber-primary/60 hover:shadow-[0_0_24px_rgba(0,229,255,0.15)]"
              >
                <div className="mb-4 flex items-center justify-between">
                  <h3 className="font-bold text-lg group-hover:text-cyber-primary transition-colors">
                    {challenge.title}
                  </h3>
                  <span className={`rounded-full border px-2 py-0.5 text-xs font-medium ${getDifficultyClass(challenge.difficulty)}`}>
                    {challenge.difficulty}
                  </span>
                </div>

                <p className="mb-4 line-clamp-2 text-sm text-cyber-muted">
                  {challenge.description}
                </p>

                <div className="mb-4 flex flex-wrap gap-1.5">
                  <span className="rounded-full border border-cyber-border bg-cyber-surface px-2 py-0.5 text-xs text-cyber-primary">
                    {challenge.category.toUpperCase()}
                  </span>
                  <span className="rounded-full border border-cyber-border bg-cyber-surface px-2 py-0.5 text-xs text-cyber-muted">
                    {challenge.timeLimit} min
                  </span>
                </div>

                <div className="flex items-center justify-between pt-4 border-t border-cyber-border">
                  <div className="flex items-center gap-4 text-sm">
                    <span className="flex items-center gap-1 text-amber-400">
                      <Star className="h-4 w-4" />
                      +{challenge.xp} XP
                    </span>
                    <span className="flex items-center gap-1 text-green-400">
                      <Flag className="h-4 w-4" />
                      {challenge.points} pts
                    </span>
                  </div>
                  <button
                    onClick={() => setSelectedChallenge(challenge)}
                    className="flex items-center gap-1.5 rounded-lg border border-cyber-primary/60 bg-cyber-primary/10 px-4 py-2 text-sm font-medium text-cyber-primary hover:bg-cyber-primary/20 transition-all"
                  >
                    VIEW
                    <ChevronRight className="h-4 w-4" />
                  </button>
                </div>
              </article>
            ))
          )}
        </div>

        <div className="mt-12 rounded-2xl border border-cyber-primary/30 bg-cyber-primary/10 p-8 text-center">
          <h3 className="mb-3 text-xl font-semibold text-cyber-primary">New to CyberVerse Game?</h3>
          <p className="mx-auto mb-6 max-w-2xl text-cyber-muted">
            Start with beginner web challenges to learn the flag submission system, then progress
            through categories. All challenges run in isolated CyberVerse environments.
          </p>
          <Link
            href="/game/challenge/getting-started"
            className="inline-flex items-center gap-2 rounded-lg border border-cyber-primary bg-cyber-primary/10 px-6 py-3 font-medium text-cyber-primary hover:bg-cyber-primary/20 transition-all"
          >
            <Zap className="h-5 w-5" />
            Start with "Getting Started"
          </Link>
        </div>
      </div>
    </div>
  );
}