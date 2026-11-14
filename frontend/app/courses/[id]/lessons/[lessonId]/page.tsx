'use client';

import { useState, useRef, useEffect } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@clerk/nextjs';
import {
  Play, Pause, Volume2, VolumeX, Maximize, ChevronLeft,
  ChevronRight, BookOpen, FileText, Lock, CheckCircle,
  List, X, Loader2, RefreshCw,
} from 'lucide-react';
import Navbar from '@/components/Navbar';
import Breadcrumbs from '@/components/Breadcrumbs';
import { API_URL, api, getTokens, ApiError } from '@/lib/api';
import { CURRICULUM } from '@/lib/curriculum';

// ─── Completion verification constants (mirror backend) ──────────────────────
const COMPLETION_MIN_PERCENT = 90;
const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const SAVE_INTERVAL_MS = 15_000; // telemetry heartbeat while watching
const STALL_TIMEOUT_MS = 12_000; // reload the stream if nothing decodes for this long

type ProgressEntry = {
  lesson_id: string;
  status: string;
  progress_percentage: number;
  last_position?: { seconds?: number; watched_seconds?: number } | null;
};

// ─── Video Player ─────────────────────────────────────────────────────────────
// Tracks *unique* watched seconds (rewinding does not double-count, seeking
// forward counts nothing), persists throttled telemetry for server-side
// completion verification, resumes from the saved position, and recovers from
// stalled or dropped streams instead of spinning forever.
function VideoPlayer({
  src, title, lessonId, canTrack, initialResume, baselineWatched, baselinePct, onWatchPercent,
}: {
  src: string;
  title: string;
  lessonId: string;
  canTrack: boolean;
  initialResume: number;
  baselineWatched: number | null;
  baselinePct: number;
  onWatchPercent?: (pct: number) => void;
}) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [playing, setPlaying] = useState(false);
  const [muted, setMuted] = useState(false);
  const [progress, setProgress] = useState(0);
  const [buffering, setBuffering] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [watchPct, setWatchPct] = useState(baselinePct);
  const [timeText, setTimeText] = useState<string | null>(null); // "0:35 / 1:34" clock
  const [resumeAt, setResumeAt] = useState<number | null>(null); // saved position the player restored

  // ── watch-tracking state (refs so handlers always see fresh values) ──
  const bucketsRef = useRef<Uint8Array | null>(null); // one slot per second of the video
  const uniqueCountRef = useRef(0); // session-unique seconds watched
  const baseWatchedRef = useRef(baselineWatched ?? 0); // seconds watched in earlier sessions
  const durRef = useRef(0);
  const lastTRef = useRef<number | null>(null);
  const pctRef = useRef(baselinePct);
  const notifiedRef = useRef(baselinePct);
  const resumeDoneRef = useRef(false);
  const pendingRestoreRef = useRef<number | null>(null); // position to restore after a forced reload
  const saveAtRef = useRef(0);
  const lastSaveAtRef = useRef(Date.now());
  const retryRef = useRef(0);
  const wasPlayingRef = useRef(false);
  const stallTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // ── helpers ────────────────────────────────────────────────────────────
  const markWatched = (from: number, to: number) => {
    const buckets = bucketsRef.current;
    if (!buckets || buckets.length === 0) return;
    const start = Math.max(0, Math.floor(from));
    const end = Math.min(buckets.length - 1, Math.floor(to));
    for (let i = start; i <= end; i++) {
      if (!buckets[i]) {
        buckets[i] = 1;
        uniqueCountRef.current += 1;
      }
    }
  };

  const recomputePct = () => {
    const dur = durRef.current;
    if (!(dur > 0)) return;
    const watched = Math.min(dur, baseWatchedRef.current + uniqueCountRef.current);
    const pct = Math.min(100, (watched / dur) * 100);
    pctRef.current = pct;
    setWatchPct(Math.round(pct * 10) / 10);
    if (Math.abs(pct - notifiedRef.current) >= 1 || (pct >= 100 && notifiedRef.current < 100)) {
      notifiedRef.current = pct;
      onWatchPercent?.(pct);
    }
  };

  const tracked = canTrack && UUID_RE.test(lessonId);

  const send = (status: 'in_progress') => {
    if (!tracked) return;
    const v = videoRef.current;
    const now = Date.now();
    const deltaSpent = Math.min(60, Math.max(0, Math.round((now - lastSaveAtRef.current) / 1000)));
    lastSaveAtRef.current = now;
    saveAtRef.current = now;
    const dur = durRef.current;
    const watched = dur > 0
      ? Math.round(Math.min(dur, baseWatchedRef.current + uniqueCountRef.current) * 10) / 10
      : undefined;
    void api
      .post(`/progress/lessons/${lessonId}`, {
        status,
        progress_percentage: Math.min(100, Math.round(pctRef.current)),
        time_spent_seconds: deltaSpent,
        position_seconds: Math.round(((v?.currentTime ?? 0) + Number.EPSILON) * 10) / 10,
        watched_seconds: watched,
      })
      .catch(() => {
        /* telemetry must never interrupt playback */
      });
  };

  const maybeSave = () => {
    if (!tracked) return;
    if (Date.now() - saveAtRef.current >= SAVE_INTERVAL_MS) send('in_progress');
  };

  const clearStallTimer = () => {
    if (stallTimerRef.current) {
      clearTimeout(stallTimerRef.current);
      stallTimerRef.current = null;
    }
  };

  const restoreAndPlay = () => {
    const el = videoRef.current;
    if (!el) return;
    el.load();
    void el.play().catch(() => { /* user can hit play */ });
  };

  // ── media event handlers ───────────────────────────────────────────────
  const onLoadedMetadata = () => {
    const v = videoRef.current;
    if (!v) return;
    const dur = isFinite(v.duration) ? v.duration : 0;
    durRef.current = dur;
    setTimeText(`${fmtTime(v.currentTime)} / ${fmtTime(dur)}`);
    if (!bucketsRef.current && dur > 0) bucketsRef.current = new Uint8Array(Math.ceil(dur));
    if (baselineWatched === null && baselinePct > 0 && dur > 0) {
      baseWatchedRef.current = (baselinePct / 100) * dur;
    }
    if (pendingRestoreRef.current != null) {
      // Forced reload (stall/error recovery) — pick up where we were.
      v.currentTime = pendingRestoreRef.current;
      pendingRestoreRef.current = null;
      if (wasPlayingRef.current && v.paused) void v.play().catch(() => {});
    } else if (!resumeDoneRef.current) {
      resumeDoneRef.current = true;
      const pos = initialResume;
      if (pos > 5 && dur > 0 && pos < dur - 8) {
        v.currentTime = pos;
        // Surface the restored position YouTube-style so the learner can see
        // where they are picking up (and start over if it was unwanted).
        setResumeAt(pos);
      }
    }
    recomputePct();
  };

  const onTimeUpdate = () => {
    const v = videoRef.current;
    if (!v) return;
    const dur = v.duration;
    if (!isFinite(dur) || dur <= 0) return;
    const t = v.currentTime;
    const last = lastTRef.current;
    // Count only natural forward playback; large jumps are seeks (count nothing).
    if (last !== null && t >= last && t - last <= 2) markWatched(last, t);
    lastTRef.current = t;
    setTimeText(`${fmtTime(t)} / ${fmtTime(dur)}`);
    setProgress((t / dur) * 100);
    recomputePct();
    maybeSave();
  };

  const onWaiting = () => {
    setBuffering(true);
    clearStallTimer();
    stallTimerRef.current = setTimeout(() => {
      // Nothing decoded for too long — the stream likely died. Reconnect and
      // resume from the current position instead of spinning forever.
      const v = videoRef.current;
      if (v) pendingRestoreRef.current = v.currentTime;
      retryRef.current += 1;
      if (retryRef.current > 5) {
        setBuffering(false);
        setError('Playback stalled repeatedly. Check your connection, then retry.');
        return;
      }
      restoreAndPlay();
    }, STALL_TIMEOUT_MS);
  };

  // Media is decodable again — stop showing the buffering overlay. Only
  // `playing` may flip the playing state (canplay also fires while paused).
  const onCanPlay = () => {
    clearStallTimer();
    setBuffering(false);
    if (wasPlayingRef.current && videoRef.current?.paused) {
      void videoRef.current.play().catch(() => {});
    }
  };

  const onPlayingUI = () => {
    clearStallTimer();
    setBuffering(false);
    setPlaying(true);
  };

  const onVideoError = () => {
    if (retryRef.current >= 3) {
      setBuffering(false);
      setError('Video failed to load. Check your connection, then retry.');
      return;
    }
    retryRef.current += 1;
    pendingRestoreRef.current = lastTRef.current ?? videoRef.current?.currentTime ?? 0;
    setBuffering(true);
    setTimeout(restoreAndPlay, 1200 * retryRef.current);
  };

  const manualRetry = () => {
    retryRef.current = 0;
    setError(null);
    setBuffering(true);
    pendingRestoreRef.current = lastTRef.current ?? videoRef.current?.currentTime ?? 0;
    const el = videoRef.current;
    if (el) {
      // Cache-bust in case a broken response got cached.
      const sep = src.includes('?') ? '&' : '?';
      el.src = `${src}${sep}_r=${Date.now()}`;
    }
    restoreAndPlay();
  };

  // YouTube keeps the "resume from" prompt up until dismissed — we clear it on
  // play (onPlay) or on either button click, so it never outstays its welcome.
  // Flush telemetry when leaving the lesson or hiding the tab.
  useEffect(() => {
    const flush = () => send('in_progress');
    const onVisibility = () => {
      if (document.visibilityState === 'hidden') flush();
    };
    document.addEventListener('visibilitychange', onVisibility);
    return () => {
      document.removeEventListener('visibilitychange', onVisibility);
      clearStallTimer();
      flush();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [canTrack, lessonId]);

  if (src.startsWith('gdrive://')) {
    const fileId = src.replace('gdrive://', '');
    return (
      <div className="relative w-full bg-black rounded-lg overflow-hidden">
        <iframe
          src={`https://drive.google.com/file/d/${fileId}/preview`}
          className="w-full aspect-video border-0"
          allow="autoplay"
          title={title}
        />
      </div>
    );
  }

  const toggle = () => {
    if (!videoRef.current) return;
    if (playing) { videoRef.current.pause(); } else { void videoRef.current.play(); }
    setPlaying(!playing);
  };

  const seek = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!videoRef.current) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const pct = (e.clientX - rect.left) / rect.width;
    videoRef.current.currentTime = pct * videoRef.current.duration;
  };

  const fmtPct = Math.min(100, Math.floor(watchPct));

  return (
    <div className="relative w-full bg-black rounded-lg overflow-hidden group">
      <video
        ref={videoRef}
        src={src}
        className="w-full aspect-video"
        preload="auto"
        playsInline
        controlsList="nodownload noremoteplayback"
        disablePictureInPicture
        onContextMenu={(e) => e.preventDefault()}
        onLoadedMetadata={onLoadedMetadata}
        onTimeUpdate={onTimeUpdate}
        onPlay={() => { wasPlayingRef.current = true; setPlaying(true); setResumeAt(null); }}
        onPause={() => { wasPlayingRef.current = false; setPlaying(false); send('in_progress'); }}
        onPlaying={onPlayingUI}
        onCanPlay={onCanPlay}
        onWaiting={onWaiting}
        onStalled={onWaiting}
        onEnded={() => {
          clearStallTimer();
          setBuffering(false);
          setPlaying(false);
          recomputePct();
          send('in_progress');
          onWatchPercent?.(pctRef.current); // exact final percentage for gating
        }}
        onError={onVideoError}
        title={title}
      />

      {/* Buffering indicator */}
      {buffering && !error && (
        <div className="absolute inset-0 flex items-center justify-center bg-black/40 pointer-events-none">
          <div className="flex flex-col items-center gap-2">
            <Loader2 className="h-10 w-10 text-cyber-primary animate-spin" />
            <span className="text-xs text-white/80 font-mono">Buffering…</span>
          </div>
        </div>
      )}

      {/* Error recovery overlay */}
      {error && (
        <div className="absolute inset-0 flex flex-col items-center justify-center gap-4 bg-black/80 px-6 text-center">
          <p className="text-sm text-white/90">{error}</p>
          <button onClick={manualRetry} className="terminal-button flex items-center gap-2 px-4 py-2 text-sm">
            <RefreshCw className="h-4 w-4" />
            Retry
          </button>
        </div>
      )}

      {/* Watch progress badge — feeds the completion gate */}
      <div className="absolute top-2 right-2 flex items-center gap-1.5 rounded bg-black/70 px-2 py-1 text-[11px] font-mono text-white/80 backdrop-blur-sm">
        <span
          role="progressbar"
          aria-valuenow={fmtPct}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label="Watched percentage"
        >
          Watched {fmtPct}%
        </span>
        {fmtPct >= COMPLETION_MIN_PERCENT && <CheckCircle className="h-3.5 w-3.5 text-cyber-success" />}
      </div>

      {/* "Resume from where you left off?" prompt — YouTube-style */}
      {resumeAt != null && (
        <div
          className="absolute left-3 bottom-16 z-10 flex items-center gap-3 rounded border border-white/10 bg-black/85 px-3 py-2 text-xs text-white/90 shadow-lg backdrop-blur-sm"
          role="status"
        >
          <span className="font-mono">
            Resume from{' '}
            <span className="font-semibold text-cyber-primary">{fmtTime(resumeAt)}</span>?
          </span>
          <button
            onClick={() => {
              setResumeAt(null);
              void videoRef.current?.play().catch(() => {});
            }}
            className="rounded bg-cyber-primary/90 px-2.5 py-1 text-[11px] font-semibold text-cyber-bg transition-colors hover:bg-cyber-primary"
          >
            Resume
          </button>
          <button
            onClick={() => {
              if (videoRef.current) videoRef.current.currentTime = 0;
              setResumeAt(null);
            }}
            className="rounded px-2.5 py-1 text-[11px] text-white/70 transition-colors hover:text-white"
          >
            Start over
          </button>
        </div>
      )}

      {/* Controls overlay */}
      <div className="absolute bottom-0 inset-x-0 bg-gradient-to-t from-black/80 to-transparent p-3 opacity-0 group-hover:opacity-100 transition-opacity">
        {/* Progress bar */}
        <div
          className="w-full h-1.5 bg-white/20 rounded-full cursor-pointer mb-3"
          onClick={seek}
        >
          <div className="h-full bg-cyber-primary rounded-full transition-all" style={{ width: `${progress}%` }} />
        </div>
        <div className="flex items-center gap-3">
          <button onClick={toggle} className="text-white hover:text-cyber-primary transition-colors" aria-label={playing ? 'Pause' : 'Play'}>
            {playing ? <Pause className="h-5 w-5" /> : <Play className="h-5 w-5" />}
          </button>
          {/* Playback clock — current position / total duration */}
          <span className="text-white/80 text-xs font-mono tabular-nums" aria-label="Playback time">
            {timeText ?? '0:00 / --:--'}
          </span>
          <button
            onClick={() => { setMuted(!muted); if (videoRef.current) videoRef.current.muted = !muted; }}
            className="text-white hover:text-cyber-primary transition-colors"
            aria-label={muted ? 'Unmute' : 'Mute'}
          >
            {muted ? <VolumeX className="h-4 w-4" /> : <Volume2 className="h-4 w-4" />}
          </button>
          <span className="text-white/60 text-xs flex-1 truncate">{title}</span>
          <button
            onClick={() => videoRef.current?.requestFullscreen()}
            className="text-white hover:text-cyber-primary transition-colors"
            aria-label="Fullscreen"
          >
            <Maximize className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* Big play button */}
      {!playing && !error && (
        <button
          onClick={toggle}
          className="absolute inset-0 flex items-center justify-center bg-black/30 hover:bg-black/40 transition-colors"
          aria-label="Play video"
        >
          <div className="w-16 h-16 rounded-full bg-cyber-primary/90 flex items-center justify-center shadow-lg">
            <Play className="h-8 w-8 text-cyber-bg ml-1" />
          </div>
        </button>
      )}
    </div>
  );
}

// ─── Blocked-content notice ─────────────────────────────────────────────────
function BlockedContentNotice({ id, message }: { id: string; message: string }) {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-cyber-bg px-6 text-center">
      <Lock className="h-12 w-12 text-cyber-primary" aria-hidden="true" />
      <h1 className="text-xl font-bold text-cyber-text">This content is blocked</h1>
      <p className="max-w-md text-sm text-cyber-muted">
        {message || 'You do not have access to this lesson right now.'}
      </p>
      <p className="max-w-md text-sm text-cyber-muted">
        If you believe you should be able to see this, contact the site owner and they will sort it out.
      </p>
      <div className="flex flex-wrap items-center justify-center gap-3">
        <Link href="/contact" className="terminal-button px-4 py-2 text-sm">
          Contact the site owner
        </Link>
        <Link href={`/courses/${id}`} className="terminal-button px-4 py-2 text-sm">
          Back to Course
        </Link>
      </div>
    </div>
  );
}

// ─── PDF Viewer ───────────────────────────────────────────────────────────────
// Textbook-style reading shell: a brief book-cover intro opens the reading
// room, then the content renders as a warm ivory "paper" page with a stacked
// top sheet, serif chapter heading under a mono running head, and a
// page-number footer with prev/next + go-to-page navigation. Page changes use
// the iframe `#page=` fragment (Chrome built-in PDF viewer); Google Drive
// previews navigate inside their own frame. Left/Right arrow keys turn pages.
function PdfViewer({ src, title }: { src: string; title: string }) {
  const isGdrive = src.startsWith('gdrive://');
  const fileId = isGdrive ? src.replace('gdrive://', '') : '';
  const [page, setPage] = useState(1);
  const [coverOpen, setCoverOpen] = useState(true);
  const [draft, setDraft] = useState('');
  const frameRef = useRef<HTMLDivElement>(null);

  const gdriveSrc = fileId ? `https://drive.google.com/file/d/${fileId}/preview` : '';
  const pdfSrc = isGdrive ? gdriveSrc : `${src}#page=${page}&view=FitW&toolbar=0&navpanes=0`;

  const goTo = (p: number) => {
    if (!Number.isFinite(p)) return;
    setPage(Math.max(1, Math.floor(p)));
    setDraft('');
  };
  const prev = () => setPage((p) => Math.max(1, p - 1));
  const next = () => setPage((p) => p + 1);

  const onKeyDown = (e: React.KeyboardEvent<HTMLDivElement>) => {
    // Don't hijack arrow keys while the user is typing a page number.
    const tag = (e.target as HTMLElement)?.tagName;
    if (tag === 'INPUT') return;
    if (e.key === 'ArrowRight') { e.preventDefault(); next(); }
    else if (e.key === 'ArrowLeft') { e.preventDefault(); prev(); }
  };

  useEffect(() => {
    frameRef.current?.focus();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ── Book cover intro ─────────────────────────────────────────────────────
  if (coverOpen) {
    return (
      <div className="relative mx-auto w-full max-w-3xl">
        <div className="relative flex min-h-[420px] flex-col items-center justify-center overflow-hidden rounded-xl border border-cyber-border bg-gradient-to-br from-[#131a3a] via-cyber-surface to-cyber-bg px-6 py-10 text-center shadow-[0_30px_80px_-20px_rgba(0,0,0,0.8)]">
          {/* Double decorative frame */}
          <div aria-hidden className="pointer-events-none absolute inset-3 rounded-lg border border-cyber-primary/25" />
          <div aria-hidden className="pointer-events-none absolute inset-4 rounded-md border border-cyber-primary/10" />
          <BookOpen className="relative h-10 w-10 text-cyber-primary" />
          <p className="relative mt-5 font-mono text-[9px] uppercase tracking-[0.4em] text-cyber-primary/80">
            CyberVerse · Academy
          </p>
          <h2 className="relative mt-3 max-w-md font-serif text-3xl leading-tight text-cyber-text">
            {title}
          </h2>
          <p className="relative mt-3 font-mono text-[10px] uppercase tracking-[0.25em] text-cyber-muted">
            {isGdrive ? 'PDF Module · Google Drive Preview' : 'PDF Module · Interactive Reading'}
          </p>
          <button
            onClick={() => setCoverOpen(false)}
            className="relative mt-8 inline-flex items-center gap-2 rounded-md bg-cyber-primary px-6 py-3 font-mono text-xs font-bold uppercase tracking-[0.25em] text-[#04151a] transition-all hover:bg-cyber-primary/90 hover:shadow-[0_0_24px_rgba(0,229,255,0.35)]"
          >
            Begin Reading <ChevronRight className="h-4 w-4" />
          </button>
        </div>
      </div>
    );
  }

  // ── Textbook reading room ─────────────────────────────────────────────────
  return (
    <div className="relative mx-auto w-full max-w-3xl">
      <div
        ref={frameRef}
        tabIndex={0}
        onKeyDown={onKeyDown}
        role="region"
        aria-label={`PDF reader: ${title}`}
        className="relative overflow-hidden rounded-xl bg-[#f7f3ea] shadow-[0_30px_80px_-20px_rgba(0,0,0,0.8)] ring-1 ring-black/40 outline-none focus-visible:ring-2 focus-visible:ring-cyber-primary/70"
      >
        {/* Stacked top sheet edge */}
        <div className="h-3 rounded-t-xl bg-gradient-to-b from-[#e7e0cd] to-[#d9d0ba]" />

        {/* Mono running head */}
        <div className="flex items-center justify-between border-b border-[#e5ddc9] px-6 py-1.5">
          <span className="font-mono text-[9px] uppercase tracking-[0.28em] text-[#8a8171]">CyberVerse</span>
          <span className="font-mono text-[9px] uppercase tracking-[0.28em] text-[#8a8171]">Reading Room</span>
          <span className="font-mono text-[9px] uppercase tracking-[0.28em] text-[#8a8171]">Lesson</span>
        </div>

        {/* Serif chapter heading */}
        <div className="flex items-end justify-between gap-4 border-b-2 border-[#cdbb9e] px-6 pb-3 pt-4">
          <div className="min-w-0">
            <p className="mb-1 font-mono text-[9px] uppercase tracking-[0.3em] text-[#a5937a]">Chapter · PDF Reader</p>
            <h2 className="truncate font-serif text-2xl leading-tight text-[#1c1917]">{title}</h2>
          </div>
          <BookOpen className="mb-1 h-6 w-6 shrink-0 text-[#a5937a]" />
        </div>

        {/* Page body */}
        <div className="relative bg-[#f7f3ea]">
          <iframe
            src={pdfSrc}
            className="h-[58vh] min-h-[320px] w-full bg-[#f7f3ea]"
            title={title}
            onContextMenu={(e) => e.preventDefault()}
          />
          {/* Gutter shadow (spine side) */}
          <div aria-hidden className="pointer-events-none absolute inset-y-0 left-0 w-10 bg-gradient-to-r from-black/[0.10] to-transparent" />
          {/* Page-fade replays on each page turn (iframe stays, no re-fetch) */}
          {!isGdrive && (
            <div key={page} aria-hidden className="page-fade pointer-events-none absolute inset-0 bg-[#f7f3ea]" />
          )}
        </div>

        {/* Footer: page navigation */}
        {isGdrive ? (
          <div className="flex items-center justify-between border-t border-[#e5ddc9] bg-[#fbf8ef] px-6 py-2">
            <span className="font-mono text-[10px] uppercase tracking-[0.25em] text-[#8a8171]">Google Drive preview</span>
            <span className="font-mono text-[10px] uppercase tracking-[0.25em] text-[#8a8171]">View only</span>
          </div>
        ) : (
          <div className="flex items-center justify-between gap-3 border-t border-[#e5ddc9] bg-[#fbf8ef] px-4 py-2 sm:px-6">
            <button
              onClick={prev}
              disabled={page <= 1}
              aria-label="Previous page"
              className="inline-flex items-center gap-1.5 rounded-md border border-[#d8cfb8] bg-[#fbf8ef] px-3 py-1.5 text-[11px] font-semibold uppercase tracking-wider text-[#1c1917] transition-colors hover:bg-[#efe9d8] disabled:cursor-not-allowed disabled:opacity-40"
            >
              <ChevronLeft className="h-3.5 w-3.5" /> Prev
            </button>
            <div className="flex items-center gap-2">
              <span className="hidden font-mono text-[10px] uppercase tracking-[0.3em] text-[#8a8171] xs:inline">Page</span>
              <input
                type="number"
                min={1}
                value={draft}
                placeholder={String(page)}
                onFocus={() => setDraft(String(page))}
                onBlur={() => setDraft('')}
                onChange={(e) => setDraft(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter') goTo(Number(draft)); }}
                aria-label="Go to page"
                className="w-12 rounded border border-[#d8cfb8] bg-white px-1.5 py-1 text-center font-mono text-[11px] text-[#1c1917] outline-none focus:border-[#a5937a]"
              />
            </div>
            <button
              onClick={next}
              aria-label="Next page"
              className="inline-flex items-center gap-1.5 rounded-md border border-[#d8cfb8] bg-[#fbf8ef] px-3 py-1.5 text-[11px] font-semibold uppercase tracking-wider text-[#1c1917] transition-colors hover:bg-[#efe9d8]"
            >
              Next <ChevronRight className="h-3.5 w-3.5" />
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Lesson data resolution ─────────────────────────────────────────────────
// Lessons may come from the static CURRICULUM (offline preview) or from the
// API as real DB rows (UUIDs). Both are normalized to ResolvedLesson.
type ResolvedLesson = {
  id: string;
  title: string;
  type: 'video' | 'pdf';
  asset: string;
  free: boolean;
  duration?: string;
};

type ApiLesson = {
  id: string;
  module_name?: string | null;
  name: string;
  lesson_type?: string;
  resources?: Array<{ type?: string; title?: string; path?: string }> | null;
  is_premium?: boolean;
};

type StructureLesson = {
  id: string;
  name: string;
  lesson_type: string;
  order: number;
  estimated_minutes?: number;
  xp_reward?: number;
  is_premium?: boolean;
  resources?: Array<{ type?: string; title?: string; path?: string }> | null;
};

type StructureModule = { id: string; name: string; order: number; lessons: StructureLesson[] };
type StructureCourse = { name: string; modules: StructureModule[] };

function lessonTypeOf(l: { lesson_type?: string; resources?: Array<{ path?: string }> | null }): 'video' | 'pdf' {
  const path = l.resources?.[0]?.path?.toLowerCase() ?? '';
  if (path) return path.endsWith('.mp4') ? 'video' : 'pdf';
  return l.lesson_type === 'video' ? 'video' : 'pdf';
}

// ─── Playback clock (m:ss, or h:mm:ss past an hour) ──────────────────────────
function fmtTime(total: number): string {
  if (!isFinite(total) || total < 0) return '0:00';
  const s = Math.floor(total % 60);
  const m = Math.floor((total / 60) % 60);
  const h = Math.floor(total / 3600);
  const mm = h > 0 ? String(m).padStart(2, '0') : String(m);
  const ss = String(s).padStart(2, '0');
  return h > 0 ? `${h}:${mm}:${ss}` : `${mm}:${ss}`;
}

// ─── Page ─────────────────────────────────────────────────────────────────────
export default function LessonPlayerPage() {
  const { id, lessonId } = useParams<{ id: string; lessonId: string }>();
  const { getToken } = useAuth();
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [token, setToken] = useState<string | null>(null);
  const [completed, setCompleted] = useState(false);
  const [markingComplete, setMarkingComplete] = useState(false);
  const [completeError, setCompleteError] = useState<string | null>(null);
  const [apiLesson, setApiLesson] = useState<ApiLesson | null>(null);
  const [apiCourse, setApiCourse] = useState<StructureCourse | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [loadingApi, setLoadingApi] = useState(false);
  const [progressEntry, setProgressEntry] = useState<ProgressEntry | null>(null);
  const [watchPct, setWatchPct] = useState(0);
  const watchPctRef = useRef(0);
  const [videoSrc, setVideoSrc] = useState<string | null>(null);
  const [blocked, setBlocked] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    // Clerk session tokens are short-lived (~60 s). The api client refreshes
    // them on 401, but a token embedded in an <iframe src> must be minted at
    // mount time — the storage copy is usually already expired by then.
    // Prefer the live Clerk token; fall back to the storage token when Clerk
    // is unavailable (e.g. token-provider edge cases during first load).
    void (async () => {
      try {
        const fresh = await getToken();
        if (!cancelled && fresh) {
          setToken(fresh);
          return;
        }
      } catch {
        // fall through to the storage token
      }
      if (!cancelled) setToken(getTokens().access);
    })();
    return () => {
      cancelled = true;
    };
  }, [getToken]);

  useEffect(() => {
    setCompleted(false);
    setCompleteError(null);
    setWatchPct(0);
    watchPctRef.current = 0;
    setProgressEntry(null);
  }, [lessonId]);

  const staticCourse = CURRICULUM[id];
  const isStatic = !!staticCourse && staticCourse.lessons.some((l) => l.id === lessonId);

  // Non-static lesson (real DB UUID): load lesson + course structure from the API.
  useEffect(() => {
    if (isStatic) return;
    setLoadError(null);
    setBlocked(null);
    if (!UUID_RE.test(lessonId)) {
      setLoadError('Lesson not found.');
      return;
    }
    let cancelled = false;
    setLoadingApi(true);
    (async () => {
      try {
        const res = await api.get<{ data: ApiLesson }>(`/lessons/${lessonId}`);
        if (!cancelled) setApiLesson(res.data);
      } catch (err) {
        if (!cancelled) {
          if (err instanceof ApiError && err.isAuthError()) {
            setBlocked(err.message || 'You do not have access to this content.');
          } else {
            setLoadError(err instanceof Error ? err.message : 'Failed to load lesson');
          }
        }
      }
      try {
        const res = await api.get<{ data: StructureCourse }>(`/courses/${id}`);
        if (!cancelled) setApiCourse(res.data);
      } catch {
        // Sidebar structure is optional — lesson content may already be loaded.
      } finally {
        if (!cancelled) setLoadingApi(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [id, lessonId, isStatic]);

  // Saved progress: completion state, resume position, watch baseline.
  useEffect(() => {
    if (!token || !UUID_RE.test(lessonId)) return;
    let cancelled = false;
    (async () => {
      try {
        const res = await api.get<{ data: ProgressEntry[] }>('/progress/lessons');
        if (cancelled) return;
        const entry = res.data.find((e) => e.lesson_id === lessonId);
        if (entry) {
          setProgressEntry(entry);
          if (entry.status === 'completed') setCompleted(true);
          const pct = entry.progress_percentage ?? 0;
          setWatchPct(pct);
          watchPctRef.current = pct;
        }
      } catch {
        // Not logged in / offline — play without a saved baseline.
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [lessonId, token]);

  // Resolve the lesson list from whichever source is available.
  const lessons: ResolvedLesson[] = isStatic && staticCourse
    ? staticCourse.lessons
    : apiCourse
      ? apiCourse.modules.flatMap((m) => m.lessons.map((l) => ({
          id: l.id,
          title: l.name,
          type: lessonTypeOf(l),
          asset: l.resources?.[0]?.path ?? '',
          free: !l.is_premium,
        })))
      : apiLesson
        ? [{
            id: apiLesson.id,
            title: apiLesson.name,
            type: lessonTypeOf(apiLesson),
            asset: apiLesson.resources?.[0]?.path ?? '',
            free: !apiLesson.is_premium,
          }]
        : [];

  const courseTitle = isStatic && staticCourse
    ? staticCourse.title
    : apiCourse?.name ?? apiLesson?.module_name ?? 'Course';

  const lessonIndex = lessons.findIndex((l) => l.id === lessonId);
  const lesson = lessonIndex >= 0 ? lessons[lessonIndex] : lessons[0];

  // Signed media URL for <video>: /stream answers 307 → signed R2 URL, and
  // browsers block no-cors <video> loads that redirect cross-origin (Chrome:
  // ERR_BLOCKED_BY_ORB), so the player must load the R2 bytes directly. The
  // presign endpoint runs the same authorization check as /stream.
  useEffect(() => {
    if (!lesson?.asset || lesson.type !== 'video' || lesson.asset.startsWith('gdrive://')) {
      setVideoSrc(null);
      return;
    }
    let cancelled = false;
    setVideoSrc(null);
    setBlocked(null);
    (async () => {
      try {
        const res = await api.get<{ data: { url: string; expires_in: number } }>(
          `/media/presign?path=${encodeURIComponent(lesson.asset)}`,
          { cache: 'no-store' },
        );
        if (!cancelled) setVideoSrc(res.data.url);
      } catch (err) {
        if (!cancelled && err instanceof ApiError && err.isAuthError()) {
          // Premium/authorization failure — the stream fallback would fail the
          // same check, so fail friendly instead of loading a dud URL.
          setBlocked(err.message || 'You do not have access to this content.');
          return;
        }
        // Fallback to the legacy streaming URL: served without a redirect
        // where R2 is not configured (local dev), so no ORB issue there.
        if (!cancelled) {
          setVideoSrc(`${API_URL}/media/stream?path=${encodeURIComponent(lesson.asset)}${token ? `&token=${token}` : ''}`);
        }
      }
    })();
    return () => { cancelled = true; };
  }, [lesson?.id, lesson?.asset, lesson?.type, token]);

  const prevLesson = lessonIndex > 0 ? lessons[lessonIndex - 1] : null;
  const nextLesson = lessonIndex >= 0 && lessonIndex < lessons.length - 1 ? lessons[lessonIndex + 1] : null;

  if (blocked) {
    return <BlockedContentNotice id={id} message={blocked} />;
  }

  if (loadError) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-4 px-4 text-center text-cyber-muted">
        <BookOpen className="h-10 w-10" />
        <p>{loadError}</p>
        <Link href={`/courses/${id}`} className="terminal-button px-4 py-2 text-sm">Back to Course</Link>
      </div>
    );
  }

  if (!lesson) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-4 text-cyber-muted">
        <BookOpen className="h-10 w-10" />
        <p>{loadingApi ? 'Loading lesson…' : 'Lesson not found.'}</p>
        <Link href={`/courses/${id}`} className="terminal-button px-4 py-2 text-sm">Back to Course</Link>
      </div>
    );
  }

  const isVideo = lesson.type === 'video';
  const needsWatchGate = isVideo && !completed && watchPct < COMPLETION_MIN_PERCENT;

  const handleWatchPercent = (pct: number) => {
    watchPctRef.current = pct;
    setWatchPct(pct);
  };

  const markComplete = async () => {
    if (markingComplete || completed) return;
    if (needsWatchGate) {
      setCompleteError(
        `Watch at least ${COMPLETION_MIN_PERCENT}% of the video to complete it (${Math.floor(watchPctRef.current)}% watched).`,
      );
      return;
    }
    setMarkingComplete(true);
    setCompleteError(null);
    if (!UUID_RE.test(lessonId)) {
      // Preview content that has no database lesson yet — mark locally.
      setCompleted(true);
      setMarkingComplete(false);
      return;
    }
    if (!token) {
      setCompleteError('Log in to save your progress.');
      setMarkingComplete(false);
      return;
    }
    try {
      // Server verifies the reported percentage against the ≥90% rule
      // (and its own stored telemetry) before accepting "completed".
      await api.post(`/progress/lessons/${lessonId}`, {
        status: 'completed',
        progress_percentage: isVideo ? Math.min(100, Math.round(watchPctRef.current)) : 100,
        time_spent_seconds: 0,
      });
      setCompleted(true);
      setWatchPct(100);
      watchPctRef.current = 100;
    } catch (err) {
      if (err instanceof Error && 'status' in err && (err as { status?: number }).status === 404) {
        setCompleted(true);
      } else {
        setCompleteError(err instanceof Error ? err.message : 'Failed to mark lesson complete');
      }
    } finally {
      setMarkingComplete(false);
    }
  };

  // Build authenticated streaming URL (or pass through gdrive link)
  const assetUrl = lesson.asset.startsWith('gdrive://')
    ? lesson.asset
    : `${API_URL}/media/stream?path=${encodeURIComponent(lesson.asset)}${token ? `&token=${token}` : ''}`;

  return (
    <div className="flex flex-col min-h-screen bg-cyber-bg">
      <Navbar />

      {/* Breadcrumb (also emits BreadcrumbList JSON-LD) */}
      <Breadcrumbs
        items={[
          { label: 'Learning Paths', href: '/courses' },
          { label: courseTitle, href: `/courses/${id}` },
          { label: lesson.title },
        ]}
      />

      <div className="flex flex-1 overflow-hidden">
        {/* Main content */}
        <main className={`flex-1 overflow-y-auto ${sidebarOpen ? 'lg:mr-80' : ''} transition-all`}>
          <div className="mx-auto max-w-4xl px-4 py-6">

            {/* Player */}
            <div className="mb-6">
              {isVideo ? (
                videoSrc ? (
                  <VideoPlayer
                    key={lesson.id}
                    src={videoSrc}
                    title={lesson.title}
                    lessonId={lesson.id}
                    canTrack={!!token}
                    initialResume={progressEntry?.last_position?.seconds ?? 0}
                    baselineWatched={progressEntry?.last_position?.watched_seconds ?? null}
                    baselinePct={progressEntry?.progress_percentage ?? 0}
                    onWatchPercent={handleWatchPercent}
                  />
                ) : (
                  <div className="flex aspect-video w-full items-center justify-center rounded-lg bg-black text-sm text-cyber-muted">
                    Preparing secure video stream…
                  </div>
                )
              ) : (
                <PdfViewer key={lesson.id} src={assetUrl} title={lesson.title} />
              )}
            </div>

            {/* Lesson title + nav */}
            <div className="flex items-start justify-between gap-4 mb-6">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  {isVideo
                    ? <Play className="h-4 w-4 text-cyber-primary" />
                    : <FileText className="h-4 w-4 text-cyber-secondary" />}
                  <span className="text-xs text-cyber-muted uppercase tracking-wider">
                    {isVideo ? 'Video Lesson' : 'PDF Module'}
                  </span>
                  {lesson.free && (
                    <span className="text-xs px-1.5 py-0.5 rounded bg-cyber-success/10 text-cyber-success font-semibold">Free Preview</span>
                  )}
                </div>
                <h1 className="text-xl font-bold text-cyber-text">{lesson.title}</h1>
                <p className="text-sm text-cyber-muted mt-1">{courseTitle}</p>
              </div>
              <div className="flex flex-col items-end gap-2 shrink-0">
                <button
                  onClick={() => setSidebarOpen(!sidebarOpen)}
                  className="hidden lg:flex items-center gap-1.5 text-xs text-cyber-muted hover:text-cyber-primary border border-cyber-border rounded px-2 py-1.5 transition-colors shrink-0"
                >
                  <List className="h-3.5 w-3.5" />
                  {sidebarOpen ? 'Hide' : 'Show'} Lessons
                </button>
                {completed ? (
                  <span className="flex items-center gap-1.5 text-xs font-semibold text-cyber-success px-2 py-1.5 rounded border border-cyber-success/40 bg-cyber-success/10">
                    <CheckCircle className="h-3.5 w-3.5" />
                    Completed
                  </span>
                ) : (
                  <button
                    onClick={() => void markComplete()}
                    disabled={markingComplete || needsWatchGate}
                    title={needsWatchGate ? `Watch at least ${COMPLETION_MIN_PERCENT}% of the video (${Math.floor(watchPct)}% watched)` : undefined}
                    className="terminal-button flex items-center gap-1.5 px-3 py-1.5 text-xs disabled:opacity-50"
                  >
                    <CheckCircle className="h-3.5 w-3.5" />
                    {markingComplete
                      ? 'Saving…'
                      : needsWatchGate
                        ? `Watch ${Math.floor(watchPct)}% / ${COMPLETION_MIN_PERCENT}%`
                        : 'Mark Complete'}
                  </button>
                )}
                {completeError && (
                  <span className="text-xs text-cyber-danger max-w-[220px] text-right">{completeError}</span>
                )}
              </div>
            </div>

            {/* Prev / Next */}
            <div className="flex justify-between gap-4">
              {prevLesson ? (
                <Link
                  href={`/courses/${id}/lessons/${prevLesson.id}`}
                  className="flex items-center gap-2 text-sm text-cyber-muted hover:text-cyber-primary terminal-card px-4 py-3 flex-1 transition-colors"
                >
                  <ChevronLeft className="h-4 w-4 shrink-0" />
                  <span className="truncate">{prevLesson.title}</span>
                </Link>
              ) : <div />}
              {nextLesson ? (
                <Link
                  href={`/courses/${id}/lessons/${nextLesson.id}`}
                  className="flex items-center gap-2 text-sm text-cyber-muted hover:text-cyber-primary terminal-card px-4 py-3 flex-1 justify-end text-right transition-colors"
                >
                  <span className="truncate">{nextLesson.title}</span>
                  <ChevronRight className="h-4 w-4 shrink-0" />
                </Link>
              ) : <div />}
            </div>
          </div>
        </main>

        {/* Sidebar — lesson list */}
        {sidebarOpen && (
          <aside className="hidden lg:flex flex-col fixed right-0 top-0 bottom-0 w-80 border-l border-cyber-border bg-cyber-surface overflow-y-auto z-40 pt-16">
            <div className="flex items-center justify-between px-4 py-3 border-b border-cyber-border">
              <span className="text-sm font-semibold text-cyber-text">Course Content</span>
              <button onClick={() => setSidebarOpen(false)} className="text-cyber-muted hover:text-cyber-primary">
                <X className="h-4 w-4" />
              </button>
            </div>
            <div className="p-2">
              {lessons.map((l, i) => {
                const isCurrent = l.id === lesson.id;
                return (
                  <Link
                    key={l.id}
                    href={`/courses/${id}/lessons/${l.id}`}
                    className={`flex items-start gap-3 px-3 py-2.5 rounded-md mb-0.5 text-sm transition-colors ${
                      isCurrent
                        ? 'bg-cyber-primary/10 text-cyber-primary border border-cyber-primary/20'
                        : 'text-cyber-muted hover:bg-cyber-border/40 hover:text-cyber-text'
                    }`}
                  >
                    <span className="text-xs font-mono mt-0.5 w-5 shrink-0 text-right">
                      {String(i + 1).padStart(2, '0')}
                    </span>
                    {l.type === 'video'
                      ? <Play className="h-3.5 w-3.5 mt-0.5 shrink-0" />
                      : <FileText className="h-3.5 w-3.5 mt-0.5 shrink-0" />}
                    <span className="flex-1 leading-snug">{l.title}</span>
                    {!l.free && !isCurrent && <Lock className="h-3 w-3 mt-1 shrink-0 opacity-40" />}
                    {isCurrent && <CheckCircle className="h-3.5 w-3.5 mt-0.5 shrink-0" />}
                  </Link>
                );
              })}
            </div>
          </aside>
        )}
      </div>
    </div>
  );
}
