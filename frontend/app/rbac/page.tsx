'use client';

import Link from 'next/link';
import { Shield, Users, Lock, UserPlus, KeyRound, AlertTriangle } from 'lucide-react';
import { useRequireAuth } from '@/lib/auth';

export default function RBACPage() {
  const { user } = useRequireAuth();

  const roles = [
    { name: 'Super Admin', level: 9, color: 'bg-rose-600', desc: 'Full system control, server access, audit logs' },
    { name: 'Administrator', level: 8, color: 'bg-amber-600', desc: 'User management, content moderation, reports' },
    { name: 'Instructor', level: 7, color: 'bg-violet-600', desc: 'Create courses, review labs, view analytics' },
    { name: 'Moderator', level: 5, color: 'bg-blue-600', desc: 'Review submissions, manage discussions' },
    { name: 'Premium Student', level: 4, color: 'bg-cyan-500', desc: 'Advanced labs, premium courses' },
    { name: 'Student', level: 2, color: 'bg-emerald-500', desc: 'Core missions, basic labs' },
    { name: 'Guest', level: 1, color: 'bg-slate-500', desc: 'Preview content, limited access' },
  ];

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 to-slate-900 text-slate-100">
      <nav className="border-b border-slate-800/60 px-6 py-4 flex items-center justify-between backdrop-blur-sm bg-slate-900/40 sticky top-0 z-50">
        <Link href="/" className="font-mono text-lg font-bold text-cyan-400">CyberVerse</Link>
        <Link href="/simulation" className="text-sm text-cyan-300 hover:text-cyan-200">Simulation</Link>
      </nav>

      <main className="max-w-5xl mx-auto px-6 py-10">
        <header className="mb-10">
          <h1 className="text-4xl font-extrabold tracking-tight mb-3">Role-Based Access Control</h1>
          <p className="text-slate-400">Every resource, endpoint, and simulation module is protected by role-level authorization.</p>
        </header>

        <section className="mb-10 bg-gradient-to-br from-slate-900/40 to-slate-950 border border-cyan-900/20 rounded-3xl p-8 shadow-xl shadow-cyan-900/5 backdrop-blur-md">
          <h2 className="text-2xl font-bold mb-6 flex items-center gap-3">
            <Shield className="h-6 w-6 text-cyan-400" /> Current Access Level
          </h2>
          <div className="flex items-center gap-6">
            <div className="h-16 w-16 rounded-full bg-gradient-to-br from-cyan-600 to-blue-700 flex items-center justify-center shadow-lg shadow-cyan-600/30">
              <Lock className="h-7 w-7 text-white" />
            </div>
            <div>
              <h3 className="text-xl font-extrabold">{user?.role || 'guest'}</h3>
              <p className="text-sm text-slate-400 font-mono">Level: {user?.role === 'super_admin' ? 9 : user?.role === 'administrator' ? 8 : user?.role === 'instructor' ? 7 : user?.role === 'moderator' ? 5 : user?.role === 'premium_student' ? 4 : 2}</p>
              <p className="text-xs text-cyan-400 mt-1">Verified via Clerk auth + backend JWT</p>
            </div>
          </div>
        </section>

        <section>
          <h2 className="text-xl font-extrabold mb-6">Access Levels</h2>
          <div className="grid md:grid-cols-2 gap-4">
            {roles.map(role => (
              <div key={role.name} className="bg-slate-900/40 border border-slate-800/50 rounded-2xl p-5 hover:border-cyan-600/30 transition-all hover:-translate-y-0.5 shadow-lg shadow-cyan-900/5">
                <div className="flex items-center gap-3 mb-3">
                  <div className={`h-8 w-8 rounded-lg ${role.color} flex items-center justify-center shadow-md`}>
                    <Users className="h-4 w-4 text-white" />
                  </div>
                  <div>
                    <h4 className="font-bold text-sm">{role.name}</h4>
                    <span className="text-[10px] text-cyan-400 font-mono">Level {role.level}</span>
                  </div>
                </div>
                <p className="text-xs text-slate-400">{role.desc}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="mt-10 bg-gradient-to-br from-amber-900/10 to-slate-900 border border-amber-900/20 rounded-3xl p-8">
          <h2 className="text-xl font-extrabold mb-4 flex items-center gap-3">
            <AlertTriangle className="h-5 w-5 text-amber-400" /> Security Notice
          </h2>
          <ul className="space-y-2 text-sm text-slate-300">
            <li>• All endpoints verify JWT access tokens via Clerk middleware and backend middleware.</li>
            <li>• Sensitive operations (lab start, admin actions) require elevated roles confirmed server-side.</li>
            <li>• No role escalation is permitted through client-side navigation.</li>
            <li>• RBAC is enforced at both middleware and endpoint layers.</li>
          </ul>
        </section>
      </main>
    </div>
  );
}
