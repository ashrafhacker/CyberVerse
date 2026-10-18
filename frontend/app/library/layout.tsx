import { sectionMeta } from '@/lib/section-meta';

// Server-component layout: exists to attach unique SEO metadata to the
// client page it wraps (client pages cannot export metadata themselves).
export const metadata = sectionMeta(
  'Learning Library',
  'Curated cybersecurity reading library — guides, cheat sheets and references for students.',
  'library',
);

export default function SectionLayout({ children }: { children: React.ReactNode }) {
  return children;
}
