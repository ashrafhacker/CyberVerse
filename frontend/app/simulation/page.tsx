'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { Terminal, Shield, AlertTriangle, CheckCircle2, Clock, Zap, ChevronRight, Eye, Lock, Wifi, Server, FileSearch, Radio } from 'lucide-react';

interface SimulationModule {
  id: string;
  title: string;
  category: 'terminal' | 'network' | 'incident' | 'forensics' | 'osint';
  difficulty: 'beginner' | 'intermediate' | 'advanced' | 'expert';
  status: 'available' | 'in_progress' | 'completed';
  time_estimate: string;
  completed_at?: string;
  progress_percent: number;
}

interface TerminalLog {
  timestamp: string;
  text: string;
  type: 'info' | 'warning' | 'success' | 'danger';
  module: string;
}

const SIM_MODULES: SimulationModule[] = [
  { id: 'TERM-001', title: 'SOC Terminal Access', category: 'terminal', difficulty: 'beginner', status: 'available', time_estimate: '15 min', progress_percent: 0 },
  { id: 'TERM-002', title: 'Linux System Investigation', category: 'terminal', difficulty: 'intermediate', status: 'available', time_estimate: '30 min', progress_percent: 0 },
  { id: 'TERM-003', title: 'Advanced Forensics Shell', category: 'terminal', difficulty: 'advanced', status: 'available', time_estimate: '45 min', progress_percent: 0 },
  { id: 'NET-001', title: 'Network Traffic Analysis', category: 'network', difficulty: 'beginner', status: 'available', time_estimate: '20 min', progress_percent: 0 },
  { id: 'NET-002', title: 'Firewall & IDS Review', category: 'network', difficulty: 'intermediate', status: 'available', time_estimate: '40 min', progress_percent: 0 },
  { id: 'INC-001', title: 'Incident Response Drill', category: 'incident', difficulty: 'intermediate', status: 'available', time_estimate: '60 min', progress_percent: 0 },
  { id: 'INC-002', title: 'Breach Containment', category: 'incident', difficulty: 'advanced', status: 'available', time_estimate: '75 min', progress_percent: 0 },
  { id: 'FORENSICS-001', title: 'Evidence Collection & Chain', category: 'forensics', difficulty: 'intermediate', status: 'available', time_estimate: '35 min', progress_percent: 0 },
  { id: 'OSINT-001', title: 'Open Source Intelligence', category: 'osint', difficulty: 'beginner', status: 'available', time_estimate: '25 min', progress_percent: 0 },
];

export default function CyberSimulationEngine() {
  const [selectedModule, setSelectedModule] = useState<SimulationModule>(SIM_MODULES[0]);
  const [logs, setLogs] = useState<TerminalLog[]>([]);
  const [isRunning, setIsRunning] = useState(false);
  const [scanProgress, setScanProgress] = useState(0);
  const [completedModules, setCompletedModules] = useState<string[]>([]);
  const logEndRef = useRef<HTMLDivElement>(null);

  const addLog = useCallback((text: string, type: TerminalLog['type'] = 'info', module: string = selectedModule.id) => {
    setLogs(prev => [...prev, { timestamp: new Date().toISOString(), text, type, module }]);
  }, [selectedModule]);

  const startSimulation = useCallback(() => {
    if (isRunning) return;
    setIsRunning(true);
    setScanProgress(0);
    addLog(`Initializing simulation for ${selectedModule.title}...`, 'info');
    addLog(`Module: ${selectedModule.id} | Difficulty: ${selectedModule.difficulty}`, 'info');

    const interval = setInterval(() => {
      setScanProgress(prev => {
        const next = prev + Math.random() * 15 + 5;
        if (next >= 100) {
          clearInterval(interval);
          setIsRunning(false);
          setCompletedModules(prev => [...prev, selectedModule.id]);
          addLog(`Simulation complete. All objectives verified.`, 'success');
          addLog(`Results: No critical vulnerabilities detected in simulated environment.`, 'success');
          return 100;
        }
        addLog(`Progress: ${(next).toFixed(0)}% — analyzing simulated network topology...`, next > 30 ? 'warning' : 'info');
        if (next > 70) addLog('Deep packet inspection complete.', 'success');
        return next;
      });
    }, 1200);
  }, [isRunning, selectedModule, addLog]);

  const getModuleIcon = (cat: string) => {
    switch (cat) {
      case 'terminal': return <Terminal className="h-4 w-4" />;
      case 'network': return <Wifi className="h-4 w-4" />;
      case 'incident': return <AlertTriangle className="h-4 w-4" />;
      case 'forensics': return <FileSearch className="h-4 w-4" />;
      case 'osint': return <Radio className="h-4 w-4" />;
      default: return <Shield className="h-4 w-4" />;
    }
  };

  const getModuleColor = (cat: string) => {
    switch (cat) {
      case 'terminal': return 'from-cyan-900/30 border-cyan-800/60 text-cyan-300';
      case 'network': return 'from-blue-900/30 border-blue-800/60 text-blue-300';
      case 'incident': return 'from-amber-900/30 border-amber-800/60 text-amber-300';
      case 'forensics': return 'from-violet-900/30 border-violet-800/60 text-violet-300';
      case 'osint': return 'from-rose-900/30 border-rose-800/60 text-rose-300';
      default: return 'from-cyan-900/30 border-cyan-800/60 text-cyan-300';
    }
  };

  useEffect(() => { if (logEndRef.current) logEndRef.current.scrollIntoView({ behavior: 'smooth' }); }, [logs]);

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 via-slate-950 to-slate-950 text-slate-100 selection:bg-cyan-500/30 selection:text-cyan-200">
      {/* Immersive header */}
      <header className="relative overflow-hidden border-b border-cyan-900/20 bg-gradient-to-r from-slate-950 via-cyan-950/10 to-slate-950">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_30%_20%,rgba(6,182,212,0.08)_0%,transparent_60%)] pointer-events-none" />
        <div className="relative max-w-6xl mx-auto px-6 py-14 md:py-20">
          <div className="flex items-center gap-3 mb-6">
            <span className="h-1.5 w-10 rounded-full bg-gradient-to-r from-cyan-400 to-cyan-600" />
            <span className="text-xs font-mono tracking-[0.2em] text-cyan-400/70 uppercase">CyberVerse Simulation Engine</span>
          </div>
          <h1 className="text-4xl md:text-6xl font-black tracking-tight text-white mb-4 leading-tight">
            <span className="bg-gradient-to-r from-cyan-300 via-blue-200 to-violet-200 bg-clip-text text-transparent">Immersive</span> Cybersecurity Labs
          </h1>
          <p className="text-lg text-slate-400 max-w-2xl leading-relaxed mb-8">
            Run safe, fully simulated cybersecurity missions inside isolated sandbox environments. 
            No external systems are ever targeted — every target, network, and evidence trail is fictional and purpose-built for learning.
          </p>
          <div className="flex items-center gap-6 text-xs text-slate-500 font-mono">
            <span className="flex items-center gap-1.5"><Lock className="h-3 w-3 text-cyan-500" /> Sandbox Isolated</span>
            <span className="flex items-center gap-1.5"><Eye className="h-3 w-3 text-cyan-500" /> No Real Targets</span>
            <span className="flex items-center gap-1.5"><Zap className="h-3 w-3 text-cyan-500" /> Fictional Data Only</span>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-6 py-10">
        <div className="grid lg:grid-cols-3 gap-8">
          {/* Simulation Modules */}
          <section className="lg:col-span-2 space-y-8">
            <div className="flex items-center justify-between mb-2">
              <h2 className="text-xl font-extrabold text-white tracking-tight">Simulation Modules</h2>
              <span className="text-xs text-cyan-400 font-mono">{SIM_MODULES.length} modules</span>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              {SIM_MODULES.map(mod => (
                <button
                  key={mod.id}
                  onClick={() => setSelectedModule(mod)}
                  className={`text-left rounded-2xl border p-5 transition-all duration-300 hover:-translate-y-1 hover:shadow-xl hover:shadow-cyan-900/20 ${
                    selectedModule.id === mod.id ? 'bg-slate-900 border-cyan-600/60 shadow-lg shadow-cyan-900/10' : `bg-gradient-to-br from-slate-900/50 to-slate-950/50 border-slate-800/50 hover:border-cyan-600/40 ${getModuleColor(mod.category)}`
                  }`}
                >
                  <div className="flex items-start justify-between mb-3">
                    <div className={`p-2 rounded-xl bg-gradient-to-br from-cyan-900/20 to-cyan-600/10 ${getModuleColor(mod.category)}`}>
                      {getModuleIcon(mod.category)}
                    </div>
                    <span className={`text-[10px] font-mono px-2 py-0.5 rounded-full border ${
                      mod.difficulty === 'beginner' ? 'bg-cyan-900/30 text-cyan-300 border-cyan-800/40' :
                      mod.difficulty === 'intermediate' ? 'bg-amber-900/20 text-amber-300 border-amber-800/30' :
                      'bg-rose-900/20 text-rose-300 border-rose-800/30'
                    }`}>{mod.difficulty}</span>
                  </div>
                  <h3 className="font-bold text-white text-sm mb-1">{mod.title}</h3>
                  <p className="text-xs text-slate-400 mb-3">{mod.category.replace('-', ' ')} · {mod.time_estimate}</p>
                  <div className="w-full h-1.5 bg-slate-800 rounded-full overflow-hidden">
                    <div className="h-full bg-gradient-to-r from-cyan-600 to-blue-500 rounded-full transition-all duration-500" style={{ width: `${mod.status === 'completed' ? 100 : mod.progress_percent}%` }} />
                  </div>
                  <span className="text-[10px] text-cyan-400/60 font-mono mt-1 block">{mod.status === 'completed' ? 'Completed' : mod.status === 'in_progress' ? 'In Progress' : 'Ready'}</span>
                </button>
              ))}
            </div>

            {/* Active Simulation Terminal */}
            <section className="bg-gradient-to-br from-slate-900/80 to-slate-950 border border-cyan-900/20 rounded-3xl overflow-hidden shadow-2xl shadow-cyan-900/10 backdrop-blur-md">
              <div className="border-b border-cyan-900/20 px-6 py-4 flex items-center justify-between bg-gradient-to-r from-cyan-950/20 to-slate-950/20">
                <div className="flex items-center gap-3">
                  <Terminal className="h-5 w-5 text-cyan-400" />
                  <h3 className="font-extrabold text-lg tracking-tight text-white">Simulation Terminal</h3>
                  <span className="text-[10px] font-mono bg-cyan-900/40 text-cyan-300 px-2 py-0.5 rounded-full border border-cyan-800/40">{selectedModule.id}</span>
                  <span className="text-[10px] font-mono bg-slate-800/60 text-slate-400 px-2 py-0.5 rounded-full">{selectedModule.difficulty}</span>
                </div>
                <button
                  onClick={() => { if (!isRunning) startSimulation(); }}
                  disabled={isRunning || selectedModule.status === 'completed'}
                  className="bg-cyan-600 hover:bg-cyan-500 disabled:opacity-40 disabled:cursor-not-allowed text-white text-sm font-bold px-5 py-2 rounded-xl shadow-lg shadow-cyan-600/20 transition-all active:scale-[0.98] flex items-center gap-2"
                >
                  <Zap className="h-3.5 w-3.5" /> {isRunning ? 'Running...' : 'Launch Simulation'}
                </button>
              </div>
              <div className="p-6">
                <div className="bg-black rounded-2xl border border-cyan-950/40 overflow-hidden shadow-inner shadow-cyan-900/20">
                  <div className="flex items-center gap-2 px-4 py-2.5 bg-gradient-to-r from-cyan-950/20 to-slate-950 border-b border-cyan-950/30">
                    <div className="h-2.5 w-2.5 rounded-full bg-rose-500/80 shadow-sm shadow-rose-500/40" />
                    <div className="h-2.5 w-2.5 rounded-full bg-amber-500/80 shadow-sm shadow-amber-500/30" />
                    <div className="h-2.5 w-2.5 rounded-full bg-emerald-500/80 shadow-sm shadow-emerald-500/30" />
                    <span className="text-[10px] text-cyan-500/50 font-mono ml-2">cyberverse-terminal</span>
                  </div>
                  <div className="p-5 font-mono text-xs leading-7 min-h-[320px] max-h-[320px] overflow-y-auto select-text space-y-0.5">
                    <p className="text-cyan-400/80 mb-2">$ cyberverse --init --sandbox --isolation=full</p>
                    <p className="text-slate-500 text-[10px] mb-4">Initializing isolated environment... All hosts fictional. No external connections permitted.</p>
                    {logs.map((log, i) => (
                      <p key={i} className={`${
                        log.type === 'success' ? 'text-emerald-400' :
                        log.type === 'danger' ? 'text-rose-400' :
                        log.type === 'warning' ? 'text-amber-400' : 'text-slate-400'
                      }`}>
                        <span className="text-cyan-500/40">[{new Date(log.timestamp).toLocaleTimeString()}]</span>{' '}
                        <span className="text-cyan-600/70">[{log.module}]</span> {log.text}
                      </p>
                    ))}
                    {isRunning && (
                      <p className="text-amber-400 animate-pulse">
                        <span className="text-cyan-500/40">[{new Date().toLocaleTimeString()}]</span>{' '}
                        <span className="text-cyan-600/70">[{selectedModule.id}]</span> Running analysis... please wait.
                      </p>
                    )}
                    {!isRunning && logs.length > 0 && selectedModule.status === 'completed' && (
                      <p className="text-emerald-400 font-bold mt-2">✓ Module completed. Evidence collected. Sandbox isolated environment preserved.</p>
                    )}
                  </div>
                  {/* Progress bar */}
                  <div className="px-5 py-3 bg-gradient-to-r from-cyan-950/10 to-slate-950 border-t border-cyan-950/20">
                    <div className="flex items-center gap-3 mb-2">
                      <span className="text-[10px] text-cyan-400 font-mono">Progress</span>
                      <span className="text-[10px] text-amber-300 font-mono">{Math.round(scanProgress)}%</span>
                    </div>
                    <div className="h-1.5 w-full bg-slate-950 rounded-full overflow-hidden shadow-inner shadow-cyan-950/20">
                      <div className="h-full bg-gradient-to-r from-cyan-600 via-blue-500 to-violet-500 rounded-full transition-all duration-300 ease-out relative" style={{ width: `${scanProgress}%` }}>
                        <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent animate-shimmer" />
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </section>
          </section>

          {/* Sidebar info */}
          <aside className="space-y-6">
            <section className="bg-gradient-to-br from-slate-900/60 to-slate-950 border border-cyan-900/20 rounded-3xl p-6 backdrop-blur-md shadow-xl shadow-cyan-900/5">
              <h3 className="font-extrabold text-lg mb-4 flex items-center gap-2">
                <Shield className="h-4 w-4 text-cyan-400" /> Safety Rules
              </h3>
              <ul className="space-y-3 text-sm text-slate-300">
                <li className="flex items-start gap-2"><CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0 mt-0.5" /> <span>Every host, IP, and company name is fictional.</span></li>
                <li className="flex items-start gap-2"><CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0 mt-0.5" /> <span>All evidence and alerts are generated by the simulation engine.</span></li>
                <li className="flex items-start gap-2"><CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0 mt-0.5" /> <span>Lab containers are fully isolated — no real targets.</span></li>
                <li className="flex items-start gap-2"><CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0 mt-0.5" /> <span>Results never affect real systems or external networks.</span></li>
              </ul>
            </section>

            <section className="bg-gradient-to-br from-slate-900/60 to-slate-950 border border-cyan-900/20 rounded-3xl p-6 backdrop-blur-md shadow-xl shadow-cyan-900/5">
              <h3 className="font-extrabold text-lg mb-4 flex items-center gap-2">
                <Server className="h-4 w-4 text-cyan-400" /> Module Details
              </h3>
              <dl className="space-y-2 text-sm">
                <div className="flex justify-between"><dt className="text-slate-500">Module</dt><dd className="font-mono text-cyan-300">{selectedModule.id}</dd></div>
                <div className="flex justify-between"><dt className="text-slate-500">Category</dt><dd className="text-cyan-300">{selectedModule.category}</dd></div>
                <div className="flex justify-between"><dt className="text-slate-500">Difficulty</dt><dd className="text-amber-300">{selectedModule.difficulty}</dd></div>
                <div className="flex justify-between"><dt className="text-slate-500">Est. Duration</dt><dd className="text-cyan-300">{selectedModule.time_estimate}</dd></div>
                <div className="flex justify-between"><dt className="text-slate-500">Status</dt><dd className="font-mono text-emerald-300">{selectedModule.status}</dd></div>
              </dl>
            </section>
          </aside>
        </div>
      </main>

      <style jsx global>{`
        @keyframes shimmer {
          0% { background-position: -200% 0; }
          100% { background-position: 200% 0; }
        }
        .animate-shimmer {
          background-size: 400% 100%;
          animation: shimmer 2s infinite linear;
        }
      `}</style>
    </div>
  );
}
