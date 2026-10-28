'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { Bell, CheckCircle2, Shield, AlertTriangle, Clock } from 'lucide-react';
import { useRequireAuth } from '@/lib/auth';
import { api } from '@/lib/api';

interface NotificationItem {
  id: string;
  type: 'mission' | 'lab' | 'mentor' | 'system';
  title: string;
  body: string;
  read: boolean;
  created_at: string;
}

export default function NotificationsPage() {
  const { user } = useRequireAuth();
  const [items, setItems] = useState<NotificationItem[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);

  useEffect(() => {
    if (!user) return;
    api.get<{ data: NotificationItem[] }>('/notifications').then(r => {
      const data = r.data.data || [];
      setItems(data);
      setUnreadCount(data.filter(i => !i.read).length);
    }).catch(() => setItems([]));
  }, [user]);

  const markRead = (id: string) => {
    api.post(`/notifications/${id}/read`).catch(() => {});
    setItems(prev => prev.map(i => i.id === id ? { ...i, read: true } : i));
    setUnreadCount(prev => Math.max(0, prev - 1));
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 to-slate-900 text-slate-100">
      <nav className="border-b border-slate-800/60 px-6 py-4 flex items-center justify-between backdrop-blur-sm bg-slate-900/40 sticky top-0 z-50">
        <Link href="/" className="font-mono text-lg font-bold text-cyan-400">CyberVerse</Link>
        <Link href="/team-chat" className="text-sm text-cyan-300 hover:text-cyan-200">Team Chat</Link>
      </nav>

      <main className="max-w-2xl mx-auto px-6 py-10">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-3xl font-extrabold">Notifications</h1>
          <div className="flex items-center gap-2 bg-slate-800/60 rounded-full px-3 py-1 text-xs font-mono text-cyan-300">
            <Bell className="h-3 w-3" /> {unreadCount} unread
          </div>
        </div>

        <div className="space-y-3">
          {items.map(n => (
            <button key={n.id} onClick={() => !n.read && markRead(n.id)} className={`w-full text-left bg-slate-900/60 border rounded-2xl p-5 transition-all hover:shadow-xl hover:shadow-cyan-900/10 ${n.read ? 'border-slate-800/60' : 'border-cyan-600/40 shadow-lg shadow-cyan-900/5'}`}>
              <div className="flex items-start gap-3">
                <div className={`h-9 w-9 rounded-xl flex items-center justify-center shrink-0 ${n.type === 'mission' ? 'bg-cyan-900/60 text-cyan-300' : n.type === 'mentor' ? 'bg-amber-900/60 text-amber-300' : n.type === 'lab' ? 'bg-rose-900/60 text-rose-300' : 'bg-slate-700 text-slate-300'}`}>
                  {n.type === 'mission' ? <Shield className="h-4 w-4" /> : n.type === 'mentor' ? <Clock className="h-4 w-4" /> : n.type === 'lab' ? <AlertTriangle className="h-4 w-4" /> : <Bell className="h-4 w-4" />}
                </div>
                <div className="flex-1 min-w-0">
                  <h3 className="font-bold text-sm mb-1">{n.title}</h3>
                  <p className="text-xs text-slate-400 leading-relaxed">{n.body}</p>
                  <div className="flex items-center gap-3 mt-2 text-[11px] text-slate-500 font-mono">
                    <span>{new Date(n.created_at).toLocaleString()}</span>
                    {n.read ? <span className="text-green-400 flex items-center gap-1"><CheckCircle2 className="h-3 w-3" /> Read</span> : <span className="text-cyan-300">Unread</span>}
                  </div>
                </div>
              </div>
            </button>
          ))}
        </div>
      </main>
    </div>
  );
}
