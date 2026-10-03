'use client';

import { useState, useRef, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import {
  Play, Pause, Volume2, VolumeX, Maximize, ChevronLeft,
  ChevronRight, BookOpen, FileText, Lock, CheckCircle,
  List, X, Download,
} from 'lucide-react';
import Navbar from '@/components/Navbar';
import { API_URL, api, getTokens } from '@/lib/api';
import { CURRICULUM } from '@/lib/curriculum';

// ─── Static curriculum data (mirrors courses/page.tsx) ───────────────────────

// ─── Video Player ─────────────────────────────────────────────────────────────
function VideoPlayer({ src, title }: { src: string; title: string }) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [playing, setPlaying] = useState(false);
  const [muted, setMuted] = useState(false);
  const [progress, setProgress] = useState(0);

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

  const onTimeUpdate = () => {
    if (!videoRef.current) return;
    const pct = (videoRef.current.currentTime / videoRef.current.duration) * 100;
    setProgress(isNaN(pct) ? 0 : pct);
  };

  const seek = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!videoRef.current) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const pct = (e.clientX - rect.left) / rect.width;
    videoRef.current.currentTime = pct * videoRef.current.duration;
  };

  return (
    <div className="relative w-full bg-black rounded-lg overflow-hidden group">
      <video
        ref={videoRef}
        src={src}
        className="w-full aspect-video"
        controlsList="nodownload noremoteplayback"
        disablePictureInPicture
        onContextMenu={(e) => e.preventDefault()}
        onTimeUpdate={onTimeUpdate}
        onPlay={() => setPlaying(true)}
        onPause={() => setPlaying(false)}
        onEnded={() => setPlaying(false)}
        title={title}
      />
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
          <button onClick={toggle} className="text-white hover:text-cyber-primary transition-colors">
            {playing ? <Pause className="h-5 w-5" /> : <Play className="h-5 w-5" />}
          </button>
          <button
            onClick={() => { setMuted(!muted); if (videoRef.current) videoRef.current.muted = !muted; }}
            className="text-white hover:text-cyber-primary transition-colors"
          >
            {muted ? <VolumeX className="h-4 w-4" /> : <Volume2 className="h-4 w-4" />}
          </button>
          <span className="text-white/60 text-xs flex-1 truncate">{title}</span>
          <button
            onClick={() => videoRef.current?.requestFullscreen()}
            className="text-white hover:text-cyber-primary transition-colors"
          >
            <Maximize className="h-4 w-4" />
          </button>
        </div>
      </div>
      {/* Big play button */}
      {!playing && (
        <button
          onClick={toggle}
          className="absolute inset-0 flex items-center justify-center bg-black/30 hover:bg-black/40 transition-colors"
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

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

function lessonTypeOf(l: { lesson_type?: string; resources?: Array<{ path?: string }> | null }): 'video' | 'pdf' {
  const path = l.resources?.[0]?.path?.toLowerCase() ?? '';
  if (path) return path.endsWith('.mp4') ? 'video' : 'pdf';
  return l.lesson_type === 'video' ? 'video' : 'pdf';
}

// ─── Page ─────────────────────────────────────────────────────────────────────
export default function LessonPlayerPage() {
  const { id, lessonId } = useParams<{ id: string; lessonId: string }>();
  const router = useRouter();
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [token, setToken] = useState<string | null>(null);
  const [completed, setCompleted] = useState(false);
  const [markingComplete, setMarkingComplete] = useState(false);
  const [completeError, setCompleteError] = useState<string | null>(null);
  const [apiLesson, setApiLesson] = useState<ApiLesson | null>(null);
  const [apiCourse, setApiCourse] = useState<StructureCourse | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [loadingApi, setLoadingApi] = useState(false);

  useEffect(() => {
    setToken(getTokens().access);
  }, []);

  useEffect(() => {
    setCompleted(false);
    setCompleteError(null);
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

  const markComplete = async () => {
    if (markingComplete || completed) return;
    setMarkingComplete(true);
    setCompleteError(null);
    if (!UUID_RE.test(lessonId)) {
      // Preview content that has no database lesson yet — mark locally.
      setCompleted(true);
      setMarkingComplete(false);
      return;
    }
    try {
      await api.post(`/progress/lessons/${lessonId}`, { status: 'completed' });
      setCompleted(true);
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
              {lesson.type === 'video' ? (
                <VideoPlayer src={assetUrl} title={lesson.title} />
              ) : (
                <PdfViewer src={assetUrl} title={lesson.title} />
              )}
            </div>

            {/* Lesson title + nav */}
            <div className="flex items-start justify-between gap-4 mb-6">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  {lesson.type === 'video'
                    ? <Play className="h-4 w-4 text-cyber-primary" />
                    : <FileText className="h-4 w-4 text-cyber-secondary" />}
                  <span className="text-xs text-cyber-muted uppercase tracking-wider">
                    {lesson.type === 'video' ? 'Video Lesson' : 'PDF Module'}
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
                    disabled={markingComplete}
                    className="terminal-button flex items-center gap-1.5 px-3 py-1.5 text-xs disabled:opacity-50"
                  >
                    <CheckCircle className="h-3.5 w-3.5" />
                    {markingComplete ? 'Saving…' : 'Mark Complete'}
                  </button>
                )}
                {completeError && (
                  <span className="text-xs text-cyber-danger">{completeError}</span>
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
