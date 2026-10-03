'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { Swords, CheckCircle2, Lock, Play, FileText } from 'lucide-react';
import Navbar from '@/components/Navbar';
import { TerminalCard, LoadingScreen } from '@/components/TerminalCard';
import { useAuth } from '@/lib/auth';
import { CURRICULUM } from '@/lib/curriculum';
import { api } from '@/lib/api';

interface CourseDetail {
  id: string;
  name: string;
  description: string;
  modules: Array<{
    id: string;
    name: string;
    description: string;
    order: number;
    estimated_minutes: number;
    resource_type?: string | null;
    resource_label?: string | null;
    lessons: Array<{
      id: string;
      name: string;
      lesson_type: string;
      order: number;
      estimated_minutes: number;
      xp_reward: number;
      is_premium: boolean;
      resources?: Array<{ type?: string; title?: string; path?: string }>;
    }>;
  }>;
  slug: string;
  difficulty: string;
  estimated_hours: number;
  is_premium: boolean;
  tags: string[];
  learning_objectives: string[];
  is_enrolled: boolean;
}

/**
 * Build a full CourseDetail from the static CURRICULUM when the API has no
 * modules for a course (content not seeded yet) or the API is unreachable.
 * Keeps the page usable with real play/open buttons instead of an empty shell.
 */
function buildStaticCourse(id: string): CourseDetail | null {
  const staticCourse = CURRICULUM[id];
  if (!staticCourse) return null;
  return {
    id,
    name: staticCourse.title,
    description: 'Offline curriculum preview. Enroll to unlock full progress tracking.',
    slug: staticCourse.courseSlug,
    difficulty: 'beginner',
    estimated_hours: Math.max(1, Math.round(staticCourse.lessons.reduce((acc, l) => {
      const m = l.duration && /^\d+:\d+$/.test(l.duration) ? l.duration.split(':').map(Number) : null;
      return acc + (m ? m[0] : 10);
    }, 0) / 60)),
    is_premium: false,
    tags: [],
    learning_objectives: [],
    is_enrolled: false,
    modules: [
      {
        id: 'static-mod',
        name: 'Curriculum',
        description: 'Lessons',
        order: 1,
        estimated_minutes: 0,
        lessons: staticCourse.lessons.map((l, ix) => ({
          id: l.id,
          name: l.title,
          lesson_type: l.type,
          order: ix + 1,
          estimated_minutes: (() => {
            const m = l.duration && /^\d+:\d+$/.test(l.duration) ? l.duration.split(':').map(Number) : null;
            return m ? m[0] : 10;
          })(),
          xp_reward: l.type === 'video' ? 50 : 25,
          is_premium: !l.free,
          resources: [{ type: l.type, title: l.title, path: l.asset }],
        })),
      },
    ],
  };
}

/** Does this lesson open a PDF? */
function isPdfLesson(lesson: CourseDetail['modules'][number]['lessons'][number]): boolean {
  if (lesson.lesson_type === 'pdf') return true;
  return (lesson.resources?.[0]?.path ?? '').toLowerCase().endsWith('.pdf');
}

export default function CourseDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { user, loading } = useAuth();
  const [data, setData] = useState<CourseDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [enrolling, setEnrolling] = useState(false);

  useEffect(() => {
    if (!id) return;
    api
      .get<{ data: CourseDetail }>(`/courses/${id}`)
      .then((res) => {
        const course = res.data;
        if (!course.modules?.length) {
          // API returned the course but no modules yet — fall back to the
          // static curriculum so the page still shows playable content.
          const fb = buildStaticCourse(id);
          if (fb) {
            setData({ ...course, modules: fb.modules });
            return;
          }
        }
        setData(course);
      })
      .catch((err) => {
        const fb = buildStaticCourse(id);
        if (fb) {
          setData(fb);
        } else {
          setError(err instanceof Error ? err.message : 'Failed to load course');
        }
      });
  }, [id]);

  const enroll = async () => {
    if (!id) return;
    if (!user) { window.location.href = `/login?redirect=/courses/${id}`; return; }
    setEnrolling(true);
    try {
      if (data?.is_premium && (user?.role === 'guest' || user?.role === 'student')) {
        const res = await api.get<{ data: Array<{ id: string; slug?: string; name: string }> }>('/premium/plans');
        const plans = res?.data ?? [];
        const beginner = plans.find((p) => /beginner/i.test(p.name) || /beginner/i.test(p.slug ?? '')) ?? plans[0];
        if (!beginner) throw new Error('No premium plans available');
        const checkout = await api.post<{ data: { checkout_url: string } }>('/premium/checkout', { plan_id: beginner.id });
        if (checkout?.data?.checkout_url) {
          window.location.href = checkout.data.checkout_url;
          return;
        }
      }

      await api.post(`/courses/${id}/enroll`);
      setData((d) => (d ? { ...d, is_enrolled: true } : d));
      // Free course: jump straight into the first lesson after enrolling.
      const first = data?.modules.flatMap((m) => m.lessons)[0];
      if (first && !data?.is_premium) {
        window.location.href = `/courses/${id}/lessons/${first.id}`;
        return;
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Enrollment or checkout failed';
      if (msg.includes('Authentication failed') || (err as { status?: number })?.status === 401) {
        window.location.href = `/login?redirect=/courses/${id}`;
        return;
      }
      setError(msg);
    } finally {
      setEnrolling(false);
    }
  };

  if (loading) return <LoadingScreen />;

  // First actionable lesson across all modules — used by the hero CTA so a
  // button ALWAYS renders (never an empty hero).
  const firstLesson = data ? data.modules.flatMap((m) => m.lessons)[0] : undefined;

  return (
    <>
      <Navbar />
      <main className="mx-auto max-w-5xl px-6 py-8">
        {error && <div className="mb-6 text-cyber-danger">{error}</div>}

        {data && (
          <>
            <TerminalCard className="mb-8" title={`course://${data.slug}`}>
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div className="max-w-xl">
                  <h1 className="text-2xl font-bold">{data.name}</h1>
                  <p className="mt-2 text-sm text-cyber-muted">{data.description}</p>
                  <div className="mt-3 flex flex-wrap gap-2 text-xs">
                    <span className="rounded bg-cyber-border px-2 py-0.5 text-cyber-muted">{data.difficulty}</span>
                    <span className="rounded bg-cyber-border px-2 py-0.5 text-cyber-muted">~{data.estimated_hours}h</span>
                    {data.is_premium && (
                      <span className="rounded bg-cyber-warning/20 px-2 py-0.5 text-cyber-warning">premium</span>
                    )}
                    {data.tags.map((tag) => (
                      <span key={tag} className="rounded bg-cyber-border px-2 py-0.5 text-cyber-muted">{tag}</span>
                    ))}
                  </div>
                </div>
                {!data.is_enrolled ? (
                  <button
                    onClick={enroll}
                    disabled={enrolling}
                    className="terminal-button inline-flex items-center gap-2"
                  >
                    <Play className="h-3.5 w-3.5" />
                    {enrolling
                      ? 'Processing...'
                      : data.is_premium
                        ? (user?.role === 'guest' || user?.role === 'student') ? 'Enroll — ₹99' : 'Enroll Now'
                        : 'Start Learning'}
                  </button>
                ) : firstLesson ? (
                  <Link
                    href={`/courses/${id}/lessons/${firstLesson.id}`}
                    className="terminal-button inline-flex items-center gap-2"
                  >
                    <Play className="h-3.5 w-3.5" />
                    Continue Course
                  </Link>
                ) : (
                  <span className="terminal-button inline-flex items-center gap-2 opacity-60" aria-disabled="true">
                    <Play className="h-3.5 w-3.5" />
                    Syllabus loading…
                  </span>
                )}
              </div>
              {data.learning_objectives.length > 0 && (
                <div className="mt-6 border-t border-cyber-border pt-4">
                  <h2 className="mb-2 text-sm font-semibold text-cyber-muted">You will learn</h2>
                  <ul className="list-inside list-disc space-y-1 text-sm">
                    {data.learning_objectives.map((obj) => (
                      <li key={obj}>{obj}</li>
                    ))}
                  </ul>
                </div>
              )}
            </TerminalCard>

            <div className="space-y-6">
              {data.modules.map((mod) => (
                <TerminalCard key={mod.id} title={`module_${mod.order}_${mod.name.toLowerCase().replace(/\s+/g, '_')}`}>
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <h2 className="font-semibold">{mod.name}</h2>
                      <p className="mt-1 text-sm text-cyber-muted">{mod.description}</p>
                      {mod.resource_label && (
                        <span className="mt-2 inline-flex items-center gap-1.5 rounded bg-cyber-secondary/10 px-2 py-0.5 font-mono text-xs text-cyber-secondary">
                          <FileText className="h-3 w-3" /> {mod.resource_label}
                        </span>
                      )}
                    </div>
                    {mod.lessons[0] && (
                      <Link
                        href={`/courses/${id}/lessons/${mod.lessons[0].id}`}
                        className="terminal-button inline-flex shrink-0 items-center gap-1.5 px-3 py-1.5 text-xs"
                      >
                        {isPdfLesson(mod.lessons[0])
                          ? <FileText className="h-3.5 w-3.5" />
                          : <Play className="h-3.5 w-3.5" />}
                        {isPdfLesson(mod.lessons[0]) ? 'Open PDF' : 'Play'}
                      </Link>
                    )}
                  </div>
                  <ul className="mt-3 space-y-1">
                    {mod.lessons.map((lesson) => (
                      <li key={lesson.id}>
                        <a
                          href={`/courses/${id}/lessons/${lesson.id}`}
                          className="flex w-full items-center justify-between rounded-md px-3 py-2 text-left text-sm transition-colors hover:bg-cyber-primary/10 hover:text-cyber-primary"
                        >
                          <span className="flex items-center gap-2">
                            {isPdfLesson(lesson)
                              ? <span className="text-cyber-secondary">📄</span>
                              : <span className="text-cyber-primary">▶</span>}
                            {lesson.order}. {lesson.name}
                            {lesson.is_premium && (
                              <span className="rounded bg-cyber-warning/20 px-1.5 py-0.5 text-xs text-cyber-warning">premium</span>
                            )}
                          </span>
                          <span className="font-mono text-xs text-cyber-muted">
                            {lesson.estimated_minutes}m · +{lesson.xp_reward} XP
                          </span>
                        </a>
                      </li>
                    ))}
                    {mod.lessons.length === 0 && (
                      <li className="px-3 py-2 text-sm text-cyber-muted">
                        Content coming soon.
                      </li>
                    )}
                  </ul>
                </TerminalCard>
              ))}
            </div>
          </>
        )}

        {!data && !error && (
          <div className="flex items-center justify-center py-16 text-cyber-muted">
            <Swords className="mr-2 h-5 w-5" /> Loading course content...
          </div>
        )}
      </main>
    </>
  );
}
