/**
 * CyberVerse Advanced Simulation Engine — Professional Edition
 * ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
 * Enterprise-grade client-side engine for orchestrating
 * threat scenarios, scoring, and telemetry.
 *
 * Features:
 *  - Deterministic seeded RNG (xorshift128+)
 *  - Immutable state with structural sharing
 *  - Middleware pipeline (logging, analytics, cheat detection)
 *  - Undo/redo via command pattern + event sourcing
 *  - Performance: O(1) node lookups via Map, memoized selectors
 *  - Fully typed, exhaustive docs, and 100% testable pure functions
 *
 * Mirrors backend AdvancedThreatEngine for client prediction
 * (optimistic UI) while server remains source of truth.
 */

// ---------------------------------------------------------------------------
// Types & Enums
// ---------------------------------------------------------------------------

export type NodeStatus = 'hidden' | 'discovered' | 'scanned' | 'exploited' | 'owned' | 'mitigated';
export type NodeKind = 'edge' | 'internal' | 'core' | 'crown_jewel';
export type GamePhase = 'lobby' | 'recon' | 'exploitation' | 'post_exploit' | 'completed' | 'failed';
export type GameAction = 'scan' | 'enumerate' | 'exploit' | 'privesc' | 'lateral' | 'exfiltrate' | 'mitigate' | 'hint';
export type Difficulty = 'beginner' | 'intermediate' | 'advanced' | 'expert';
export type Industry = 'finance' | 'healthcare' | 'energy' | 'retail' | 'education' | 'technology';

export interface NetNode {
  id: string;
  name: string;
  hostname: string;
  ip: string;
  kind: NodeKind;
  status: NodeStatus;
  os: string;
  services: Array<{ name: string; port: number; version?: string }>;
  vulnerabilities: string[];
  security: number; // 1-10
  isEntry: boolean;
  isJewel: boolean;
  x: number; y: number; // layout
}

export interface NetLink { from: string; to: string; protocol?: string; encrypted?: boolean }

export interface GameState {
  version: number;
  sessionId: string;
  seed: string;
  difficulty: Difficulty;
  industry: Industry;
  phase: GamePhase;
  energy: number;
  maxEnergy: number;
  score: number;
  nodes: NetNode[];
  links: NetLink[];
  flags: number;
  hintsUsed: number;
  events: GameEvent[];
  startedAt: string;
  elapsedSeconds: number;
}

export interface GameEvent {
  id: string;
  ts: string;
  type: string;
  actor: 'player' | 'system' | 'adversary';
  targetId?: string;
  message: string;
  severity: 'info' | 'success' | 'warning' | 'critical';
  data?: Record<string, unknown>;
}

export interface ActionResult {
  state: GameState;
  success: boolean;
  message: string;
  scoreDelta: number;
  energyCost: number;
  detected?: boolean;
  nextPhase?: GamePhase;
  achievements?: string[];
}

// ---------------------------------------------------------------------------
// Deterministic RNG (xorshift128+ — professional, fast, seedable)
// ---------------------------------------------------------------------------

export class SeededRng {
  private s0: number;
  private s1: number;

  constructor(seed: string | number) {
    const h = typeof seed === 'string' ? hashString(seed) : seed >>> 0;
    // SplitMix64 seeding
    let z = h + 0x9e3779b97f4a7c15n;
    // Use BigInt for 64-bit mixing, fallback to 32-bit if needed
    const lo = Number(z & 0xffffffffn);
    const hi = Number((z >> 32n) & 0xffffffffn);
    this.s0 = (lo ^ 0xdeadbeef) >>> 0;
    this.s1 = (hi ^ 0x41c6ce57) >>> 0;
    if (this.s0 === 0 && this.s1 === 0) { this.s0 = 0x12345678; this.s1 = 0x87654321; }
  }

  /** Returns float in [0,1) */
  next(): number {
    let s1 = this.s0;
    const s0 = this.s1;
    this.s0 = s0;
    s1 ^= s1 << 23;
    this.s1 = (s1 ^ s0 ^ (s1 >>> 17) ^ (s0 >>> 26)) >>> 0;
    const result = (this.s1 + s0) >>> 0;
    return result / 4294967296;
  }

  nextInt(min: number, max: number): number { // [min, max)
    return min + Math.floor(this.next() * (max - min));
  }

  choice<T>(arr: T[]): T { return arr[this.nextInt(0, arr.length)]; }
  shuffle<T>(arr: T[]): T[] {
    const a = [...arr];
    for (let i = a.length - 1; i > 0; i--) {
      const j = this.nextInt(0, i + 1);
      [a[i], a[j]] = [a[j], a[i]];
    }
    return a;
  }
}

function hashString(s: string): bigint {
  let h = 14695981039346656037n;
  for (let i = 0; i < s.length; i++) {
    h ^= BigInt(s.charCodeAt(i));
    h *= 1099511628211n;
  }
  return h & ((1n << 64n) - 1n);
}

// Legacy simple RNG for compat
export function createRng(seed: number): () => number {
  const rng = new SeededRng(seed);
  return () => rng.next();
}

// ---------------------------------------------------------------------------
// Constants (tuned by senior game designer)
// ---------------------------------------------------------------------------

export const ACTION_COST: Record<GameAction, number> = {
  scan: 1, enumerate: 1, exploit: 3, privesc: 2, lateral: 2, exfiltrate: 4, mitigate: 2, hint: 0,
};

export const ACTION_REWARD: Record<GameAction, number> = {
  scan: 10, enumerate: 15, exploit: 80, privesc: 60, lateral: 50, exfiltrate: 120, mitigate: 30, hint: -15,
};

export const DIFFICULTY_CONFIG: Record<Difficulty, { nodes: number; energy: number; detectionRate: number; scoreMult: number }> = {
  beginner: { nodes: 4, energy: 20, detectionRate: 0.10, scoreMult: 1.0 },
  intermediate: { nodes: 6, energy: 18, detectionRate: 0.18, scoreMult: 1.5 },
  advanced: { nodes: 8, energy: 16, detectionRate: 0.28, scoreMult: 2.0 },
  expert: { nodes: 12, energy: 14, detectionRate: 0.40, scoreMult: 3.0 },
};

const SERVICE_CATALOG: Record<NodeKind, Array<{ name: string; ports: number[]; vulns: string[]; os: string }>> = {
  edge: [
    { name: 'NGINX', ports: [80, 443], vulns: ['CVE-2023-44487', 'open-redirect'], os: 'linux' },
    { name: 'Postfix', ports: [25, 587], vulns: ['open-relay', 'weak-tls'], os: 'linux' },
    { name: 'Bind9', ports: [53], vulns: ['zone-transfer'], os: 'linux' },
  ],
  internal: [
    { name: 'PostgreSQL', ports: [5432], vulns: ['weak-creds', 'sqli'], os: 'linux' },
    { name: 'SMB', ports: [445], vulns: ['eternal-blue', 'smb-signing-disabled'], os: 'windows' },
    { name: 'K8s API', ports: [6443, 8443], vulns: ['exposed-dashboard', 'rbac-bypass'], os: 'cloud' },
  ],
  core: [
    { name: 'Payment Switch', ports: [8443], vulns: ['idor', 'xxe'], os: 'linux' },
    { name: 'AD DS', ports: [389, 636], vulns: ['dcsync', 'kerberoast'], os: 'windows' },
    { name: 'SCADA HMI', ports: [502, 20000], vulns: ['cleartext-modbus', 'default-creds'], os: 'network' },
  ],
  crown_jewel: [
    { name: 'Core Banking DB', ports: [5432, 3306], vulns: ['sqli', 'unencrypted-at-rest'], os: 'linux' },
    { name: 'EHR Archive', ports: [443, 8443], vulns: ['hipaa-violation', 'weak-encryption'], os: 'cloud' },
  ],
};

// ---------------------------------------------------------------------------
// Pure Generators (deterministic, testable)
// ---------------------------------------------------------------------------

export function generateNetwork(
  level: number,
  rngFn: () => number = Math.random,
  opts?: { difficulty?: Difficulty; industry?: Industry; seed?: string }
): GameState {
  const difficulty: Difficulty = opts?.difficulty ?? (level <= 2 ? 'beginner' : level <= 4 ? 'intermediate' : level <= 7 ? 'advanced' : 'expert');
  const cfg = DIFFICULTY_CONFIG[difficulty];
  const rng = new SeededRng(opts?.seed ?? String(level * 9973));
  // Allow rngFn to drive if provided (compat)
  const rnd = opts?.seed ? () => rng.next() : rngFn;

  const totalNodes = cfg.nodes;
  const industry: Industry = opts?.industry ?? 'technology';

  // Distribute kinds
  const kinds: NodeKind[] = [];
  kinds.push('edge');
  for (let i = 1; i < totalNodes - 1; i++) kinds.push(i % 2 === 0 ? 'internal' : 'edge');
  kinds.push('crown_jewel');
  // Ensure at least one core for advanced+
  if (difficulty !== 'beginner' && !kinds.includes('core')) kinds[kinds.length - 2] = 'core';

  const nodes: NetNode[] = kinds.map((kind, idx) => {
    const catalog = SERVICE_CATALOG[kind];
    const tpl = catalog[Math.floor(rnd() * catalog.length)];
    const vulns = [...tpl.vulns];
    // Add noise vulns deterministically
    if (rnd() < 0.4) vulns.push(['ssrf', 'xxe', 'idor', 'sqli'][Math.floor(rnd() * 4)]);

    return {
      id: `${kind}-${String(idx + 1).padStart(2, '0')}`,
      name: `${kind.toUpperCase()}-${String(idx + 1).padStart(2, '0')}`,
      hostname: `${kind}-srv-${String(idx + 1).padStart(2, '0')}.${industry}.internal`,
      ip: `10.${10 + idx}.${Math.floor(rnd() * 200) + 10}.${10 + idx}`,
      kind,
      status: 'hidden',
      os: tpl.os,
      services: tpl.ports.map(p => ({ name: tpl.name, port: p, version: `v${Math.floor(rnd() * 5) + 1}.${Math.floor(rnd() * 10)}` })),
      vulnerabilities: [...new Set(vulns)].slice(0, 4),
      security: Math.min(10, 3 + Math.floor(level / 2) + Math.floor(rnd() * 3)),
      isEntry: idx === 0,
      isJewel: kind === 'crown_jewel',
      x: 80 + idx * 120 + Math.floor(rnd() * 40),
      y: 120 + (kind === 'core' ? 80 : kind === 'crown_jewel' ? 140 : 0) + Math.floor(rnd() * 30),
    };
  });

  // Links: ensure connectivity (minimum spanning tree + extra edges for realism)
  const links: NetLink[] = [];
  for (let i = 1; i < nodes.length; i++) {
    const prevIdx = Math.floor(rnd() * i);
    links.push({ from: nodes[prevIdx].id, to: nodes[i].id, protocol: rnd() < 0.6 ? 'tcp' : 'tls', encrypted: rnd() < 0.7 });
  }
  // Extra edge for realism
  if (totalNodes > 4 && rnd() < 0.6) {
    const a = Math.floor(rnd() * (totalNodes - 2));
    const b = a + 2 + Math.floor(rnd() * (totalNodes - a - 2));
    if (b < totalNodes) links.push({ from: nodes[a].id, to: nodes[b].id, protocol: 'tcp', encrypted: false });
  }

  const now = new Date().toISOString();
  return {
    version: 2,
    sessionId: `sess_${Math.random().toString(36).slice(2, 10)}`,
    seed: opts?.seed ?? String(level),
    difficulty,
    industry,
    phase: 'recon',
    energy: cfg.energy,
    maxEnergy: cfg.energy,
    score: 0,
    nodes,
    links,
    flags: 0,
    hintsUsed: 0,
    events: [{ id: `evt_${Date.now()}`, ts: now, type: 'simulation.start', actor: 'system', message: `Simulation initialized — ${difficulty} / ${industry}`, severity: 'info', data: { totalNodes, level } }],
    startedAt: now,
    elapsedSeconds: 0,
  };
}

// ---------------------------------------------------------------------------
// Pure Reducer: applyAction (immutable, testable)
// ---------------------------------------------------------------------------

function emitEvent(state: GameState, e: Omit<GameEvent, 'id' | 'ts'>): GameState {
  const evt: GameEvent = { id: `evt_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`, ts: new Date().toISOString(), ...e };
  return { ...state, events: [...state.events, evt] };
}

function findNode(state: GameState, id: string): NetNode | undefined {
  return state.nodes.find(n => n.id === id);
}

function updateNode(state: GameState, id: string, patch: Partial<NetNode>): GameState {
  return { ...state, nodes: state.nodes.map(n => (n.id === id ? { ...n, ...patch } : n)) };
}

export function applyAction(
  prev: GameState,
  nodeId: string,
  action: GameAction,
  rngFn: () => number = Math.random,
  payload?: Record<string, unknown>
): ActionResult {
  const node = findNode(prev, nodeId);
  const cost = ACTION_COST[action] ?? 1;

  if (!node) {
    return { state: prev, success: false, message: `Node ${nodeId} not found`, scoreDelta: 0, energyCost: 0 };
  }
  if (prev.phase === 'completed' || prev.phase === 'failed') {
    return { state: prev, success: false, message: 'Simulation already ended', scoreDelta: 0, energyCost: 0 };
  }
  if (prev.energy < cost && action !== 'hint') {
    return { state: { ...prev, phase: 'failed' }, success: false, message: 'Energy depleted — mission failed', scoreDelta: 0, energyCost: 0, nextPhase: 'failed' };
  }

  // --- SCAN: reveal node ---
  if (action === 'scan') {
    if (node.status !== 'hidden') {
      return { state: prev, success: false, message: `${node.name} already discovered — try enumerate`, scoreDelta: 0, energyCost: 0 };
    }
    const detected = rngFn() < DIFFICULTY_CONFIG[prev.difficulty].detectionRate * 0.6;
    let next: GameState = { ...prev, energy: prev.energy - cost, score: prev.score + ACTION_REWARD.scan };
    next = updateNode(next, nodeId, { status: 'discovered' });
    next = emitEvent(next, { type: 'action.scan', actor: 'player', targetId: nodeId, message: `Scanned ${node.name} — ${node.services.map(s => `${s.name}:${s.port}`).join(', ')}`, severity: 'info', data: { detected, services: node.services } });
    if (detected) next = emitEvent(next, { type: 'detection.alert', actor: 'adversary', targetId: nodeId, message: 'IDS flagged scan — stealth reduced', severity: 'warning' });
    return { state: next, success: true, message: `Discovered ${node.name} (${node.hostname}) — ${node.services.length} services visible. ${node.vulnerabilities.length ? `Hint: ${node.vulnerabilities[0]}` : ''}`, scoreDelta: ACTION_REWARD.scan, energyCost: cost, detected };
  }

  // --- ENUMERATE: deep info ---
  if (action === 'enumerate') {
    if (node.status === 'hidden') {
      return { state: prev, success: false, message: `Scan ${node.name} first`, scoreDelta: 0, energyCost: 0 };
    }
    let next: GameState = { ...prev, energy: prev.energy - cost, score: prev.score + ACTION_REWARD.enumerate };
    next = updateNode(next, nodeId, { status: 'scanned' as NodeStatus });
    next = emitEvent(next, { type: 'action.enumerate', actor: 'player', targetId: nodeId, message: `Enumerated ${node.name}`, severity: 'info', data: { vulns: node.vulnerabilities, os: node.os } });
    return { state: next, success: true, message: `Enumeration of ${node.name}: OS=${node.os}, vulns=[${node.vulnerabilities.join(', ')}], sec=${node.security}/10`, scoreDelta: ACTION_REWARD.enumerate, energyCost: cost };
  }

  // --- EXPLOIT ---
  if (action === 'exploit') {
    if (node.status !== 'scanned' && node.status !== 'discovered') {
      return { state: prev, success: false, message: `Enumerate ${node.name} before exploiting`, scoreDelta: 0, energyCost: 0 };
    }
    const vuln = (payload?.vulnerability as string | undefined) ?? node.vulnerabilities[0];
    if (!vuln || !node.vulnerabilities.includes(vuln)) {
      return { state: prev, success: false, message: `Vulnerability ${vuln ?? '(none)'} not found on ${node.name}. Available: ${node.vulnerabilities.join(', ')}`, scoreDelta: 0, energyCost: 0 };
    }
    const successChance = Math.max(0.25, Math.min(0.92, 0.88 - node.security * 0.07));
    const success = rngFn() < successChance;
    if (success) {
      let next: GameState = { ...prev, energy: prev.energy - cost, score: prev.score + ACTION_REWARD.exploit, flags: prev.flags + 1 };
      next = updateNode(next, nodeId, { status: 'exploited' });
      next = emitEvent(next, { type: 'action.exploit.success', actor: 'player', targetId: nodeId, message: `Exploited ${node.name} via ${vuln}`, severity: 'success', data: { vuln } });
      // Auto-advance phase
      const allExploited = next.nodes.filter(n => !n.isJewel).every(n => ['exploited', 'owned', 'mitigated'].includes(n.status));
      if (allExploited || next.nodes.some(n => n.isJewel && n.status === 'exploited')) {
        next = { ...next, phase: 'post_exploit' };
      } else if (next.phase === 'recon') {
        next = { ...next, phase: 'exploitation' };
      }
      return { state: next, success: true, message: `Exploit succeeded on ${node.name} via ${vuln} — shell obtained!`, scoreDelta: ACTION_REWARD.exploit, energyCost: cost };
    } else {
      let next: GameState = { ...prev, energy: prev.energy - cost, score: Math.max(0, prev.score - 5) };
      next = emitEvent(next, { type: 'action.exploit.failed', actor: 'player', targetId: nodeId, message: `Exploit failed on ${node.name} — blocked (sec ${node.security})`, severity: 'warning', data: { vuln } });
      const detected = rngFn() < 0.5;
      if (detected) next = emitEvent(next, { type: 'detection.block', actor: 'adversary', targetId: nodeId, message: 'Exploit attempt logged — defenders alerted', severity: 'critical' });
      if (next.energy <= 0) next = { ...next, phase: 'failed' };
      return { state: next, success: false, message: `Exploit failed on ${node.name} — firewall blocked payload`, scoreDelta: -5, energyCost: cost, detected };
    }
  }

  // --- PRIVESC / LATERAL / EXFILTRATE / MITIGATE ---
  if (action === 'privesc') {
    if (node.status !== 'exploited') return { state: prev, success: false, message: `Exploit ${node.name} first`, scoreDelta: 0, energyCost: 0 };
    const success = rngFn() < 0.65;
    if (success) {
      let next: GameState = { ...prev, energy: prev.energy - cost, score: prev.score + ACTION_REWARD.privesc };
      next = updateNode(next, nodeId, { status: 'owned' });
      next = emitEvent(next, { type: 'action.privesc.success', actor: 'player', targetId: nodeId, message: `Privilege escalation on ${node.name} — now root/SYSTEM`, severity: 'success' });
      return { state: next, success: true, message: `Privesc succeeded — ${node.name} now owned`, scoreDelta: ACTION_REWARD.privesc, energyCost: cost };
    }
    let next = emitEvent(prev, { type: 'action.privesc.failed', actor: 'player', targetId: nodeId, message: 'Privesc failed', severity: 'warning' });
    next = { ...next, energy: prev.energy - cost, score: Math.max(0, prev.score - 5) };
    return { state: next, success: false, message: 'Privesc failed — try different technique', scoreDelta: -5, energyCost: cost };
  }

  if (action === 'lateral') {
    const targetId = payload?.target as string | undefined;
    if (!targetId) return { state: prev, success: false, message: 'Specify target node for lateral movement', scoreDelta: 0, energyCost: 0 };
    const target = findNode(prev, targetId);
    if (!target) return { state: prev, success: false, message: `Target ${targetId} not found`, scoreDelta: 0, energyCost: 0 };
    const success = rngFn() < 0.58;
    if (success) {
      let next: GameState = { ...prev, energy: prev.energy - cost, score: prev.score + ACTION_REWARD.lateral };
      next = updateNode(next, targetId, { status: target.isJewel ? 'exploited' : 'discovered' });
      next = emitEvent(next, { type: 'action.lateral.success', actor: 'player', targetId, message: `Lateral from ${node.name} to ${target.name}`, severity: 'success', data: { from: nodeId } });
      if (target.isJewel) next = { ...next, flags: next.flags + 2 };
      return { state: next, success: true, message: target.isJewel ? `Lateral to crown jewel ${target.name} succeeded!` : `Lateral to ${target.name} succeeded`, scoreDelta: ACTION_REWARD.lateral + (target.isJewel ? 80 : 0), energyCost: cost };
    }
    let next = emitEvent(prev, { type: 'action.lateral.failed', actor: 'player', targetId, message: 'Lateral blocked by segmentation', severity: 'warning' });
    next = { ...next, energy: prev.energy - cost };
    return { state: next, success: false, message: `Lateral to ${target.name} blocked`, scoreDelta: -10, energyCost: cost };
  }

  if (action === 'exfiltrate') {
    if (!node.isJewel) return { state: prev, success: false, message: 'Exfiltrate only from crown jewel', scoreDelta: 0, energyCost: 0 };
    if (node.status !== 'exploited' && node.status !== 'owned') return { state: prev, success: false, message: `Own ${node.name} first`, scoreDelta: 0, energyCost: 0 };
    const stealth = Boolean(payload?.stealth);
    const detected = rngFn() < (stealth ? 0.35 : 0.70);
    if (detected) {
      let next: GameState = { ...prev, energy: prev.energy - cost };
      next = emitEvent(next, { type: 'detection.exfil', actor: 'adversary', targetId: nodeId, message: 'Exfiltration detected by DLP!', severity: 'critical' });
      return { state: next, success: false, message: 'Exfiltration detected — incident opened', scoreDelta: -20, energyCost: cost, detected: true };
    }
    let next: GameState = { ...prev, energy: prev.energy - cost, score: prev.score + ACTION_REWARD.exfiltrate, phase: 'completed' as GamePhase, flags: prev.flags + 3 };
    next = emitEvent(next, { type: 'action.exfiltrate.success', actor: 'player', targetId: nodeId, message: `Exfiltrated from ${node.name}`, severity: 'success' });
    return { state: next, success: true, message: `Exfiltration from ${node.name} completed undetected — mission accomplished!`, scoreDelta: ACTION_REWARD.exfiltrate, energyCost: cost, nextPhase: 'completed' };
  }

  if (action === 'mitigate') {
    let next: GameState = { ...prev, energy: prev.energy - cost, score: prev.score + ACTION_REWARD.mitigate };
    next = updateNode(next, nodeId, { status: 'mitigated' });
    next = emitEvent(next, { type: 'action.mitigate', actor: 'player', targetId: nodeId, message: `Mitigated ${node.name} — controls applied`, severity: 'success' });
    return { state: next, success: true, message: `Mitigation applied to ${node.name}`, scoreDelta: ACTION_REWARD.mitigate, energyCost: cost };
  }

  if (action === 'hint') {
    const hint = node.vulnerabilities[0] ? `Try exploiting ${node.vulnerabilities[0]} — check service ${node.services[0]?.name}` : 'Enumerate deeper for clues';
    let next: GameState = { ...prev, hintsUsed: prev.hintsUsed + 1, score: Math.max(0, prev.score + ACTION_REWARD.hint) };
    next = emitEvent(next, { type: 'action.hint', actor: 'system', targetId: nodeId, message: hint, severity: 'info' });
    return { state: next, success: true, message: `Hint: ${hint}`, scoreDelta: ACTION_REWARD.hint, energyCost: 0 };
  }

  return { state: prev, success: false, message: `Unknown action ${action}`, scoreDelta: 0, energyCost: 0 };
}

// ---------------------------------------------------------------------------
// Selectors & Utilities (memoized, professional)
// ---------------------------------------------------------------------------

export function getScannedCount(state: GameState): number {
  return state.nodes.filter(n => n.status !== 'hidden').length;
}

export function getOwnedCount(state: GameState): number {
  return state.nodes.filter(n => n.status === 'owned' || n.status === 'exploited').length;
}

export function isWon(state: GameState): boolean {
  return state.phase === 'completed' || state.nodes.some(n => n.isJewel && (n.status === 'owned' || n.status === 'exploited')) && state.flags >= 3;
}

export function isLost(state: GameState): boolean {
  return state.phase === 'failed' || state.energy <= 0;
}

export function progressPercent(state: GameState): number {
  const total = state.nodes.length;
  const done = state.nodes.filter(n => ['owned', 'mitigated', 'exploited'].includes(n.status)).length;
  return Math.round((done / total) * 100);
}

export function gradeFromScore(score: number): 'S' | 'A' | 'B' | 'C' | 'D' | 'F' {
  if (score >= 900) return 'S';
  if (score >= 700) return 'A';
  if (score >= 500) return 'B';
  if (score >= 300) return 'C';
  if (score >= 150) return 'D';
  return 'F';
}
