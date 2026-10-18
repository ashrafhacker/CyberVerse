import { sectionMeta } from '@/lib/section-meta';

// Server-component layout: exists to attach unique SEO metadata to the
// client page it wraps (client pages cannot export metadata themselves).
export const metadata = sectionMeta(
  'External Labs',
  'Curated external practice platforms and labs recommended by CyberVerse.',
  'external-labs',
);

export default function SectionLayout({ children }: { children: React.ReactNode }) {
  return children;
}
