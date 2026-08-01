'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { Zap, Flame, Target, BookOpen } from 'lucide-react';
import { useAuth } from '@/lib/auth';
import Navbar from '@/components/Navbar';
import { TerminalCard, StatCard, XPBar, LoadingScreen } from '@/components/TerminalCard';
import { api } from '@/lib/api';
import type { Course, DailyChallenge, PlayerProgress, Profile } from '@/lib/types';

export default function DashboardPage() {
  const { user, loading } = useAuth();
  const [profile, setProfile] = useState<Profile | null>(null);
  const [progress, setProgress] = useState<PlayerProgress | null>(null);
  const [daily, setDaily] = useState<DailyChallenge[]>([]);
  const [courses, setCourses] = useState<Course[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!user) return;
    Promise.all([
      api.get<{ data: Profile }>('/profile/'),
      api.get<{ data: PlayerProgress }>('/progress/overview'),
      api.get<DailyChallenge[]>('/missions/daily'),
      api.get<{ data: { items: Course[] } }>('/courses?page_size=3'),
    ])
      .then(([p, pr, d, c]) => {
        setProfile(p.data);
        setProgress(pr.data);
        setDaily(d);
        setCourses(c.data.items);
      })
      .catch((err) => setError(err instanceof Error ? err.message : 'Failed to load dashboard'));
  }, [user]);

  if (loading || !user) return <LoadingScreen />;
  if (error) {
    return (
      <>
        <Navbar />
        <div className="mx-auto max-w-7xl px-6 py-16 text-center text-cyber-danger">{error}</div>
      </>
    );
  }

  const xpForNext = 100 * (progress?.level ?? 1);

  return (
    <>
      <Navbar />
      <main className="mx-auto max-w-7xl px-6 py-8">
        <div className="mb-8 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">
              Welcome back, <span className="text-cyber-primary">{profile?.username ?? user.email}</span>
            </h1>
            <p className="mt-1 font-mono text-sm text-cyber-muted">
              rank: {profile?.rank ?? 'recruit'} · access: {user.role}
            </p>
          </div>
          <Link href="/missions" className="terminal-button">New Mission</Link>
        </div>

        <div className="mb-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatCard label="XP" value={profile?.xp ?? 0} icon={Zap} />
          <StatCard label="Level" value={profile?.level ?? 1} icon={Target} />
          <StatCard label="Streak" value={`${progress?.learning_streak ?? 0} days`} accent="text-cyber-warning" icon={Flame} />
          <StatCard label="Missions" value={progress?.missions_completed ?? 0} accent="text-cyber-success" icon={BookOpen} />
        </div>

        <div className="grid gap-6 lg:grid-cols-2">
          <div className="space-y-6">
            <XPBar xp={profile?.xp ?? 0} level={profile?.level ?? 1} xpForNext={xpForNext} />

            <TerminalCard title="daily_missions.sh">
              <h3 className="mb-3 font-semibold">Daily challenges</h3>
              {daily.length === 0 ? (
                <p className="text-sm text-cyber-muted">No challenges today. Check back after the daily rotation.</p>
              ) : (
                <ul className="space-y-2">
                  {daily.map((c) => (
                    <li key={c.id} className="flex items-center justify-between rounded-md border border-cyber-border px-3 py-2 text-sm">
                      <div>
                        <span>{c.title}</span>
                        <p className="text-xs text-cyber-muted">{c.description}</p>
                      </div>
                      <span className="font-mono text-xs text-cyber-primary">+{c.xp_reward} XP</span>
                    </li>
                  ))}
                </ul>
              )}
            </TerminalCard>
          </div>

          <TerminalCard title="recommended_courses.json">
            <h3 className="mb-3 font-semibold">Continue learning</h3>
            {courses.length === 0 ? (
              <p className="text-sm text-cyber-muted">No courses published yet.</p>
            ) : (
              <ul className="space-y-2">
                {courses.map((c) => (
                  <li key={c.id}>
                    <Link
                      href={`/courses/${c.id}`}
                      className="block rounded-md border border-cyber-border px-3 py-2 text-sm transition-colors hover:border-cyber-primary"
                    >
                      <span className="font-medium">{c.name}</span>
                      <span className="ml-2 rounded bg-cyber-border px-1.5 py-0.5 text-xs text-cyber-muted">{c.difficulty}</span>
                      <p className="mt-1 text-xs text-cyber-muted line-clamp-2">{c.description}</p>
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </TerminalCard>
        </div>
      </main>
    </>
  );
}
