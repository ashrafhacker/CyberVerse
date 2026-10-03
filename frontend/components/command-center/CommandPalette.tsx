'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { CornerDownLeft, Search } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { SearchTarget } from './CommandTopbar';

const MAX_RESULTS = 12;

function score(target: SearchTarget, query: string): number {
  const q = query.toLowerCase();
  const label = target.label.toLowerCase();
  const group = target.group.toLowerCase();
  const hint = (target.hint ?? '').toLowerCase();

  if (label === q) return 100;
  if (label.startsWith(q)) return 80;
  if (label.includes(q)) return 60;
  if (group.includes(q)) return 30;
  if (hint.includes(q)) return 20;
  return 0;
}

export default function CommandPalette({
  open,
  onClose,
  targets,
}: {
  open: boolean;
  onClose: () => void;
  targets: SearchTarget[];
}) {
  const router = useRouter();
  const [query, setQuery] = useState('');
  const [cursor, setCursor] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  const results = useMemo(() => {
    const q = query.trim();
    if (!q) return targets.slice(0, MAX_RESULTS);
    return targets
      .map((t) => ({ t, s: score(t, q) }))
      .filter((r) => r.s > 0)
      .sort((a, b) => b.s - a.s)
      .slice(0, MAX_RESULTS)
      .map((r) => r.t);
  }, [query, targets]);

  useEffect(() => {
    if (open) {
      setQuery('');
      setCursor(0);
      const id = setTimeout(() => inputRef.current?.focus(), 20);
      return () => clearTimeout(id);
    }
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        onClose();
      } else if (e.key === 'ArrowDown') {
        e.preventDefault();
        setCursor((c) => (results.length === 0 ? 0 : (c + 1) % results.length));
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        setCursor((c) => (results.length === 0 ? 0 : (c - 1 + results.length) % results.length));
      } else if (e.key === 'Enter') {
        e.preventDefault();
        const picked = results[cursor];
        if (picked) {
          router.push(picked.href);
          onClose();
        }
      }
    };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [open, results, cursor, router, onClose]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-[60] flex items-start justify-center p-4 pt-24" role="dialog" aria-modal="true" aria-label="Command palette">
      <div className="absolute inset-0 bg-black/75 backdrop-blur-sm" onClick={onClose} />
      <div className="relative w-full max-w-xl overflow-hidden rounded-2xl border border-cyber-border bg-cyber-surface shadow-2xl">
        <div className="flex items-center gap-3 border-b border-cyber-border/60 px-4 py-3">
          <Search className="h-4 w-4 text-cyber-muted" />
          <input
            ref={inputRef}
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setCursor(0);
            }}
            placeholder="Search courses, labs, missions, CTF challenges, tools…"
            aria-label="Search the academy"
            className="w-full bg-transparent font-mono text-sm text-cyber-text placeholder:text-cyber-muted focus:outline-none"
          />
          <kbd className="rounded-lg border border-cyber-border/60 bg-cyber-bg px-2 py-0.5 font-mono text-[10px] text-cyber-muted">
            ESC
          </kbd>
        </div>

        <ul className="max-h-80 overflow-y-auto p-2">
          {results.length === 0 ? (
            <li className="px-3 py-8 text-center font-mono text-xs text-cyber-muted">
              No match for “{query}”. Try a course title, tool slug or lab name.
            </li>
          ) : (
            results.map((t, i) => (
              <li key={t.id}>
                <button
                  type="button"
                  onMouseEnter={() => setCursor(i)}
                  onClick={() => {
                    router.push(t.href);
                    onClose();
                  }}
                  className={cn(
                    'flex w-full items-center justify-between gap-3 rounded-lg px-3 py-2.5 text-left transition-colors',
                    i === cursor ? 'bg-cyber-primary/10 text-cyber-primary' : 'hover:bg-cyber-bg',
                  )}
                >
                  <span className="min-w-0">
                    <span className="block truncate text-sm">{t.label}</span>
                    {t.hint && <span className="block truncate text-[11px] text-cyber-muted">{t.hint}</span>}
                  </span>
                  <span className="flex shrink-0 items-center gap-2">
                    <span className="rounded-full border border-cyber-border/60 px-2 py-0.5 font-mono text-[9px] uppercase tracking-wider text-cyber-muted">
                      {t.group}
                    </span>
                    {i === cursor && <CornerDownLeft className="h-3.5 w-3.5" />}
                  </span>
                </button>
              </li>
            ))
          )}
        </ul>
      </div>
    </div>
  );
}