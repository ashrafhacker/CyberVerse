import { sectionMeta } from '@/lib/section-meta';

// Server-component layout: exists to attach unique SEO metadata to the
// client page it wraps (client pages cannot export metadata themselves).
export const metadata = sectionMeta(
  'Threat Intel Feed',
  'Live-style threat intelligence feed for training — indicators, TTPs and MITRE ATT&CK mapping.',
  'threat-intel',
);

export default function SectionLayout({ children }: { children: React.ReactNode }) {
  return children;
}
