import { sectionMeta } from '@/lib/section-meta';

// Server-component layout: exists to attach unique SEO metadata to the
// client page it wraps (client pages cannot export metadata themselves).
export const metadata = sectionMeta(
  'Security Tools',
  'Free in-browser cybersecurity tools: dorker, hash tools and reconnaissance utilities for learners.',
  'tools',
);

export default function SectionLayout({ children }: { children: React.ReactNode }) {
  return children;
}
