'use client';

import { useState, useRef, useEffect } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import {
  Play, Pause, Volume2, VolumeX, Maximize, ChevronLeft,
  ChevronRight, BookOpen, FileText, Lock, CheckCircle,
  List, X, Loader2, RefreshCw,
} from 'lucide-react';
import Navbar from '@/components/Navbar';
import { API_URL, api, getTokens } from '@/lib/api';
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
      if (pos > 5 && dur > 0 && pos < dur - 8) v.currentTime = pos;
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
        onPlay={() => { wasPlayingRef.current = true; setPlaying(true); }}
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

// ─── PDF Viewer ───────────────────────────────────────────────────────────────
function PdfViewer({ src, title }: { src: string; title: string }) {
  return (
    <div className="w-full rounded-lg overflow-hidden border border-cyber-border">
      <div className="flex items-center justify-between px-4 py-2 bg-cyber-surface border-b border-cyber-border">
        <div className="flex items-center gap-2">
          <FileText className="h-4 w-4 text-cyber-secondary" />
          <span className="text-sm font-medium text-cyber-text truncate max-w-sm">{title}</span>
        </div>
        <span className="text-xs text-cyber-muted">View only</span>
      </div>
      <iframe
        src={`${src}#toolbar=0&navpanes=0&view=FitH`}
        className="w-full h-[75vh]"
        title={title}
        onContextMenu={(e) => e.preventDefault()}
      />
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

// ─── Page ─────────────────────────────────────────────────────────────────────
export default function LessonPlayerPage() {
  const { id, lessonId } = useParams<{ id: string; lessonId: string }>();
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

  useEffect(() => {
    setToken(getTokens().access);
  }, []);

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
        if (!cancelled) setLoadError(err instanceof Error ? err.message : 'Failed to load lesson');
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
  const prevLesson = lessonIndex > 0 ? lessons[lessonIndex - 1] : null;
  const nextLesson = lessonIndex >= 0 && lessonIndex < lessons.length - 1 ? lessons[lessonIndex + 1] : null;

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

      {/* Breadcrumb */}
      <div className="border-b border-cyber-border bg-cyber-surface/50">
        <div className="mx-auto max-w-screen-2xl px-4 py-2 flex items-center gap-2 text-xs text-cyber-muted">
          <Link href="/courses" className="hover:text-cyber-primary transition-colors">Learning Paths</Link>
          <ChevronRight className="h-3 w-3" />
          <Link href={`/courses/${id}`} className="hover:text-cyber-primary transition-colors truncate max-w-[200px]">{courseTitle}</Link>
          <ChevronRight className="h-3 w-3" />
          <span className="text-cyber-text truncate max-w-[200px]">{lesson.title}</span>
        </div>
      </div>

      <div className="flex flex-1 overflow-hidden">
        {/* Main content */}
        <main className={`flex-1 overflow-y-auto ${sidebarOpen ? 'lg:mr-80' : ''} transition-all`}>
          <div className="mx-auto max-w-4xl px-4 py-6">

            {/* Player */}
            <div className="mb-6">
              {isVideo ? (
                <VideoPlayer
                  key={lesson.id}
                  src={assetUrl}
                  title={lesson.title}
                  lessonId={lesson.id}
                  canTrack={!!token}
                  initialResume={progressEntry?.last_position?.seconds ?? 0}
                  baselineWatched={progressEntry?.last_position?.watched_seconds ?? null}
                  baselinePct={progressEntry?.progress_percentage ?? 0}
                  onWatchPercent={handleWatchPercent}
                />
              ) : (
                <PdfViewer src={assetUrl} title={lesson.title} />
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
