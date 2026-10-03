'use client';

import Link from 'next/link';
import { useState } from 'react';
import { Shield, Zap, Terminal, BookOpen, Play, Clock, ChevronDown, ChevronRight, Lock, CheckCircle, Star } from 'lucide-react';
import Navbar from '@/components/Navbar';

// ─── Static curriculum data (mirrors learning_paths_seed.sql) ───────────────

const DIFFICULTY_META: Record<string, { label: string; color: string; bg: string }> = {
  beginner:     { label: 'Beginner',     color: 'text-cyber-success', bg: 'bg-cyber-success/10' },
  intermediate: { label: 'Intermediate', color: 'text-cyber-warning', bg: 'bg-cyber-warning/10' },
  advanced:     { label: 'Advanced',     color: 'text-cyber-danger',  bg: 'bg-cyber-danger/10'  },
};

const PATHS = [
  {
    id: 'path-ceh-foundations',
    slug: 'ceh-foundations',
    icon: Shield,
    title: 'CEH Foundations',
    description: 'Master the core concepts of ethical hacking using the official CEH v12 curriculum. Covers networking, OS fundamentals, footprinting, scanning, enumeration, and system hacking.',
    difficulty: 'beginner',
    estimated_hours: 40,
    color: '#22d3ee',
    courses_count: 2,
    lessons_count: 74,
    courses: [
      {
        id: 'course-ceh-pdf-modules',
        title: 'CEH v12 — Official Module PDFs (20 Modules)',
        description: 'The complete 20-module CEH v12 official study guide covering all exam domains.',
        difficulty: 'beginner',
        estimated_hours: 40,
        tags: ['CEH', 'EC-Council', 'PDF', 'Theory'],
        modules: [
          { id: 'mod-ceh-01', title: 'Module 01 – Introduction to Ethical Hacking', type: 'pdf', lessons: 1, free: true },
          { id: 'mod-ceh-02', title: 'Module 02 – Footprinting and Reconnaissance', type: 'pdf', lessons: 1, free: false },
          { id: 'mod-ceh-03', title: 'Module 03 – Scanning Networks', type: 'pdf', lessons: 1, free: false },
          { id: 'mod-ceh-04', title: 'Module 04 – Enumeration', type: 'pdf', lessons: 1, free: false },
          { id: 'mod-ceh-05', title: 'Module 05 – Vulnerability Analysis', type: 'pdf', lessons: 1, free: false },
          { id: 'mod-ceh-06', title: 'Module 06 – System Hacking', type: 'pdf', lessons: 7, free: false },
          { id: 'mod-ceh-07', title: 'Module 07 – Malware Threats', type: 'pdf', lessons: 15, free: false },
          { id: 'mod-ceh-08', title: 'Module 08 – Sniffing', type: 'pdf', lessons: 5, free: false },
          { id: 'mod-ceh-09', title: 'Module 09 – Social Engineering', type: 'pdf', lessons: 1, free: false },
          { id: 'mod-ceh-10', title: 'Module 10 – Denial-of-Service', type: 'pdf', lessons: 1, free: false },
          { id: 'mod-ceh-11', title: 'Module 11 – Session Hijacking', type: 'pdf', lessons: 1, free: false },
          { id: 'mod-ceh-12', title: 'Module 12 – Evading IDS, Firewalls & Honeypots', type: 'pdf', lessons: 10, free: false },
          { id: 'mod-ceh-13', title: 'Module 13 – Hacking Web Servers', type: 'pdf', lessons: 1, free: false },
          { id: 'mod-ceh-14', title: 'Module 14 – Hacking Web Applications', type: 'pdf', lessons: 13, free: false },
          { id: 'mod-ceh-15', title: 'Module 15 – SQL Injection', type: 'pdf', lessons: 1, free: false },
          { id: 'mod-ceh-16', title: 'Module 16 – Hacking Wireless Networks', type: 'pdf', lessons: 1, free: false },
          { id: 'mod-ceh-17', title: 'Module 17 – Hacking Mobile Platforms', type: 'pdf', lessons: 1, free: false },
          { id: 'mod-ceh-18', title: 'Module 18 – IoT and OT Hacking', type: 'pdf', lessons: 8, free: false },
          { id: 'mod-ceh-19', title: 'Module 19 – Cloud Computing', type: 'pdf', lessons: 1, free: false },
          { id: 'mod-ceh-20', title: 'Module 20 – Cryptography', type: 'pdf', lessons: 1, free: false },
        ],
      },
    ],
  },
  {
    id: 'path-ceh-advanced',
    slug: 'ceh-advanced',
    icon: Zap,
    title: 'CEH Advanced Techniques',
    description: 'Deep dive into advanced ethical hacking: web app attacks, session hijacking, SQL injection, cryptography, cloud security, and IoT hacking — fully aligned to CEH v12.',
    difficulty: 'intermediate',
    estimated_hours: 60,
    color: '#a78bfa',
    courses_count: 2,
    lessons_count: 160,
    courses: [
      {
        id: 'course-ceh-system-network',
        title: 'CEH v12 — System & Network Security (Video)',
        description: 'System penetration testing, malware threats, network sniffing, ARP poisoning, session hijacking, and evading IDS / firewalls.',
        difficulty: 'intermediate',
        estimated_hours: 25,
        tags: ['CEH', 'System Hacking', 'Malware', 'Network'],
        modules: [
          { id: 'mod-sys-01', title: 'System Security & Penetration Testing', type: 'video', lessons: 6, free: true },
          { id: 'mod-sys-02', title: 'Malware Threats (Virus, Worm, Trojan, Rootkit)', type: 'video', lessons: 15, free: false },
          { id: 'mod-sys-03', title: 'Network Sniffing & ARP Poisoning', type: 'video', lessons: 5, free: false },
          { id: 'mod-sys-04', title: 'Evading IDS, Firewalls & Honeypots', type: 'video', lessons: 10, free: false },
          { id: 'mod-sys-05', title: 'IoT Hacking Deep Dive', type: 'video', lessons: 8, free: false },
        ],
      },
      {
        id: 'course-ceh-advanced-cybersec',
        title: 'CEH v12 — Advanced Cybersecurity (Video)',
        description: 'Web server attacks, web application hacking, SQL injection, wireless network hacking, mobile platform hacking, cloud computing security.',
        difficulty: 'advanced',
        estimated_hours: 35,
        tags: ['CEH', 'Web Hacking', 'SQL Injection', 'Wireless'],
        modules: [
          { id: 'mod-adv-01', title: 'Web Server Attacks & Exploitation', type: 'video', lessons: 8, free: true },
          { id: 'mod-adv-02', title: 'Web Application Hacking (OWASP Top 10)', type: 'video', lessons: 12, free: false },
          { id: 'mod-adv-03', title: 'SQL Injection — All Techniques', type: 'video', lessons: 10, free: false },
          { id: 'mod-adv-04', title: 'Wireless Network Hacking (WPA2, Evil Twin)', type: 'video', lessons: 9, free: false },
          { id: 'mod-adv-05', title: 'Mobile Platform Hacking (Android / iOS)', type: 'video', lessons: 7, free: false },
          { id: 'mod-adv-06', title: 'Cloud Security & Pen Testing', type: 'video', lessons: 8, free: false },
          { id: 'mod-adv-07', title: 'Cryptography & Quantum Security', type: 'video', lessons: 6, free: false },
        ],
      },
    ],
  },
  {
    id: 'path-hands-on-hacking',
    slug: 'hands-on-hacking',
    icon: Terminal,
    title: 'Hands-On Hacking (No Theory)',
    description: 'Pure practical hacking skills using real tools in sandboxed labs: Burp Suite Pro, HTTP Debugger, OTP bypass, IDOR, price tampering, and account takeover.',
    difficulty: 'advanced',
    estimated_hours: 25,
    color: '#34d399',
    courses_count: 2,
    lessons_count: 16,
    courses: [
      {
        id: 'course-burp-suite',
        title: 'Burp Suite Live Practical',
        description: 'Hands-on sessions with Burp Suite Pro: OTP bypass, account takeover via IDOR, automated form flooding, response manipulation.',
        difficulty: 'advanced',
        estimated_hours: 15,
        tags: ['Burp Suite', 'Web Hacking', 'OTP Bypass', 'IDOR'],
        modules: [
          { id: 'mod-burp-01', title: 'Setup: Install Burp Suite Pro & Firefox Proxy', type: 'video', lessons: 2, free: true },
          { id: 'mod-burp-02', title: 'OTP Bypass Techniques', type: 'video', lessons: 3, free: false },
          { id: 'mod-burp-03', title: 'Account Takeover Attacks', type: 'video', lessons: 3, free: false },
          { id: 'mod-burp-04', title: 'Price Tampering & Form Flooding', type: 'video', lessons: 2, free: false },
        ],
      },
      {
        id: 'course-http-debugger',
        title: 'HTTP Debugger Pro Basics',
        description: 'Learn to intercept and manipulate HTTP traffic with HTTP Debugger Pro, including API parameter tampering.',
        difficulty: 'intermediate',
        estimated_hours: 5,
        tags: ['HTTP', 'Traffic Interception', 'API Hacking'],
        modules: [
          { id: 'mod-http-01', title: 'Installing HTTP Debugger Pro', type: 'video', lessons: 1, free: true },
          { id: 'mod-http-02', title: 'Using HTTP Debugger Pro Like a Pro', type: 'video', lessons: 1, free: false },
          { id: 'mod-http-03', title: 'Price Tampering with TamperDev', type: 'video', lessons: 1, free: false },
        ],
      },
    ],
  },
];

// ─── Sub-components ──────────────────────────────────────────────────────────

function DifficultyBadge({ level }: { level: string }) {
  const m = DIFFICULTY_META[level] ?? DIFFICULTY_META.beginner;
  return (
    <span className={`rounded px-2 py-0.5 text-xs font-semibold ${m.bg} ${m.color}`}>
      {m.label}
    </span>
  );
}

function ModuleRow({ mod, index }: { mod: typeof PATHS[0]['courses'][0]['modules'][0]; index: number }) {
  return (
    <div className="flex items-center gap-3 py-2 px-3 rounded hover:bg-cyber-border/40 transition-colors group">
      <span className="text-xs font-mono text-cyber-muted w-5 text-right shrink-0">{String(index + 1).padStart(2, '0')}</span>
      {mod.type === 'video' ? (
        <Play className="h-3.5 w-3.5 text-cyber-primary shrink-0" />
      ) : (
        <BookOpen className="h-3.5 w-3.5 text-cyber-secondary shrink-0" />
      )}
      <span className="text-sm text-cyber-text flex-1">{mod.title}</span>
      <div className="flex items-center gap-2 shrink-0">
        <span className="text-xs text-cyber-muted">{mod.lessons} {mod.lessons === 1 ? 'lesson' : 'lessons'}</span>
        {mod.free ? (
          <span className="text-xs text-cyber-success font-semibold">FREE</span>
        ) : (
          <Lock className="h-3 w-3 text-cyber-muted opacity-50" />
        )}
      </div>
    </div>
  );
}

function CourseAccordion({ course }: { course: typeof PATHS[0]['courses'][0] }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="border border-cyber-border rounded-lg overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-start gap-4 p-4 text-left hover:bg-cyber-surface/50 transition-colors"
      >
        <div className="flex-1 min-w-0">
          <div className="flex flex-wrap items-center gap-2 mb-1">
            <span className="font-semibold text-cyber-text">{course.title}</span>
            <DifficultyBadge level={course.difficulty} />
          </div>
          <p className="text-xs text-cyber-muted line-clamp-2">{course.description}</p>
          <div className="flex flex-wrap gap-1.5 mt-2">
            {course.tags.map(t => (
              <span key={t} className="text-xs px-1.5 py-0.5 rounded bg-cyber-border text-cyber-muted">{t}</span>
            ))}
          </div>
        </div>
        <div className="flex flex-col items-end gap-1 shrink-0">
          <div className="flex items-center gap-1 text-xs text-cyber-muted">
            <Clock className="h-3 w-3" />
            <span>~{course.estimated_hours}h</span>
          </div>
          <span className="text-xs text-cyber-muted">{course.modules.length} modules</span>
          {open ? <ChevronDown className="h-4 w-4 text-cyber-muted mt-1" /> : <ChevronRight className="h-4 w-4 text-cyber-muted mt-1" />}
        </div>
      </button>
      {open && (
        <div className="border-t border-cyber-border bg-cyber-bg/50 p-2">
          {course.modules.map((mod, i) => (
            <ModuleRow key={mod.id} mod={mod} index={i} />
          ))}
          <div className="mt-3 px-3">
            <Link
              href={`/courses/${course.id}`}
              className="terminal-button inline-flex items-center gap-2 px-4 py-2 text-sm"
            >
              <Play className="h-3.5 w-3.5" />
              Start Course
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}

function PathCard({ path, active, onClick }: {
  path: typeof PATHS[0];
  active: boolean;
  onClick: () => void;
}) {
  const Icon = path.icon;
  const dm = DIFFICULTY_META[path.difficulty];
  return (
    <button
      onClick={onClick}
      style={{ borderColor: active ? path.color : undefined }}
      className={`w-full text-left p-4 rounded-lg border transition-all duration-200 ${
        active
          ? 'bg-cyber-surface border-opacity-80 shadow-lg'
          : 'border-cyber-border hover:border-cyber-primary/50 bg-cyber-surface/40'
      }`}
    >
      <div className="flex items-start gap-3">
        <div
          className="mt-0.5 p-2 rounded-md shrink-0"
          style={{ backgroundColor: `${path.color}18` }}
        >
          <Icon className="h-5 w-5" style={{ color: path.color }} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap mb-1">
            <span className="font-bold text-sm text-cyber-text">{path.title}</span>
            <span className={`text-xs px-1.5 py-0.5 rounded font-semibold ${dm.bg} ${dm.color}`}>{dm.label}</span>
          </div>
          <div className="flex flex-wrap gap-3 text-xs text-cyber-muted">
            <span className="flex items-center gap-1"><Clock className="h-3 w-3" />{path.estimated_hours}h</span>
            <span className="flex items-center gap-1"><BookOpen className="h-3 w-3" />{path.courses_count} courses</span>
            <span className="flex items-center gap-1"><Play className="h-3 w-3" />{path.lessons_count} lessons</span>
          </div>
        </div>
        {active && <CheckCircle className="h-4 w-4 shrink-0 mt-0.5" style={{ color: path.color }} />}
      </div>
    </button>
  );
}

// ─── Page ────────────────────────────────────────────────────────────────────

export default function LearningPathsPage() {
  const [activePathId, setActivePathId] = useState(PATHS[0].id);
  const activePath = PATHS.find(p => p.id === activePathId) ?? PATHS[0];

  return (
    <>
      <Navbar />
      <main className="mx-auto max-w-7xl px-4 py-10 sm:px-6">
        {/* Header */}
        <div className="mb-10">
          <div className="mb-2 flex items-center gap-2 font-mono text-xs text-cyber-secondary">
            <Star className="h-3.5 w-3.5" />
            <span>Curated from CEH v12 &amp; Hands-On Hacking curriculum</span>
          </div>
          <h1 className="text-3xl font-bold sm:text-4xl">
            Learning <span className="text-cyber-primary">Paths</span>
          </h1>
          <p className="mt-2 max-w-2xl text-cyber-muted">
            Structured, step-by-step paths from zero to advanced. Each path contains video lectures,
            PDF study guides, and practical labs — all inside a safe, simulated environment.
          </p>
        </div>

        <div className="grid gap-8 lg:grid-cols-[340px,1fr]">
          {/* Left: Path selector */}
          <div>
            <h2 className="mb-3 text-xs font-semibold uppercase tracking-widest text-cyber-muted">
              Choose your path
            </h2>
            <div className="space-y-3">
              {PATHS.map(path => (
                <PathCard
                  key={path.id}
                  path={path}
                  active={path.id === activePathId}
                  onClick={() => setActivePathId(path.id)}
                />
              ))}
            </div>

            {/* Stats summary */}
            <div className="mt-6 terminal-card p-4 space-y-2">
              <p className="text-xs font-mono text-cyber-secondary mb-3">$ total_curriculum --stats</p>
              {[
                { label: 'Total Hours', value: `${PATHS.reduce((a, p) => a + p.estimated_hours, 0)}h` },
                { label: 'Total Lessons', value: `${PATHS.reduce((a, p) => a + p.lessons_count, 0)}+` },
                { label: 'CEH v12 Modules', value: '20' },
                { label: 'Skill Levels', value: '3' },
              ].map(s => (
                <div key={s.label} className="flex justify-between text-sm">
                  <span className="text-cyber-muted">{s.label}</span>
                  <span className="font-mono font-bold text-cyber-primary">{s.value}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Right: Active path detail */}
          <div>
            <div className="terminal-card p-5 mb-6" style={{ borderColor: `${activePath.color}30` }}>
              <div className="flex items-start gap-4 mb-4">
                <div className="p-3 rounded-lg shrink-0" style={{ backgroundColor: `${activePath.color}18` }}>
                  <activePath.icon className="h-7 w-7" style={{ color: activePath.color }} />
                </div>
                <div>
                  <h2 className="text-xl font-bold text-cyber-text">{activePath.title}</h2>
                  <p className="mt-1 text-sm text-cyber-muted">{activePath.description}</p>
                  <div className="mt-3 flex flex-wrap gap-3 text-sm">
                    <DifficultyBadge level={activePath.difficulty} />
                    <span className="flex items-center gap-1 text-cyber-muted">
                      <Clock className="h-3.5 w-3.5" />{activePath.estimated_hours} hours
                    </span>
                    <span className="flex items-center gap-1 text-cyber-muted">
                      <BookOpen className="h-3.5 w-3.5" />{activePath.courses_count} courses
                    </span>
                    <span className="flex items-center gap-1 text-cyber-muted">
                      <Play className="h-3.5 w-3.5" />{activePath.lessons_count}+ lessons
                    </span>
                  </div>
                </div>
              </div>
              <Link
                href={`/register?redirect=${encodeURIComponent(`/courses/${activePath.courses[0]?.id}`)}`}
                id={`enroll-${activePath.slug}`}
                className="terminal-button inline-flex items-center gap-2 px-6 py-2.5"
                style={{ backgroundColor: activePath.color, color: '#070a14' }}
              >
                <Play className="h-4 w-4" />
                Enroll — Free
              </Link>
            </div>

            {/* Courses accordion */}
            <h3 className="mb-3 text-sm font-semibold uppercase tracking-widest text-cyber-muted">
              Course Curriculum
            </h3>
            <div className="space-y-3">
              {activePath.courses.map(course => (
                <CourseAccordion key={course.id} course={course} />
              ))}
            </div>
          </div>
        </div>
      </main>
    </>
  );
}
