import type { Metadata } from 'next';

const BASE = process.env.NEXT_PUBLIC_SITE_URL ?? 'https://cyberverse.io';

/**
 * Per-section metadata helper. Route layout files call this so every public
 * page ships a unique <title>, meta description, Open Graph tags, and a
 * self-referencing canonical instead of inheriting the root values.
 */
export function sectionMeta(
  title: string,
  description: string,
  path: string,
  ogType: 'website' | 'article' = 'website',
): Metadata {
  const url = path ? `${BASE}/${path}` : BASE;
  return {
    title,
    description,
    alternates: { canonical: url },
    openGraph: {
      title: `${title} | CyberVerse`,
      description,
      url,
      siteName: 'CyberVerse',
      type: ogType,
      images: [{ url: '/og-image.png', width: 1200, height: 630, alt: `${title} — CyberVerse` }],
    },
    twitter: {
      card: 'summary_large_image',
      title: `${title} | CyberVerse`,
      description,
      images: ['/og-image.png'],
    },
  };
}
