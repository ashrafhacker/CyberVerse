'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { GraduationCap, FileText } from 'lucide-react';
import Navbar from '@/components/Navbar';
import { TerminalCard, LoadingScreen } from '@/components/TerminalCard';
import { useRequireAuth } from '@/lib/auth';
import { api } from '@/lib/api';
import type { UserRole } from '@/lib/types';

const INSTRUCTOR_ROLES: UserRole[] = ['instructor', 'administrator', 'developer', 'super_admin'];

interface InstructorStats {
  my_courses: number;
  total_enrollments: number;
  total_lessons: number;
  average_completion: number;
}

export default function InstructorPage() {
  const { user, loading } = useRequireAuth();
  const router = useRouter();
  const [stats, setStats] = useState<InstructorStats | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!user) return;
    if (!user.role || !INSTRUCTOR_ROLES.includes(user.role)) {
      router.replace('/dashboard');
      return;
    }
    api
      .get<{ data: InstructorStats }>('/instructor/stats')
      .then((res) => setStats(res.data))
      .catch((err) => setError(err instanceof Error ? err.message : 'Failed to load instructor stats'));
  }, [user, router]);

  if (loading || !user) return <LoadingScreen />;

  return (
    <>
      <Navbar />
      <main className="mx-auto max-w-7xl px-6 py-8">
        <div className="mb-8">
          <h1 className="flex items-center gap-2 text-2xl font-bold">
            <GraduationCap className="h-6 w-6 text-cyber-secondary" /> Instructor Studio
          </h1>
          <p className="mt-1 text-sm text-cyber-muted">
            Manage your courses, track enrollments, and author content.
          </p>
        </div>

        {error && <div className="mb-6 text-cyber-danger">{error}</div>}

        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <TerminalCard title="courses">
            <p className="text-xs uppercase tracking-wider text-cyber-muted">My courses</p>
            <p className="mt-2 font-mono text-3xl font-bold text-cyber-primary">{stats?.my_courses ?? 0}</p>
          </TerminalCard>
          <TerminalCard title="enrollments">
            <p className="text-xs uppercase tracking-wider text-cyber-muted">Total enrollments</p>
            <p className="mt-2 font-mono text-3xl font-bold text-cyber-success">{stats?.total_enrollments ?? 0}</p>
          </TerminalCard>
          <TerminalCard title="lessons">
            <p className="text-xs uppercase tracking-wider text-cyber-muted">Lessons authored</p>
            <p className="mt-2 font-mono text-3xl font-bold text-cyber-secondary">{stats?.total_lessons ?? 0}</p>
          </TerminalCard>
          <TerminalCard title="completion">
            <p className="text-xs uppercase tracking-wider text-cyber-muted">Avg. completion</p>
            <p className="mt-2 font-mono text-3xl font-bold text-cyber-warning">{stats?.average_completion ?? 0}%</p>
          </TerminalCard>
        </div>

        <TerminalCard title="content_management.md" className="mt-8">
          <div className="flex items-center gap-3">
            <FileText className="h-5 w-5 text-cyber-muted" />
            <div>
              <h2 className="font-semibold">Content authoring tools</h2>
              <p className="text-sm text-cyber-muted">
                Course and lesson editors are available through the instructor API endpoints:
                <span className="font-mono text-cyber-primary"> /api/v1/instructor/*</span>
              </p>
            </div>
          </div>
        </TerminalCard>
      </main>
    </>
  );
}
