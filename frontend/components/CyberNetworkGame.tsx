'use client';

import { useEffect, useRef, useState } from 'react';
import {
  ACTION_COST,
  applyAction,
  createRng,
  generateNetwork,
  type GameAction,
  type GameState,
  type NetNode,
} from '@/lib/game/network';

const LEVEL_TIME = 90;
const MAX_LEVEL = 8;
const HS_KEY = 'cyberverse:hs';

const LAYER_X: Record<NetNode['kind'], number> = { edge: 90, internal: 300, core: 510 };
const STATUS_COLOR = {
  hidden: '#164e63',
  scanned: '#b45309',
  accessed: '#15803d',
} as const;
const STATUS_TEXT = { hidden: '#67e8f9', scanned: '#fbbf24', accessed: '#6ee7b7' } as const;

interface LogLine {
  id: number;
  text: string;
}

function newGame(level: number, seed = 1): GameState {
  return generateNetwork(level, createRng(seed));
}

function layoutNodes(nodes: NetNode[]) {
  const columns = new Map<NetNode['kind'], NetNode[]>();
  for (const node of nodes) {
    columns.set(node.kind, [...(columns.get(node.kind) ?? []), node]);
  }
  return Array.from(columns.entries()).flatMap(([kind, col]) =>
    col.map((node, i) => ({
      node,
      x: LAYER_X[kind],
      y: 60 + ((col.length === 1 ? 0.5 : (i + 1) / (col.length + 1)) * 360),
    })),
  );
}

export default function CyberNetworkGame() {
  const [game, setGame] = useState<GameState>(() => newGame(1));
  const [log, setLog] = useState<LogLine[]>([
    { id: 0, text: 'authorized assessment of fictional sandbox network' },
    { id: 1, text: 'scan nodes to reveal services · exploit weaknesses · access everything' },
  ]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [timeLeft, setTimeLeft] = useState(LEVEL_TIME);
  const [best, setBest] = useState<Record<number, number>>({});
  const logRef = useRef<HTMLDivElement>(null);
  const nextId = useRef(2);

  const energyMax = 8 + game.level * 2;
  const selected = game.nodes.find((n) => n.id === selectedId) ?? null;
  const remaining = game.nodes.filter((n) => n.status !== 'accessed').length;

  useEffect(() => {
    setBest(JSON.parse(localStorage.getItem(HS_KEY) ?? '{}'));
  }, []);

  useEffect(() => {
    if (game.phase !== 'playing') return;
    const timer = setInterval(() => setTimeLeft((t) => t - 1), 1000);
    return () => clearInterval(timer);
  }, [game.phase]);

  useEffect(() => {
    if (timeLeft > 0 || game.phase !== 'playing') return;
    pushLog('[x] time expired — session terminated');
    setGame((g) => ({ ...g, phase: 'lost' }));
  }, [timeLeft, game.phase]);

  useEffect(() => {
    if (game.phase !== 'won') return;
    setBest((prev) => {
      const next = { ...prev, [game.level]: Math.max(prev[game.level] ?? 0, game.score) };
      localStorage.setItem(HS_KEY, JSON.stringify(next));
      return next;
    });
  }, [game.phase, game.level, game.score]);

  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight;
  }, [log]);

  function pushLog(text: string) {
    setLog((prev) => [...prev.slice(-60), { id: nextId.current++, text }]);
  }

  function startLevel(level: number) {
    setGame(newGame(level));
    setSelectedId(null);
    setTimeLeft(LEVEL_TIME);
    setLog([
      { id: nextId.current++, text: `--- level ${level}: ${'=@'.repeat(level)} ---` },
      { id: nextId.current++, text: `engage ${game.nodes.length} hosts · ${energyMax} energy · ${LEVEL_TIME}s` },
    ]);
  }

  function act(action: GameAction) {
    if (!selected || game.phase !== 'playing') return;
    const { state, message } = applyAction(game, selected.id, action);
    if (!message) return;
    setGame(state);
    pushLog(message);
    if (state.phase === 'won') pushLog('[!] network compromised — operation complete');
  }

  const placed = layoutNodes(game.nodes);

  return (
    <div className="terminal-card flex flex-col gap-4 p-5">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-cyber-border pb-3">
        <div className="flex items-center gap-3">
          <span className="font-mono text-sm text-cyber-secondary">LEVEL {game.level}</span>
          <span className="rounded border border-cyber-border px-2 py-0.5 font-mono text-xs text-cyber-muted">
            {remaining} hosts remaining
          </span>
        </div>
        <div className="flex items-center gap-4 font-mono text-sm">
          <span className="text-cyber-primary">score {game.score}</span>
          <span className={timeLeft <= 10 ? 'text-red-400' : 'text-cyber-muted'}>time {Math.max(timeLeft, 0)}s</span>
          <span className="text-cyber-muted">best {best[game.level] ?? 0}</span>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-[1fr_300px]">
        <div className="relative rounded border border-cyber-border bg-cyber-bg/60 p-2">
          <svg viewBox="0 0 600 460" className="w-full">
            <defs>
              <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto">
                <path d="M0,0 L10,5 L0,10 z" fill="#334155" />
              </marker>
            </defs>
            {game.links.map((link) => {
              const from = placed.find((p) => p.node.id === link.from);
              const to = placed.find((p) => p.node.id === link.to);
              if (!from || !to) return null;
              return (
                <line
                  key={`${link.from}-${link.to}`}
                  x1={from.x + 34}
                  y1={from.y}
                  x2={to.x - 34}
                  y2={to.y}
                  stroke="#334155"
                  strokeWidth={1.5}
                  markerEnd="url(#arrow)"
                />
              );
            })}
            {placed.map(({ node, x, y }) => (
              <g
                key={node.id}
                transform={`translate(${x},${y})`}
                className="cursor-pointer"
                onClick={() => setSelectedId(node.id)}
              >
                <circle r={30} fill="#0b1120" stroke={STATUS_COLOR[node.status]} strokeWidth={2} />
                {node.status === 'accessed' && <circle r={22} fill="none" stroke="#22c55e" strokeWidth={1} opacity={0.5} />}
                <text y={-38} textAnchor="middle" fill={STATUS_TEXT[node.status]} fontSize={13} fontFamily="monospace">
                  {node.name}
                </text>
                <text y={46} textAnchor="middle" fill="#64748b" fontSize={10} fontFamily="monospace">
                  {node.status === 'hidden' ? '???' : node.service}
                </text>
                {selectedId === node.id && (
                  <circle r={34} fill="none" stroke="#00e5ff" strokeWidth={1} strokeDasharray="4 3" />
                )}
              </g>
            ))}
          </svg>
        </div>

        <div className="flex flex-col gap-3">
          <div className="rounded border border-cyber-border p-3">
            <p className="mb-1 font-mono text-xs text-cyber-muted">ENERGY</p>
            <div className="h-2 overflow-hidden rounded bg-cyber-bg">
              <div
                className={`h-full transition-all ${game.energy / energyMax > 0.35 ? 'bg-cyber-primary' : 'bg-red-500'}`}
                style={{ width: `${(game.energy / energyMax) * 100}%` }}
              />
            </div>
            <p className="mt-1 font-mono text-xs text-cyber-muted">
              {game.energy} / {energyMax}
            </p>
          </div>

          <div className="min-h-[150px] rounded border border-cyber-border p-3">
            {selected ? (
              <>
                <p className="font-mono text-sm text-cyber-primary">{selected.name}</p>
                <p className="mt-1 font-mono text-xs text-cyber-muted">
                  {selected.status === 'hidden' ? 'service unknown' : selected.service}
                </p>
                {selected.status !== 'hidden' && (
                  <>
                    <p className="mt-1 font-mono text-xs text-cyber-secondary">ports: {selected.ports.join(', ')}</p>
                    <p className="mt-1 font-mono text-xs text-cyber-muted">weakness: {selected.weakness}</p>
                  </>
                )}
                <p className="mt-1 font-mono text-xs text-cyber-muted">
                  security: {selected.status === 'hidden' ? '???' : '●'.repeat(selected.security) + '○'.repeat(5 - selected.security)}
                </p>
                <div className="mt-3 flex gap-2">
                  <button
                    className="terminal-button-ghost px-3 py-1 text-xs"
                    onClick={() => act('scan')}
                    disabled={game.phase !== 'playing' || selected.status === 'accessed' || game.energy < ACTION_COST.scan}
                  >
                    scan · -{ACTION_COST.scan}
                  </button>
                  <button
                    className="terminal-button px-3 py-1 text-xs"
                    onClick={() => act('exploit')}
                    disabled={
                      game.phase !== 'playing' ||
                      selected.status !== 'scanned' ||
                      game.energy < ACTION_COST.exploit
                    }
                  >
                    exploit · -{ACTION_COST.exploit}
                  </button>
                </div>
              </>
            ) : (
              <p className="font-mono text-xs text-cyber-muted">&gt; select a node on the map to begin</p>
            )}
          </div>

          <div ref={logRef} className="h-40 overflow-y-auto rounded border border-cyber-border bg-cyber-bg/60 p-2 font-mono text-xs">
            {log.map((line) => (
              <p
                key={line.id}
                className={line.text.startsWith('[+]') ? 'text-cyber-secondary' : line.text.startsWith('[!]') ? 'text-green-400' : line.text.startsWith('[x]') ? 'text-red-400' : 'text-cyber-muted'}
              >
                {line.text}
              </p>
            ))}
          </div>
        </div>
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3 border-t border-cyber-border pt-3">
        <div className="flex gap-2">
          {Array.from({ length: MAX_LEVEL }, (_, i) => i + 1).map((level) => (
            <button
              key={level}
              className={`rounded border px-2.5 py-1 font-mono text-xs transition-colors ${
                game.level === level
                  ? 'border-cyber-primary text-cyber-primary'
                  : 'border-cyber-border text-cyber-muted hover:border-cyber-primary'
              }`}
              onClick={() => startLevel(level)}
            >
              {level}
            </button>
          ))}
        </div>
        {game.phase === 'won' && (
          <div className="flex items-center gap-3">
            <span className="font-mono text-sm text-green-400">network compromised +{game.level * 50}</span>
            <button
              className="terminal-button px-4 py-1.5 text-sm"
              onClick={() => startLevel(Math.min(game.level + 1, MAX_LEVEL))}
            >
              next level →
            </button>
          </div>
        )}
        {game.phase === 'lost' && (
          <div className="flex items-center gap-3">
            <span className="font-mono text-sm text-red-400">session terminated — try again</span>
            <button className="terminal-button px-4 py-1.5 text-sm" onClick={() => startLevel(game.level)}>
              retry
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
