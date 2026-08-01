'use client';

import Link from 'next/link';
import { Shield, Terminal, Globe, Lock, Trophy, Zap } from 'lucide-react';
import { useAuth } from '@/lib/auth';

const features = [
  {
    icon: Terminal,
    title: 'Hands-On Missions',
    description:
      'Complete interactive cybersecurity missions in a fully simulated sandbox — safe, legal, and zero risk to real systems.',
  },
  {
    icon: Lock,
    title: 'Progressive Learning Paths',
    description:
      'Structured paths from networking basics to advanced offensive and defensive security techniques.',
  },
  {
    icon: Globe,
    title: 'Cyber Defense Scenarios',
    description:
      'Defend simulated networks against scripted attacks and learn incident response by doing.',
  },
  {
    icon: Trophy,
    title: 'Gamified Progression',
    description:
      'Earn XP, level up, unlock badges, climb leaderboards, and collect verified certificates of completion.',
  },
];

export default function Home() {
  const { user } = useAuth();

  return (
    <div className="min-h-screen">
      <header className="mx-auto flex max-w-7xl items-center justify-between px-6 py-6">
        <div className="flex items-center gap-2">
          <Shield className="h-8 w-8 text-cyber-primary" />
          <span className="font-mono text-xl font-bold glow-text text-cyber-primary">
            CyberVerse
          </span>
        </div>
        <nav className="flex items-center gap-6 text-sm text-cyber-muted">
          <a href="#features" className="hover:text-cyber-primary">Features</a>
          <Link href="/courses" className="hover:text-cyber-primary">Learning Paths</Link>
          <a href="#faq" className="hover:text-cyber-primary">FAQ</a>
          <Link href="/game" className="text-cyber-secondary hover:text-cyber-primary">Game</Link>
          <Link href="/library" className="text-cyber-secondary hover:text-cyber-primary">Library</Link>
          {user ? (
            <Link href="/dashboard" className="terminal-button">Dashboard</Link>
          ) : (
            <div className="flex gap-3">
              <Link href="/login" className="terminal-button-ghost">Log in</Link>
              <Link href="/register" className="terminal-button">Get Started</Link>
            </div>
          )}
        </nav>
      </header>

      <main>
        <section className="bg-grid-pattern [background-size:40px_40px] bg-cyber-bg py-24 text-center">
          <div className="mx-auto max-w-4xl px-6">
            <p className="mb-4 font-mono text-sm text-cyber-secondary">
              &gt; // educational cybersecurity simulation platform
            </p>
            <h1 className="mb-6 text-5xl font-bold tracking-tight md:text-7xl">
              Learn Cybersecurity{' '}
              <span className="glow-text text-cyber-primary">By Doing.</span>
            </h1>
            <p className="mx-auto mb-10 max-w-2xl text-lg text-cyber-muted">
              CyberVerse turns security education into an interactive adventure.
              Attack, defend, and investigate — inside a controlled sandbox where
              every action is legal, simulated, and designed to teach.
            </p>
            <div className="flex justify-center gap-4">
              {user ? (
                <Link href="/dashboard" className="terminal-button px-8 py-3 text-base">
                  Enter the Verse
                </Link>
              ) : (
                <>
                  <Link href="/register" className="terminal-button px-8 py-3 text-base">
                    Start Free
                  </Link>
                  <Link href="/login" className="terminal-button-ghost px-8 py-3 text-base">
                    Log In
                  </Link>
                </>
              )}
            </div>
            <p className="mt-8 font-mono text-xs text-cyber-muted">
              free forever for learners · no credit card required
            </p>
          </div>
        </section>

        <section id="features" className="mx-auto max-w-7xl px-6 py-20">
          <h2 className="mb-12 text-center text-3xl font-bold">
            A <span className="text-cyber-primary">safe place</span> to break things
          </h2>
          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
            {features.map(({ icon: Icon, title, description }) => (
              <div key={title} className="terminal-card p-6 transition-colors hover:border-cyber-primary">
                <Icon className="mb-4 h-8 w-8 text-cyber-primary" />
                <h3 className="mb-2 font-semibold">{title}</h3>
                <p className="text-sm text-cyber-muted">{description}</p>
              </div>
            ))}
          </div>
        </section>

        <section id="paths" className="border-y border-cyber-border bg-cyber-surface/50 py-20">
          <div className="mx-auto max-w-7xl px-6">
            <h2 className="mb-12 text-center text-3xl font-bold">
              Choose your <span className="text-cyber-primary">path</span>
            </h2>
            <div className="grid gap-6 md:grid-cols-3">
              {[
                {
                  title: 'Cybersecurity Foundations',
                  icon: Shield,
                  desc: 'Networks, protocols, cryptography, and core security concepts.',
                  level: 'Beginner',
                },
                {
                  title: 'Offensive Security',
                  icon: Zap,
                  desc: 'Reconnaissance, vulnerability discovery, and exploitation — in sandboxes only.',
                  level: 'Intermediate',
                },
                {
                  title: 'Defensive Security',
                  icon: Lock,
                  desc: 'Detection, incident response, hardening, and forensics.',
                  level: 'Advanced',
                },
              ].map(({ title, icon: Icon, desc, level }) => (
                <div key={title} className="terminal-card p-6">
                  <Icon className="mb-4 h-8 w-8 text-cyber-secondary" />
                  <div className="mb-2 flex items-center justify-between">
                    <h3 className="font-semibold">{title}</h3>
                    <span className="rounded bg-cyber-border px-2 py-0.5 text-xs text-cyber-muted">{level}</span>
                  </div>
                  <p className="text-sm text-cyber-muted">{desc}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section id="faq" className="mx-auto max-w-3xl px-6 py-20">
          <h2 className="mb-12 text-center text-3xl font-bold">Frequently asked</h2>
          <div className="space-y-4">
            {[
              {
                q: 'Is this legal?',
                a: "Yes. Every mission runs inside CyberVerse's own simulated environments. You never interact with real systems, networks, or third parties.",
              },
              {
                q: 'Do I need prior experience?',
                a: 'No. Paths start from zero and scale progressively. Concepts are explained inline before each hands-on mission.',
              },
              {
                q: 'Do I get certificates?',
                a: 'Completing a course path grants a verifiable certificate and unlocks badges, titles, and leaderboard standing.',
              },
              {
                q: 'Is it really free?',
                a: 'All core content is free. A premium tier adds advanced labs, AI tutoring, and priority support.',
              },
            ].map(({ q, a }) => (
              <div key={q} className="terminal-card p-5">
                <h3 className="mb-1 font-semibold text-cyber-primary">{q}</h3>
                <p className="text-sm text-cyber-muted">{a}</p>
              </div>
            ))}
          </div>
        </section>
      </main>

      <footer className="border-t border-cyber-border py-8 text-center font-mono text-xs text-cyber-muted">
        <p>CyberVerse © 2026 — Educational use only. No real-world attacks.</p>
        <p className="mt-1">operational.legal</p>
      </footer>
    </div>
  );
}
