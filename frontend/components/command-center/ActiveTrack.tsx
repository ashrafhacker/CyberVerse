'use client';

import Link from 'next/link';
import { BookOpen, ChevronRight, Columns2 } from 'lucide-react';
import { clampPercent } from '@/lib/command-center';
import type { CCCourseTrack } from '@/lib/command-center';

function meter(percent: number): string {
  const filled = Math.round((clampPercent(percent) / 100) * 20);
  return `[${'█'.repeat(filled)}${'░'.repeat(20 - filled)}]`;
}

export default function ActiveTrack({ track }: { track: CCCourseTrack }) {
  return (
    <section className="flex flex-col gap-4 rounded-2xl border border-cyber-border/60 bg-cyber-surface p-5 shadow-2xl">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <BookOpen className="h-5 w-5 text-cyber-secondary" />
          <span className="font-mono text-[10px] uppercase tracking-wider text-cyber-muted">Active curriculum track</span>
        </div>
        <span className="rounded-full border border-cyber-border/60 bg-cyber-bg/60 px-2.5 py-1 font-mono text-[10px] text-cyber-secondary">
          track ref: {track.courseId.slice(0, 8).toUpperCase()}
        </span>
      </div>

      <div className="flex flex-col justify-between gap-4 md:flex-row md:items-center">
        <div className="flex-1">
          <span className="font-mono text-[10px] uppercase tracking-wider text-cyber-primary">Course module</span>
          <h3 className="mt-0.5 text-lg font-bold">{track.courseName}</h3>
          <p className="mt-1 text-sm text-cyber-muted">
            <span className="font-medium text-cyber-primary">{track.moduleName}</span> — {track.lessonName}
          </p>
        </div>

        <div className="min-w-[240px] rounded-xl border border-cyber-border/60 bg-cyber-bg/60 p-3 font-mono shadow-inner">
          <div className="mb-1 flex justify-between text-[11px] text-cyber-muted">
            <span>Module completion</span>
            <span className="font-bold text-cyber-primary">{track.percent}%</span>
          </div>
          <div className="select-none font-bold tracking-tight text-cyber-primary">{meter(track.percent)}</div>
          <div className="mt-1.5 flex items-center justify-between text-[10px] text-cyber-muted">
            <span>est. {track.minutesLeft} mins remaining</span>
            <span className="font-bold text-cyber-primary">+{track.xpReward} XP</span>
          </div>
        </div>
      </div>

      <div className="flex flex-col justify-between gap-3 rounded-xl border border-cyber-border/60 bg-cyber-bg/60 p-4 sm:flex-row sm:items-center">
        <div className="flex min-w-0 items-center gap-2 text-sm text-cyber-muted">
          <span className="font-mono text-[10px] uppercase text-cyber-muted">Next module:</span>
          <span className="truncate font-medium text-cyber-text">
            {track.nextLessonName ?? 'Course complete — pick a new track'}
          </span>
        </div>
        <Link
          href={`/courses/${track.courseId}/lessons/${track.lessonId}`}
          className="flex shrink-0 items-center justify-center gap-2 rounded-xl bg-cyber-secondary px-4 py-2.5 font-mono text-xs font-bold uppercase tracking-wider text-cyber-bg shadow-md transition-colors hover:bg-cyber-primary"
        >
          <Columns2 className="h-4 w-4" />
          Launch split-screen lab
          <ChevronRight className="h-3.5 w-3.5" />
        </Link>
      </div>
    </section>
  );
}