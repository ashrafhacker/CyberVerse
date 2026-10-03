'use client';

import { useState, useEffect, useMemo, useCallback, memo } from 'react';
import Link from 'next/link';
import { Shield, Terminal, Globe, Lock, Trophy, Zap, ShieldAlert, Users, Cpu, Eye, Award, ArrowRight, Sparkles, Activity, BookOpen, Target } from 'lucide-react';
import { motion, AnimatePresence, type Variants } from 'framer-motion';
import { useAuth } from '@/lib/auth';

interface Feature {
  id: string;
  icon: React.ComponentType<{ className?: string }>;
  title: string;
  description: string;
  accent: string;
  stats: string;
}

interface Path {
  id: string;
  icon: React.ComponentType<{ className?: string }>;
  title: string;
  description: string;
  level: 'Beginner' | 'Intermediate' | 'Advanced' | 'Expert';
  duration: string;
  modules: number;
  color: string;
}

interface Faq {
  q: string;
  a: string;
  category: 'general' | 'pricing' | 'certification' | 'legal';
}

const containerVariants: Variants = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.08, delayChildren: 0.12 } },
};

const itemVariants: Variants = {
  hidden: { opacity: 0, y: 16 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.45, ease: [0.22, 1, 0.36, 1] } },
};

const cardHover = { y: -4, scale: 1.01, transition: { duration: 0.2 } };

const FEATURES: Feature[] = [
  { id: 'missions', icon: Terminal, title: 'Hands-On Missions', description: 'Interactive sandboxes with guided exploits, forensics, and defense scenarios — zero risk to real systems.', accent: 'text-cyan-400', stats: '200+ missions' },
  { id: 'paths', icon: BookOpen, title: 'Progressive Learning Paths', description: 'From networking fundamentals to advanced offensive & defensive tradecraft, structured for mastery.', accent: 'text-violet-400', stats: '4 mastery tracks' },
  { id: 'scenarios', icon: Globe, title: 'Cyber Defense Scenarios', description: 'Defend simulated enterprise networks against scripted APTs and learn incident response by doing.', accent: 'text-emerald-400', stats: 'Live SOC sim' },
  { id: 'gamified', icon: Trophy, title: 'Gamified Progression', description: 'Earn XP, level up, unlock titles/badges, climb global leaderboards, and collect verified certificates.', accent: 'text-amber-400', stats: 'Seasonal leagues' },
  { id: 'mentor', icon: Cpu, title: 'AI Mentor (24/7)', description: 'Context-aware tutor explains concepts, reviews payloads, and suggests next steps — without spoiling the challenge.', accent: 'text-pink-400', stats: 'GPT-4o powered' },
  { id: 'labs', icon: Eye, title: 'CyberVerse Labs', description: 'Forensic workbenches, evidence lockers, and report builders — practice real analyst workflows.', accent: 'text-sky-400', stats: 'UE5-ready' },
];

const PATHS: Path[] = [
  { id: 'foundations', icon: Shield, title: 'Cybersecurity Foundations', description: 'Networks, protocols, cryptography, OS fundamentals, and security mindset.', level: 'Beginner', duration: '40h', modules: 20, color: 'border-cyan-500/40' },
  { id: 'offensive', icon: Zap, title: 'Offensive Security', description: 'Recon, vuln discovery, exploitation, and post-exploitation — fully sandboxed.', level: 'Intermediate', duration: '60h', modules: 28, color: 'border-violet-500/40' },
  { id: 'defensive', icon: Lock, title: 'Defensive Security', description: 'Detection engineering, IR, hardening, threat hunting, and forensics.', level: 'Advanced', duration: '80h', modules: 32, color: 'border-emerald-500/40' },
  { id: 'expert', icon: Target, title: 'Expert Operations', description: 'Red vs Blue exercises, purple teaming, and enterprise SOC simulations.', level: 'Expert', duration: '100h+', modules: 18, color: 'border-amber-500/40' },
];

const FAQS: Faq[] = [
  { q: 'Is this legal and safe?', a: "Yes. Every mission runs inside CyberVerse's isolated simulations. You never touch real systems, networks, or third parties. All payloads are synthetic.", category: 'legal' },
  { q: 'Do I need prior experience?', a: 'No. Foundations starts from zero and scales progressively. Concepts are explained inline before each hands-on step, with hints and AI mentor support.', category: 'general' },
  { q: 'Do I get certificates?', a: 'Completing a path grants a verifiable certificate (PDF + on-chain hash) and unlocks badges, titles, and leaderboard standing.', category: 'certification' },
  { q: 'How much does it cost?', a: 'Beginner ₹99/mo, Intermediate ₹399/mo, Advanced (with licensed tooling) ₹5,000/mo. Cancel anytime. Education discounts available.', category: 'pricing' },
  { q: 'Can I use it in classrooms?', a: 'Yes — instructor dashboards, classrooms, assignments, and analytics are built-in. Contact us for institutional licensing.', category: 'general' },
  { q: 'Is my progress tracked?', a: 'All progress is encrypted at rest, exportable, and portable. You can request deletion per GDPR at any time.', category: 'general' },
];

const STATS = [
  { value: '50K+', label: 'Learners' },
  { value: '200+', label: 'Missions' },
  { value: '99.9%', label: 'Uptime' },
  { value: '4.8/5', label: 'Rating' },
];

const FeatureCard = memo(function FeatureCard({ feature }: { feature: Feature }) {
  const Icon = feature.icon;
  return (
    <motion.div variants={itemVariants} whileHover={cardHover} className="terminal-card group p-6 transition-all hover:border-cyber-primary/60 hover:shadow-[0_0_24px_rgba(34,211,238,0.15)]">
      <Icon className={`mb-4 h-8 w-8 ${feature.accent}`} />
      <h3 className="mb-1.5 font-semibold tracking-tight">{feature.title}</h3>
      <p className="mb-3 text-sm leading-relaxed text-cyber-muted">{feature.description}</p>
      <span className="inline-flex items-center gap-1.5 rounded-full border border-cyber-border bg-cyber-surface px-2.5 py-1 text-xs font-medium text-cyber-muted">
        <Activity className="h-3 w-3" /> {feature.stats}
      </span>
    </motion.div>
  );
});

const PathCard = memo(function PathCard({ path }: { path: Path }) {
  const Icon = path.icon;
  const levelColor: Record<string, string> = { Beginner: 'bg-emerald-500/15 text-emerald-400', Intermediate: 'bg-sky-500/15 text-sky-400', Advanced: 'bg-violet-500/15 text-violet-400', Expert: 'bg-amber-500/15 text-amber-400' };
  return (
    <motion.div variants={itemVariants} whileHover={cardHover} className={`terminal-card p-6 ${path.color} transition-colors`}>
      <div className="mb-4 flex items-start justify-between">
        <Icon className="h-8 w-8 text-cyber-primary" />
        <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${levelColor[path.level]}`}>{path.level}</span>
      </div>
      <h3 className="mb-2 font-semibold">{path.title}</h3>
      <p className="mb-4 text-sm text-cyber-muted">{path.description}</p>
      <div className="flex items-center gap-3 text-xs text-cyber-muted">
        <span className="inline-flex items-center gap-1"><BookOpen className="h-3.5 w-3.5" /> {path.modules} modules</span>
        <span className="inline-flex items-center gap-1"><Zap className="h-3.5 w-3.5" /> {path.duration}</span>
      </div>
    </motion.div>
  );
});

export default function Home() {
  const { user, loading } = useAuth();
  const [mounted, setMounted] = useState(false);
  const [faqOpen, setFaqOpen] = useState<string | null>(null);

  useEffect(() => setMounted(true), []);

  const toggleFaq = useCallback((q: string) => {
    setFaqOpen(prev => (prev === q ? null : q));
  }, []);

  const jsonLd = useMemo(() => ({
    '@context': 'https://schema.org',
    '@type': 'EducationalOrganization',
    name: 'CyberVerse',
    description: 'Educational cybersecurity simulation platform — learn by doing in safe sandboxes.',
    url: 'https://cyberverse.io',
    offers: { '@type': 'AggregateOffer', priceCurrency: 'INR', lowPrice: '99', highPrice: '5000' },
  }), []);

  return (
    <div suppressHydrationWarning className="min-h-screen bg-cyber-bg text-cyber-text">
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }} />

      <header className="sticky top-0 z-40 border-b border-cyber-border/60 bg-cyber-bg/80 backdrop-blur supports-[backdrop-filter]:bg-cyber-bg/60">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
          <Link href="/" className="flex items-center gap-2.5">
            <span className="grid h-8 w-8 place-items-center rounded-lg bg-cyber-primary text-cyber-bg">
              <Shield className="h-5 w-5" />
            </span>
            <span className="font-mono text-xl font-bold tracking-tight">
              <span className="glow-text text-cyber-primary">Cyber</span>Verse
            </span>
            <span className="ml-2 hidden rounded bg-cyber-primary/15 px-1.5 py-0.5 text-xs font-bold text-cyber-primary md:inline">PRO</span>
          </Link>

          <nav aria-label="Primary" className="hidden items-center gap-6 text-sm text-cyber-muted md:flex">
            <a href="#features" className="hover:text-cyber-primary transition-colors">Features</a>
            <Link href="/courses" className="hover:text-cyber-primary transition-colors">Learning Paths</Link>
            <Link href="/labs" className="hover:text-cyber-primary transition-colors">Labs</Link>
            <Link href="/game" className="hover:text-cyber-primary transition-colors">Game</Link>
            <Link href="/library" className="hover:text-cyber-primary transition-colors">Library</Link>
            <Link href="/leaderboard" className="hover:text-cyber-primary transition-colors">Leaderboard</Link>
          </nav>

          <div suppressHydrationWarning className="flex items-center gap-3">
            {!mounted || loading ? (
              <div className="h-9 w-32 animate-pulse rounded bg-cyber-surface" aria-hidden />
            ) : user ? (
              <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex items-center gap-3">
                <span className="hidden text-sm text-cyber-muted md:inline">Hi, {user.full_name?.split(' ')[0]}</span>
                <Link href="/dashboard" className="terminal-button inline-flex items-center gap-2">
                  Dashboard <ArrowRight className="h-4 w-4" />
                </Link>
              </motion.div>
            ) : (
              <div className="flex items-center gap-2">
                <Link href="/login" className="terminal-button-ghost hidden md:inline-flex">Log in</Link>
                <Link href="/register" className="terminal-button inline-flex items-center gap-2">
                  Get Started <Sparkles className="h-4 w-4" />
                </Link>
              </div>
            )}
          </div>
        </div>
      </header>

      <main>
        <section className="relative overflow-hidden bg-grid-pattern [background-size:40px_40px] py-20 md:py-28">
          <div className="pointer-events-none absolute -top-24 right-1/4 h-[420px] w-[420px] rounded-full bg-cyan-500/15 blur-[80px]" />
          <div className="pointer-events-none absolute -bottom-24 left-1/4 h-[420px] w-[420px] rounded-full bg-violet-500/15 blur-[80px]" />

          <motion.div suppressHydrationWarning variants={containerVariants} initial="hidden" animate="visible" className="relative mx-auto max-w-5xl px-6 text-center">
            <motion.p variants={itemVariants} className="mb-4 inline-flex items-center gap-2 rounded-full border border-cyber-primary/30 bg-cyber-primary/10 px-3 py-1 font-mono text-xs text-cyber-primary">
              <span className="h-2 w-2 animate-pulse rounded-full bg-emerald-400" />
              {'>'} // educational cybersecurity simulation platform — v2.1 PRO
            </motion.p>

            <motion.h1 variants={itemVariants} className="mb-6 text-5xl font-extrabold tracking-tight md:text-7xl">
              Learn Cybersecurity{' '}
              <span className="glow-text bg-gradient-to-r from-cyan-400 to-violet-400 bg-clip-text text-transparent">By Doing.</span>
            </motion.h1>

            <motion.p variants={itemVariants} className="mx-auto mb-8 max-w-2xl text-lg leading-relaxed text-cyber-muted">
              Attack, defend, and investigate — inside a controlled sandbox where every action is{' '}
              <span className="font-medium text-cyber-text">legal, simulated, and designed to teach</span>.
              Enterprise-grade pedagogy trusted by 50K+ learners.
            </motion.p>

            <motion.div suppressHydrationWarning variants={itemVariants} className="flex flex-wrap justify-center gap-4">
              {!mounted || loading ? (
                <div className="h-12 w-64 animate-pulse rounded bg-cyber-surface" />
              ) : user ? (
                <Link href="/dashboard" className="terminal-button px-8 py-3 text-base inline-flex items-center gap-2">
                  Enter the Verse <ArrowRight className="h-5 w-5" />
                </Link>
              ) : (
                <>
                  <Link href="/register" className="terminal-button px-8 py-3 text-base inline-flex items-center gap-2">
                    Start Learning — Free <ArrowRight className="h-5 w-5" />
                  </Link>
                  <Link href="/courses" className="terminal-button-ghost px-8 py-3 text-base inline-flex items-center gap-2">
                    <Eye className="h-5 w-5" /> View Curriculum
                  </Link>
                </>
              )}
            </motion.div>

            <motion.p variants={itemVariants} className="mt-6 font-mono text-xs text-cyber-muted">No credit card required • Cancel anytime • GDPR compliant</motion.p>

            <motion.div variants={itemVariants} className="mx-auto mt-10 grid max-w-3xl grid-cols-2 gap-4 md:grid-cols-4">
              {STATS.map(s => (
                <div key={s.label} className="rounded-xl border border-cyber-border bg-cyber-surface/60 px-4 py-3">
                  <div className="text-2xl font-bold text-cyber-primary">{s.value}</div>
                  <div className="text-xs uppercase tracking-widest text-cyber-muted">{s.label}</div>
                </div>
              ))}
            </motion.div>
          </motion.div>
        </section>

        <div className="mx-auto max-w-7xl px-6">
          <motion.div initial={{ opacity: 0, y: 8 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} className="flex items-center gap-2.5 rounded-xl border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-300">
            <ShieldAlert className="h-5 w-5 flex-shrink-0" />
            <span><strong>Educational only:</strong> All content is for defense education — never for attacking real systems. Learn to secure, not exploit.</span>
          </motion.div>
        </div>

        <section id="features" className="mx-auto max-w-7xl px-6 py-20">
          <div className="mb-10 text-center">
            <h2 className="text-3xl font-bold tracking-tight md:text-4xl">A <span className="text-cyber-primary">safe place</span> to break things</h2>
            <p className="mx-auto mt-3 max-w-2xl text-cyber-muted">Professional tooling, pedagogically sound — crafted with infosec educators and SOC analysts.</p>
          </div>
          <motion.div variants={containerVariants} initial="hidden" whileInView="visible" viewport={{ once: true, margin: '-80px' }} className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
            {FEATURES.map(f => (
              <FeatureCard key={f.id} feature={f} />
            ))}
          </motion.div>
        </section>

        <section id="paths" className="border-y border-cyber-border bg-cyber-surface/40 py-20">
          <div className="mx-auto max-w-7xl px-6">
            <div className="mb-10 text-center">
              <h2 className="text-3xl font-bold tracking-tight md:text-4xl">Choose your <span className="text-cyber-primary">path</span></h2>
              <p className="mx-auto mt-3 max-w-2xl text-cyber-muted">Structured progression from fundamentals to expert operations — with certificates at each milestone.</p>
            </div>
            <motion.div variants={containerVariants} initial="hidden" whileInView="visible" viewport={{ once: true, margin: '-80px' }} className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
              {PATHS.map(p => (
                <PathCard key={p.id} path={p} />
              ))}
            </motion.div>

            <div className="mt-10 flex justify-center">
              <Link href="/courses" className="terminal-button-ghost inline-flex items-center gap-2 px-6 py-3">
                Explore full curriculum <ArrowRight className="h-4 w-4" />
              </Link>
            </div>
          </div>
        </section>

        <section className="mx-auto max-w-7xl px-6 py-20">
          <div className="grid gap-8 md:grid-cols-3">
            {[
              { step: '01', title: 'Learn', desc: 'Bite-sized lessons with inline labs. Concepts before commands.' },
              { step: '02', title: 'Practice', desc: 'Hands-on missions with instant feedback and AI mentor guidance.' },
              { step: '03', title: 'Prove', desc: ' Earn XP, certificates, and leaderboard rank — verifiable and portable.' },
            ].map(s => (
              <div key={s.step} className="relative">
                <div className="font-mono text-6xl font-black text-cyber-border">{s.step}</div>
                <h3 className="mt-2 text-xl font-semibold">{s.title}</h3>
                <p className="mt-1 text-sm text-cyber-muted">{s.desc}</p>
              </div>
            ))}
          </div>
        </section>

        <section id="faq" className="mx-auto max-w-3xl px-6 py-20">
          <h2 className="mb-8 text-center text-3xl font-bold">Frequently asked</h2>
          <div className="space-y-3">
            {FAQS.map(({ q, a, category }) => (
              <div key={q} className="terminal-card overflow-hidden">
                <button
                  onClick={() => toggleFaq(q)}
                  aria-expanded={faqOpen === q}
                  aria-controls={`faq-${q.slice(0, 12)}`}
                  className="flex w-full items-center justify-between px-5 py-4 text-left"
                >
                  <div className="flex items-center gap-3">
                    <span className="rounded bg-cyber-primary/15 px-2 py-1 text-xs font-bold text-cyber-primary">{category}</span>
                    <span className="font-medium">{q}</span>
                  </div>
                  <motion.span animate={{ rotate: faqOpen === q ? 45 : 0 }} className="text-cyber-primary">+</motion.span>
                </button>
                <AnimatePresence initial={false}>
                  {faqOpen === q && (
                    <motion.div
                      id={`faq-${q.slice(0, 12)}`}
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: 'auto', opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      transition={{ duration: 0.25 }}
                      className="overflow-hidden"
                    >
                      <p className="px-5 pb-4 text-sm leading-relaxed text-cyber-muted">{a}</p>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            ))}
          </div>
        </section>

        <section className="mx-auto max-w-5xl px-6 pb-20">
          <div className="rounded-2xl border border-cyber-primary/30 bg-gradient-to-br from-cyber-primary/10 via-violet-500/10 to-cyan-500/10 p-8 text-center md:p-12">
            <h2 className="text-3xl font-bold md:text-4xl">Ready to enter the Verse?</h2>
            <p className="mx-auto mt-3 max-w-2xl text-cyber-muted">Join 50K+ learners securing the future. Start free, upgrade when you're ready for advanced tooling.</p>
            <div className="mt-6 flex justify-center gap-3">
              <Link href="/register" className="terminal-button px-8 py-3 inline-flex items-center gap-2">Create free account <Award className="h-5 w-5" /></Link>
              <Link href="/courses" className="terminal-button-ghost px-6 py-3">Browse courses</Link>
            </div>
          </div>
        </section>
      </main>

      <footer className="border-t border-cyber-border py-10">
        <div className="mx-auto max-w-7xl px-6">
          <div className="flex flex-col items-center justify-between gap-4 md:flex-row">
            <div className="flex items-center gap-2 font-mono text-sm text-cyber-muted">
              <Shield className="h-4 w-4 text-cyber-primary" /> CyberVerse © 2026 — Educational use only.
            </div>
            <div className="flex gap-4 text-xs text-cyber-muted">
              <Link href="/support" className="hover:text-cyber-primary">Support</Link>
              <Link href="/tools" className="hover:text-cyber-primary">Tools</Link>
              <Link href="/library" className="hover:text-cyber-primary">Library</Link>
              <span className="inline-flex items-center gap-1"><Users className="h-3 w-3" /> 50K+ learners</span>
            </div>
          </div>
          <p className="mt-4 text-center font-mono text-xs text-cyber-muted/60">operational.legal • gdpr.compliant • soc2.in.progress</p>
        </div>
      </footer>
    </div>
  );
}