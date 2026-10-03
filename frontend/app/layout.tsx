import type { Metadata } from 'next';
import { AuthProvider } from '@/lib/auth';
import './globals.css';

export const metadata: Metadata = {
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
    icon: '/favicon.svg',
    shortcut: '/favicon.svg',
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark" suppressHydrationWarning>
      <head>
        <link rel="preconnect" href="https://api.cesium.com" crossOrigin="anonymous" />
        <link rel="preconnect" href="https://assets.cesium.com" crossOrigin="anonymous" />
        <link rel="dns-prefetch" href="https://api.cesium.com" />
        <link rel="dns-prefetch" href="https://assets.cesium.com" />
        {/* Fonts: async (media="print" → "all" on load) so they never block
            first paint — previously two render-blocking @imports in globals.css.
            Single combined request; JetBrains Mono added (referenced by the
            design system but never loaded before). */}
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          rel="stylesheet"
          href="https://fonts.googleapis.com/css2?family=Red+Hat+Display:wght@400;500;600;700&family=Inter:wght@400;500;600;700&family=Inter+Tight:wght@400;500;600;700&family=Rethink+Sans:wght@400;500;600;700&family=Instrument+Sans:wght@400;500;600;700&family=Instrument+Serif:ital@0;1&family=Tillana:wght@400;500;600;700&family=Geist:wght@400;500;600;700&family=Urbanist:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;700&display=swap"
          media="print"
          onLoad={(e) => { e.currentTarget.media = 'all'; }}
        />
        <noscript>
          <link
            rel="stylesheet"
            href="https://fonts.googleapis.com/css2?family=Red+Hat+Display:wght@400;500;600;700&family=Inter:wght@400;500;600;700&family=Inter+Tight:wght@400;500;600;700&family=Rethink+Sans:wght@400;500;600;700&family=Instrument+Sans:wght@400;500;600;700&family=Instrument+Serif:ital@0;1&family=Tillana:wght@400;500;600;700&family=Geist:wght@400;500;600;700&family=Urbanist:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;700&display=swap"
          />
        </noscript>
      </head>
      <body suppressHydrationWarning>
        <AuthProvider>
          {children}
        </AuthProvider>
      </body>
    </html>
  );
}

