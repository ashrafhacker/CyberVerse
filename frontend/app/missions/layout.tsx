import { sectionMeta } from '@/lib/section-meta';

// Server-component layout: exists to attach unique SEO metadata to the
// client page it wraps (client pages cannot export metadata themselves).
export const metadata = sectionMeta(
  'Daily Missions',
  'Daily cybersecurity missions and skill challenges that award XP, streaks and badges.',
  'missions',
);

export default function SectionLayout({ children }: { children: React.ReactNode }) {
  return children;
}
