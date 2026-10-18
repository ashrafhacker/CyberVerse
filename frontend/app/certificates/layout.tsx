import { sectionMeta } from '@/lib/section-meta';

// Server-component layout: exists to attach unique SEO metadata to the
// client page it wraps (client pages cannot export metadata themselves).
export const metadata = sectionMeta(
  'Certificates',
  'Earn verifiable CyberVerse certificates by completing courses and passing assessments.',
  'certificates',
);

export default function SectionLayout({ children }: { children: React.ReactNode }) {
  return children;
}
