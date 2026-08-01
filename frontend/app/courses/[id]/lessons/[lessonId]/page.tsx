'use client';

import { useState, useRef } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import {
  Play, Pause, Volume2, VolumeX, Maximize, ChevronLeft,
  ChevronRight, BookOpen, FileText, Lock, CheckCircle,
  List, X, Download,
} from 'lucide-react';
import Navbar from '@/components/Navbar';
import { API_URL } from '@/lib/api';

// ─── Static curriculum data (mirrors courses/page.tsx) ───────────────────────
const CURRICULUM: Record<string, {
  title: string;
  courseSlug: string;
  lessons: Array<{ id: string; title: string; type: 'video' | 'pdf'; asset: string; free: boolean; duration?: string }>;
}> = {
  'course-ceh-pdf-modules': {
    title: 'CEH v12 — Official Module PDFs',
    courseSlug: 'ceh-v12/pdfs',
    lessons: Array.from({ length: 20 }, (_, i) => ({
      id: `mod-ceh-${String(i + 1).padStart(2, '0')}`,
      title: `Module ${String(i + 1).padStart(2, '0')} — ${[
        'Introduction to Ethical Hacking', 'Footprinting and Reconnaissance',
        'Scanning Networks', 'Enumeration', 'Vulnerability Analysis',
        'System Hacking', 'Malware Threats', 'Sniffing', 'Social Engineering',
        'Denial-of-Service', 'Session Hijacking', 'Evading IDS, Firewalls & Honeypots',
        'Hacking Web Servers', 'Hacking Web Applications', 'SQL Injection',
        'Hacking Wireless Networks', 'Hacking Mobile Platforms',
        'IoT and OT Hacking', 'Cloud Computing', 'Cryptography',
      ][i]}`,
      type: 'pdf' as const,
      asset: `ceh-v12/pdfs/CEH v12 - Module${String(i + 1).padStart(2, '0')}.pdf`,
      free: i === 0,
    })),
  },
  'course-ceh-system-network': {
    title: 'CEH v12 — System & Network Security',
    courseSlug: 'ceh-v12-specialization/system-and-network-security',
    lessons: [
      { id: 'les-sn-01', title: 'System Hacking Introduction', type: 'video', asset: 'ceh-v12-specialization/system-and-network-security/01_system-security-and-malware-threats/02_1-2-system-penetration-testing/01_system-hacking.mp4', free: true, duration: '7:00' },
      { id: 'les-sn-02', title: 'Password Cracking Techniques', type: 'video', asset: 'ceh-v12-specialization/system-and-network-security/01_system-security-and-malware-threats/02_1-2-system-penetration-testing/02_password-cracking-techniques.mp4', free: false, duration: '8:00' },
      { id: 'les-sn-03', title: 'Types of Password Attacks', type: 'video', asset: 'ceh-v12-specialization/system-and-network-security/01_system-security-and-malware-threats/02_1-2-system-penetration-testing/03_types-of-password-attacks.mp4', free: false, duration: '6:00' },
      { id: 'les-sn-04', title: 'Microsoft Authentication', type: 'video', asset: 'ceh-v12-specialization/system-and-network-security/01_system-security-and-malware-threats/02_1-2-system-penetration-testing/04_microsoft-authentication.mp4', free: false, duration: '7:30' },
      { id: 'les-sn-05', title: 'Password Salting', type: 'video', asset: 'ceh-v12-specialization/system-and-network-security/01_system-security-and-malware-threats/02_1-2-system-penetration-testing/05_password-salting.mp4', free: false, duration: '5:00' },
      { id: 'les-sn-06', title: 'Demo: Cracking Passwords with VMs', type: 'video', asset: 'ceh-v12-specialization/system-and-network-security/01_system-security-and-malware-threats/02_1-2-system-penetration-testing/06_password-salting.mp4', free: false, duration: '10:00' },
      { id: 'les-ml-01', title: 'Malware Threats Overview', type: 'video', asset: 'ceh-v12-specialization/system-and-network-security/01_system-security-and-malware-threats/03_1-3-malware-threats/01_malware-threats.mp4', free: true, duration: '8:00' },
      { id: 'les-ml-02', title: 'Ways of Malware Propagation', type: 'video', asset: 'ceh-v12-specialization/system-and-network-security/01_system-security-and-malware-threats/03_1-3-malware-threats/02_ways-of-malware-propagation.mp4', free: false, duration: '6:30' },
      { id: 'les-ml-03', title: 'What is a Virus?', type: 'video', asset: 'ceh-v12-specialization/system-and-network-security/01_system-security-and-malware-threats/03_1-3-malware-threats/03_what-is-a-virus.mp4', free: false, duration: '6:00' },
      { id: 'les-ml-07', title: 'What is a Rootkit?', type: 'video', asset: 'ceh-v12-specialization/system-and-network-security/01_system-security-and-malware-threats/03_1-3-malware-threats/07_what-is-rootkit.mp4', free: false, duration: '6:30' },
      { id: 'les-ml-10', title: 'Trojan and Trojan Horse', type: 'video', asset: 'ceh-v12-specialization/system-and-network-security/01_system-security-and-malware-threats/03_1-3-malware-threats/10_trojan-and-trojan-horse.mp4', free: false, duration: '7:00' },
      { id: 'les-ids-01', title: 'Firewall, Evading IDS & Honeypots', type: 'video', asset: 'ceh-v12-specialization/system-and-network-security/02_network-security-and-evasion-techniques/01_2-1-evading-ids-firewalls-and-honeypots/01_firewall-evading-ids-and-honeypots.mp4', free: true, duration: '8:00' },
      { id: 'les-ids-02', title: 'Types of Firewalls', type: 'video', asset: 'ceh-v12-specialization/system-and-network-security/02_network-security-and-evasion-techniques/01_2-1-evading-ids-firewalls-and-honeypots/02_types-of-firewalls.mp4', free: false, duration: '6:30' },
      { id: 'les-ids-07', title: 'Intrusion Detection Tool: Snort', type: 'video', asset: 'ceh-v12-specialization/system-and-network-security/02_network-security-and-evasion-techniques/01_2-1-evading-ids-firewalls-and-honeypots/07_intrusion-detection-tool-snort.mp4', free: false, duration: '8:00' },
      { id: 'les-ids-08', title: 'What is a Honeypot?', type: 'video', asset: 'ceh-v12-specialization/system-and-network-security/02_network-security-and-evasion-techniques/01_2-1-evading-ids-firewalls-and-honeypots/08_what-is-honeypot.mp4', free: false, duration: '6:00' },
      { id: 'les-iot-01', title: 'IoT Hacking Introduction', type: 'video', asset: 'ceh-v12-specialization/system-and-network-security/02_network-security-and-evasion-techniques/02_2-2-iot-hacking/01_iot-hacking.mp4', free: true, duration: '7:00' },
      { id: 'les-iot-04', title: 'IoT Technologies and Protocols', type: 'video', asset: 'ceh-v12-specialization/system-and-network-security/02_network-security-and-evasion-techniques/02_2-2-iot-hacking/04_iot-technologies-and-protocols.mp4', free: false, duration: '8:05' },
      { id: 'les-iot-08', title: 'IoT Hacking Methodology', type: 'video', asset: 'ceh-v12-specialization/system-and-network-security/02_network-security-and-evasion-techniques/02_2-2-iot-hacking/08_iot-hacking-methodology.mp4', free: false, duration: '11:25' },
    ],
  },
  'course-burp-suite': {
    title: 'Burp Suite Live Practical',
    courseSlug: 'hands-on-hacking/burp-suite',
    lessons: [
      { id: 'les-burp-01', title: 'Install Burp Suite Pro for Free', type: 'video', asset: 'hands-on-hacking/burp-suite/1 -Install Burp Suite Pro for free.mp4', free: true, duration: '~103MB' },
      { id: 'les-burp-02', title: 'Configure Burp Suite with Firefox Proxy', type: 'video', asset: 'hands-on-hacking/burp-suite/2 -Configure Burp Suite with Firefox Proxy.mp4', free: false },
      { id: 'les-burp-03', title: 'OTP Bypass by Response Manipulation', type: 'video', asset: 'hands-on-hacking/burp-suite/3 -OTP Bypass by Response Manipulation.mp4', free: false },
      { id: 'les-burp-04', title: 'OTP Bypass by Bruteforcing', type: 'video', asset: 'hands-on-hacking/burp-suite/4 -OTP Bypass by Bruteforcing.mp4', free: false },
      { id: 'les-burp-05', title: 'Account Takeover by OTP Bypass', type: 'video', asset: 'hands-on-hacking/burp-suite/5 -Account Takeover by OTP Bypass.mp4', free: false },
      { id: 'les-burp-07', title: 'Account Takeover by IDOR', type: 'video', asset: 'hands-on-hacking/burp-suite/7 -Account Takeover by IDOR.mp4', free: false },
      { id: 'les-burp-09', title: 'Live Price Tampering Bugs on Websites', type: 'video', asset: 'hands-on-hacking/burp-suite/9 -Live Price Tampering Bugs on Websites.mp4', free: false },
      { id: 'les-burp-10', title: 'Automated Form Flooding with Burp', type: 'video', asset: 'hands-on-hacking/burp-suite/10 -Automated Form Flooding with Burp.mp4', free: false },
    ],
  },
  'course-http-debugger': {
    title: 'HTTP Debugger Pro Basics',
    courseSlug: 'hands-on-hacking/http-debugger',
    lessons: [
      { id: 'les-http-01', title: 'Installing HTTP Debugger Pro', type: 'video', asset: 'hands-on-hacking/http-debugger/1 -Installing HTTP Debugger Pro.mp4', free: true },
      { id: 'les-http-02', title: 'Using HTTP Debugger Pro Like a Pro', type: 'video', asset: 'hands-on-hacking/http-debugger/2 -Using HTTP Debugger Pro like a Pro.mp4', free: false },
      { id: 'les-http-03', title: 'Price Tampering with TamperDev', type: 'video', asset: 'hands-on-hacking/http-debugger/1 -Price Tampering with TamperDev.mp4', free: false },
    ],
  },
};

// ─── Video Player ─────────────────────────────────────────────────────────────
function VideoPlayer({ src, title }: { src: string; title: string }) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [playing, setPlaying] = useState(false);
  const [muted, setMuted] = useState(false);
  const [progress, setProgress] = useState(0);

  const toggle = () => {
    if (!videoRef.current) return;
    if (playing) { videoRef.current.pause(); } else { void videoRef.current.play(); }
    setPlaying(!playing);
  };

  const onTimeUpdate = () => {
    if (!videoRef.current) return;
    const pct = (videoRef.current.currentTime / videoRef.current.duration) * 100;
    setProgress(isNaN(pct) ? 0 : pct);
  };

  const seek = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!videoRef.current) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const pct = (e.clientX - rect.left) / rect.width;
    videoRef.current.currentTime = pct * videoRef.current.duration;
  };

  return (
    <div className="relative w-full bg-black rounded-lg overflow-hidden group">
      <video
        ref={videoRef}
        src={src}
        className="w-full aspect-video"
        onTimeUpdate={onTimeUpdate}
        onPlay={() => setPlaying(true)}
        onPause={() => setPlaying(false)}
        onEnded={() => setPlaying(false)}
        title={title}
      />
      {/* Controls overlay */}
      <div className="absolute bottom-0 inset-x-0 bg-gradient-to-t from-black/80 to-transparent p-3 opacity-0 group-hover:opacity-100 transition-opacity">
        {/* Progress bar */}
        <div
          className="w-full h-1.5 bg-white/20 rounded-full cursor-pointer mb-3"
          onClick={seek}
        >
          <div className="h-full bg-cyber-primary rounded-full transition-all" style={{ width: `${progress}%` }} />
        </div>
        <div className="flex items-center gap-3">
          <button onClick={toggle} className="text-white hover:text-cyber-primary transition-colors">
            {playing ? <Pause className="h-5 w-5" /> : <Play className="h-5 w-5" />}
          </button>
          <button
            onClick={() => { setMuted(!muted); if (videoRef.current) videoRef.current.muted = !muted; }}
            className="text-white hover:text-cyber-primary transition-colors"
          >
            {muted ? <VolumeX className="h-4 w-4" /> : <Volume2 className="h-4 w-4" />}
          </button>
          <span className="text-white/60 text-xs flex-1 truncate">{title}</span>
          <button
            onClick={() => videoRef.current?.requestFullscreen()}
            className="text-white hover:text-cyber-primary transition-colors"
          >
            <Maximize className="h-4 w-4" />
          </button>
        </div>
      </div>
      {/* Big play button */}
      {!playing && (
        <button
          onClick={toggle}
          className="absolute inset-0 flex items-center justify-center bg-black/30 hover:bg-black/40 transition-colors"
        >
          <div className="w-16 h-16 rounded-full bg-cyber-primary/90 flex items-center justify-center shadow-lg">
            <Play className="h-8 w-8 text-cyber-bg ml-1" />
          </div>
        </button>
      )}
    </div>
  );
}

// ─── PDF Viewer ───────────────────────────────────────────────────────────────
function PdfViewer({ src, title }: { src: string; title: string }) {
  return (
    <div className="w-full rounded-lg overflow-hidden border border-cyber-border">
      <div className="flex items-center justify-between px-4 py-2 bg-cyber-surface border-b border-cyber-border">
        <div className="flex items-center gap-2">
          <FileText className="h-4 w-4 text-cyber-secondary" />
          <span className="text-sm font-medium text-cyber-text truncate max-w-sm">{title}</span>
        </div>
        <a
          href={src}
          download
          className="flex items-center gap-1.5 text-xs text-cyber-muted hover:text-cyber-primary transition-colors"
        >
          <Download className="h-3.5 w-3.5" />
          Download PDF
        </a>
      </div>
      <iframe
        src={`${src}#toolbar=1&navpanes=1&view=FitH`}
        className="w-full h-[75vh]"
        title={title}
      />
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────
export default function LessonPlayerPage() {
  const { id, lessonId } = useParams<{ id: string; lessonId: string }>();
  const router = useRouter();
  const [sidebarOpen, setSidebarOpen] = useState(true);

  const course = CURRICULUM[id];
  if (!course) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-4 text-cyber-muted">
        <BookOpen className="h-10 w-10" />
        <p>Course not found.</p>
        <Link href="/courses" className="terminal-button px-4 py-2 text-sm">Back to Paths</Link>
      </div>
    );
  }

  const lessonIndex = course.lessons.findIndex(l => l.id === lessonId);
  const lesson = lessonIndex >= 0 ? course.lessons[lessonIndex] : course.lessons[0];
  const prevLesson = lessonIndex > 0 ? course.lessons[lessonIndex - 1] : null;
  const nextLesson = lessonIndex < course.lessons.length - 1 ? course.lessons[lessonIndex + 1] : null;

  // Build authenticated streaming URL
  const assetUrl = `${API_URL}/media/stream?path=${encodeURIComponent(lesson.asset)}`;

  return (
    <div className="flex flex-col min-h-screen bg-cyber-bg">
      <Navbar />

      {/* Breadcrumb */}
      <div className="border-b border-cyber-border bg-cyber-surface/50">
        <div className="mx-auto max-w-screen-2xl px-4 py-2 flex items-center gap-2 text-xs text-cyber-muted">
          <Link href="/courses" className="hover:text-cyber-primary transition-colors">Learning Paths</Link>
          <ChevronRight className="h-3 w-3" />
          <Link href={`/courses/${id}`} className="hover:text-cyber-primary transition-colors truncate max-w-[200px]">{course.title}</Link>
          <ChevronRight className="h-3 w-3" />
          <span className="text-cyber-text truncate max-w-[200px]">{lesson.title}</span>
        </div>
      </div>

      <div className="flex flex-1 overflow-hidden">
        {/* Main content */}
        <main className={`flex-1 overflow-y-auto ${sidebarOpen ? 'lg:mr-80' : ''} transition-all`}>
          <div className="mx-auto max-w-4xl px-4 py-6">

            {/* Player */}
            <div className="mb-6">
              {lesson.type === 'video' ? (
                <VideoPlayer src={assetUrl} title={lesson.title} />
              ) : (
                <PdfViewer src={assetUrl} title={lesson.title} />
              )}
            </div>

            {/* Lesson title + nav */}
            <div className="flex items-start justify-between gap-4 mb-6">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  {lesson.type === 'video'
                    ? <Play className="h-4 w-4 text-cyber-primary" />
                    : <FileText className="h-4 w-4 text-cyber-secondary" />}
                  <span className="text-xs text-cyber-muted uppercase tracking-wider">
                    {lesson.type === 'video' ? 'Video Lesson' : 'PDF Module'}
                  </span>
                  {lesson.free && (
                    <span className="text-xs px-1.5 py-0.5 rounded bg-cyber-success/10 text-cyber-success font-semibold">Free Preview</span>
                  )}
                </div>
                <h1 className="text-xl font-bold text-cyber-text">{lesson.title}</h1>
                <p className="text-sm text-cyber-muted mt-1">{course.title}</p>
              </div>
              <button
                onClick={() => setSidebarOpen(!sidebarOpen)}
                className="hidden lg:flex items-center gap-1.5 text-xs text-cyber-muted hover:text-cyber-primary border border-cyber-border rounded px-2 py-1.5 transition-colors shrink-0"
              >
                <List className="h-3.5 w-3.5" />
                {sidebarOpen ? 'Hide' : 'Show'} Lessons
              </button>
            </div>

            {/* Prev / Next */}
            <div className="flex justify-between gap-4">
              {prevLesson ? (
                <Link
                  href={`/courses/${id}/lessons/${prevLesson.id}`}
                  className="flex items-center gap-2 text-sm text-cyber-muted hover:text-cyber-primary terminal-card px-4 py-3 flex-1 transition-colors"
                >
                  <ChevronLeft className="h-4 w-4 shrink-0" />
                  <span className="truncate">{prevLesson.title}</span>
                </Link>
              ) : <div />}
              {nextLesson ? (
                <Link
                  href={`/courses/${id}/lessons/${nextLesson.id}`}
                  className="flex items-center gap-2 text-sm text-cyber-muted hover:text-cyber-primary terminal-card px-4 py-3 flex-1 justify-end text-right transition-colors"
                >
                  <span className="truncate">{nextLesson.title}</span>
                  <ChevronRight className="h-4 w-4 shrink-0" />
                </Link>
              ) : <div />}
            </div>
          </div>
        </main>

        {/* Sidebar — lesson list */}
        {sidebarOpen && (
          <aside className="hidden lg:flex flex-col fixed right-0 top-0 bottom-0 w-80 border-l border-cyber-border bg-cyber-surface overflow-y-auto z-40 pt-16">
            <div className="flex items-center justify-between px-4 py-3 border-b border-cyber-border">
              <span className="text-sm font-semibold text-cyber-text">Course Content</span>
              <button onClick={() => setSidebarOpen(false)} className="text-cyber-muted hover:text-cyber-primary">
                <X className="h-4 w-4" />
              </button>
            </div>
            <div className="p-2">
              {course.lessons.map((l, i) => {
                const isCurrent = l.id === lesson.id;
                return (
                  <Link
                    key={l.id}
                    href={`/courses/${id}/lessons/${l.id}`}
                    className={`flex items-start gap-3 px-3 py-2.5 rounded-md mb-0.5 text-sm transition-colors ${
                      isCurrent
                        ? 'bg-cyber-primary/10 text-cyber-primary border border-cyber-primary/20'
                        : 'text-cyber-muted hover:bg-cyber-border/40 hover:text-cyber-text'
                    }`}
                  >
                    <span className="text-xs font-mono mt-0.5 w-5 shrink-0 text-right">
                      {String(i + 1).padStart(2, '0')}
                    </span>
                    {l.type === 'video'
                      ? <Play className="h-3.5 w-3.5 mt-0.5 shrink-0" />
                      : <FileText className="h-3.5 w-3.5 mt-0.5 shrink-0" />}
                    <span className="flex-1 leading-snug">{l.title}</span>
                    {!l.free && !isCurrent && <Lock className="h-3 w-3 mt-1 shrink-0 opacity-40" />}
                    {isCurrent && <CheckCircle className="h-3.5 w-3.5 mt-0.5 shrink-0" />}
                  </Link>
                );
              })}
            </div>
          </aside>
        )}
      </div>
    </div>
  );
}
