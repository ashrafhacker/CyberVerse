export type NodeStatus = 'hidden' | 'scanned' | 'accessed';
export type NodeKind = 'edge' | 'internal' | 'core';
export type GamePhase = 'playing' | 'won' | 'lost';
export type GameAction = 'scan' | 'exploit';

export interface NetNode {
  id: string;
  name: string;
  service: string;
  ports: number[];
  weakness: string;
  security: number;
  kind: NodeKind;
  status: NodeStatus;
}

export interface NetLink {
  from: string;
  to: string;
}

export interface GameState {
  level: number;
  energy: number;
  score: number;
  nodes: NetNode[];
  links: NetLink[];
  phase: GamePhase;
}

export interface ActionResult {
  state: GameState;
  message: string;
}

export const ACTION_COST: Record<GameAction, number> = { scan: 1, exploit: 2 };
export const SCAN_REWARD = 10;

export const SERVICES: Record<NodeKind, { service: string; ports: number[]; weakness: string }[]> = {
  edge: [
    { service: 'HTTP Web Server', ports: [80, 443, 8080], weakness: 'outdated Apache Struts (CVE-2017-5638)' },
    { service: 'DNS Resolver', ports: [53, 5353], weakness: 'open recursive resolution' },
    { service: 'Mail Relay', ports: [25, 587, 993], weakness: 'weak TLS 1.0 cipher suite' },
    { service: 'FTP Server', ports: [21], weakness: 'anonymous login enabled' },
  ],
  internal: [
    { service: 'Database', ports: [3306, 5432, 1433], weakness: 'default credentials on admin account' },
    { service: 'API Gateway', ports: [8000, 8443], weakness: 'broken object-level authorization' },
    { service: 'File Share', ports: [445, 139], weakness: 'unpatched SMBv1 (EternalBlue)' },
  ],
  core: [
    { service: 'Admin Panel', ports: [8443, 3000], weakness: 'session cookie without HttpOnly flag' },
    { service: 'Payment Gateway', ports: [443, 8443], weakness: 'SQL injection in refund endpoint' },
    { service: 'Backup Vault', ports: [22, 873], weakness: 'rsync with no access list' },
  ],
};

export function createRng(seed: number): () => number {
  let a = seed >>> 0;
  return () => {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function pick<T>(items: T[], rng: () => number): T {
  return items[Math.floor(rng() * items.length)];
}

function exploitChance(node: NetNode, level: number): number {
  const base = 0.95 - node.security * 0.12 + Math.min(level - 1, 3) * 0.05;
  return Math.min(0.95, Math.max(0.25, base));
}

export function generateNetwork(level: number, rng: () => number = Math.random): GameState {
  const totalNodes = Math.min(2 + level, 8);
  const kinds: NodeKind[] = ['edge', 'internal', 'core'];
  const cap: Record<NodeKind, number> = { edge: 4, internal: 3, core: 2 };
  const counts: Record<NodeKind, number> = { edge: 0, internal: 0, core: 0 };

  let remaining = totalNodes;
  let cursor = 0;
  while (remaining > 0) {
    const kind = kinds[cursor % kinds.length];
    if (counts[kind] < cap[kind]) {
      counts[kind]++;
      remaining--;
    }
    cursor++;
  }

  const nodes: NetNode[] = [];
  for (const kind of kinds) {
    for (let n = 1; n <= counts[kind]; n++) {
      const template = pick(SERVICES[kind], rng);
      nodes.push({
        id: `${kind}-${n}`,
        name: `${kind}-${String(n).padStart(2, '0')}`,
        service: template.service,
        ports: template.ports,
        weakness: template.weakness,
        security: Math.min(5, 1 + Math.floor(level / 2) + Math.floor(rng() * 2)),
        kind,
        status: 'hidden',
      });
    }
  }

  const layerIndex: Record<NodeKind, number> = { edge: 0, internal: 1, core: 2 };
  const links: NetLink[] = [];
  for (let i = 1; i < nodes.length; i++) {
    const node = nodes[i];
    const prev = nodes
      .slice(0, i)
      .filter((n) => layerIndex[n.kind] < layerIndex[node.kind]);
    const source = prev.length > 0 ? pick(prev, rng) : nodes[0];
    if (source.id !== node.id && !links.some((l) => l.from === source.id && l.to === node.id)) {
      links.push({ from: source.id, to: node.id });
    }
  }
  const firstCore = nodes.find((n) => n.kind === 'core');
  const internal = nodes.filter((n) => n.kind === 'internal');
  if (firstCore && internal.length > 0 && !links.some((l) => l.to === firstCore.id)) {
    const source = pick(internal, rng);
    links.push({ from: source.id, to: firstCore.id });
  }

  return {
    level,
    energy: 8 + level * 2,
    score: 0,
    nodes,
    links,
    phase: 'playing',
  };
}

export function applyAction(
  prev: GameState,
  nodeId: string,
  action: GameAction,
  rng: () => number = Math.random,
): ActionResult {
  const node = prev.nodes.find((n) => n.id === nodeId);
  if (!node || prev.phase !== 'playing' || prev.energy <= 0) {
    return { state: prev, message: '' };
  }
  const cost = ACTION_COST[action];

  if (action === 'scan') {
    if (node.status === 'accessed') {
      return { state: prev, message: `[i] ${node.name} already accessed — no more data to collect` };
    }
    if (node.status === 'scanned') {
      return { state: prev, message: `[i] ${node.name} already scanned — try exploiting it` };
    }
    const state: GameState = {
      ...prev,
      energy: prev.energy - cost,
      score: prev.score + SCAN_REWARD,
      nodes: prev.nodes.map((n) => (n.id === nodeId ? { ...n, status: 'scanned' as NodeStatus } : n)),
      phase: 'playing',
    };
    return {
      state,
      message: `[+] scan ${node.name}: ${node.service} open on ${node.ports.join(', ')} — ${node.weakness}`,
    };
  }

  if (node.status !== 'scanned') {
    return { state: prev, message: `[i] scan ${node.name} first before exploiting` };
  }

  const success = rng() < exploitChance(node, prev.level);
  const state: GameState = {
    ...prev,
    energy: prev.energy - cost,
    score: prev.score + (success ? 50 + node.security * 10 : 0),
    nodes: prev.nodes.map((n) =>
      n.id === nodeId ? { ...n, status: success ? ('accessed' as NodeStatus) : n.status } : n,
    ),
    phase: 'playing',
  };

  if (success && state.nodes.every((n) => n.status === 'accessed')) {
    const bonus = prev.level * 50;
    return {
      state: { ...state, score: state.score + bonus, phase: 'won' },
      message: `[!] access granted to ${node.name} — network compromised (+${bonus} bonus)`,
    };
  }
  if (success) {
    return {
      state,
      message: `[!] access granted to ${node.name} — ${node.weakness} exploited`,
    };
  }
  if (state.energy <= 0) {
    return { state: { ...state, phase: 'lost' }, message: `[x] exploit failed on ${node.name} — energy depleted` };
  }
  return { state, message: `[x] exploit failed on ${node.name} — firewall blocked the payload` };
}
