import Link from 'next/link';
import { ChevronRight } from 'lucide-react';

export interface Crumb {
  label: string;
  href?: string;
}

const BASE = process.env.NEXT_PUBLIC_SITE_URL ?? 'https://cyberverse.io';

/**
 * Accessible breadcrumb trail with matching BreadcrumbList JSON-LD.
 * Last item has no href (current page). Used on course, lesson, and lab
 * pages; keep every public deep link passing through here.
 */
export default function Breadcrumbs({ items }: { items: Crumb[] }) {
  const jsonLd = {
    '@context': 'https://schema.org',
    '@type': 'BreadcrumbList',
    itemListElement: items.map((c, i) => ({
      '@type': 'ListItem',
      position: i + 1,
      name: c.label,
      ...(c.href ? { item: `${BASE}${c.href}` } : {}),
    })),
  };

  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />
      <nav aria-label="Breadcrumb" className="border-b border-cyber-border bg-cyber-surface/50">
        <ol className="mx-auto flex max-w-screen-2xl items-center gap-2 px-4 py-2 text-xs text-cyber-muted">
          {items.map((c, i) => (
            <li key={`${c.label}-${i}`} className="flex min-w-0 items-center gap-2">
              {i > 0 && <ChevronRight className="h-3 w-3 shrink-0" aria-hidden />}
              {c.href ? (
                <Link href={c.href} className="truncate transition-colors hover:text-cyber-primary">
                  {c.label}
                </Link>
              ) : (
                <span className="truncate text-cyber-text" aria-current="page">
                  {c.label}
                </span>
              )}
            </li>
          ))}
        </ol>
      </nav>
    </>
  );
}
