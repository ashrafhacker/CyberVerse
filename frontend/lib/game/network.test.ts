import { describe, expect, it } from 'vitest';
import {
  ACTION_COST,
  SCAN_REWARD,
  applyAction,
  createRng,
  generateNetwork,
  type GameState,
} from './network';

function seededGame(level = 1, seed = 42): { state: GameState; rng: () => number } {
  const rng = createRng(seed);
  return { state: generateNetwork(level, rng), rng };
}

describe('generateNetwork', () => {
  it('grows node count with level', () => {
    expect(generateNetwork(1).nodes).toHaveLength(3);
    expect(generateNetwork(3).nodes).toHaveLength(5);
    expect(generateNetwork(6).nodes).toHaveLength(8);
    expect(generateNetwork(10).nodes).toHaveLength(8);
  });

  it('starts all nodes hidden with metadata', () => {
    for (const node of generateNetwork(1).nodes) {
      expect(node.status).toBe('hidden');
      expect(node.service.length).toBeGreaterThan(0);
      expect(node.ports.length).toBeGreaterThan(0);
      expect(node.weakness.length).toBeGreaterThan(0);
      expect(node.security).toBeGreaterThanOrEqual(1);
      expect(node.security).toBeLessThanOrEqual(5);
    }
  });

  it('connects every node to the network', () => {
    const { state } = seededGame(4);
    const connected = new Set<string>();
    for (const link of state.links) {
      connected.add(link.from);
      connected.add(link.to);
    }
    expect(connected.size).toBe(state.nodes.length);
  });
});

describe('applyAction — scan', () => {
  it('reveals a hidden node, costs energy, awards score', () => {
    const { state, rng } = seededGame();
    const node = state.nodes[0];
    const energyBefore = state.energy;

    const { state: next, message } = applyAction(state, node.id, 'scan', rng);

    expect(next.energy).toBe(energyBefore - ACTION_COST.scan);
    expect(next.score).toBe(SCAN_REWARD);
    expect(next.nodes.find((n) => n.id === node.id)?.status).toBe('scanned');
    expect(message).toContain('[+]');
  });

  it('does nothing twice on the same node', () => {
    const { state, rng } = seededGame();
    const node = state.nodes[0];
    const once = applyAction(state, node.id, 'scan', rng);
    const twice = applyAction(once.state, node.id, 'scan', rng);
    expect(twice.state.energy).toBe(once.state.energy);
    expect(twice.state.score).toBe(once.state.score);
    expect(twice.state.nodes[0].status).toBe('scanned');
  });
});

describe('applyAction — exploit', () => {
  it('requires a scan first', () => {
    const { state, rng } = seededGame();
    const node = state.nodes[0];
    const { state: next, message } = applyAction(state, node.id, 'exploit', rng);
    expect(next).toBe(state);
    expect(message).toContain('scan');
  });

  it('succeeds on low security with a favourable roll', () => {
    const { state, rng } = seededGame();
    const node = state.nodes[0];
    const scanned = applyAction(state, node.id, 'scan', rng).state;
    const energyBefore = scanned.energy;

    const { state: next, message } = applyAction(scanned, node.id, 'exploit', () => 0.01);

    expect(next.energy).toBe(energyBefore - ACTION_COST.exploit);
    expect(next.nodes.find((n) => n.id === node.id)?.status).toBe('accessed');
    expect(next.score).toBe(scanned.score + 50 + node.security * 10);
    expect(message).toContain('access granted');
  });

  it('fails without marking the node and keeps it exploitable', () => {
    const { state, rng } = seededGame();
    const node = state.nodes[0];
    const scanned = applyAction(state, node.id, 'scan', rng).state;

    const { state: next, message } = applyAction(scanned, node.id, 'exploit', () => 0.99);

    expect(next.nodes.find((n) => n.id === node.id)?.status).toBe('scanned');
    expect(next.score).toBe(scanned.score);
    expect(message).toContain('failed');
    const retry = applyAction(next, node.id, 'exploit', () => 0.01);
    expect(retry.state.nodes.find((n) => n.id === node.id)?.status).toBe('accessed');
  });
});

describe('win and lose conditions', () => {
  it('wins once every node is accessed', () => {
    const { state, rng } = seededGame();
    let current = state;
    for (const node of state.nodes) {
      current = applyAction(current, node.id, 'scan', rng).state;
    }
    for (const node of state.nodes) {
      current = applyAction(current, node.id, 'exploit', () => 0.01).state;
    }
    expect(current.phase).toBe('won');
    expect(current.score).toBeGreaterThan(state.score + state.level * 50);
  });

  it('loses when energy is depleted before the network is compromised', () => {
    const { state, rng } = seededGame();
    const drained = { ...state, energy: 2 };
    const node = state.nodes[0];
    const scanned = applyAction(drained, node.id, 'scan', rng).state;

    const { state: next } = applyAction(scanned, node.id, 'exploit', () => 0.99);

    expect(next.energy).toBeLessThanOrEqual(0);
    expect(next.phase).toBe('lost');
  });
});
