import { sectionMeta } from '@/lib/section-meta';

// Server-component layout: exists to attach unique SEO metadata to the
// client page it wraps (client pages cannot export metadata themselves).
export const metadata = sectionMeta(
  'Cyber Labs',
  'Launch isolated cyber range lab sessions — web exploitation, network defense and forensics labs in a safe sandbox.',
  'labs',
);

export default function SectionLayout({ children }: { children: React.ReactNode }) {
  return children;
}
