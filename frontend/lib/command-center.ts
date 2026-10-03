/**
 * Command Center data layer.
 *
 * Aggregates every endpoint the Command Center deck renders into a single
 * snapshot. Each request degrades independently: when the backend is
 * unreachable (offline sandbox, backend still booting, token expired) the
 * affected panel falls back to its tactical placeholder instead of blanking
 * the whole page. `degraded` tells the shell which panels are standing on
 * placeholder data so it can surface the SIMULATION FEEDBACK banner.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { api } from './api';

// ---------------------------------------------------------------------------
// Panel payload types
// ---------------------------------------------------------------------------

export type ObjectiveState = 'completed' | 'active' | 'pending';

export interface CCMissionObjective {
  id: string;
  name: string;
  description?: string | null;
  objectiveType?: string | null;
  xpReward: number;
  state: ObjectiveState;
}

export interface CCMission {
  id: string;
  slug?: string;
  name: string;
  brief: string;
  difficulty: string;
  xpReward: number;
  estimatedMinutes: number;
  status: string;
  objectives: CCMissionObjective[];
  objectivesMet: number;
  objectivesTotal: number;
}

export interface CCCourseTrack {
  courseId: string;
  courseName: string;
  moduleName: string;
  lessonName: string;
  lessonId: string;
  lessonType: string;
  nextLessonName: string | null;
  xpReward: number;
  minutesLeft: number;
  percent: number;
  enrolled: boolean;
  href: string;
}

export interface CCSkillAxis {
  slug: string;
  name: string;
  shortName: string;
  percent: number;
  level: number;
  maxLevel: number;
}

export interface CCDayCell {
  /** ISO date (yyyy-mm-dd) for this cell. */
  date: string;
  label: string;
  /** 0 = no activity, 1..4 = relative intensity. */
  intensity: number;
  activities: number;
  isToday: boolean;
}

export interface CCWarEvent {
  id: string;
  actor: string;
  verb: string;
  target: string;
  meta: string;
  tone: 'primary' | 'secondary';
}

export interface CTTournament {
  id: string;
  name: string;
  status: string;
  startAt: string;
  endAt: string;
  registeredPlayers: number;
  maxPlayers: number;
  registeredTeams: number;
}

export interface CCWarRoom {
  solved: number;
  total: number;
  rank: number | null;
  totalPlayers: number | null;
  events: CCWarEvent[];
  tournament: CTTournament | null;
  /** Slug of the challenge currently armed in the quick-submit box. */
  activeSlug: string | null;
  isMock: boolean;
}

export interface CCRibbon {
  level: number;
  rank: string;
  nextRank: string | null;
  xpIntoLevel: number;
  xpNeeded: number;
  levelPercent: number;
  totalXp: number;
  coins: number;
  streak: number;
  longestStreak: number;
  labsCompleted: number;
  missionsCompleted: number;
  lessonsCompleted: number;
  quizzesPassed: number;
  timeSpentSeconds: number;
  badges: string[];
  titles: string[];
  /** Share of all completed activity spent in labs. 0-100. */
  labShare: number;
  hoursLogged: number;
}

export interface CCPathCard {
  id: string;
  title: string;
  blurb: string;
  difficulty: string;
  xp: number;
  meta: string;
  href: string;
  tone: 'info' | 'warn' | 'danger';
}

export interface CCNotification {
  id: string;
  type: string;
  title: string;
  body?: string | null;
  link?: string | null;
  isRead: boolean;
  createdAt: string | null;
}

export interface CCLabSessionRef {
  id: string;
  status: string;
  facility: string;
  mission: string | null;
  href: string;
}

export interface CommandCenterSnapshot {
  displayName: string;
  username: string;
  initials: string;
  role: string;
  ribbon: CCRibbon;
  mission: CCMission;
  track: CCCourseTrack;
  axes: CCSkillAxis[];
  heatmap: CCDayCell[];
  paths: CCPathCard[];
  warRoom: CCWarRoom;
  unread: number;
  notifications: CCNotification[];
  labSession: CCLabSessionRef | null;
  /** Panel ids currently rendered from placeholders instead of live data. */
  mockPanels: Array<'ribbon' | 'mission' | 'track' | 'axes' | 'paths' | 'warRoom'>;
  lastSyncedAt: number | null;
}

// ---------------------------------------------------------------------------
// Endpoint shapes (only what this deck consumes)
// ---------------------------------------------------------------------------

interface Envelope<T> {
  data?: T;
}

interface LevelInfo {
  level: number;
  current_xp: number;
  current_level_xp: number;
  next_level_xp: number;
  xp_into_level: number;
  xp_needed: number;
  progress_percent: number;
}

interface SkillProgress {
  total_xp: number;
  level: number;
  rank: string;
  next_rank?: string | null;
  next_rank_level?: number | null;
  branches: Array<{
    slug: string;
    name: string;
    level: number;
    max_level: number;
    xp_in_branch: number;
    activities: number;
  }>;
}

interface MissionDetail {
  id: string;
  name: string;
  description?: string | null;
  short_description?: string | null;
  difficulty: string;
  xp_reward: number;
  estimated_minutes: number;
  objectives: Array<{
    id: string;
    name: string;
    description?: string | null;
    objective_type?: string | null;
    xp_reward: number;
  }>;
}

interface MissionProgressState {
  status: string;
  current_objective_index: number;
  objectives: Array<{ objective_id: string; status: string }>;
}

interface CourseStructure {
  id: string;
  name: string;
  modules: Array<{
    id: string;
    name: string;
    order: number;
    lessons: Array<{
      id: string;
      name: string;
      lesson_type: string;
      order: number;
      estimated_minutes?: number | null;
      xp_reward: number;
    }>;
  }>;
  is_enrolled?: boolean;
  enrollment_progress?: number;
  estimated_hours?: number;
}

interface CtfChallenge {
  id: string;
  slug: string;
  title: string;
  points: number;
  solved: boolean;
}

interface CtfLeaderRow {
  display_name?: string | null;
  points: number;
  solved: number;
}

interface LessonProgressRow {
  lesson_id: string;
  status: string;
  updated_at?: string | null;
  completed_at?: string | null;
}

interface TournamentRow {
  id: string;
  name: string;
  status: string;
  start_at: string;
  end_at: string;
  registered_players: number;
  max_players: number;
  registered_teams: number;
}

interface GameTournamentList {
  tournaments: TournamentRow[];
  total: number;
}

// ---------------------------------------------------------------------------
// Tactical placeholders (used per-panel when the API is unreachable)
// ---------------------------------------------------------------------------

export const MOCK_MISSION: CCMission = {
  id: 'mock-mission',
  name: 'Operation Ghost Protocol: Triage Infiltrated Node',
  brief:
    'Identify unauthorized lateral movement across the sandbox subnet and contain the persistent C2 beacon before host egress triggers.',
  difficulty: 'hard',
  xpReward: 350,
  estimatedMinutes: 45,
  status: 'in_progress',
  objectivesMet: 2,
  objectivesTotal: 3,
  objectives: [
    { id: 'o1', name: 'Extract PCAP telemetry from the perimeter firewall', xpReward: 100, state: 'completed' },
    { id: 'o2', name: 'Decrypt TLS 1.3 session keys using Wireshark lab', xpReward: 100, state: 'completed' },
    { id: 'o3', name: 'Deploy containment rule to isolate the compromised host', xpReward: 150, state: 'active' },
  ],
};

export const MOCK_TRACK: CCCourseTrack = {
  courseId: 'mock-course',
  courseName: 'Advanced Web Penetration & API Security',
  moduleName: 'Module 4 · Exfiltration Paths',
  lessonName: 'Lesson 4.3: SSRF to Cloud Metadata Exfiltration',
  lessonId: 'mock-lesson',
  lessonType: 'theory',
  nextLessonName: 'Bypassing WAF via Unicode Normalization',
  xpReward: 120,
  minutesLeft: 22,
  percent: 78,
  enrolled: true,
  href: '/courses',
};

export const MOCK_AXES: CCSkillAxis[] = [
  { slug: 'network-defense', name: 'Network Defense', shortName: 'NET DEF', percent: 92, level: 12, maxLevel: 20 },
  { slug: 'soc-ir', name: 'SOC & Incident Response', shortName: 'SOC IR', percent: 90, level: 11, maxLevel: 20 },
  { slug: 'web-security', name: 'Web Penetration Security', shortName: 'WEB SEC', percent: 85, level: 10, maxLevel: 20 },
  { slug: 'osint-recon', name: 'OSINT & Recon', shortName: 'OSINT', percent: 78, level: 9, maxLevel: 20 },
  { slug: 'reversing', name: 'Reverse Engineering', shortName: 'REV ENG', percent: 61, level: 7, maxLevel: 20 },
  { slug: 'forensics', name: 'Digital Forensics', shortName: 'FORENSICS', percent: 54, level: 6, maxLevel: 20 },
];

export const MOCK_PATHS: CCPathCard[] = [
  {
    id: 'mock-path-1',
    title: 'Automated Threat Hunting with SIEM & Suricata',
    blurb: 'Build custom rule engines and parse ELK indices under sustained packet saturation.',
    difficulty: 'intermediate',
    xp: 500,
    meta: '6 tactical labs',
    href: '/courses',
    tone: 'info',
  },
  {
    id: 'mock-path-2',
    title: 'Buffer Overflow & Memory Exploitation in Linux x64',
    blurb: 'Defeat ASLR, NX and stack canaries using ROP chains and tailored shellcode.',
    difficulty: 'advanced',
    xp: 850,
    meta: '8 tactical labs',
    href: '/courses',
    tone: 'warn',
  },
  {
    id: 'mock-path-3',
    title: 'Active Directory Kerberoasting Defense',
    blurb: 'Simulate enterprise forest compromise and harden Kerberos TGT validation.',
    difficulty: 'expert',
    xp: 1200,
    meta: '10 tactical labs',
    href: '/courses',
    tone: 'danger',
  },
];

export const MOCK_WAR_EVENTS: CCWarEvent[] = [
  { id: 'm1', actor: '@krypton', verb: 'solved', target: 'Kernel Panic', meta: '+250 pts', tone: 'primary' },
  { id: 'm2', actor: '@0xViper', verb: 'captured flag on', target: 'ShadowDB', meta: '1 hint used', tone: 'secondary' },
  { id: 'm3', actor: 'Team ZeroDay', verb: 'defended node', target: 'Bastion-01', meta: 'red team ejected', tone: 'primary' },
];

export const MOCK_RIBBON: CCRibbon = {
  level: 12,
  rank: 'Cyber Analyst',
  nextRank: null,
  xpIntoLevel: 14850,
  xpNeeded: 5000,
  levelPercent: 72,
  totalXp: 14850,
  coins: 3200,
  streak: 18,
  longestStreak: 24,
  labsCompleted: 42,
  missionsCompleted: 12,
  lessonsCompleted: 68,
  quizzesPassed: 51,
  timeSpentSeconds: 172800,
  badges: ['Ghost Hunter'],
  titles: ['Cyber Analyst'],
  labShare: 34,
  hoursLogged: 48,
};

export const MOCK_HEATMAP: CCDayCell[] = buildHeatmap([]);

// ---------------------------------------------------------------------------
// Pure helpers (unit-tested in lib/command-center.test.ts)
// ---------------------------------------------------------------------------

export function initialsOf(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return 'CV';
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

export function greetingFor(date: Date): string {
  const h = date.getHours();
  if (h < 5) return 'Still up';
  if (h < 12) return 'Good morning';
  if (h < 18) return 'Good afternoon';
  return 'Good evening';
}

export function clampPercent(value: number): number {
  if (!Number.isFinite(value)) return 0;
  return Math.max(0, Math.min(100, Math.round(value)));
}

export function formatNumber(value: number): string {
  if (!Number.isFinite(value)) return '0';
  return new Intl.NumberFormat('en-US').format(Math.round(value));
}

export function formatDuration(totalSeconds: number): string {
  if (!Number.isFinite(totalSeconds) || totalSeconds <= 0) return '0m';
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.round((totalSeconds % 3600) / 60);
  if (hours <= 0) return `${minutes}m`;
  return `${hours}h ${minutes}m`;
}

export function formatCountdown(msRemaining: number): string {
  const total = Math.max(0, Math.floor(msRemaining / 1000));
  const h = String(Math.floor(total / 3600)).padStart(2, '0');
  const m = String(Math.floor((total % 3600) / 60)).padStart(2, '0');
  const s = String(total % 60).padStart(2, '0');
  return `${h}h : ${m}m : ${s}s`;
}

/**
 * Buckets lesson-progress timestamps into the trailing 30-day activity grid.
 * Cells are ordered oldest -> newest and coloured by relative density so the
 * 30-day heatmap always renders from real `updated_at` values when present.
 */
export function buildHeatmap(
  timestamps: string[],
  days = 30,
  now: Date = new Date(),
): CCDayCell[] {
  const counts = new Map<string, number>();
  for (const raw of timestamps) {
    if (!raw) continue;
    const d = new Date(raw);
    if (Number.isNaN(d.getTime())) continue;
    const key = dayKey(d);
    counts.set(key, (counts.get(key) ?? 0) + 1);
  }

  const max = Math.max(1, ...counts.values());
  const cells: CCDayCell[] = [];
  for (let offset = days - 1; offset >= 0; offset -= 1) {
    const date = new Date(now.getFullYear(), now.getMonth(), now.getDate() - offset);
    const key = dayKey(date);
    const activities = counts.get(key) ?? 0;
    const ratio = activities / max;
    cells.push({
      date: key,
      label: `${activities} update${activities === 1 ? '' : 's'} on ${key}`,
      intensity: activities === 0 ? 0 : Math.max(1, Math.min(4, Math.ceil(ratio * 4))),
      activities,
      isToday: offset === 0,
    });
  }
  return cells;
}

function dayKey(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

/** Turns raw radar values (0-100 per axis) into SVG polygon point strings. */
export function radarPolygonPoints(values: number[], radius = 90, cx = 120, cy = 120): string {
  return values
    .map((value, i) => {
      const angle = (Math.PI * 2 * i) / Math.max(1, values.length) - Math.PI / 2;
      const r = (clampPercent(value) / 100) * radius;
      return `${(cx + r * Math.cos(angle)).toFixed(1)},${(cy + r * Math.sin(angle)).toFixed(1)}`;
    })
    .join(' ');
}

/** Equally spaced ring outlines for the radar background. */
export function radarRingPoints(sides: number, radius: number, cx = 120, cy = 120): string {
  return Array.from({ length: sides }, (_, i) => {
    const angle = (Math.PI * 2 * i) / Math.max(1, sides) - Math.PI / 2;
    return `${(cx + radius * Math.cos(angle)).toFixed(1)},${(cy + radius * Math.sin(angle)).toFixed(1)}`;
  }).join(' ');
}

/** Flattens a course structure into the ordered lesson list for "next up". */
export function flattenLessons(structure: CourseStructure): Array<{
  moduleName: string;
  lesson: CourseStructure['modules'][number]['lessons'][number];
}> {
  const flat: Array<{
    moduleName: string;
    lesson: CourseStructure['modules'][number]['lessons'][number];
  }> = [];
  for (const module of [...(structure.modules ?? [])].sort((a, b) => a.order - b.order)) {
    const lessons = [...(module.lessons ?? [])].sort((a, b) => a.order - b.order);
    for (const lesson of lessons) flat.push({ moduleName: module.name, lesson });
  }
  return flat;
}

export function resolveTrack(
  structure: CourseStructure | null,
  completedLessonIds: Set<string>,
): CCCourseTrack | null {
  if (!structure) return null;
  const flat = flattenLessons(structure);
  if (flat.length === 0) return null;

  const index = flat.findIndex(({ lesson }) => !completedLessonIds.has(lesson.id));
  const target = index === -1 ? flat[flat.length - 1] : flat[index];
  const next = index === -1 ? null : flat[index + 1] ?? null;
  const percent = Math.round((completedLessonIds.size / flat.length) * 100);

  const remainingMinutes = flat
    .slice(index === -1 ? 0 : index)
    .reduce((sum, { lesson }) => sum + (lesson.estimated_minutes ?? 0), 0);

  return {
    courseId: structure.id,
    courseName: structure.name,
    moduleName: target.moduleName,
    lessonName: target.lesson.name,
    lessonId: target.lesson.id,
    lessonType: target.lesson.lesson_type,
    nextLessonName: next?.lesson.name ?? null,
    xpReward: target.lesson.xp_reward,
    minutesLeft: Math.max(1, Math.round(remainingMinutes)),
    percent,
    enrolled: structure.is_enrolled ?? false,
    href: `/courses/${structure.id}`,
  };
}

export function resolveMission(
  detail: MissionDetail | null,
  progress: MissionProgressState | null,
): CCMission | null {
  if (!detail) return null;
  const completed = new Set(
    (progress?.objectives ?? [])
      .filter((o) => o.status === 'completed')
      .map((o) => o.objective_id),
  );
  const objectives: CCMissionObjective[] = (detail.objectives ?? []).map((objective, i) => ({
    id: objective.id,
    name: objective.name,
    description: objective.description ?? null,
    objectiveType: objective.objective_type ?? null,
    xpReward: objective.xp_reward,
    state: completed.has(objective.id)
      ? 'completed'
      : i === (progress?.current_objective_index ?? 0)
        ? 'active'
        : 'pending',
  }));

  return {
    id: detail.id,
    name: detail.name,
    brief: detail.short_description ?? detail.description ?? '',
    difficulty: detail.difficulty,
    xpReward: detail.xp_reward,
    estimatedMinutes: detail.estimated_minutes,
    status: progress?.status ?? 'not_started',
    objectives,
    objectivesMet: objectives.filter((o) => o.state === 'completed').length,
    objectivesTotal: objectives.length,
  };
}

export function toWarEvents(rows: CtfLeaderRow[]): CCWarEvent[] {
  return rows.slice(0, 6).map((row, i) => ({
    id: `lb-${i}-${row.display_name ?? 'anon'}`,
    actor: row.display_name ?? 'anonymous',
    verb: row.solved > 0 ? `captured ${row.solved} flag${row.solved === 1 ? '' : 's'}` : 'entered the arena',
    target: `${formatNumber(row.points)} pts`,
    meta: i === 0 ? 'leading the board' : 'on the weekly board',
    tone: i % 2 === 0 ? 'primary' : 'secondary',
  }));
}

export function pickUpcomingTournament(list: TournamentRow[]): CTTournament | null {
  const mapped = (list ?? []).map((t) => ({
    id: t.id,
    name: t.name,
    status: t.status,
    startAt: t.start_at,
    endAt: t.end_at,
    registeredPlayers: t.registered_players,
    maxPlayers: t.max_players,
    registeredTeams: t.registered_teams,
  }));
  const upcoming = mapped
    .filter((t) => t.status === 'upcoming' || new Date(t.startAt).getTime() > Date.now())
    .sort((a, b) => new Date(a.startAt).getTime() - new Date(b.startAt).getTime());
  return upcoming[0] ?? mapped[0] ?? null;
}

export function labShareOf(ribbon: Pick<CCRibbon, 'labsCompleted' | 'missionsCompleted' | 'lessonsCompleted'>): number {
  const total = ribbon.labsCompleted + ribbon.missionsCompleted + ribbon.lessonsCompleted;
  if (total <= 0) return 0;
  return clampPercent((ribbon.labsCompleted / total) * 100);
}

// ---------------------------------------------------------------------------
// Aggregation
// ---------------------------------------------------------------------------

async function safe<T>(path: string): Promise<T | null> {
  try {
    const res = await api.get<Envelope<T>>(path, { timeoutMs: 8000, retries: 1 });
    return (res?.data ?? null) as T | null;
  } catch {
    return null;
  }
}

async function loadSnapshot(): Promise<CommandCenterSnapshot> {
  const [
    profile,
    progress,
    levelInfo,
    skills,
    missions,
    courses,
    challenges,
    ctfBoard,
    weeklyBoard,
    tournaments,
    lessonProgress,
    notifications,
    labSessions,
  ] = await Promise.all([
    safe<import('./types').Profile>('/profile/'),
    safe<import('./types').PlayerProgress>('/progress/overview'),
    safe<LevelInfo>('/profile/level'),
    safe<SkillProgress>('/skills'),
    safe<{ items: import('./types').Mission[] }>('/missions?page_size=6'),
    safe<{ items: import('./types').Course[] }>('/courses?page_size=6'),
    safe<CtfChallenge[]>('/ctf/challenges'),
    safe<CtfLeaderRow[]>('/ctf/leaderboard'),
    safe<{ my_rank: number | null; total_players: number }>('/leaderboard/?type=weekly&limit=1'),
    safe<GameTournamentList>('/game/tournaments?page_size=10'),
    safe<LessonProgressRow[]>('/progress/lessons'),
    safe<{ items: Array<{ id: string; notification_type: string; title: string; body?: string; link?: string; is_read: boolean; created_at?: string }> }>(
      '/notifications?page_size=5',
    ),
    safe<import('./types').LabSession[]>('/labs/sessions'),
  ]);

  const activeMissionId = progress?.current_mission_id ?? null;
  const activeCourseId = progress?.current_course_id ?? null;

  const [missionDetail, missionProgress, courseStructure] = await Promise.all([
    activeMissionId ? safe<MissionDetail>(`/missions/${activeMissionId}`) : Promise.resolve(null),
    activeMissionId ? safe<MissionProgressState>(`/missions/${activeMissionId}/progress`) : Promise.resolve(null),
    activeCourseId ? safe<CourseStructure>(`/courses/${activeCourseId}`) : Promise.resolve(null),
  ]);

  // --- ribbon -------------------------------------------------------------
  const completedLessonIds = new Set(
    (lessonProgress ?? [])
      .filter((l) => l.status === 'completed')
      .map((l) => l.lesson_id),
  );
  const lessonTimestamps = (lessonProgress ?? [])
    .map((l) => l.updated_at ?? l.completed_at ?? '')
    .filter(Boolean);

  const labShare = labShareOf({
    labsCompleted: progress?.labs_completed ?? 0,
    missionsCompleted: progress?.missions_completed ?? 0,
    lessonsCompleted: progress?.lessons_completed ?? 0,
  });

  const ribbon: CCRibbon = {
    level: levelInfo?.level ?? progress?.level ?? profile?.level ?? MOCK_RIBBON.level,
    rank: skills?.rank ?? profile?.rank ?? MOCK_RIBBON.rank,
    nextRank: skills?.next_rank ?? null,
    xpIntoLevel: levelInfo?.xp_into_level ?? progress?.total_xp ?? MOCK_RIBBON.xpIntoLevel,
    xpNeeded: levelInfo?.xp_needed ?? MOCK_RIBBON.xpNeeded,
    levelPercent: clampPercent(levelInfo?.progress_percent ?? MOCK_RIBBON.levelPercent),
    totalXp: skills?.total_xp ?? progress?.total_xp ?? profile?.xp ?? MOCK_RIBBON.totalXp,
    coins: profile?.coins ?? progress?.total_coins ?? MOCK_RIBBON.coins,
    streak: progress?.learning_streak ?? 0,
    longestStreak: progress?.longest_streak ?? 0,
    labsCompleted: progress?.labs_completed ?? 0,
    missionsCompleted: progress?.missions_completed ?? 0,
    lessonsCompleted: progress?.lessons_completed ?? 0,
    quizzesPassed: progress?.quizzes_passed ?? 0,
    timeSpentSeconds: progress?.time_spent_seconds ?? 0,
    badges: profile?.badges ?? [],
    titles: profile?.titles ?? [],
    labShare,
    hoursLogged: Math.round((progress?.time_spent_seconds ?? 0) / 3600),
  };

  // --- mission ------------------------------------------------------------
  const mockPanels: CommandCenterSnapshot['mockPanels'] = [];
  const resolvedMission =
    resolveMission(missionDetail, missionProgress) ??
    resolveMission(missions?.items?.[0] ? { ...missions.items[0], objectives: [] } : null, null);
  if (!resolvedMission) mockPanels.push('mission');
  const mission = resolvedMission ?? MOCK_MISSION;

  // --- active track -------------------------------------------------------
  const resolvedTrack =
    resolveTrack(courseStructure, completedLessonIds) ??
    (courses?.items?.[0]
      ? {
          ...MOCK_TRACK,
          courseId: courses.items[0].id,
          courseName: courses.items[0].name,
          href: `/courses/${courses.items[0].id}`,
        }
      : null);
  if (!resolvedTrack) mockPanels.push('track');
  const track = resolvedTrack ?? MOCK_TRACK;

  // --- skills radar -------------------------------------------------------
  const liveAxes: CCSkillAxis[] = (skills?.branches ?? []).slice(0, 6).map((b) => ({
    slug: b.slug,
    name: b.name,
    shortName: shortAxisName(b.name),
    percent: b.max_level > 0 ? clampPercent((b.level / b.max_level) * 100) : 0,
    level: b.level,
    maxLevel: b.max_level,
  }));
  if (liveAxes.length < 3) mockPanels.push('axes');
  const resolvedAxes = liveAxes.length === 6 ? liveAxes : MOCK_AXES;

  // --- recommended paths --------------------------------------------------
  const paths: CCPathCard[] = (courses?.items ?? [])
    .filter((c) => c.id !== track.courseId)
    .slice(0, 3)
    .map((c) => ({
      id: c.id,
      title: c.name,
      blurb: c.short_description || c.description || 'Self-paced track with graded labs.',
      difficulty: c.difficulty,
      xp: Math.max(100, Math.round(c.estimated_hours * 150)),
      meta: `${c.estimated_hours}h estimated`,
      href: `/courses/${c.id}`,
      tone: toneForDifficulty(c.difficulty),
    }));
  if (paths.length === 0) {
    mockPanels.push('paths');
    paths.push(...MOCK_PATHS);
  }

  // --- war room -----------------------------------------------------------
  const challengeList = challenges ?? [];
  const solved = challengeList.filter((c) => c.solved).length;
  const warEvents = ctfBoard && ctfBoard.length > 0 ? toWarEvents(ctfBoard) : MOCK_WAR_EVENTS;
  if (warRoom_isMock(challenges, ctfBoard)) mockPanels.push('warRoom');
  const warRoom: CCWarRoom = {
    solved,
    total: challengeList.length,
    rank: weeklyBoard?.my_rank ?? null,
    totalPlayers: weeklyBoard?.total_players ?? null,
    events: warEvents,
    tournament: pickUpcomingTournament(tournaments?.tournaments ?? []),
    activeSlug: challengeList.find((c) => !c.solved)?.slug ?? challengeList[0]?.slug ?? null,
    isMock: warRoom_isMock(challenges, ctfBoard),
  };

  // --- notifications + lab session ---------------------------------------
  const notificationItems = notifications?.items ?? [];
  const activeSession = (labSessions ?? []).find((s) => s.status === 'active') ?? (labSessions ?? [])[0] ?? null;

  const displayName = profile?.username || 'Operator';

  return {
    displayName,
    username: profile?.username ?? 'operator',
    initials: initialsOf(displayName),
    role: skills?.rank ?? profile?.rank ?? 'recruit',
    ribbon,
    mission,
    track,
    axes: resolvedAxes,
    heatmap: buildHeatmap(lessonTimestamps),
    paths,
    warRoom,
    unread: notificationItems.filter((n) => !n.is_read).length,
    notifications: notificationItems.map((n) => ({
      id: n.id,
      type: n.notification_type,
      title: n.title,
      body: n.body ?? null,
      link: n.link ?? null,
      isRead: n.is_read,
      createdAt: n.created_at ?? null,
    })),
    labSession: activeSession
      ? {
          id: activeSession.id,
          status: activeSession.status,
          facility: activeSession.current_facility_slug,
          mission: activeSession.mission_slug ?? null,
          href: `/labs/${activeSession.id}`,
        }
      : null,
    mockPanels,
    lastSyncedAt: Date.now(),
  };
}

function warRoom_isMock(challenges: CtfChallenge[] | null, board: CtfLeaderRow[] | null): boolean {
  return challenges === null || board === null || board.length === 0;
}

function shortAxisName(name: string): string {
  const cleaned = name.replace(/[^a-z0-9 ]/gi, '').trim();
  const words = cleaned.split(/\s+/).filter(Boolean);
  if (words.length === 1) return cleaned.toUpperCase().slice(0, 9);
  if (words.length === 2) return words.map((w) => w[0].toUpperCase()).join(' ');
  return words.map((w) => w[0].toUpperCase()).join('') + ' SEC';
}

function toneForDifficulty(difficulty: string): CCPathCard['tone'] {
  switch (difficulty) {
    case 'easy':
    case 'beginner':
      return 'info';
    case 'medium':
    case 'intermediate':
      return 'warn';
    default:
      return 'danger';
  }
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export type SnapshotStatus = 'loading' | 'live' | 'degraded';

export function useCommandCenter(): {
  snapshot: CommandCenterSnapshot;
  status: SnapshotStatus;
  refreshing: boolean;
  refresh: () => void;
} {
  const [snapshot, setSnapshot] = useState<CommandCenterSnapshot>(() => ({
    displayName: 'Operator',
    username: 'operator',
    initials: 'CV',
    role: 'recruit',
    ribbon: MOCK_RIBBON,
    mission: MOCK_MISSION,
    track: MOCK_TRACK,
    axes: MOCK_AXES,
    heatmap: MOCK_HEATMAP,
    paths: MOCK_PATHS,
    warRoom: {
      solved: 0,
      total: 0,
      rank: null,
      totalPlayers: null,
      events: MOCK_WAR_EVENTS,
      tournament: null,
      activeSlug: null,
      isMock: true,
    },
    unread: 0,
    notifications: [],
    labSession: null,
    mockPanels: ['ribbon', 'mission', 'track', 'axes', 'paths', 'warRoom'],
    lastSyncedAt: null,
  }));
  const [status, setStatus] = useState<SnapshotStatus>('loading');
  const [refreshing, setRefreshing] = useState(false);
  const mounted = useRef(true);

  const refresh = useCallback(() => {
    setRefreshing(true);
    loadSnapshot()
      .then((next) => {
        if (!mounted.current) return;
        setSnapshot(next);
        setStatus(next.mockPanels.length === 0 ? 'live' : 'degraded');
      })
      .finally(() => {
        if (mounted.current) setRefreshing(false);
      });
  }, []);

  useEffect(() => {
    mounted.current = true;
    refresh();
    return () => {
      mounted.current = false;
    };
  }, [refresh]);

  return { snapshot, status, refreshing, refresh };
}

/** Live countdown hook for the tournament banner. */
export function useCountdown(targetIso: string | null | undefined): string | null {
  const [label, setLabel] = useState<string | null>(null);

  useEffect(() => {
    if (!targetIso) {
      setLabel(null);
      return;
    }
    const target = new Date(targetIso).getTime();
    if (Number.isNaN(target)) {
      setLabel(null);
      return;
    }
    const tick = () => setLabel(formatCountdown(target - Date.now()));
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, [targetIso]);

  return label;
}