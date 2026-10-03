'use client';

import { useEffect, useState, useRef } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { Terminal, Shield, AlertTriangle, Play, Square, Save, Activity, Command, X, Bot, HelpCircle, Radar, ListTree } from 'lucide-react';
import { api } from '@/lib/api';
import { useRequireAuth } from '@/lib/auth';
import Navbar from '@/components/Navbar';
import { LoadingScreen, TerminalCard } from '@/components/TerminalCard';
import type { APIResponse, LabSession, LabWorld, LabAnalysis } from '@/lib/types';

export default function RealTimeLabPage() {
  const { user, loading } = useRequireAuth();
  const params = useParams();
  const router = useRouter();
  
  const [session, setSession] = useState<LabSession | null>(null);
  const [world, setWorld] = useState<LabWorld | null>(null);
  const [analysis, setAnalysis] = useState<LabAnalysis | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [terminalOutput, setTerminalOutput] = useState<string[]>([]);
  const [command, setCommand] = useState('');
  const [busy, setBusy] = useState(false);
  
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!user || !params.id) return;
    
    setTerminalOutput(['> Initializing secure connection to CyberVerse Sandbox...', '> Allocating virtual environment...', '> Environment ready. Type "help" for available commands.']);

    api.get<APIResponse<LabSession>>(`/labs/sessions/${params.id}`)
      .then(res => { if (res.data) setSession(res.data); })
      .catch(err => setError(err instanceof Error ? err.message : 'Failed to load session'));
      
    api.get<APIResponse<LabWorld>>(`/labs/sessions/${params.id}/world`)
      .then(res => { if (res.data) setWorld(res.data); })
      .catch(err => console.warn('Failed to load world', err));
  }, [user, params.id]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [terminalOutput]);

  const executeCommand = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!command.trim() || busy) return;
    
    const cmd = command.trim();
    setTerminalOutput(prev => [...prev, `root@sandbox:~# ${cmd}`]);
    setCommand('');
    setBusy(true);

    try {
      if (cmd === 'help') {
        setTerminalOutput(prev => [...prev, 'Available commands:', '  scan    - Run network scan', '  logs    - Review correlated log events', '  analyze - Generate Neo analysis of the incident', '  status  - View lab status', '  clear   - Clear terminal']);
      } else if (cmd === 'clear') {
        setTerminalOutput([]);
      } else if (cmd === 'scan') {
        setTerminalOutput(prev => [...prev, 'Scanning target network (10.0.0.0/24)...']);
        await new Promise(r => setTimeout(r, 1200));
        const hosts = (world?.assets ?? []).map((a: any) => `  ${a.hostname ?? a.id} (${a.type}) ${a.ip_address ?? ''} - criticality: ${a.criticality ?? 'medium'}`);
        setTerminalOutput(prev => [...prev, `Found ${hosts.length} managed host(s) in scope:`, ...hosts, 'Unmanaged/off-scope hosts are excluded by the sandbox boundary.']);
      } else if (cmd === 'logs') {
        const logs = world?.logs ?? [];
        if (logs.length === 0) {
          setTerminalOutput(prev => [...prev, 'No correlated log events loaded.']);
        } else {
          setTerminalOutput(prev => [...prev, `Reviewing ${logs.length} correlated log event(s) for this incident:`]);
          logs.slice(0, 15).forEach((entry: any) => {
            const ts = entry.timestamp ?? entry.last_run ?? '';
            const who = entry.user_id ?? entry.asset_id ?? entry.device ?? entry.src ?? entry.source_ip ?? '';
            setTerminalOutput(p => [...p, `  [${ts}] ${entry.event ?? entry.type}: ${who} ${entry.command ?? entry.path ?? entry.dst_ip ?? ''}`]);
          });
          if (logs.length > 15) setTerminalOutput(p => [...p, `  ... and ${logs.length - 15} more events.`]);
        }
      } else if (cmd === 'analyze') {
        setTerminalOutput(prev => [...prev, 'Neo is correlating telemetry across the sandbox...']);
        await new Promise(r => setTimeout(r, 800));
        const res = await api.get<APIResponse<LabAnalysis>>(`/labs/sessions/${session?.id}/analysis`);
        const a = res.data;
        if (a) {
          setAnalysis(a);
          setTerminalOutput(prev => [
            ...prev,
            `[Neo Analysis] confidence ${a.confidence}% - ${a.overview}`,
            '',
            'Kill chain:',
            ...a.kill_chain.map((phase: any) => `  [${phase.label}] ${phase.summary} (${phase.event_count} events, ${phase.alert_count} alerts)${phase.critical ? ' [CRITICAL]' : ''}`),
            '',
            'Recommendations:',
            ...a.recommendations.map((r: string, i: number) => `  ${i + 1}. ${r}`),
          ]);
        }
      } else if (cmd === 'status') {
        setTerminalOutput(prev => [...prev, `Session ID: ${session?.id}`, `Difficulty: ${session?.difficulty ?? 'beginner'}`, `Status: ${session?.status}`]);
      } else {
        // Record event in backend
        await api.post(`/labs/sessions/${session?.id}/events`, {
          event_type: 'command_execution',
          details: { command: cmd }
        });
        setTerminalOutput(prev => [...prev, `bash: ${cmd}: command not found`]);
      }
    } catch (err) {
      setTerminalOutput(prev => [...prev, `Error executing command: ${err instanceof Error ? err.message : 'Unknown error'}`]);
    } finally {
      setBusy(false);
    }
  };

  const completeLab = async () => {
    if (!session) return;
    if (!confirm('Are you sure you want to end this lab session and submit your report?')) return;
    
    try {
      setBusy(true);
      // Generate the Neo debrief analysis before finalizing.
      try { await api.get(`/labs/sessions/${session.id}/analysis`); } catch { /* non-fatal */ }
      await api.post(`/labs/sessions/${session.id}/complete`);
      router.push('/labs');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to complete lab');
    } finally {
      setBusy(false);
    }
  };

  if (loading || !user || !session) return <LoadingScreen />;

  return (
    <div className="flex h-screen flex-col bg-cyber-dark text-cyber-text">
      <header className="flex h-14 items-center justify-between border-b border-cyber-border bg-cyber-bg px-6">
        <div className="flex items-center gap-4">
          <button onClick={() => router.push('/labs')} className="text-cyber-muted hover:text-cyber-primary">
            <X className="h-5 w-5" />
          </button>
          <div>
            <h1 className="font-mono text-sm font-semibold uppercase tracking-wider text-cyber-primary">
              Mission: {session.mission_slug?.replace(/_/g, ' ') || 'Sandbox Session'}
            </h1>
            <p className="text-xs text-cyber-muted">Status: {session.status} · Facility: {session.current_facility_slug}</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 rounded bg-cyber-surface px-3 py-1 font-mono text-xs text-cyber-success">
            <Activity className="h-3 w-3 animate-pulse" /> Live Sandbox
          </div>
          <button onClick={completeLab} disabled={busy} className="terminal-button py-1.5 text-xs">
            Submit & Exit
          </button>
        </div>
      </header>

      <div className="flex flex-1 overflow-hidden">
        {/* Left Sidebar - Objectives & Context */}
        <div className="w-80 border-r border-cyber-border bg-cyber-surface/30 flex flex-col">
          <div className="p-4 border-b border-cyber-border">
            <h2 className="font-semibold flex items-center gap-2 text-cyber-primary">
              <Shield className="h-4 w-4" /> Briefing
            </h2>
            <p className="mt-2 text-xs text-cyber-muted leading-relaxed">
              You are investigating an active alert at {String((world?.company as Record<string, unknown>)?.name ?? 'the target enterprise')}. 
              Use the terminal to run diagnostics, review logs, and collect evidence to resolve the incident.
            </p>
          </div>
          
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            <TerminalCard title="objectives.yml">
              <ul className="space-y-3">
                <li className="flex items-start gap-2 text-xs">
                  <Square className="mt-0.5 h-3 w-3 shrink-0 text-cyber-muted" />
                  <span>Analyze initial intrusion vector and compromised accounts.</span>
                </li>
                <li className="flex items-start gap-2 text-xs">
                  <Square className="mt-0.5 h-3 w-3 shrink-0 text-cyber-muted" />
                  <span>Identify lateral movement or privilege escalation.</span>
                </li>
                <li className="flex items-start gap-2 text-xs">
                  <Square className="mt-0.5 h-3 w-3 shrink-0 text-cyber-muted" />
                  <span>Recommend remediation and containment steps.</span>
                </li>
              </ul>
            </TerminalCard>

            <TerminalCard title="evidence.lockbox">
              {world?.evidence?.length === 0 ? (
                <p className="text-xs text-cyber-muted">No evidence collected yet.</p>
              ) : (
                <ul className="space-y-2">
                  {world?.evidence?.map((item: any, i: number) => (
                    <li key={i} className="text-xs flex items-center gap-2">
                      <Save className="h-3 w-3 text-cyber-primary" /> {item.title || item.evidence_key}
                    </li>
                  ))}
                  <li className="text-xs text-cyber-muted italic mt-2">Use &apos;analyze&apos; in terminal to collect evidence.</li>
                </ul>
              )}
            </TerminalCard>
          </div>
        </div>

        {/* Main Terminal Window */}
        <div className="flex flex-1 flex-col bg-black">
          {error && (
            <div className="bg-cyber-danger/10 p-2 text-center text-xs text-cyber-danger border-b border-cyber-danger/20">
              <AlertTriangle className="inline h-3 w-3 mr-1 mb-0.5" /> {error}
            </div>
          )}
          
          <div className="flex-1 overflow-y-auto p-4 font-mono text-sm text-cyber-text" onClick={() => document.getElementById('cmd-input')?.focus()}>
            {terminalOutput.map((line, i) => (
              <div key={i} className={`${line.startsWith('root@') ? 'text-cyber-primary mt-2' : line.startsWith('>') ? 'text-cyber-muted' : 'text-gray-300'} mb-1 break-all`}>
                {line}
              </div>
            ))}
            <div ref={endRef} />
          </div>
          
          <form onSubmit={executeCommand} className="flex items-center gap-2 border-t border-cyber-border bg-cyber-dark/80 p-3">
            <span className="font-mono text-cyber-primary font-bold ml-1">root@sandbox:~#</span>
            <input
              id="cmd-input"
              type="text"
              value={command}
              onChange={e => setCommand(e.target.value)}
              disabled={busy}
              className="flex-1 bg-transparent font-mono text-cyber-text focus:outline-none disabled:opacity-50"
              autoFocus
              autoComplete="off"
              spellCheck="false"
            />
          </form>
        </div>

        {/* Right Panel - Neo Analysis */}
        <div className="hidden w-96 flex-col border-l border-cyber-border bg-cyber-surface/30 lg:flex">
          <div className="flex items-center justify-between border-b border-cyber-border p-4">
            <h2 className="font-semibold flex items-center gap-2 text-cyber-primary">
              <Radar className="h-4 w-4" /> Neo Analysis
            </h2>
            <button
              onClick={async (e) => {
                e.preventDefault();
                try {
                  const res = await api.get<APIResponse<LabAnalysis>>(`/labs/sessions/${session?.id}/analysis`);
                  if (res.data) setAnalysis(res.data);
                } catch (err) {
                  setError(err instanceof Error ? err.message : 'Failed to load analysis');
                }
              }}
              disabled={busy}
              className="terminal-button py-1 text-xs"
            >
              Run
            </button>
          </div>

          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {!analysis ? (
              <p className="text-xs text-cyber-muted">
                Run <span className="font-mono text-cyber-primary">analyze</span> in the terminal to have Neo correlate
                the telemetry into a kill-chain narrative.
              </p>
            ) : (
              <>
                <TerminalCard title={`neo_analysis.confidence_${analysis.confidence}%`}>
                  <p className="text-xs leading-relaxed text-cyber-muted">{analysis.overview}</p>
                  {analysis.coverage && (
                    <p className="mt-2 text-xs text-cyber-text">
                      Evidence coverage: <span className="text-cyber-success">{analysis.coverage.collected}/{analysis.coverage.total} ({analysis.coverage.percent}%)</span>
                    </p>
                  )}
                </TerminalCard>

                <TerminalCard title="kill_chain">
                  <ul className="space-y-3">
                    {analysis.kill_chain.map((phase, i) => (
                      <li key={phase.phase} className="text-xs">
                        <div className="flex items-center justify-between">
                          <span className="flex items-center gap-1 font-semibold text-cyber-primary">
                            <ListTree className="h-3 w-3" /> {phase.label}
                            {phase.critical && <AlertTriangle className="h-3 w-3 text-cyber-danger" />}
                          </span>
                          <span className="text-cyber-muted">{phase.event_count} events</span>
                        </div>
                        <p className="mt-0.5 text-cyber-muted">{phase.summary}</p>
                        {phase.evidence && phase.evidence.length > 0 && (
                          <div className="mt-1 flex flex-wrap gap-1">
                            {phase.evidence.map((ev: any) => (
                              <span key={ev?.id ?? ev?.key} className={`rounded px-1.5 py-0.5 text-[10px] ${ev?.collected ? 'bg-cyber-success/15 text-cyber-success' : 'bg-cyber-surface text-cyber-muted'}`}>
                                {ev?.collected ? '●' : '○'} {ev?.title ?? ev?.key}
                              </span>
                            ))}
                          </div>
                        )}
                      </li>
                    ))}
                  </ul>
                </TerminalCard>

                <TerminalCard title="recommendations.yml">
                  <ol className="space-y-1.5">
                    {analysis.recommendations.map((rec, i) => (
                      <li key={i} className="text-xs text-cyber-text">
                        <span className="text-cyber-primary">{i + 1}.</span> {rec}
                      </li>
                    ))}
                  </ol>
                  {(analysis.safety_metadata as Record<string, unknown>)?.fictional_only && (
                    <p className="mt-3 text-[10px] text-cyber-muted italic">
                      Simulation data only — guidance applies to this fictional sandbox.
                    </p>
                  )}
                </TerminalCard>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
