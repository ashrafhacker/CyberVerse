'use client';

import Link from 'next/link';
import { useState } from 'react';
import { Flag, Loader2, Radio, Swords } from 'lucide-react';
import { api } from '@/lib/api';
import { cn } from '@/lib/utils';
import { formatCountdown, useCountdown } from '@/lib/command-center';
import type { CCWarRoom } from '@/lib/command-center';

interface SubmissionResult {
  correct: boolean;
  message: string;
  points: number;
  firstBlood: boolean;
}

export default function WarRoom({ warRoom }: { warRoom: CCWarRoom }) {
  const [flag, setFlag] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<SubmissionResult | null>(null);

  const countdown = useCountdown(warRoom.tournament?.startAt ?? null);

  const submit = async () => {
    const slug = warRoom.activeSlug;
    const value = flag.trim();
    if (!slug || !value || submitting) return;
    setSubmitting(true);
    setResult(null);
    try {
      const res = await api.post<{
        data: { correct: boolean; message: string; points_earned: number; first_blood: boolean };
      }>(`/ctf/challenges/${slug}/submit`, { flag: value });
      setResult({
        correct: res.data.correct,
        message: res.data.message,
        points: res.data.points_earned,
        firstBlood: res.data.first_blood,
      });
      if (res.data.correct) setFlag('');
    } catch (err) {
      setResult({
        correct: false,
        message: err instanceof Error ? err.message : 'Submission failed.',
        points: 0,
        firstBlood: false,
      });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <section className="flex flex-col gap-4 rounded-2xl border border-cyber-border/60 bg-cyber-surface p-5 shadow-2xl">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <Flag className="h-5 w-5 text-cyber-secondary" />
          <h3 className="text-sm font-bold">War room feed</h3>
        </div>
        <span className="flex items-center gap-1.5 rounded-full border border-cyber-border/60 bg-cyber-border/40 px-2.5 py-1 font-mono text-[10px] font-bold uppercase text-cyber-primary">
          <span className="h-2 w-2 animate-ping rounded-full bg-cyber-primary" />
          Live
        </span>
      </div>

      {warRoom.tournament ? (
        <div className="relative flex flex-col gap-2.5 overflow-hidden rounded-xl border border-cyber-border/60 bg-cyber-bg/60 p-3 shadow-inner">
          <div className="flex items-center justify-between gap-2 font-mono text-[11px]">
            <span className="truncate font-bold tracking-wider text-cyber-primary">{warRoom.tournament.name}</span>
            <span className="shrink-0 rounded border border-cyber-primary/30 bg-cyber-primary/10 px-2 py-0.5 font-bold text-cyber-primary">
              {warRoom.tournament.status}
            </span>
          </div>
          <div className="flex flex-wrap items-center justify-between gap-2">
            <span className="font-mono text-xs text-cyber-muted">
              {warRoom.tournament.status === 'active' ? 'Ends in' : 'Starts in'}{' '}
              <span className="font-bold text-cyber-primary">
                {countdown ?? (warRoom.tournament.status === 'active' ? '—' : formatCountdown(0))}
              </span>
            </span>
            <span className="font-mono text-[10px] text-cyber-muted">
              {warRoom.tournament.registeredPlayers}/{warRoom.tournament.maxPlayers} players ·{' '}
              {warRoom.tournament.registeredTeams} teams
            </span>
          </div>
          <Link
            href="/game/tournaments"
            className="flex items-center justify-center gap-2 rounded-xl bg-cyber-secondary px-3 py-1.5 font-mono text-[11px] font-bold uppercase tracking-wider text-cyber-bg shadow-md transition-colors hover:bg-cyber-primary"
          >
            <Swords className="h-3.5 w-3.5" />
            Register squad
          </Link>
        </div>
      ) : (
        <p className="rounded-xl border border-cyber-border/60 bg-cyber-bg/60 px-3 py-2.5 font-mono text-[11px] text-cyber-muted">
          No tournament scheduled. Open the arena to host one.
        </p>
      )}

      <div className="flex items-center justify-between gap-2 font-mono text-[11px] text-cyber-muted">
        <span>
          Flags captured: <span className="font-bold text-cyber-primary">{warRoom.solved}</span>/{warRoom.total}
        </span>
        {warRoom.rank !== null && (
          <span>
            Weekly rank: <span className="font-bold text-cyber-primary">#{warRoom.rank}</span>
            {warRoom.totalPlayers ? ` of ${warRoom.totalPlayers}` : ''}
          </span>
        )}
      </div>

      <div className="flex flex-col gap-2.5 font-mono text-[12px]">
        {warRoom.events.map((event) => (
          <div
            key={event.id}
            className="flex items-start gap-2.5 rounded-xl border border-cyber-border/50 bg-cyber-bg/60 px-3 py-2.5"
          >
            <span className={cn('mt-0.5 font-bold', event.tone === 'primary' ? 'text-cyber-primary' : 'text-cyber-secondary')}>
              &rsaquo;
            </span>
            <div className="min-w-0 flex-1 leading-snug">
              <span className={cn('font-semibold', event.tone === 'primary' ? 'text-cyber-primary' : 'text-cyber-secondary')}>
                {event.actor}
              </span>
              <span className="text-cyber-muted"> {event.verb} </span>
              <span className="font-bold">{event.target}</span>
              <div className="mt-0.5 font-mono text-[10px] text-cyber-muted">{event.meta}</div>
            </div>
          </div>
        ))}
      </div>

      <div>
        <div className="relative flex items-center">
          <input
            value={flag}
            onChange={(e) => setFlag(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') void submit();
            }}
            placeholder={warRoom.activeSlug ? 'flag{cyberverse_...}' : 'no challenge armed'}
            aria-label="Submit a flag"
            className="w-full rounded-xl border border-cyber-border/60 bg-cyber-bg/60 py-2.5 pl-3.5 pr-24 font-mono text-xs text-cyber-text placeholder:text-cyber-muted focus:border-cyber-primary focus:shadow-[0_0_12px_rgba(0,229,255,0.2)] focus:outline-none"
          />
          <button
            type="button"
            onClick={() => void submit()}
            disabled={submitting || !flag.trim() || !warRoom.activeSlug}
            className="absolute right-1.5 flex items-center gap-1.5 rounded-lg bg-cyber-border px-3 py-1.5 font-mono text-[11px] font-bold uppercase text-cyber-primary transition-colors hover:bg-cyber-primary hover:text-cyber-bg disabled:cursor-not-allowed disabled:opacity-50"
          >
            {submitting ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Radio className="h-3.5 w-3.5" />}
            Submit
          </button>
        </div>

        {result && (
          <p
            className={cn(
              'mt-2 rounded-lg border px-3 py-2 font-mono text-[11px]',
              result.correct
                ? 'border-cyber-success/30 bg-cyber-success/10 text-cyber-success'
                : 'border-cyber-danger/30 bg-cyber-danger/10 text-cyber-danger',
            )}
          >
            {result.message}
            {result.firstBlood && ' · First blood!'}
            {result.correct && result.points > 0 && ` · +${result.points} pts`}
          </p>
        )}
      </div>
    </section>
  );
}