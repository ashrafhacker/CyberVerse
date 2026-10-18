import type { MetadataRoute } from 'next';

const BASE = process.env.NEXT_PUBLIC_SITE_URL ?? 'https://cyberverse.io';

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      {
        // Public marketing/learning pages are crawlable; every authenticated
        // or account-specific area is disallowed (they render client-side
        // behind auth and would only waste crawl budget / leak route names).
        userAgent: '*',
        allow: '/',
        disallow: ['/dashboard', '/admin', '/instructor', '/profile', '/api/'],
      },
    ],
    sitemap: `${BASE}/sitemap.xml`,
  };
}
