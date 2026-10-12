import type { Metadata } from 'next';
import {
  Red_Hat_Display,
  Inter,
  Inter_Tight,
  Rethink_Sans,
  Instrument_Sans,
  Instrument_Serif,
  Tillana,
  Geist,
  Urbanist,
  JetBrains_Mono,
} from 'next/font/google';
import { AuthProvider } from '@/lib/auth';
import './globals.css';

const redHatDisplay = Red_Hat_Display({
  subsets: ['latin'],
  weight: ['400', '500', '600', '700'],
  variable: '--font-red-hat-display',
  display: 'swap',
});

const inter = Inter({
  subsets: ['latin'],
  weight: ['400', '500', '600', '700'],
  variable: '--font-inter',
  display: 'swap',
});

const interTight = Inter_Tight({
  subsets: ['latin'],
  weight: ['400', '500', '600', '700'],
  variable: '--font-inter-tight',
  display: 'swap',
});

const rethinkSans = Rethink_Sans({
  subsets: ['latin'],
  weight: ['400', '500', '600', '700'],
  variable: '--font-rethink-sans',
  display: 'swap',
});

const instrumentSans = Instrument_Sans({
  subsets: ['latin'],
  weight: ['400', '500', '600', '700'],
  variable: '--font-instrument-sans',
  display: 'swap',
});

const instrumentSerif = Instrument_Serif({
  subsets: ['latin'],
  weight: ['400'],
  style: ['normal', 'italic'],
  variable: '--font-instrument-serif',
  display: 'swap',
});

const tillana = Tillana({
  subsets: ['latin'],
  weight: ['400', '500', '600', '700'],
  variable: '--font-tillana',
  display: 'swap',
});

const geist = Geist({
  subsets: ['latin'],
  weight: ['400', '500', '600', '700'],
  variable: '--font-geist',
  display: 'swap',
});

const urbanist = Urbanist({
  subsets: ['latin'],
  weight: ['400', '500', '600', '700'],
  variable: '--font-urbanist',
  display: 'swap',
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ['latin'],
  weight: ['400', '500', '700'],
  variable: '--font-jetbrains-mono',
  display: 'swap',
});

const fontVariables = [
  redHatDisplay.variable,
  inter.variable,
  interTight.variable,
  rethinkSans.variable,
  instrumentSans.variable,
  instrumentSerif.variable,
  tillana.variable,
  geist.variable,
  urbanist.variable,
  jetbrainsMono.variable,
].join(' ');

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
    <html lang="en" className={`dark ${fontVariables}`} suppressHydrationWarning>
      <head>
        <link rel="preconnect" href="https://api.cesium.com" crossOrigin="anonymous" />
        <link rel="preconnect" href="https://assets.cesium.com" crossOrigin="anonymous" />
        <link rel="dns-prefetch" href="https://api.cesium.com" />
        <link rel="dns-prefetch" href="https://assets.cesium.com" />
        {/* Fonts are self-hosted via `next/font` (see font variables above) so
            they never block first paint and require no external Google Fonts
            request. */}
      </head>
      <body suppressHydrationWarning>
        <AuthProvider>
          {children}
        </AuthProvider>
      </body>
    </html>
  );
}

