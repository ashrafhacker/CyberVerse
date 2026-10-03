'use client';

import Link from 'next/link';
import { ChevronRight, Compass, Play } from 'lucide-react';
import { cn } from '@/lib/utils';
import { formatNumber } from '@/lib/command-center';
import type { CCPathCard } from '@/lib/command-center';

const TONE: Record<CCPathCard['tone'], string> = {
  info: 'border-cyber-border/60 bg-cyber-border/40 text-cyber-secondary',
  warn: 'border-cyber-warning/30 bg-cyber-warning/10 text-cyber-warning',
  danger: 'border-cyber-danger/30 bg-cyber-danger/10 text-cyber-danger',
};

export default function RecommendedPaths({ paths }: { paths: CCPathCard[] }) {
  return (
    <section className="flex flex-col gap-4">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <Compass className="h-5 w-5 text-cyber-primary" />
          <h3 className="text-sm font-bold uppercase tracking-wider">Recommended intelligence paths</h3>
        </div>
        <Link
          href="/courses"
          className="flex items-center gap-1 font-mono text-[11px] text-cyber-primary transition-colors hover:text-cyber-text"
        >
          Explore all tracks
          <ChevronRight className="h-3.5 w-3.5" />
        </Link>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        {paths.map((path) => (
          <article
            key={path.id}
            className="group flex flex-col justify-between gap-4 rounded-2xl border border-cyber-border/60 bg-cyber-surface p-4 shadow-xl transition-colors hover:border-cyber-primary/40 hover:bg-cyber-surface/80"
          >
            <div className="flex flex-col gap-2">
              <div className="flex items-center justify-between gap-2">
                <span
                  className={cn(
                    'rounded-full border px-2.5 py-1 font-mono text-[10px] font-bold uppercase',
                    TONE[path.tone],
                  )}
                >
                  {path.difficulty}
                </span>
                <span className="font-mono text-[11px] font-bold text-cyber-primary">+{formatNumber(path.xp)} XP</span>
              </div>
              <h4 className="text-base font-bold leading-snug transition-colors group-hover:text-cyber-primary">
                {path.title}
              </h4>
              <p className="line-clamp-2 text-sm text-cyber-muted">{path.blurb}</p>
            </div>

            <div className="flex items-center justify-between gap-2 pt-1">
              <span className="truncate font-mono text-[11px] text-cyber-muted">{path.meta}</span>
              <Link
                href={path.href}
                aria-label={`Open ${path.title}`}
                className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border border-cyber-border/60 bg-cyber-bg text-cyber-muted shadow-sm transition-colors group-hover:border-cyber-primary group-hover:bg-cyber-primary group-hover:text-cyber-bg"
              >
                <Play className="h-4 w-4" />
              </Link>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}