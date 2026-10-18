import type { MetadataRoute } from 'next';

const BASE = process.env.NEXT_PUBLIC_SITE_URL ?? 'https://cyberverse.io';

// Static public routes. Auth-gated app surfaces (dashboard/admin/profile)
// are intentionally excluded — they are also disallowed in robots.txt.
const ROUTES: { path: string; changeFrequency: 'daily' | 'weekly' | 'monthly'; priority: number }[] = [
  { path: '', changeFrequency: 'daily', priority: 1 },
  { path: 'courses', changeFrequency: 'daily', priority: 0.9 },
  { path: 'labs', changeFrequency: 'daily', priority: 0.9 },
  { path: 'missions', changeFrequency: 'weekly', priority: 0.8 },
  { path: 'game', changeFrequency: 'weekly', priority: 0.8 },
  { path: 'global-arena', changeFrequency: 'weekly', priority: 0.7 },
  { path: 'external-labs', changeFrequency: 'monthly', priority: 0.6 },
  { path: 'tools', changeFrequency: 'weekly', priority: 0.7 },
  { path: 'library', changeFrequency: 'weekly', priority: 0.7 },
  { path: 'leaderboard', changeFrequency: 'daily', priority: 0.6 },
  { path: 'certificates', changeFrequency: 'monthly', priority: 0.5 },
  { path: 'threat-intel', changeFrequency: 'weekly', priority: 0.5 },
  { path: 'contact', changeFrequency: 'monthly', priority: 0.4 },
];

export default function sitemap(): MetadataRoute.Sitemap {
  const now = new Date();
  return ROUTES.map((r) => ({
    url: r.path ? `${BASE}/${r.path}` : BASE,
    lastModified: now,
    changeFrequency: r.changeFrequency,
    priority: r.priority,
  }));
}
