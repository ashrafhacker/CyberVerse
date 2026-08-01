'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import Navbar from '@/components/Navbar';
import { TerminalCard, LoadingScreen } from '@/components/TerminalCard';
import { useAuth } from '@/lib/auth';
import { api } from '@/lib/api';
import type { Course, LearningPath } from '@/lib/types';

interface CourseCardProps {
  course: Course;
}

function CourseCard({ course }: CourseCardProps) {
  return (
    <Link
      href={`/courses/${course.id}`}
      className="block rounded-md border border-cyber-border px-4 py-3 transition-colors hover:border-cyber-primary"
    >
      <div className="flex items-center justify-between gap-2">
        <span className="font-medium">{course.name}</span>
        {course.is_premium && (
          <span className="rounded bg-cyber-warning/20 px-2 py-0.5 text-xs text-cyber-warning">premium</span>
        )}
      </div>
      <p className="mt-1 text-sm text-cyber-muted line-clamp-2">{course.description}</p>
      <div className="mt-2 flex flex-wrap gap-2 text-xs">
        <span className="rounded bg-cyber-border px-2 py-0.5 text-cyber-muted">{course.difficulty}</span>
        <span className="rounded bg-cyber-border px-2 py-0.5 text-cyber-muted">~{course.estimated_hours}h</span>
        {course.tags.slice(0, 3).map((tag) => (
          <span key={tag} className="rounded bg-cyber-border px-2 py-0.5 text-cyber-muted">{tag}</span>
        ))}
      </div>
    </Link>
  );
}

export default function CoursesPage() {
  const { user, loading } = useAuth();
  const [paths, setPaths] = useState<LearningPath[]>([]);
  const [allCourses, setAllCourses] = useState<Course[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!user) return;
    Promise.all([
      api.get<LearningPath[]>('/courses/learning-paths'),
      api.get<{ data: { items: Course[] } }>('/courses'),
    ])
      .then(([p, c]) => {
        setPaths(p);
        setAllCourses(c.data.items);
      })
      .catch((err) => setError(err instanceof Error ? err.message : 'Failed to load courses'));
  }, [user]);

  if (loading || !user) return <LoadingScreen />;

  return (
    <>
      <Navbar />
      <main className="mx-auto max-w-7xl px-6 py-8">
        <div className="mb-8">
          <h1 className="text-2xl font-bold">Learning <span className="text-cyber-primary">Paths</span></h1>
          <p className="mt-1 text-sm text-cyber-muted">Pick a path and start earning XP.</p>
        </div>

        {error && <div className="mb-6 text-cyber-danger">{error}</div>}

        {paths.map((path) => (
          <TerminalCard key={path.id} title={`path://${path.name.toLowerCase().replace(/\s+/g, '-')}`} className="mb-8">
            <div className="mb-4">
              <h2 className="text-lg font-bold">{path.name}</h2>
              <p className="mt-1 text-sm text-cyber-muted">{path.description}</p>
              <div className="mt-2 flex gap-2 text-xs">
                <span className="rounded bg-cyber-border px-2 py-0.5 text-cyber-muted">{path.difficulty}</span>
                {path.is_premium && (
                  <span className="rounded bg-cyber-warning/20 px-2 py-0.5 text-cyber-warning">premium</span>
                )}
              </div>
            </div>
            <div className="space-y-2">
              {allCourses.filter((c) => c.difficulty === path.difficulty).length === 0 && (
                <p className="text-sm text-cyber-muted">Courses for this path appear here once published.</p>
              )}
              {allCourses
                .filter((c) => c.difficulty === path.difficulty)
                .map((course) => (
                  <CourseCard key={course.id} course={course} />
                ))}
            </div>
          </TerminalCard>
        ))}

        {paths.length === 0 && (
          <TerminalCard title="all_courses.sh">
            {allCourses.length === 0 ? (
              <p className="text-sm text-cyber-muted">No courses published yet. Check back soon.</p>
            ) : (
              <div className="space-y-2">
                {allCourses.map((course) => (
                  <CourseCard key={course.id} course={course} />
                ))}
              </div>
            )}
          </TerminalCard>
        )}
      </main>
    </>
  );
}
