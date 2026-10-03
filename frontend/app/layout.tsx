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
      </head>
      <body suppressHydrationWarning>
        <AuthProvider>
          {children}
        </AuthProvider>
      </body>
    </html>
  );
}

