'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { Loader2, Settings2, X } from 'lucide-react';
import { useRequireAuth } from '@/lib/auth';
import { LoadingScreen } from '@/components/TerminalCard';
import { useCommandCenter } from '@/lib/command-center';
import CommandSidebar from '@/components/command-center/CommandSidebar';
import CommandTopbar, { MobileNavSheet, type SearchTarget } from '@/components/command-center/CommandTopbar';
import CommandPalette from '@/components/command-center/CommandPalette';
import TacticalHeader, { StatusStrip } from '@/components/command-center/TacticalHeader';
import StatRibbon, { ribbonCells } from '@/components/command-center/StatRibbon';
import MissionHero from '@/components/command-center/MissionHero';
import ActiveTrack from '@/components/command-center/ActiveTrack';
import RecommendedPaths from '@/components/command-center/RecommendedPaths';
import SkillsMatrix from '@/components/command-center/SkillsMatrix';
import WarRoom from '@/components/command-center/WarRoom';

const STATIC_TARGETS: SearchTarget[] = [
  { id: 'nav-dashboard', label: 'Command Center', group: 'Navigation', href: '/dashboard-v2' },
  { id: 'nav-classic', label: 'Classic dashboard', group: 'Navigation', href: '/dashboard' },
  { id: 'nav-courses', label: 'Learn · course catalog', group: 'Navigation', href: '/courses', hint: 'Course tracks and modules' },
  { id: 'nav-missions', label: 'Missions console', group: 'Navigation', href: '/missions', hint: 'Daily and weekly challenges' },
  { id: 'nav-labs', label: 'Cyber Labs', group: 'Navigation', href: '/labs', hint: 'Sandbox lab facilities' },
  { id: 'nav-ctf', label: 'CTF Arena', group: 'Navigation', href: '/ctf', hint: 'Capture the flag challenges' },
  { id: 'nav-soc', label: 'SOC Center', group: 'Navigation', href: '/soc', hint: 'Alerts and incident response' },
  { id: 'nav-threat', label: 'Threat Intel', group: 'Navigation', href: '/threat-intel', hint: 'CVEs and MITRE techniques' },
  { id: 'nav-tools', label: 'Cyber Tools', group: 'Navigation', href: '/tools', hint: 'Dorker and utilities' },
  { id: 'nav-arsenal', label: 'Cyber Arsenal', group: 'Navigation', href: '/arsenal', hint: 'Tool catalog' },
  { id: 'nav-game', label: 'Global Arena', group: 'Navigation', href: '/game', hint: 'Tournaments and teams' },
  { id: 'nav-lb', label: 'Global Leaderboard', group: 'Navigation', href: '/leaderboard' },
  { id: 'nav-certs', label: 'Achievements & certificates', group: 'Navigation', href: '/certificates' },
  { id: 'nav-progression', label: 'Progression', group: 'Navigation', href: '/progression', hint: 'Inventory and quests' },
  { id: 'nav-library', label: 'Library', group: 'Navigation', href: '/library', hint: 'Saved resources' },
  { id: 'nav-profile', label: 'Operator profile', group: 'Navigation', href: '/profile' },
  { id: 'nav-external', label: 'External Labs', group: 'Navigation', href: '/external-labs' },
];

export default function CommandCenterPage() {
  const { user, loading } = useRequireAuth();
  const { snapshot, status, refreshing, refresh } = useCommandCenter();
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [navOpen, setNavOpen] = useState(false);
  const [configOpen, setConfigOpen] = useState(false);

  const targets = useMemo<SearchTarget[]>(
    () => [
      ...STATIC_TARGETS,
      ...snapshot.paths.map((p) => ({
        id: `path-${p.id}`,
        label: p.title,
        group: 'Course',
        href: p.href,
        hint: p.blurb,
      })),
      { id: 'mission-active', label: snapshot.mission.name, group: 'Mission', href: '/missions', hint: snapshot.mission.brief },
      { id: 'track-active', label: snapshot.track.lessonName, group: 'Lesson', href: snapshot.track.href, hint: snapshot.track.courseName },
    ],
    [snapshot],
  );

  const closePalette = useCallback(() => setPaletteOpen(false), []);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        setPaletteOpen((v) => !v);
      }
    };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, []);

  if (loading || !user) return <LoadingScreen />;

  const ribbon = snapshot.ribbon;

  return (
    <div className="min-h-screen bg-cyber-bg text-cyber-text">
      <CommandSidebar
        level={ribbon.level}
        rank={ribbon.rank}
        streak={ribbon.streak}
        xp={ribbon.totalXp}
        xpPercent={ribbon.levelPercent}
        unread={snapshot.unread}
        onNavigate={() => setNavOpen(false)}
      />

      <CommandTopbar
        xp={ribbon.totalXp}
        level={ribbon.level}
        streak={ribbon.streak}
        unread={snapshot.unread}
        notifications={snapshot.notifications}
        initials={snapshot.initials}
        refreshing={refreshing}
        onRefresh={refresh}
        onOpenPalette={() => setPaletteOpen(true)}
        onToggleNav={() => setNavOpen(true)}
        targets={targets}
      />

      <MobileNavSheet open={navOpen} onClose={() => setNavOpen(false)} targets={targets} />

      <main className="px-4 pb-16 pt-20 lg:ml-64 lg:px-6">
        <div className="mx-auto flex max-w-[1600px] flex-col gap-6">
          <TacticalHeader
            displayName={snapshot.displayName}
            role={ribbon.rank}
            status={status}
            refreshing={refreshing}
            onRefresh={refresh}
            missionCount={snapshot.mission.objectivesTotal}
            onOpenConfig={() => setConfigOpen(true)}
          />

          <StatRibbon
            cells={ribbonCells({
              level: ribbon.level,
              rank: ribbon.rank,
              levelPercent: ribbon.levelPercent,
              totalXp: ribbon.totalXp,
              xpNeeded: ribbon.xpNeeded,
              coins: ribbon.coins,
              streak: ribbon.streak,
              longestStreak: ribbon.longestStreak,
              labsCompleted: ribbon.labsCompleted,
              labShare: ribbon.labShare,
              missionsCompleted: ribbon.missionsCompleted,
              lessonsCompleted: ribbon.lessonsCompleted,
              quizzesPassed: ribbon.quizzesPassed,
              hoursLogged: ribbon.hoursLogged,
              badges: ribbon.badges,
              flagsSolved: snapshot.warRoom.solved,
              flagsTotal: snapshot.warRoom.total,
              globalRank: snapshot.warRoom.rank,
              hoursHref: '/progression',
            })}
          />

          <div className="grid grid-cols-1 gap-6 xl:grid-cols-12">
            <div className="flex flex-col gap-6 xl:col-span-8">
              <MissionHero
                mission={snapshot.mission}
                labHref={snapshot.labSession?.href ?? '/labs'}
                isMock={snapshot.mission.id === 'mock-mission'}
              />
              <ActiveTrack track={snapshot.track} />
              <RecommendedPaths paths={snapshot.paths} />
            </div>

            <div className="flex flex-col gap-6 xl:col-span-4">
              <SkillsMatrix
                axes={snapshot.axes}
                heatmap={snapshot.heatmap}
                hoursLogged={ribbon.hoursLogged}
                isMock={snapshot.mockPanels.includes('axes')}
              />
              <WarRoom warRoom={snapshot.warRoom} />
            </div>
          </div>

          <StatusStrip status={status} lastSyncedAt={snapshot.lastSyncedAt} onOpenConfig={() => setConfigOpen(true)} />
        </div>
      </main>

      <CommandPalette open={paletteOpen} onClose={closePalette} targets={targets} />

      {configOpen && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center p-4" role="dialog" aria-modal="true" aria-label="Deck configuration">
          <div className="absolute inset-0 bg-black/75 backdrop-blur-sm" onClick={() => setConfigOpen(false)} />
          <div className="relative w-full max-w-lg rounded-2xl border border-cyber-border bg-cyber-surface p-5 shadow-2xl">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="flex items-center gap-2 text-lg font-bold">
                <Settings2 className="h-5 w-5 text-cyber-primary" />
                Deck configuration
              </h2>
              <button type="button" onClick={() => setConfigOpen(false)} aria-label="Close" className="text-cyber-muted hover:text-cyber-primary">
                <X className="h-5 w-5" />
              </button>
            </div>

            <dl className="grid grid-cols-2 gap-3 font-mono text-[11px]">
              <Row label="Feed status" value={status} />
              <Row label="Armed challenge" value={snapshot.warRoom.activeSlug ?? 'none'} />
              <Row label="Last sync" value={snapshot.lastSyncedAt ? new Date(snapshot.lastSyncedAt).toLocaleTimeString('en-US') : 'pending'} />
              <Row label="Unread alerts" value={String(snapshot.unread)} />
            </dl>

            <div className="mt-4 flex flex-wrap gap-2">
              <Link
                href="/dashboard"
                className="flex-1 rounded-xl border border-cyber-border/60 bg-cyber-bg/60 px-4 py-2.5 text-center font-mono text-[11px] uppercase tracking-wider transition-colors hover:border-cyber-primary/50"
              >
                Classic dashboard
              </Link>
              <button
                type="button"
                onClick={refresh}
                className="flex flex-1 items-center justify-center gap-2 rounded-xl bg-cyber-primary px-4 py-2.5 font-mono text-[11px] font-bold uppercase tracking-wider text-cyber-bg"
              >
                <Loader2 className={`h-3.5 w-3.5 ${refreshing ? 'animate-spin' : ''}`} />
                Force resync
              </button>
            </div>

            {snapshot.mockPanels.length > 0 && (
              <p className="mt-3 font-mono text-[10px] text-cyber-warning">
                Placeholder panels: {snapshot.mockPanels.join(', ')}
              </p>
            )}

            <p className="mt-4 font-mono text-[10px] leading-relaxed text-cyber-muted">
              Panels degrade independently: any endpoint the backend cannot answer falls back to its tactical
              placeholder and the deck header switches to DEGRADED FEED.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-cyber-border/60 bg-cyber-bg/60 px-3 py-2">
      <dt className="uppercase tracking-wider text-cyber-muted">{label}</dt>
      <dd className="mt-0.5 truncate font-bold text-cyber-primary">{value}</dd>
    </div>
  );
}