'use client';

import { useEffect, useMemo, useState } from 'react';
import {
  Activity,
  Brain,
  CheckCircle2,
  Cloud,
  Code2,
  Database,
  FileSearch,
  FlaskConical,
  Lock,
  Play,
  Radar,
  ServerCog,
  ShieldCheck,
} from 'lucide-react';
import Navbar from '@/components/Navbar';
import { LoadingScreen, TerminalCard } from '@/components/TerminalCard';
import { api } from '@/lib/api';
import { useAuth } from '@/lib/auth';
import type { APIResponse, LabFacility, LabMission, LabSession, LabWorld } from '@/lib/types';

const facilityIcons: Record<string, typeof Activity> = {
  soc: Radar,
  enterprise: ServerCog,
  forensics: FileSearch,
  malware: FlaskConical,
  cloud: Cloud,
  secure_coding: Code2,
  network_defense: ShieldCheck,
};

const safetyRules = [
  'Built-in labs use fictional companies, identities, infrastructure, logs, and evidence.',
  'Malware analysis uses harmless training samples and simulated behavior replay.',
  'Home lab connections require ownership or explicit authorization, scope, and audit logs.',
];

export default function LabsPage() {
  const { user, loading } = useAuth();
  const [facilities, setFacilities] = useState<LabFacility[]>([]);
  const [missions, setMissions] = useState<LabMission[]>([]);
  const [activeSession, setActiveSession] = useState<LabSession | null>(null);
  const [world, setWorld] = useState<LabWorld | null>(null);
  const [selectedFacility, setSelectedFacility] = useState('soc');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!user) return;

    Promise.all([
      api.get<APIResponse<LabFacility[]>>('/labs/facilities'),
      api.get<APIResponse<LabMission[]>>('/labs/missions'),
    ])
      .then(([facilityResponse, missionResponse]) => {
        setFacilities(facilityResponse.data ?? []);
        setMissions(missionResponse.data ?? []);
      })
      .catch((err) => setError(err instanceof Error ? err.message : 'Failed to load CyberVerse Labs'));
  }, [user]);

  const selectedMissions = useMemo(
    () => missions.filter((mission) => facilities.find((facility) => facility.id === mission.facility_id)?.slug === selectedFacility),
    [facilities, missions, selectedFacility],
  );
  const starterMission = selectedMissions[0] ?? missions[0];

  async function startMission(mission: LabMission) {
    setBusy(true);
    setError(null);
    try {
      const sessionResponse = await api.post<APIResponse<LabSession>>('/labs/sessions', {
        mission_id: mission.id,
        facility: selectedFacility,
        difficulty: mission.difficulty,
        mode: 'solo',
        mentor_level: 'guided',
      });
      const session = sessionResponse.data;
      if (!session) throw new Error('Lab session did not start');
      setActiveSession(session);

      const worldResponse = await api.get<APIResponse<LabWorld>>(`/labs/sessions/${session.id}/world`);
      setWorld(worldResponse.data ?? null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start lab session');
    } finally {
      setBusy(false);
    }
  }

  if (loading || !user) return <LoadingScreen />;

  return (
    <>
      <Navbar />
      <main className="mx-auto max-w-7xl px-6 py-8">
        <div className="mb-6 flex flex-col justify-between gap-4 md:flex-row md:items-end">
          <div>
            <h1 className="text-2xl font-bold">
              CyberVerse <span className="text-cyber-primary">Labs</span>
            </h1>
            <p className="mt-1 max-w-3xl text-sm text-cyber-muted">
              Defensive cybersecurity simulations for SOC, enterprise, forensics, malware analysis, cloud, secure coding, and network defense.
            </p>
          </div>
          <button
            disabled={!starterMission || busy}
            onClick={() => starterMission && void startMission(starterMission)}
            className="terminal-button flex items-center justify-center gap-2 px-4 py-2 text-sm disabled:cursor-not-allowed disabled:opacity-50"
          >
            <Play className="h-4 w-4" />
            Start SOC Slice
          </button>
        </div>

        {error && (
          <div className="mb-6 rounded-md border border-cyber-danger/40 bg-cyber-danger/10 px-4 py-3 text-sm text-cyber-danger">
            {error}
          </div>
        )}

        <section className="mb-8 grid gap-4 lg:grid-cols-7">
          {facilities.map((facility) => {
            const Icon = facilityIcons[facility.facility_type] ?? Activity;
            const active = facility.slug === selectedFacility;
            return (
              <button
                key={facility.id}
                onClick={() => setSelectedFacility(facility.slug)}
                className={`rounded-md border px-3 py-3 text-left transition-colors ${
                  active
                    ? 'border-cyber-primary bg-cyber-primary/10 text-cyber-primary'
                    : 'border-cyber-border bg-cyber-surface/40 text-cyber-muted hover:border-cyber-primary/50 hover:text-cyber-primary'
                }`}
              >
                <Icon className="mb-3 h-5 w-5" />
                <div className="text-sm font-semibold text-cyber-text">{facility.name}</div>
                <div className="mt-1 font-mono text-[11px] uppercase tracking-normal">LVL {facility.min_level}</div>
              </button>
            );
          })}
        </section>

        <div className="grid gap-6 lg:grid-cols-[1.15fr_0.85fr]">
          <TerminalCard title="lab_missions.json">
            {selectedMissions.length === 0 ? (
              <p className="text-sm text-cyber-muted">This facility is ready in the world plan; playable missions are queued for the next content pass.</p>
            ) : (
              <div className="space-y-4">
                {selectedMissions.map((mission) => (
                  <div key={mission.id} className="rounded-md border border-cyber-border p-4">
                    <div className="mb-3 flex items-start justify-between gap-3">
                      <div>
                        <h2 className="font-semibold">{mission.title}</h2>
                        <p className="mt-1 text-sm text-cyber-muted">{mission.story_context}</p>
                      </div>
                      <span className="shrink-0 rounded border border-cyber-primary/40 px-2 py-1 font-mono text-xs text-cyber-primary">
                        {mission.difficulty}
                      </span>
                    </div>
                    <div className="flex flex-wrap gap-2 text-xs text-cyber-muted">
                      <span>{mission.mission_type.replace(/_/g, ' ')}</span>
                      <span>{mission.estimated_minutes}m</span>
                      <span>{mission.objectives.length} objectives</span>
                      <span>{mission.tools.length} tools</span>
                    </div>
                    <button
                      disabled={busy}
                      onClick={() => void startMission(mission)}
                      className="terminal-button-ghost mt-4 flex items-center gap-2 px-3 py-2 text-xs disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      <Play className="h-3.5 w-3.5" />
                      Launch Mission
                    </button>
                  </div>
                ))}
              </div>
            )}
          </TerminalCard>

          <div className="space-y-6">
            <TerminalCard title="safety_policy.yml">
              <div className="space-y-3">
                {safetyRules.map((rule) => (
                  <div key={rule} className="flex gap-3 text-sm">
                    <Lock className="mt-0.5 h-4 w-4 shrink-0 text-cyber-success" />
                    <span className="text-cyber-muted">{rule}</span>
                  </div>
                ))}
              </div>
            </TerminalCard>

            <TerminalCard title="ai_mentor.status">
              <div className="flex items-start gap-3">
                <Brain className="mt-1 h-5 w-5 text-cyber-secondary" />
                <div>
                  <h2 className="font-semibold">Guided mode online</h2>
                  <p className="mt-1 text-sm text-cyber-muted">
                    The mentor explains defensive workflows, reviews evidence, generates hints, and keeps every answer scoped to the fictional lab.
                  </p>
                </div>
              </div>
            </TerminalCard>
          </div>
        </div>

        {activeSession && world && (
          <section className="mt-8 grid gap-6 lg:grid-cols-3">
            <TerminalCard title="active_session.json">
              <div className="space-y-2 text-sm">
                <div className="flex items-center gap-2 text-cyber-success">
                  <CheckCircle2 className="h-4 w-4" />
                  Session {activeSession.status}
                </div>
                <p className="text-cyber-muted">Seed: <span className="font-mono text-cyber-text">{world.scenario_seed}</span></p>
                <p className="text-cyber-muted">Company: <span className="text-cyber-text">{String(world.company.name ?? 'Fictional enterprise')}</span></p>
              </div>
            </TerminalCard>
            <TerminalCard title="assets.ndjson">
              <p className="text-sm text-cyber-muted">{world.assets.length} generated assets and {world.identities.length} identities loaded.</p>
            </TerminalCard>
            <TerminalCard title="evidence.lockbox">
              <p className="text-sm text-cyber-muted">{world.evidence.length} evidence items available with synthetic chain-of-custody support.</p>
            </TerminalCard>
          </section>
        )}

        <section className="mt-8 grid gap-4 md:grid-cols-3">
          {[
            ['SOC Operations', 'SIEM, endpoint, email security, alerts, cases, timelines, and daily briefings.'],
            ['Scenario Generator', 'Varies company size, topology, users, alerts, misconfigurations, incidents, and compliance tasks.'],
            ['Progression', 'XP, levels, achievements, certifications, mission history, AI feedback, and career profile.'],
          ].map(([title, body]) => (
            <div key={title} className="rounded-md border border-cyber-border bg-cyber-surface/40 p-4">
              <Database className="mb-3 h-5 w-5 text-cyber-primary" />
              <h2 className="font-semibold">{title}</h2>
              <p className="mt-1 text-sm text-cyber-muted">{body}</p>
            </div>
          ))}
        </section>
      </main>
    </>
  );
}
