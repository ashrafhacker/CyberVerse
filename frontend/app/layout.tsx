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
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body>
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
