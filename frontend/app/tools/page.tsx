'use client';

import Link from 'next/link';
import { Shield, Wrench, Search, Code, Terminal, Github, ExternalLink, Flag, Globe } from 'lucide-react';
import { useAuth } from '@/lib/auth';

const INTERNAL_TOOLS = [
  {
    title: 'Google Dorker',
    description: 'A powerful tool to generate Google Dorks for finding exposed files, directories, and vulnerabilities.',
    icon: Search,
    href: '/tools/dorker',
    internal: true,
  },
  {
    title: 'Cyber Arsenal',
    description: 'A verified directory of free, open-source security tools for learning and defensive operations.',
    icon: Wrench,
    href: '/arsenal',
    internal: true,
  },
  {
    title: 'Capture the Flag',
    description: 'Practice core skill categories through synthetic, solvable security puzzles with a live leaderboard.',
    icon: Flag,
    href: '/ctf',
    internal: true,
  },
  {
    title: 'SOC Simulator',
    description: 'Triage simulated alerts and drive incidents through the full investigation and containment lifecycle.',
    icon: Terminal,
    href: '/soc',
    internal: true,
  },
  {
    title: 'Threat Intelligence',
    description: 'Reference curated CVE and MITRE ATT&CK knowledge sourced from official public data.',
    icon: Globe,
    href: '/threat-intel',
    internal: true,
  },
];

const REPOSITORIES = [
  {
    name: 'Wireshark',
    description: 'The world\u2019s most popular network protocol analyzer for traffic inspection and analysis.',
    url: 'https://github.com/wireshark/wireshark',
    stars: '7.4k',
  },
  {
    name: 'Burp Suite (PortSwigger)',
    description: 'Reference documentation and community resources for the Burp Suite web security testing tool.',
    url: 'https://github.com/PortSwigger',
    stars: 'community',
  },
  {
    name: 'OWASP Top 10',
    description: 'The official OWASP Top 10 web application security risks list and supporting resources.',
    url: 'https://github.com/OWASP/Top10',
    stars: '4.3k',
  },
  {
    name: 'Metasploit Framework',
    description: 'Open-source penetration testing framework used for vulnerability research and exploit development.',
    url: 'https://github.com/rapid7/metasploit-framework',
    stars: '35k+',
  },
  {
    name: 'Nmap',
    description: 'The network mapper — industry-standard tool for network discovery and security auditing.',
    url: 'https://github.com/nmap/nmap',
    stars: '10k+',
  },
  {
    name: 'CyberChef',
    description: 'A web app for encryption, encoding, compression, and data analysis — the Swiss Army knife of the SOC analyst.',
    url: 'https://github.com/gchq/CyberChef',
    stars: '29k+',
  },
];

export default function ToolsPage() {
  const { user } = useAuth();

  return (
    <div className="min-h-screen bg-grid-pattern [background-size:40px_40px] bg-cyber-bg">
      <header className="mx-auto flex max-w-7xl items-center justify-between px-6 py-6 border-b border-cyber-border/30 bg-cyber-bg/80 backdrop-blur-md sticky top-0 z-40">
        <div className="flex items-center gap-2">
          <Shield className="h-8 w-8 text-cyber-primary" />
          <Link href="/" className="font-mono text-xl font-bold glow-text text-cyber-primary">
            CyberVerse
          </Link>
        </div>
        <nav className="flex items-center gap-6 text-sm text-cyber-muted">
          <Link href="/courses" className="hover:text-cyber-primary">Learning Paths</Link>
          <Link href="/game" className="hover:text-cyber-primary">Game</Link>
          <Link href="/library" className="hover:text-cyber-primary">Library</Link>
          <Link href="/arsenal" className="hover:text-cyber-primary">Arsenal</Link>
          <Link href="/soc" className="hover:text-cyber-primary">SOC</Link>
          <Link href="/threat-intel" className="hover:text-cyber-primary">Threat Intel</Link>
          <Link href="/ctf" className="hover:text-cyber-primary">CTF</Link>
          <Link href="/tools" className="text-cyber-primary font-semibold">Tools</Link>
          {user ? (
            <Link href="/dashboard" className="terminal-button">Dashboard</Link>
          ) : (
            <Link href="/login" className="terminal-button-ghost">Log in</Link>
          )}
        </nav>
      </header>

      <main className="mx-auto max-w-7xl px-6 py-12">
        <div className="mb-12">
          <h1 className="font-mono text-4xl font-bold text-cyber-primary glow-text flex items-center gap-4">
            <Wrench className="h-10 w-10" />
            CyberVerse Tools & Resources
          </h1>
          <p className="mt-4 text-cyber-muted text-lg max-w-3xl">
            A curated collection of internal tools, community utilities, and essential open-source repositories to aid in your ethical hacking and cybersecurity journey.
          </p>
        </div>

        <section className="mb-16">
          <h2 className="text-2xl font-bold mb-6 flex items-center gap-2 border-b border-cyber-border pb-2">
            <Terminal className="text-cyber-secondary" /> Utilities & Tools
          </h2>
          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
            {INTERNAL_TOOLS.map((tool) => {
              const Icon = tool.icon;
              return (
                <div key={tool.title} className="terminal-card p-6 hover:border-cyber-primary transition-colors flex flex-col h-full">
                  <div className="flex items-center gap-3 mb-4">
                    <div className="p-3 bg-cyber-primary/10 rounded-lg text-cyber-primary">
                      <Icon className="h-6 w-6" />
                    </div>
                    <h3 className="font-bold text-lg">{tool.title}</h3>
                  </div>
                  <p className="text-cyber-muted mb-6 flex-grow">{tool.description}</p>
                  
                  {tool.internal ? (
                    <Link href={tool.href} className="terminal-button text-center block w-full mt-auto">
                      Launch Tool
                    </Link>
                  ) : (
                    <a href={tool.href} target="_blank" rel="noopener noreferrer" className="terminal-button-ghost text-center block w-full mt-auto">
                      Visit Site
                    </a>
                  )}
                </div>
              );
            })}
          </div>
        </section>

        <section className="mb-16">
          <h2 className="text-2xl font-bold mb-6 flex items-center gap-2 border-b border-cyber-border pb-2">
            <Github className="text-cyber-secondary" /> Open-Source Repositories
          </h2>
          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
            {REPOSITORIES.map((repo) => (
              <a
                key={repo.name}
                href={repo.url}
                target="_blank"
                rel="noopener noreferrer"
                className="terminal-card p-6 hover:border-cyber-primary transition-colors flex flex-col h-full"
              >
                <div className="flex items-center gap-3 mb-4">
                  <div className="p-3 bg-cyber-secondary/10 rounded-lg text-cyber-secondary">
                    <Github className="h-6 w-6" />
                  </div>
                  <div className="min-w-0">
                    <h3 className="font-bold text-lg truncate">{repo.name}</h3>
                    <span className="text-xs font-mono text-cyber-muted">★ {repo.stars}</span>
                  </div>
                </div>
                <p className="text-cyber-muted text-sm mb-6 flex-grow">{repo.description}</p>
                <span className="flex items-center gap-2 text-cyber-primary text-sm mt-auto">
                  <ExternalLink className="h-4 w-4" /> View on GitHub
                </span>
              </a>
            ))}
          </div>
        </section>
      </main>
    </div>
  );
}

