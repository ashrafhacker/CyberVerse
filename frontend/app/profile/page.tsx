'use client';

import { useEffect, useState } from 'react';
import { User as UserIcon, BadgeCheck } from 'lucide-react';
import Navbar from '@/components/Navbar';
import { TerminalCard, StatCard, XPBar, LoadingScreen } from '@/components/TerminalCard';
import { useRequireAuth } from '@/lib/auth';
import { api } from '@/lib/api';
import type { Profile } from '@/lib/types';

export default function ProfilePage() {
  const { user, loading } = useRequireAuth();
  const [profile, setProfile] = useState<Profile | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!user) return;
    api
      .get<{ data: Profile }>('/profile/')
      .then((res) => setProfile(res.data))
      .catch((err) => setError(err instanceof Error ? err.message : 'Failed to load profile'));
  }, [user]);

  if (loading || !user) return <LoadingScreen />;

  return (
    <>
      <Navbar />
      <main className="mx-auto max-w-5xl px-6 py-8">
        {error && <div className="mb-6 text-cyber-danger">{error}</div>}

        {profile && (
          <>
            <TerminalCard className="mb-8" title={`agent://${profile.username}`}>
              <div className="flex flex-wrap items-center gap-6">
                <div className="flex h-24 w-24 items-center justify-center rounded-lg border border-cyber-border bg-cyber-bg">
                  <UserIcon className="h-12 w-12 text-cyber-muted" />
                </div>
                <div className="flex-1">
                  <h1 className="flex items-center gap-2 text-2xl font-bold">
                    {profile.username}
                    <BadgeCheck className="h-5 w-5 text-cyber-primary" />
                  </h1>
                  <p className="mt-1 text-sm text-cyber-muted">
                    {user.full_name} · {user.role} · {user.email}
                  </p>
                  {profile.bio && <p className="mt-2 text-sm text-cyber-text">{profile.bio}</p>}
                  <div className="mt-3 flex flex-wrap gap-2 text-xs">
                    {profile.badges.map((badge) => (
                      <span key={badge} className="rounded bg-cyber-secondary/20 px-2 py-0.5 text-cyber-secondary">
                        {badge}
                      </span>
                    ))}
                    {profile.badges.length === 0 && (
                      <span className="text-cyber-muted">no badges yet — keep completing missions</span>
                    )}
                  </div>
                </div>
                {profile.equipped_title && (
                  <span className="rounded-md border border-cyber-primary/40 bg-cyber-primary/10 px-3 py-1 font-mono text-sm text-cyber-primary">
                    [{profile.equipped_title}]
                  </span>
                )}
              </div>
            </TerminalCard>

            <div className="mb-6 grid gap-4 sm:grid-cols-3">
              <StatCard label="Total XP" value={profile.xp} />
              <StatCard label="Level" value={profile.level} />
              <StatCard label="Coins" value={profile.coins} accent="text-cyber-warning" />
            </div>

            <XPBar xp={profile.xp} level={profile.level} xpForNext={100 * profile.level} />

            <TerminalCard title="stats.json" className="mt-6">
              <pre className="overflow-x-auto font-mono text-xs text-cyber-muted">
                {JSON.stringify(profile.statistics, null, 2)}
              </pre>
            </TerminalCard>
          </>
        )}

        {!profile && !error && (
          <p className="py-16 text-center font-mono text-cyber-muted">&gt; loading profile...</p>
        )}
      </main>
    </>
  );
}
