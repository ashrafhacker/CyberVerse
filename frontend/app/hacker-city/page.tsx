'use client';

import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';
import {
  Building2,
  Bug,
  Cpu,
  Fingerprint,
  Flag,
  Lock,
  MapPin,
  Network,
  Radar,
  Terminal,
  Trophy,
  Bot,
} from 'lucide-react';
import { api } from '@/lib/api';

interface SkillProgress {
  total_xp: number;
  level: number;
  rank: string;
  next_rank: string | null;
  next_rank_level: number | null;
}

type DistrictStatus = 'online' | 'locked' | 'coming';

interface District {
  id: string;
  name: string;
  tagline: string;
  description: string;
  icon: React.ComponentType<{ className?: string }>;
  href: string;
  /** 0 = always open */
  levelReq: number;
  /** false = module still being wired into the grid */
  available: boolean;
  category: string;
  /** map centre in % coordinates of the map container (lg only; mobile stacks) */
  cx: number;
  cy: number;
  /** literal Tailwind position classes so JIT picks them up */
  posClass: string;
  accent: {
    text: string;
    border: string;
    bg: string;
    glow: string;
  };
}

const DISTRICTS: District[] = [
  {
    id: 'gate',
    name: 'Command Center',
    tagline: 'The city grid starts here.',
    description:
      'Your tactical home base: active missions, course tracks, skills matrix and war-room objectives rendered from live command feeds.',
    icon: Cpu,
    href: '/dashboard-v2',
    levelReq: 0,
    available: true,
    category: 'Core Operations',
    cx: 14,
    cy: 14,
    posClass: 'lg:left-[14%] lg:top-[14%]',
    accent: { text: 'text-cyber-primary', border: 'border-cyber-primary/50', bg: 'bg-cyber-primary/10', glow: 'shadow-[0_0_18px_rgba(0,229,255,0.35)]' },
  },
  {
    id: 'terminal',
    name: 'Terminal Wars',
    tagline: 'The command-line coliseum.',
    description:
      'Live shell duels against scripted adversaries — pipe, grep, chmod and exploit your way through timed operator challenges.',
    icon: Terminal,
    href: '/terminal-wars',
    levelReq: 2,
    available: true,
    category: 'Offense',
    cx: 40,
    cy: 10,
    posClass: 'lg:left-[40%] lg:top-[10%]',
    accent: { text: 'text-emerald-400', border: 'border-emerald-400/50', bg: 'bg-emerald-400/10', glow: 'shadow-[0_0_18px_rgba(52,211,153,0.35)]' },
  },
  {
    id: 'network',
    name: 'Network Lab',
    tagline: 'Packets, topologies and traffic.',
    description:
      'Sandboxed network facilities: design topologies, capture traffic, hunt anomalies and defend segmented subnets.',
    icon: Network,
    href: '/labs',
    levelReq: 0,
    available: true,
    category: 'Infrastructure',
    cx: 72,
    cy: 16,
    posClass: 'lg:left-[72%] lg:top-[16%]',
    accent: { text: 'text-cyber-primary', border: 'border-cyber-primary/50', bg: 'bg-cyber-primary/10', glow: 'shadow-[0_0_18px_rgba(0,229,255,0.35)]' },
  },
  {
    id: 'web',
    name: 'Web Exploit Arena',
    tagline: 'Break simulated apps, learn the fix.',
    description:
      'In-browser exploitation grounds: SQLi, XSS, SSRF and IDOR against fictional targets — every payload mocked, every flag validated server-side.',
    icon: Bug,
    href: '/web-exploit-arena',
    levelReq: 3,
    available: true,
    category: 'Offense',
    cx: 16,
    cy: 52,
    posClass: 'lg:left-[16%] lg:top-[52%]',
    accent: { text: 'text-violet-400', border: 'border-violet-400/50', bg: 'bg-violet-400/10', glow: 'shadow-[0_0_18px_rgba(167,139,250,0.35)]' },
  },
  {
    id: 'soc',
    name: 'SOC Fortress',
    tagline: 'Detect. Triage. Contain.',
    description:
      'Full incident-response lifecycle: triage simulated alerts, drive investigations, deploy containment and close incidents.',
    icon: Radar,
    href: '/soc',
    levelReq: 2,
    available: true,
    category: 'Defense',
    cx: 46,
    cy: 40,
    posClass: 'lg:left-[46%] lg:top-[40%]',
    accent: { text: 'text-emerald-400', border: 'border-emerald-400/50', bg: 'bg-emerald-400/10', glow: 'shadow-[0_0_18px_rgba(52,211,153,0.35)]' },
  },
  {
    id: 'forensics',
    name: 'Forensics Vault',
    tagline: 'Evidence never lies.',
    description:
      'Work forensic cases, log evidence with hash verification, and maintain chain-of-custody timelines for simulated intrusions.',
    icon: Fingerprint,
    href: '/digital-forensics',
    levelReq: 4,
    available: true,
    category: 'Investigation',
    cx: 78,
    cy: 46,
    posClass: 'lg:left-[78%] lg:top-[46%]',
    accent: { text: 'text-amber-400', border: 'border-amber-400/50', bg: 'bg-amber-400/10', glow: 'shadow-[0_0_18px_rgba(251,191,36,0.35)]' },
  },
  {
    id: 'ctf',
    name: 'CTF Arena',
    tagline: 'Flags, puzzles, leaderboards.',
    description:
      'Synthetic, solvable security puzzles across web, crypto, forensics and OSINT with a live competitive leaderboard.',
    icon: Flag,
    href: '/ctf',
    levelReq: 0,
    available: true,
    category: 'Offense',
    cx: 30,
    cy: 84,
    posClass: 'lg:left-[30%] lg:top-[84%]',
    accent: { text: 'text-violet-400', border: 'border-violet-400/50', bg: 'bg-violet-400/10', glow: 'shadow-[0_0_18px_rgba(167,139,250,0.35)]' },
  },
  {
    id: 'ai',
    name: 'AI Mentor Nexus',
    tagline: 'The mentor follows you city-wide.',
    description:
      'An always-on AI mentor overlay that explains concepts, reviews your approach and hints without spoiling — available on every district street.',
    icon: Bot,
    href: '/dashboard-v2',
    levelReq: 0,
    available: true,
    category: 'Core Operations',
    cx: 56,
    cy: 74,
    posClass: 'lg:left-[56%] lg:top-[74%]',
    accent: { text: 'text-cyber-primary', border: 'border-cyber-primary/50', bg: 'bg-cyber-primary/10', glow: 'shadow-[0_0_18px_rgba(0,229,255,0.35)]' },
  },
  {
    id: 'rankings',
    name: 'Rankings Plaza',
    tagline: 'XP, ranks and district mastery.',
    description:
      'Track XP, levels, streaks, quests, inventory and rank progression across every branch of the agency.',
    icon: Trophy,
    href: '/progression',
    levelReq: 0,
    available: true,
    category: 'Progression',
    cx: 84,
    cy: 84,
    posClass: 'lg:left-[84%] lg:top-[84%]',
    accent: { text: 'text-amber-400', border: 'border-amber-400/50', bg: 'bg-amber-400/10', glow: 'shadow-[0_0_18px_rgba(251,191,36,0.35)]' },
  },
];

/** Data-link lines drawn centre-to-centre in the same % coordinate space as the nodes. */
const LINKS: Array<[string, string]> = [
  ['gate', 'terminal'],
  ['terminal', 'network'],
  ['gate', 'web'],
  ['web', 'soc'],
  ['terminal', 'soc'],
  ['soc', 'network'],
  ['soc', 'forensics'],
  ['soc', 'ai'],
  ['web', 'ctf'],
  ['ctf', 'ai'],
  ['ai', 'rankings'],
  ['forensics', 'rankings'],
];

function districtStatus(d: District, level: number): DistrictStatus {
  if (!d.available) return 'coming';
  if (d.levelReq > 0 && level < d.levelReq) return 'locked';
  return 'online';
}

const STATUS_META: Record<DistrictStatus, { label: string; dot: string; text: string }> = {
  online: { label: 'Online', dot: 'bg-emerald-400', text: 'text-emerald-400' },
  locked: { label: 'Locked', dot: 'bg-amber-400', text: 'text-amber-400' },
  coming: { label: 'Coming online', dot: 'bg-cyber-primary animate-pulse', text: 'text-cyber-primary' },
};

export default function HackerCityPage() {
  const [skills, setSkills] = useState<SkillProgress | null>(null);
  const [selectedId, setSelectedId] = useState('gate');

  useEffect(() => {
    api
      .get<{ data: SkillProgress }>('/skills')
      .then((r) => setSkills(r.data))
      .catch(() => setSkills(null));
  }, []);

  const level = skills?.level ?? 0;
  const selected = useMemo(() => DISTRICTS.find((d) => d.id === selectedId) ?? DISTRICTS[0], [selectedId]);
  const selectedStatus = districtStatus(selected, level);
  const SelectedIcon = selected.icon;

  const onlineCount = DISTRICTS.filter((d) => districtStatus(d, level) === 'online').length;

  const byId = useMemo(() => new Map(DISTRICTS.map((d) => [d.id, d])), []);

  return (
    <div className="relative min-h-screen overflow-hidden bg-cyber-bg">
      {/* Ambient grid backdrop */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 opacity-40"
        style={{
          backgroundImage:
            'linear-gradient(rgba(0,229,255,0.06) 1px, transparent 1px), linear-gradient(90deg, rgba(0,229,255,0.06) 1px, transparent 1px)',
          backgroundSize: '48px 48px',
          maskImage: 'radial-gradient(ellipse at 50% 30%, black 30%, transparent 80%)',
          WebkitMaskImage: 'radial-gradient(ellipse at 50% 30%, black 30%, transparent 80%)',
        }}
      />
      {/* Skyline silhouette */}
      <svg
        aria-hidden
        className="pointer-events-none absolute bottom-0 left-0 h-40 w-full text-cyber-surface/70"
        viewBox="0 0 1440 160"
        preserveAspectRatio="none"
      >
        <path
          fill="currentColor"
          d="M0,160 L0,96 L48,96 L48,64 L96,64 L96,96 L150,96 L150,40 L168,40 L168,24 L186,24 L186,40 L204,40 L204,96 L280,96 L280,72 L330,72 L330,112 L390,112 L390,56 L430,56 L430,88 L500,88 L500,32 L520,32 L520,16 L540,16 L540,32 L560,32 L560,88 L640,88 L640,120 L700,120 L700,64 L760,64 L760,96 L830,96 L830,48 L880,48 L880,104 L950,104 L950,72 L1010,72 L1010,36 L1040,36 L1040,20 L1070,20 L1070,72 L1140,72 L1140,112 L1200,112 L1200,80 L1270,80 L1270,120 L1340,120 L1340,96 L1440,96 L1440,160 Z"
        />
      </svg>

      <main className="relative mx-auto max-w-7xl px-4 py-10 sm:px-6 lg:px-8">
        {/* Header */}
        <header className="mb-8 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
          <div>
            <p className="mb-2 flex items-center gap-2 font-mono text-xs uppercase tracking-[0.25em] text-cyber-muted">
              <MapPin className="h-3.5 w-3.5" /> Nine districts · one grid
            </p>
            <h1 className="font-mono text-4xl font-bold text-cyber-primary drop-shadow-[0_0_18px_rgba(0,229,255,0.45)] sm:text-5xl">
              HACKER CITY
            </h1>
            <p className="mt-2 max-w-xl text-sm text-cyber-muted">
              Navigate the cyberpunk metropolis. Every district is a live training module — clear the
              level gate, jack in, and climb the ranks.
            </p>
          </div>

          <div className="terminal-card w-full max-w-sm p-4 md:w-auto">
            <div className="flex items-center justify-between gap-4">
              <div>
                <p className="font-mono text-[11px] uppercase tracking-wider text-cyber-muted">Operator</p>
                <p className="font-mono text-lg font-bold text-cyber-primary">
                  {skills ? (
                    <>
                      LVL {skills.level} <span className="text-cyber-muted">·</span> {skills.rank}
                    </>
                  ) : (
                    <span className="text-cyber-muted">Loading…</span>
                  )}
                </p>
              </div>
              <div className="text-right">
                <p className="font-mono text-[11px] uppercase tracking-wider text-cyber-muted">Total XP</p>
                <p className="font-mono text-lg font-bold text-cyber-secondary">
                  {skills ? skills.total_xp.toLocaleString() : '—'}
                </p>
              </div>
            </div>
            <div className="mt-3 flex items-center justify-between border-t border-cyber-border/60 pt-3 font-mono text-[11px] text-cyber-muted">
              <span>
                <span className="text-emerald-400">{onlineCount}</span>/{DISTRICTS.length} districts online
              </span>
              <span>
                {skills?.next_rank
                  ? `Next: ${skills.next_rank} @ LVL ${skills.next_rank_level}`
                  : 'Max rank reached'}
              </span>
            </div>
          </div>
        </header>

        <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_320px]">
          {/* Map */}
          <section
            aria-label="Hacker City district map"
            className="terminal-card relative overflow-hidden p-4 sm:p-6 lg:min-h-[640px]"
          >
            {/* Data-link lines (desktop only, same % coordinate space as nodes) */}
            <svg
              aria-hidden
              className="pointer-events-none absolute inset-0 hidden h-full w-full lg:block"
              viewBox="0 0 100 100"
              preserveAspectRatio="none"
            >
              {LINKS.map(([a, b]) => {
                const from = byId.get(a);
                const to = byId.get(b);
                if (!from || !to) return null;
                return (
                  <line
                    key={`${a}-${b}`}
                    x1={from.cx}
                    y1={from.cy}
                    x2={to.cx}
                    y2={to.cy}
                    stroke="rgba(0,229,255,0.22)"
                    strokeWidth="0.3"
                    strokeDasharray="1.6 1.4"
                    vectorEffect="non-scaling-stroke"
                  />
                );
              })}
            </svg>

            {/* District nodes: absolute on lg, stacked grid on small screens */}
            <div className="grid gap-4 sm:grid-cols-2 lg:block lg:h-full">
              {DISTRICTS.map((d, i) => {
                const Icon = d.icon;
                const status = districtStatus(d, level);
                const isSel = d.id === selectedId;
                const meta = STATUS_META[status];
                return (
                  <button
                    key={d.id}
                    type="button"
                    aria-pressed={isSel}
                    aria-label={`${d.name} — ${meta.label}`}
                    onClick={() => setSelectedId(d.id)}
                    style={{ animationDelay: `${i * 60}ms` }}
                    className={[
                      'group flex w-full items-center gap-3 rounded-xl border p-3 text-left backdrop-blur transition-all',
                      'animate-[fadeInUp_0.5s_ease-out_both] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyber-primary',
                      d.accent.border,
                      isSel ? `${d.accent.bg} ${d.accent.glow} ring-1 ring-current` : 'bg-cyber-bg/60 hover:bg-cyber-surface/80',
                      status === 'locked' || status === 'coming' ? 'opacity-75 hover:opacity-100' : '',
                      'lg:absolute lg:w-44 lg:-translate-x-1/2 lg:-translate-y-1/2',
                      d.posClass,
                    ].join(' ')}
                  >
                    <span className={`relative shrink-0 rounded-lg p-2 ${d.accent.bg} ${d.accent.text}`}>
                      <Icon className="h-5 w-5" aria-hidden />
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="flex items-center gap-2">
                        <span className="truncate font-mono text-sm font-semibold text-cyber-text">
                          {d.name}
                        </span>
                        {status === 'locked' && <Lock className="h-3 w-3 shrink-0 text-amber-400" aria-hidden />}
                      </span>
                      <span className="mt-0.5 flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-wider">
                        <span className={`h-1.5 w-1.5 rounded-full ${meta.dot}`} aria-hidden />
                        <span className={meta.text}>
                          {status === 'locked' ? `Reach LVL ${d.levelReq}` : meta.label}
                        </span>
                      </span>
                    </span>
                  </button>
                );
              })}
            </div>
          </section>

          {/* Detail panel */}
          <aside aria-label="Selected district details" className="terminal-card flex flex-col p-5">
            <div className="mb-4 flex items-center gap-3">
              <span className={`rounded-lg p-2.5 ${selected.accent.bg} ${selected.accent.text}`}>
                <SelectedIcon className="h-6 w-6" aria-hidden />
              </span>
              <div className="min-w-0">
                <p className="font-mono text-[10px] uppercase tracking-wider text-cyber-muted">
                  {selected.category}
                </p>
                <h2 className="truncate font-mono text-lg font-bold text-cyber-text">{selected.name}</h2>
              </div>
            </div>

            <p className="font-mono text-xs italic text-cyber-muted">“{selected.tagline}”</p>
            <p className="mt-3 flex-1 text-sm leading-relaxed text-cyber-muted">{selected.description}</p>

            <dl className="mt-4 space-y-2 border-t border-cyber-border/60 pt-4 font-mono text-xs">
              <div className="flex items-center justify-between">
                <dt className="text-cyber-muted">Status</dt>
                <dd className={`flex items-center gap-1.5 ${STATUS_META[selectedStatus].text}`}>
                  <span className={`h-1.5 w-1.5 rounded-full ${STATUS_META[selectedStatus].dot}`} aria-hidden />
                  {STATUS_META[selectedStatus].label}
                </dd>
              </div>
              <div className="flex items-center justify-between">
                <dt className="text-cyber-muted">Access</dt>
                <dd className="text-cyber-text">
                  {selected.levelReq === 0 ? 'Open to all' : `Level ${selected.levelReq}+`}
                </dd>
              </div>
            </dl>

            <div className="mt-5">
              {selectedStatus === 'online' ? (
                <Link
                  href={selected.href}
                  className={`terminal-button block w-full text-center transition-all ${selected.accent.glow}`}
                >
                  Enter District →
                </Link>
              ) : selectedStatus === 'locked' ? (
                <button
                  type="button"
                  disabled
                  className="block w-full cursor-not-allowed rounded-md border border-amber-400/40 bg-amber-400/10 px-4 py-2 text-sm font-semibold text-amber-400 opacity-80"
                >
                  <Lock className="mr-1.5 inline h-3.5 w-3.5" aria-hidden />
                  Reach Level {selected.levelReq} to enter
                </button>
              ) : (
                <button
                  type="button"
                  disabled
                  className="block w-full cursor-not-allowed rounded-md border border-cyber-primary/40 bg-cyber-primary/10 px-4 py-2 text-sm font-semibold text-cyber-primary opacity-80"
                >
                  <span className="mr-1.5 inline h-1.5 w-1.5 animate-pulse rounded-full bg-cyber-primary align-middle" aria-hidden />
                  District coming online
                </button>
              )}
            </div>

            {selectedStatus === 'locked' && (
              <p className="mt-3 text-center font-mono text-[11px] text-cyber-muted">
                Earn XP in CTF, Labs or SOC missions to level up.
              </p>
            )}
          </aside>
        </div>

        <footer className="mt-10 border-t border-cyber-border/60 pt-4 text-center font-mono text-[11px] text-cyber-muted">
          “The city never sleeps. Neither does the SOC.” — CyberVerse Agency dispatch
        </footer>
      </main>
    </div>
  );
}
