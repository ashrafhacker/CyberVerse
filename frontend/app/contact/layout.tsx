import { sectionMeta } from '@/lib/section-meta';

// Server-component layout: attaches unique SEO metadata to the client
// contact page (client pages cannot export metadata themselves).
export const metadata = sectionMeta(
  'Contact',
  'Contact the CyberVerse team about courses, institutional licensing, or partnerships. We usually reply within one business day.',
  'contact',
);

export default function ContactLayout({ children }: { children: React.ReactNode }) {
  return children;
}
