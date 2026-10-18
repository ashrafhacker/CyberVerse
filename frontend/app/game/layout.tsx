import { sectionMeta } from '@/lib/section-meta';

// Server-component layout: exists to attach unique SEO metadata to the
// client page it wraps (client pages cannot export metadata themselves).
export const metadata = sectionMeta(
  'Cyber Game',
  'Play CyberVerse CTF challenges, tournaments and team battles to earn XP on the global leaderboard.',
  'game',
);

export default function SectionLayout({ children }: { children: React.ReactNode }) {
  return children;
}
