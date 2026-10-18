import { sectionMeta } from '@/lib/section-meta';

// Server-component layout: exists to attach unique SEO metadata to the
// client page it wraps (client pages cannot export metadata themselves).
export const metadata = sectionMeta(
  'Global Arena',
  'Cross-player arena rankings and seasons for the CyberVerse community.',
  'global-arena',
);

export default function SectionLayout({ children }: { children: React.ReactNode }) {
  return children;
}
