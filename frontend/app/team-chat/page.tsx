'use client';

import { useEffect, useState, useCallback, useRef } from 'react';
import Link from 'next/link';
import { Send, Users, Shield, Clock, Bell, FileText, MessageSquare, CheckCircle2 } from 'lucide-react';
import { useRequireAuth } from '@/lib/auth';
import { api } from '@/lib/api';
import { useToast } from '@/lib/toast';

interface ChatMessage {
  id: string;
  sender: string;
  text: string;
  timestamp: string;
  type: 'text' | 'image' | 'file';
  image_url?: string;
  file_url?: string;
}

interface TeamData {
  team_id: string;
  name: string;
  members: Array<{ id: string; username: string; role: string; avatar_url?: string }>;
  role: string;
  is_owner: boolean;
  created_at: string;
  description: string;
}

export default function TeamChatPage() {
  const { user, loading } = useRequireAuth();
  const { showToast } = useToast();
  const [teamData, setTeamData] = useState<TeamData | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [typing, setTyping] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });

  useEffect(() => { scrollToBottom(); }, [messages]);

  useEffect(() => {
    if (!user) return;
    const load = async () => {
      try {
        const [tRes, mRes] = await Promise.all([
          api.get<{ data: TeamData }>('/teams/current'),
          api.get<{ data: ChatMessage[] }>('/teams/messages'),
        ]);
        setTeamData(tRes.data.data);
        setMessages(mRes.data.data);
      } catch (e: any) {
        showToast('Failed to load team data: ' + (e?.message || 'Unknown error'), 'error');
      }
    };
    load();
  }, [user, showToast]);

  const handleSend = useCallback(async () => {
    if (!input.trim() || !teamData) return;
    setIsSending(true);
    try {
      const res = await api.post<ChatMessage>('/teams/messages', {
        team_id: teamData.team_id,
        message: input.trim(),
        type: 'text',
      });
      setMessages(prev => [...prev, res.data.data]);
      setInput('');
    } catch (err: any) {
      showToast('Failed to send message', 'error');
    } finally {
      setIsSending(false);
    }
  }, [input, teamData, showToast]);

  if (loading || !user) return <div className="p-8 text-center">Loading chat...</div>;

  if (!teamData) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-slate-950 to-slate-900 text-slate-100">
        <nav className="border-b border-slate-800/60 px-6 py-4 flex items-center justify-between backdrop-blur-sm bg-slate-900/40 sticky top-0 z-50">
          <Link href="/" className="font-mono text-lg font-bold text-cyan-400">CyberVerse</Link>
          <Link href="/teams" className="text-sm text-cyan-300 hover:text-cyan-200">Back to Teams</Link>
        </nav>
        <main className="max-w-4xl mx-auto px-6 py-20 text-center">
          <Users className="mx-auto h-16 w-16 text-cyan-400/40 mb-6" />
          <h2 className="text-3xl font-bold mb-4">No Team Active</h2>
          <p className="text-slate-400 mb-8">Join or create a team to start collaborating with other agents.</p>
          <Link href="/teams" className="inline-flex items-center gap-2 bg-cyan-500 hover:bg-cyan-600 text-white px-8 py-3 rounded-lg font-semibold transition-colors shadow-lg shadow-cyan-500/20">
            <Users className="h-4 w-4" /> Create Team
          </Link>
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 to-slate-900 text-slate-100">
      <nav className="border-b border-slate-800/60 px-6 py-4 flex items-center justify-between backdrop-blur-sm bg-slate-900/40 sticky top-0 z-50">
        <div className="flex items-center gap-3">
          <Link href="/" className="font-mono text-lg font-bold text-cyan-400">CyberVerse</Link>
          <span className="text-slate-600">/</span>
          <span className="font-medium text-cyan-300">Team Chat</span>
        </div>
        <Link href="/teams" className="text-sm text-cyan-300 hover:text-cyan-200">Back to Teams</Link>
      </nav>

      <main className="max-w-3xl mx-auto px-6 py-8">
        <header className="mb-8">
          <h1 className="text-3xl font-extrabold tracking-tight text-white">{teamData.name}</h1>
          <p className="text-sm text-slate-400 mt-1 font-mono">Team ID: {teamData.team_id}</p>
        </header>

        <section className="bg-slate-900/60 border border-slate-800/60 rounded-2xl p-6 shadow-xl shadow-cyan-900/10 backdrop-blur-md mb-8">
          <div className="space-y-6 max-h-[60vh] overflow-y-auto pr-2">
            {messages.length === 0 && (
              <div className="text-center text-slate-500 py-12">
                <MessageSquare className="mx-auto h-10 w-10 mb-2 opacity-40" />
                <p className="text-sm">No messages yet. Start the conversation!</p>
              </div>
            )}
            {messages.map(msg => (
              <article key={msg.id} className="flex gap-4">
                <div className={`flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center text-xs font-bold ${msg.sender === user.email ? 'bg-cyan-600 text-white' : 'bg-slate-700 text-cyan-300'}`}>
                  {msg.sender?.charAt(0)?.toUpperCase() ?? 'U'}
                </div>
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-xs font-bold text-cyan-300">{msg.sender}</span>
                    <span className="text-[11px] text-slate-500">{new Date(msg.timestamp).toLocaleString()}</span>
                  </div>
                  <p className="text-sm text-slate-100 leading-relaxed">{msg.text}</p>
                  {msg.image_url && (
                    <img src={msg.image_url} alt="Shared image" className="mt-2 max-w-xs rounded-lg border border-slate-700 shadow-lg shadow-cyan-900/20" />
                  )}
                  {msg.file_url && (
                    <a href={msg.file_url} target="_blank" rel="noopener noreferrer" className="mt-2 inline-block text-xs bg-slate-700 hover:bg-slate-600 text-cyan-300 px-3 py-1 rounded-full font-medium transition">File</a>
                  )}
                </div>
              </article>
            ))}
            <div ref={messagesEndRef} />
          </div>

          <div className="mt-6 flex gap-3">
            <input
              type="text"
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter') handleSend(); }}
              placeholder="Type a message to the team..."
              className="flex-1 bg-slate-950 border border-slate-700 rounded-xl px-4 py-3 text-sm text-white placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-cyan-500/40 focus:border-cyan-500 transition-all"
              aria-label="Team message input"
            />
            <button
              onClick={handleSend}
              disabled={isSending || !input.trim()}
              aria-label="Send message"
              className="bg-cyan-600 hover:bg-cyan-500 disabled:opacity-40 disabled:cursor-not-allowed text-white px-5 py-3 rounded-xl font-semibold shadow-lg shadow-cyan-600/20 transition-all active:scale-[0.98]"
            >
              <Send className="h-4 w-4" />
            </button>
          </div>
        </section>

        <section className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <Link href="/teams" className="group bg-slate-900/40 hover:bg-slate-900/70 border border-slate-800/60 hover:border-cyan-600/30 rounded-2xl p-5 transition-all hover:shadow-xl hover:shadow-cyan-900/20 hover:-translate-y-0.5">
            <Shield className="h-6 w-6 text-cyan-400 mb-3" />
            <h3 className="font-bold text-white mb-1">Team Dashboard</h3>
            <p className="text-xs text-slate-400">View standings, roles, and active missions.</p>
          </Link>
          <Link href="/docs" className="group bg-slate-900/40 hover:bg-slate-900/70 border border-slate-800/60 hover:border-cyan-600/30 rounded-2xl p-5 transition-all hover:shadow-xl hover:shadow-cyan-900/20 hover:-translate-y-0.5">
            <FileText className="h-6 w-6 text-cyan-400 mb-3" />
            <h3 className="font-bold text-white mb-1">Document & Reports</h3>
            <p className="text-xs text-slate-400">Team reports, strategy docs, version-controlled files.</p>
          </Link>
          <Link href="/notifications" className="group bg-slate-900/40 hover:bg-slate-900/70 border border-slate-800/60 hover:border-cyan-600/30 rounded-2xl p-5 transition-all hover:shadow-xl hover:shadow-cyan-900/20 hover:-translate-y-0.5">
            <Bell className="h-6 w-6 text-cyan-400 mb-3" />
            <h3 className="font-bold text-white mb-1">Notifications</h3>
            <p className="text-xs text-slate-400">Real-time alerts from missions, labs, and mentors.</p>
          </Link>
        </section>
      </main>
    </div>
  );
}
