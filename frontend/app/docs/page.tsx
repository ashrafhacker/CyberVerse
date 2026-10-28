'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { FileText, Clock, CheckCircle2, ArrowUpRight } from 'lucide-react';
import { useRequireAuth } from '@/lib/auth';
import { api } from '@/lib/api';

interface Doc {
  id: string;
  title: string;
  description: string;
  slug: string;
  version: string;
  updated_at: string;
  author: string;
  is_published: boolean;
  type: 'report' | 'strategy' | 'tutorial';
}

export default function DocumentsPage() {
  const { user } = useRequireAuth();
  const [docs, setDocs] = useState<Doc[]>([]);
  const [filter, setFilter] = useState('all');

  useEffect(() => {
    if (!user) return;
    api.get<{ data: Doc[] }>('/docs/team').then(r => setDocs(r.data.data || [])).catch(() => setDocs([]));
  }, [user]);

  const types = filter === 'all' ? docs : docs.filter(d => d.type === filter);

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 to-slate-900 text-slate-100">
      <nav className="border-b border-slate-800/60 px-6 py-4 flex items-center justify-between backdrop-blur-sm bg-slate-900/40 sticky top-0 z-50">
        <Link href="/" className="font-mono text-lg font-bold text-cyan-400">CyberVerse</Link>
        <Link href="/team-chat" className="text-sm text-cyan-300 hover:text-cyan-200">Chat</Link>
      </nav>

      <main className="max-w-5xl mx-auto px-6 py-10">
        <h1 className="text-3xl font-extrabold mb-2">Team Documents</h1>
        <p className="text-slate-400 mb-8">Version-controlled reports, strategies, and tutorials.</p>

        <div className="flex gap-3 mb-8">
          {['all', 'report', 'strategy', 'tutorial'].map(t => (
            <button
              key={t}
              onClick={() => setFilter(t)}
              className={`px-3 py-1 rounded-full text-xs font-semibold border transition ${filter === t ? 'bg-cyan-600 text-white border-cyan-500' : 'bg-slate-900 border-slate-700 text-slate-300 hover:border-slate-600'}`}
            >
              {t}
            </button>
          ))}
        </div>

        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {types.map(doc => (
            <Link href={`/docs/${doc.slug}`} key={doc.id} className="block bg-slate-900/60 border border-slate-800/60 hover:border-cyan-600/40 rounded-2xl p-6 transition-all hover:-translate-y-1 shadow-lg shadow-cyan-900/10 hover:shadow-cyan-900/20">
              <div className="flex items-start justify-between mb-3">
                <FileText className="h-6 w-6 text-cyan-400" />
                <span className="text-[10px] font-mono bg-cyan-900/40 text-cyan-300 px-2 py-0.5 rounded-full">v{doc.version}</span>
              </div>
              <h3 className="font-bold text-lg mb-1">{doc.title}</h3>
              <p className="text-xs text-slate-400 mb-4 line-clamp-2">{doc.description}</p>
              <div className="flex items-center justify-between text-xs text-slate-500">
                <span className="flex items-center gap-1"><Clock className="h-3 w-3" /> {new Date(doc.updated_at).toLocaleDateString()}</span>
                <span className="font-mono">{doc.author}</span>
              </div>
              <div className="mt-4 pt-3 border-t border-slate-800/40 flex items-center gap-2 text-sm font-medium text-cyan-300">
                Read <ArrowUpRight className="h-3 w-3" />
              </div>
            </Link>
          ))}
        </div>
      </main>
    </div>
  );
}
