import { sectionMeta } from '@/lib/section-meta';

// Server-component layout: exists to attach unique SEO metadata to the
// client page it wraps (client pages cannot export metadata themselves).
export const metadata = sectionMeta(
  'Cyber Security Courses',
  'Hands-on cybersecurity courses: CEH v12 modules, ethical hacking, network defense and cryptography learning paths.',
  'courses',
);

export default function SectionLayout({ children }: { children: React.ReactNode }) {
  return children;
}
