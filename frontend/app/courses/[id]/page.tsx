'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { Swords, CheckCircle2, Lock } from 'lucide-react';
import Navbar from '@/components/Navbar';
import { TerminalCard, LoadingScreen } from '@/components/TerminalCard';
import { useAuth } from '@/lib/auth';
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
    lessons: Array<{
      id: string;
      name: string;
      lesson_type: string;
      order: number;
      estimated_minutes: number;
      xp_reward: number;
      is_premium: boolean;
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

export default function CourseDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { user, loading } = useAuth();
  const [data, setData] = useState<CourseDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [enrolling, setEnrolling] = useState(false);

  useEffect(() => {
    if (!user || !id) return;
    api
      .get<{ data: CourseDetail }>(`/courses/${id}`)
      .then((res) => setData(res.data))
      .catch((err) => setError(err instanceof Error ? err.message : 'Failed to load course'));
  }, [user, id]);

  const enroll = async () => {
    if (!id) return;
    setEnrolling(true);
    try {
      await api.post(`/courses/${id}/enroll`);
      setData((d) => (d ? { ...d, is_enrolled: true } : d));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Enrollment failed');
    } finally {
      setEnrolling(false);
    }
  };

  if (loading || !user) return <LoadingScreen />;

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
                {!data.is_enrolled && (
                  <button onClick={enroll} disabled={enrolling} className="terminal-button">
                    {enrolling ? 'Enrolling...' : 'Enroll Now'}
                  </button>
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
                  <h2 className="mb-1 font-semibold">{mod.name}</h2>
                  <p className="mb-3 text-sm text-cyber-muted">{mod.description}</p>
                  <ul className="space-y-1">
                    {mod.lessons.map((lesson) => (
                      <li key={lesson.id}>
                        <a
                          href={`/courses/${id}/lessons/${lesson.id}`}
                          className="flex w-full items-center justify-between rounded-md px-3 py-2 text-left text-sm transition-colors hover:bg-cyber-primary/10 hover:text-cyber-primary"
                        >
                          <span className="flex items-center gap-2">
                            {lesson.lesson_type === 'pdf'
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
