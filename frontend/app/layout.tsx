import type { Metadata } from 'next';
import { ClerkProvider } from '@clerk/nextjs';
import { AuthProvider } from '@/lib/auth';
import { ToastProvider } from '@/lib/toast';
import CookieConsent from '@/components/CookieConsent';
import AIMentorWidgetWrapper from './AIMentorWidgetWrapper';
import './globals.css';

// Clerk clerk-js bundle tuning.
//
// The browser fetches clerk-js from the instance origin derived from the
// publishable key (307 -> pinned version, Cloudflare, immutable cache). On a
// cold connection that first fetch pays DNS+TLS (~0.5s+) and a slow or blocked
// fetch trips Clerk's 15s scriptLoadTimeout with
// "ClerkRuntimeError: failed_to_load_clerk_js". Two mitigations:
//  1. <link rel="preconnect"> to the origin actually used (below), and
//  2. NEXT_PUBLIC_CLERK_JS_URL as an escape hatch to serve clerk-js from an
//     alternate CDN (e.g. https://cdn.jsdelivr.net/npm/@clerk/clerk-js@5/dist/clerk.browser.js)
//     when the instance domain is unreachable from a visitor's network.
//     next.config.mjs adds the override's origin to script-src at build time.
const clerkJsUrl = process.env.NEXT_PUBLIC_CLERK_JS_URL || undefined;
const clerkPreconnectOrigin = (() => {
  if (clerkJsUrl) {
    try {
      return new URL(clerkJsUrl).origin;
    } catch {
      // fall through to the instance origin below
    }
  }
  try {
    const b64 = (process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY ?? '').split('_')[2] ?? '';
    return b64 ? `https://${atob(b64).replace(/\$$/, '')}` : null;
  } catch {
    return null;
  }
})();

// NOTE (offline/fast builds): previously Inter + JetBrains Mono were loaded
// via next/font/google, which downloads woff2 from Google at build time and
// fails the whole production build when fonts.googleapis.com is unreachable.
// The design system only needs the --cv-font-sans / --cv-font-mono variables
// (see tailwind.config.ts + globals.css), so define them as system stacks.
// Zero network requests, zero build-time downloads.

// Self-hosted via next/font: Next downloads the woff2 at build time, subsets
// it, emits @font-face with a preload hint and serves it from our own origin.
//
// This replaced a render-path <link> to Google Fonts that requested TWELVE
// families (Inter, Inter Tight, Rethink Sans, Instrument Sans/Serif, Tillana,
// Geist, Urbanist, Red Hat Display, JetBrains Mono, ...). Measured cost of that
// link: 1,142 KB across 36 separate cross-origin requests plus a 55 KB CSS
// fetch — roughly 6x the entire homepage JS bundle, on every page.
//
// Every other --font-* token was defined but never referenced.
export const metadata: Metadata = {
  // Without an explicit base, Next falls back to http://localhost:3000 and
  // logs a warning on every build, and any absolute OG/Twitter URL resolves
  // to localhost for real visitors.
  metadataBase: new URL(process.env.NEXT_PUBLIC_SITE_URL ?? 'https://cyberverse.io'),
  title: {
    default: 'CyberVerse — Learn Cybersecurity by Doing',
    template: '%s | CyberVerse',
  },
  description:
    'Educational cybersecurity simulation platform. Learn ethical hacking, defense, and security fundamentals through hands-on missions in a safe, legal sandbox.',
  keywords: [
    'cybersecurity',
    'ethical hacking',
    'education',
    'cyber range',
    'penetration testing',
    'security training',
  ],
  openGraph: {
    title: 'CyberVerse',
    description: 'Learn cybersecurity by doing — safely, legally, and free.',
    type: 'website',
    images: [{ url: '/og-image.png', width: 1200, height: 630, alt: 'CyberVerse — Learn Cybersecurity By Doing' }],
  },
  twitter: {
    card: 'summary_large_image',
    title: 'CyberVerse',
    description: 'Learn cybersecurity by doing — safely, legally, and free.',
    images: ['/og-image.png'],
  },
  icons: {
    icon: [
      { url: '/favicon-32.png', sizes: '32x32', type: 'image/png' },
      { url: '/icon-192.png', sizes: '192x192', type: 'image/png' },
      { url: '/favicon.svg', type: 'image/svg+xml' },
    ],
    shortcut: '/favicon.svg',
    apple: '/apple-touch-icon.png',
  },
  manifest: '/site.webmanifest',
  alternates: {
    // Site-wide default canonical; individual route layouts override their
    // own path so section pages never inherit "/" as canonical.
    canonical: '/',
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html
      lang="en"
      className="dark"
      suppressHydrationWarning
      style={{
        ['--cv-font-sans' as string]:
          "Inter, ui-sans-serif, system-ui, -apple-system, 'Segoe UI', sans-serif",
        ['--cv-font-mono' as string]:
          "'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, monospace",
      }}
    >
      <head>
        {/* No Cesium preconnect here on purpose. Cesium is only used by the
            /globe route and is already code-split; preconnecting its CDN on
            every page cost an extra DNS lookup + TLS handshake for the ~95% of
            visitors who never open the globe.

            No fonts.gstatic.com prefetch either: fonts are self-hosted from
            our own origin via next/font, so that origin is never contacted. */}
        {clerkPreconnectOrigin && (
          <link rel="preconnect" href={clerkPreconnectOrigin} crossOrigin="" />
        )}
      </head>
      <body suppressHydrationWarning>
        <script
          type="application/ld+json"
          // WebSite schema: enables sitelinks search-box eligibility.
          dangerouslySetInnerHTML={{
            __html: JSON.stringify({
              '@context': 'https://schema.org',
              '@type': 'WebSite',
              name: 'CyberVerse',
              url: process.env.NEXT_PUBLIC_SITE_URL ?? 'https://cyberverse.io',
              potentialAction: {
                '@type': 'SearchAction',
                target: {
                  '@type': 'EntryPoint',
                  urlTemplate: `${process.env.NEXT_PUBLIC_SITE_URL ?? 'https://cyberverse.io'}/courses?q={search_term_string}`,
                },
                'query-input': 'required name=search_term_string',
              },
            }),
          }}
        />
        <ClerkProvider {...(clerkJsUrl ? { clerkJSUrl: clerkJsUrl } : {})}>
          <AuthProvider>
            <ToastProvider>
              {children}
              <CookieConsent />
              {/* AI mentor: client-only floating chat (no SSR, no hydration
                  cost) so it loads after the page is interactive. */}
              <AIMentorWidgetWrapper />
            </ToastProvider>
          </AuthProvider>
        </ClerkProvider>
      </body>
    </html>
  );
}