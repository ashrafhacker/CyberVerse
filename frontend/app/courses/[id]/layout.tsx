import type { Metadata } from 'next';

const BASE = process.env.NEXT_PUBLIC_SITE_URL ?? 'https://cyberverse.io';
const BACKEND = process.env.BACKEND_URL ?? 'http://127.0.0.1:8000';

interface CoursePayload {
  name?: string;
  title?: string;
  description?: string;
  slug?: string;
  difficulty?: string;
  estimated_hours?: number;
  tags?: string[];
  learning_objectives?: string[];
}

async function fetchCourse(id: string): Promise<CoursePayload | null> {
  try {
    const res = await fetch(`${BACKEND}/api/v1/courses/${id}`, {
      // Course browse is public server-side (OptionalUser); no auth header.
      next: { revalidate: 300 },
      signal: AbortSignal.timeout(4000),
    });
    if (!res.ok) return null;
    const json = await res.json();
    return (json?.data ?? null) as CoursePayload | null;
  } catch {
    return null;
  }
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ id: string }>;
}): Promise<Metadata> {
  const { id } = await params;
  const course = await fetchCourse(id);
  const name = course?.name ?? course?.title ?? 'Course';
  const description =
    course?.description ??
    'Hands-on cybersecurity course on CyberVerse — learn by doing in a safe, legal sandbox.';
  const url = `${BASE}/courses/${id}`;
  return {
    title: name,
    description,
    alternates: { canonical: url },
    openGraph: {
      title: `${name} | CyberVerse`,
      description,
      url,
      siteName: 'CyberVerse',
      type: 'article',
      images: [{ url: '/og-image.png', width: 1200, height: 630, alt: `${name} — CyberVerse` }],
    },
    twitter: {
      card: 'summary_large_image',
      title: `${name} | CyberVerse`,
      description,
      images: ['/og-image.png'],
    },
  };
}

export default function CourseLayout({ children }: { children: React.ReactNode }) {
  return children;
}
