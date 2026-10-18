'use client';

// Public contact page. Posts to /api/v1/contact (rate-limited + honeypot
// server-side), surfaces success/error through the global toast system, and
// fires a consent-gated GA4 conversion event on submit.

import { useState } from 'react';
import { Mail, Send, ShieldCheck } from 'lucide-react';
import Navbar from '@/components/Navbar';
import Breadcrumbs from '@/components/Breadcrumbs';
import { TerminalCard } from '@/components/TerminalCard';
import { useToast } from '@/lib/toast';
import { trackConversion } from '@/lib/analytics';

export default function ContactPage() {
  const toast = useToast();
  const [sending, setSending] = useState(false);
  const [form, setForm] = useState({ name: '', email: '', subject: '', message: '', website: '' });

  const set = (key: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) =>
    setForm((f) => ({ ...f, [key]: e.target.value }));

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (sending) return;
    setSending(true);
    try {
      const res = await fetch('/api/v1/contact', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => null);
        throw new Error(body?.detail ?? 'Something went wrong. Please try again.');
      }
      trackConversion('contact_submit', { subject_category: form.subject.slice(0, 40) });
      toast.success('Message sent — we usually reply within one business day.');
      setForm({ name: '', email: '', subject: '', message: '', website: '' });
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Unable to send your message.');
    } finally {
      setSending(false);
    }
  };

  return (
    <>
      <Navbar />
      <Breadcrumbs items={[{ label: 'Home', href: '/' }, { label: 'Contact' }]} />
      <main className="mx-auto max-w-3xl px-6 py-10">
        <h1 className="text-2xl font-bold">Contact the CyberVerse team</h1>
        <p className="mt-2 text-sm text-cyber-muted">
          Questions about courses, institutional licensing, or partnerships — send us a message.
          Already enrolled and need help with an account issue? Open a ticket from your dashboard.
        </p>

        <TerminalCard className="mt-8" title="contact://new-message">
          <form onSubmit={submit} className="space-y-4">
            <div className="grid gap-4 sm:grid-cols-2">
              <label className="block">
                <span className="terminal-label">Name</span>
                <input required minLength={2} maxLength={120} className="terminal-input" value={form.name} onChange={set('name')} autoComplete="name" />
              </label>
              <label className="block">
                <span className="terminal-label">Email</span>
                <input required type="email" maxLength={254} className="terminal-input" value={form.email} onChange={set('email')} autoComplete="email" />
              </label>
            </div>
            <label className="block">
              <span className="terminal-label">Subject</span>
              <input required minLength={3} maxLength={200} className="terminal-input" value={form.subject} onChange={set('subject')} />
            </label>
            <label className="block">
              <span className="terminal-label">Message</span>
              <textarea required minLength={10} maxLength={5000} rows={6} className="terminal-input resize-y" value={form.message} onChange={set('message')} />
            </label>
            {/* Honeypot: invisible to humans, catches naive bots. */}
            <input
              type="text"
              tabIndex={-1}
              autoComplete="off"
              aria-hidden="true"
              className="hidden"
              value={form.website}
              onChange={set('website')}
            />
            <div className="flex items-center justify-between gap-3">
              <p className="inline-flex items-center gap-1.5 text-xs text-cyber-muted">
                <ShieldCheck className="h-3.5 w-3.5" /> Rate-limited & spam-protected
              </p>
              <button type="submit" disabled={sending} className="terminal-button inline-flex items-center gap-2">
                <Send className="h-4 w-4" />
                {sending ? 'Sending…' : 'Send message'}
              </button>
            </div>
          </form>
        </TerminalCard>

        <p className="mt-6 inline-flex items-center gap-2 text-xs text-cyber-muted">
          <Mail className="h-3.5 w-3.5" /> We never share your contact details with third parties.
        </p>
      </main>
    </>
  );
}
