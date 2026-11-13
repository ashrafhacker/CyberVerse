'use client';

import Link from 'next/link';
import {
  Activity,
  AlertCircle,
  CheckCircle,
  ChevronLeft,
  ChevronRight,
  FileText,
  Filter,
  Loader2,
  Plus,
  Search,
  Shield,
  ShieldAlert,
  X,
} from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';
import { api } from '@/lib/api';

interface ChainOfCustodyEntry {
  evidence_id: string;
  case_id: string;
  action: string;
  actor: string;
  timestamp: string;
  notes: string | null;
}

interface Case {
  id: string;
  case_number: string;
  title: string;
  description: string;
  severity: string;
  status: string;
  opened_at: string;
  closed_at: string | null;
  evidence_count: number;
}

interface Evidence {
  id: string;
  case_id: string;
  name: string;
  category: string;
  hash_sha256: string | null;
  size_bytes: number | null;
  source_host: string | null;
  status: string;
  notes: string | null;
  collected_by: string | null;
  chain_of_custody: ChainOfCustodyEntry[];
}

interface CaseSummary {
  case: Case;
  evidence_count: number;
  evidence: Evidence[];
}

interface PageData<T> {
  items: T[];
  total: number;
  page: number;
  total_pages: number;
}

const STATUS_COLORS: Record<string, string> = {
  open: 'bg-blue-500/20 text-blue-400',
  investigating: 'bg-amber-500/20 text-amber-400',
  contained: 'bg-orange-500/20 text-orange-400',
  pending: 'bg-gray-500/20 text-gray-400',
  verified: 'bg-green-500/20 text-green-400',
  compromised: 'bg-red-500/20 text-red-400',
  closed: 'bg-slate-500/20 text-slate-400',
};

const SEVERITY_COLORS: Record<string, string> = {
  critical: 'bg-red-500/20 text-red-400',
  high: 'bg-orange-500/20 text-orange-400',
  medium: 'bg-amber-500/20 text-amber-400',
  low: 'bg-green-500/20 text-green-400',
};

const CATEGORIES = [
  'disk_image',
  'memory_dump',
  'log_file',
  'network_capture',
  'document',
  'mobile',
  'other',
];

const EVIDENCE_STATUSES = [
  'pending',
  'verified',
  'compromised',
];

const errorMessage = (err: unknown, fallback: string): string =>
  err instanceof Error && err.message ? err.message : fallback;

export default function DigitalForensicsPage() {
  const [cases, setCases] = useState<Case[]>([]);
  const [casePage, setCasePage] = useState(1);
  const [caseTotalPages, setCaseTotalPages] = useState(1);
  const [caseTotal, setCaseTotal] = useState(0);
  const [caseLoading, setCaseLoading] = useState(true);
  const [caseError, setCaseError] = useState('');

  const [selectedCase, setSelectedCase] = useState<Case | null>(null);
  const [evidence, setEvidence] = useState<Evidence[]>([]);
  const [evidenceLoading, setEvidenceLoading] = useState(false);
  const [evidenceError, setEvidenceError] = useState('');

  const [showCreateCase, setShowCreateCase] = useState(false);
  const [showCreateEvidence, setShowCreateEvidence] = useState(false);
  const [showCaseDetail, setShowCaseDetail] = useState(false);

  const [caseFilters, setCaseFilters] = useState({
    status: '',
    severity: '',
    search: '',
  });

  const [newCase, setNewCase] = useState({
    title: '',
    description: '',
    severity: 'medium',
  });

  const [newEvidence, setNewEvidence] = useState({
    case_id: '',
    name: '',
    category: 'disk_image',
    hash_sha256: '',
    size_bytes: '',
    source_host: '',
    notes: '',
  });

  const [detailCase, setDetailCase] = useState<CaseSummary | null>(null);

  const loadCases = useCallback(async () => {
    setCaseLoading(true);
    setCaseError('');
    try {
      const params = new URLSearchParams({
        page: String(casePage),
        page_size: '20',
      });
      if (caseFilters.status) params.append('status', caseFilters.status);
      if (caseFilters.severity) params.append('severity', caseFilters.severity);
      if (caseFilters.search) params.append('search', caseFilters.search);

      const res = await api.get<{ data: PageData<Case> }>(`/digital-forensics/cases?${params}`);
      setCases(res.data.items);
      setCaseTotal(res.data.total);
      setCaseTotalPages(res.data.total_pages);
    } catch (err) {
      setCaseError('Failed to load cases');
      console.error(err);
    } finally {
      setCaseLoading(false);
    }
  }, [casePage, caseFilters]);

  const loadEvidence = useCallback(async (caseId: string) => {
    setEvidenceLoading(true);
    setEvidenceError('');
    try {
      const res = await api.get<{ data: Evidence[] }>(`/digital-forensics/cases/${caseId}/evidence`);
      setEvidence(res.data);
    } catch (err) {
      setEvidenceError('Failed to load evidence');
      console.error(err);
    } finally {
      setEvidenceLoading(false);
    }
  }, []);

  const loadCaseDetail = useCallback(async (caseId: string) => {
    try {
      const res = await api.get<{ data: CaseSummary }>(`/digital-forensics/cases/${caseId}/summary`);
      setDetailCase(res.data);
    } catch (err) {
      console.error(err);
    }
  }, []);

  useEffect(() => {
    loadCases();
  }, [loadCases]);

  useEffect(() => {
    if (selectedCase) {
      loadEvidence(selectedCase.id);
      loadCaseDetail(selectedCase.id);
    }
  }, [selectedCase, loadEvidence, loadCaseDetail]);

  const handleCreateCase = async (e: React.FormEvent) => {
    e.preventDefault();
    setCaseError('');
    try {
      await api.post('/digital-forensics/cases', {
        title: newCase.title,
        description: newCase.description,
        severity: newCase.severity,
      });
      setShowCreateCase(false);
      setNewCase({ title: '', description: '', severity: 'medium' });
      loadCases();
    } catch (err) {
      const message = errorMessage(err, 'Failed to create case');
      setCaseError(message);
      console.error(err);
    }
  };

  const handleCreateEvidence = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedCase) return;
    setEvidenceError('');
    const sizeBytes = newEvidence.size_bytes.trim()
      ? Number(newEvidence.size_bytes)
      : undefined;
    if (sizeBytes !== undefined && (!Number.isFinite(sizeBytes) || sizeBytes < 0)) {
      setEvidenceError('Size (bytes) must be a non-negative number');
      return;
    }
    try {
      await api.post('/digital-forensics/evidence', {
        case_id: selectedCase.id,
        name: newEvidence.name,
        category: newEvidence.category,
        hash_sha256: newEvidence.hash_sha256 || undefined,
        size_bytes: sizeBytes,
        source_host: newEvidence.source_host || undefined,
        notes: newEvidence.notes || undefined,
      });
      setShowCreateEvidence(false);
      setNewEvidence({ case_id: '', name: '', category: 'disk_image', hash_sha256: '', size_bytes: '', source_host: '', notes: '' });
      loadEvidence(selectedCase.id);
      loadCases();
    } catch (err) {
      const message = errorMessage(err, 'Failed to add evidence');
      setEvidenceError(message);
      console.error(err);
    }
  };

  const handleUpdateEvidenceStatus = async (evidenceId: string, status: string) => {
    setEvidenceError('');
    try {
      await api.patch(`/digital-forensics/evidence/${evidenceId}/status`, { status });
      loadEvidence(selectedCase!.id);
    } catch (err) {
      setEvidenceError(errorMessage(err, 'Failed to update evidence status'));
      console.error(err);
    }
  };

  const handleCloseCase = async (caseId: string) => {
    setCaseError('');
    try {
      await api.patch(`/digital-forensics/cases/${caseId}/close`);
      loadCases();
      if (selectedCase?.id === caseId) setSelectedCase(null);
    } catch (err) {
      setCaseError(errorMessage(err, 'Failed to close case'));
      console.error(err);
    }
  };

  const handleAddTimeline = async (evidenceId: string, action: string, actor: string, notes: string) => {
    try {
      await api.post(`/digital-forensics/evidence/${evidenceId}/timeline`, {
        action,
        actor,
        notes: notes || undefined,
      });
      if (selectedCase) loadEvidence(selectedCase.id);
    } catch (err) {
      setEvidenceError(errorMessage(err, 'Failed to add timeline entry'));
      console.error(err);
    }
  };

  return (
    <div className="min-h-screen bg-cyber-bg">
      <div className="container mx-auto px-4 py-8">
        <div className="flex items-center justify-between mb-8">
          <h1 className="text-3xl font-orbitron font-bold text-cyber-primary tracking-wider">
            DIGITAL FORENSICS
          </h1>
          <button
            onClick={() => { setCaseError(''); setShowCreateCase(true); }}
            className="terminal-button px-4 py-2"
          >
            <Plus className="w-4 h-4 mr-2" /> NEW CASE
          </button>
        </div>

        {showCreateCase && (
          <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50">
            <div className="bg-cyber-surface border border-cyber-primary/30 rounded-lg p-6 w-full max-w-2xl max-h-[90vh] overflow-y-auto">
              <h2 className="text-xl font-orbitron font-bold text-cyber-primary mb-4">CREATE FORENSIC CASE</h2>
              <form onSubmit={handleCreateCase} className="space-y-4">
                <div>
                  <label className="block text-sm text-cyber-muted mb-1">CASE TITLE</label>
                  <input
                    type="text"
                    value={newCase.title}
                    onChange={(e) => setNewCase({ ...newCase, title: e.target.value })}
                    className="terminal-input w-full"
                    required
                  />
                </div>
                <div>
                  <label className="block text-sm text-cyber-muted mb-1">DESCRIPTION</label>
                  <textarea
                    value={newCase.description}
                    onChange={(e) => setNewCase({ ...newCase, description: e.target.value })}
                    className="terminal-input w-full"
                    rows={4}
                    required
                  />
                </div>
                <div>
                  <label className="block text-sm text-cyber-muted mb-1">SEVERITY</label>
                  <select
                    value={newCase.severity}
                    onChange={(e) => setNewCase({ ...newCase, severity: e.target.value })}
                    className="terminal-input w-full"
                  >
                    <option value="low">LOW</option>
                    <option value="medium">MEDIUM</option>
                    <option value="high">HIGH</option>
                    <option value="critical">CRITICAL</option>
                  </select>
                </div>
                {caseError && (
                  <div className="text-cyber-danger text-sm flex items-center gap-2">
                    <AlertCircle className="w-4 h-4 shrink-0" />
                    <span>{caseError}</span>
                  </div>
                )}
                <div className="flex gap-2 pt-2">
                  <button type="submit" className="terminal-button px-4 py-2">CREATE</button>
                  <button
                    type="button"
                    onClick={() => { setCaseError(''); setShowCreateCase(false); }}
                    className="terminal-button-ghost px-4 py-2"
                  >
                    CANCEL
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {selectedCase && showCreateEvidence && (
          <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50">
            <div className="bg-cyber-surface border border-cyber-primary/30 rounded-lg p-6 w-full max-w-2xl max-h-[90vh] overflow-y-auto">
              <h2 className="text-xl font-orbitron font-bold text-cyber-primary mb-4">ADD EVIDENCE</h2>
              <form onSubmit={handleCreateEvidence} className="space-y-4">
                <div>
                  <label className="block text-sm text-cyber-muted mb-1">EVIDENCE NAME</label>
                  <input
                    type="text"
                    value={newEvidence.name}
                    onChange={(e) => setNewEvidence({ ...newEvidence, name: e.target.value })}
                    className="terminal-input w-full"
                    required
                  />
                </div>
                <div>
                  <label className="block text-sm text-cyber-muted mb-1">CATEGORY</label>
                  <select
                    value={newEvidence.category}
                    onChange={(e) => setNewEvidence({ ...newEvidence, category: e.target.value })}
                    className="terminal-input w-full"
                  >
                    {CATEGORIES.map((c) => (
                      <option key={c} value={c}>{c.toUpperCase()}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm text-cyber-muted mb-1">SHA-256 HASH (optional)</label>
                  <input
                    type="text"
                    value={newEvidence.hash_sha256}
                    onChange={(e) => setNewEvidence({ ...newEvidence, hash_sha256: e.target.value })}
                    className="terminal-input w-full font-mono"
                    placeholder="e3b0c44298fc1c149afbf4c8996fb924..."
                  />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm text-cyber-muted mb-1">SIZE (bytes, optional)</label>
                    <input
                      type="number"
                      value={newEvidence.size_bytes}
                      onChange={(e) => setNewEvidence({ ...newEvidence, size_bytes: e.target.value })}
                      className="terminal-input w-full"
                    />
                  </div>
                  <div>
                    <label className="block text-sm text-cyber-muted mb-1">SOURCE HOST (optional)</label>
                    <input
                      type="text"
                      value={newEvidence.source_host}
                      onChange={(e) => setNewEvidence({ ...newEvidence, source_host: e.target.value })}
                      className="terminal-input w-full"
                    />
                  </div>
                </div>
                <div>
                  <label className="block text-sm text-cyber-muted mb-1">NOTES (optional)</label>
                  <textarea
                    value={newEvidence.notes}
                    onChange={(e) => setNewEvidence({ ...newEvidence, notes: e.target.value })}
                    className="terminal-input w-full"
                    rows={3}
                  />
                </div>
                {evidenceError && (
                  <div className="text-cyber-danger text-sm flex items-center gap-2">
                    <AlertCircle className="w-4 h-4 shrink-0" />
                    <span>{evidenceError}</span>
                  </div>
                )}
                <div className="flex gap-2 pt-2">
                  <button type="submit" className="terminal-button px-4 py-2">ADD EVIDENCE</button>
                  <button
                    type="button"
                    onClick={() => { setEvidenceError(''); setShowCreateEvidence(false); }}
                    className="terminal-button-ghost px-4 py-2"
                  >
                    CANCEL
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {showCaseDetail && detailCase && (
          <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50">
            <div className="bg-cyber-surface border border-cyber-primary/30 rounded-lg p-6 w-full max-w-3xl max-h-[90vh] overflow-y-auto">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-xl font-orbitron font-bold text-cyber-primary">
                  CASE {detailCase.case.case_number}
                </h2>
                <button
                  onClick={() => setShowCaseDetail(false)}
                  className="text-cyber-muted hover:text-cyber-primary"
                >
                  <X className="w-6 h-6" />
                </button>
              </div>
              <div className="space-y-4">
                <div className="flex items-center gap-2">
                  <span className={`px-2 py-1 rounded text-xs font-mono ${SEVERITY_COLORS[detailCase.case.severity]}`}>
                    {detailCase.case.severity.toUpperCase()}
                  </span>
                  <span className={`px-2 py-1 rounded text-xs font-mono ${STATUS_COLORS[detailCase.case.status]}`}>
                    {detailCase.case.status.toUpperCase()}
                  </span>
                </div>
                <p className="text-cyber-text">{detailCase.case.description}</p>
                <div className="text-sm text-cyber-muted">
                  <p>Opened: {new Date(detailCase.case.opened_at).toLocaleString()}</p>
                  {detailCase.case.closed_at && (
                    <p>Closed: {new Date(detailCase.case.closed_at).toLocaleString()}</p>
                  )}
                </div>
                <h3 className="text-lg font-orbitron text-cyber-primary border-t border-cyber-primary/30 pt-4">
                  EVIDENCE ({detailCase.evidence_count})
                </h3>
                {detailCase.evidence.length === 0 ? (
                  <p className="text-cyber-muted text-center py-4">No evidence items yet</p>
                ) : (
                  <div className="space-y-2">
                    {detailCase.evidence.map((ev) => (
                      <div key={ev.id} className="bg-cyber-bg/50 border border-cyber-primary/20 rounded p-3">
                        <div className="flex items-center justify-between">
                          <div>
                            <p className="font-mono text-cyber-primary">{ev.name}</p>
                            <p className="text-xs text-cyber-muted">{ev.category.toUpperCase()}</p>
                          </div>
                          <span className={`px-2 py-1 rounded text-xs font-mono ${STATUS_COLORS[ev.status]}`}>
                            {ev.status.toUpperCase()}
                          </span>
                        </div>
                        {ev.hash_sha256 && (
                          <p className="text-xs font-mono text-cyber-muted mt-1">
                            SHA-256: {ev.hash_sha256.substring(0, 32)}...
                          </p>
                        )}
                        {ev.chain_of_custody && ev.chain_of_custody.length > 0 && (
                          <div className="mt-2 border-t border-cyber-primary/20 pt-2">
                            <p className="text-xs font-mono text-cyber-muted mb-1">CHAIN OF CUSTODY</p>
                            <ul className="space-y-1">
                              {ev.chain_of_custody.map((entry, i) => (
                                <li key={i} className="text-xs text-cyber-muted flex flex-wrap items-center gap-2">
                                  <span className="font-mono text-cyber-accent">
                                    {new Date(entry.timestamp).toLocaleString()}
                                  </span>
                                  <span className="font-mono">{entry.action.toUpperCase()}</span>
                                  <span>by {entry.actor}</span>
                                  {entry.notes && <span>— {entry.notes}</span>}
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
                {detailCase.case.status !== 'closed' && (
                  <button
                    onClick={() => handleCloseCase(detailCase.case.id)}
                    className="terminal-button-destructive w-full mt-4"
                  >
                    CLOSE CASE
                  </button>
                )}
              </div>
            </div>
          </div>
        )}

        <div className="terminal-card mb-6">
          <div className="flex flex-col sm:flex-row gap-4 mb-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-cyber-muted" />
              <input
                type="text"
                placeholder="Search cases..."
                value={caseFilters.search}
                onChange={(e) => setCaseFilters({ ...caseFilters, search: e.target.value })}
                className="terminal-input pl-10"
              />
            </div>
            <select
              value={caseFilters.status}
              onChange={(e) => setCaseFilters({ ...caseFilters, status: e.target.value })}
              className="terminal-input w-full sm:w-48"
            >
              <option value="">ALL STATUS</option>
              <option value="open">OPEN</option>
              <option value="investigating">INVESTIGATING</option>
              <option value="contained">CONTAINED</option>
              <option value="closed">CLOSED</option>
            </select>
            <select
              value={caseFilters.severity}
              onChange={(e) => setCaseFilters({ ...caseFilters, severity: e.target.value })}
              className="terminal-input w-full sm:w-48"
            >
              <option value="">ALL SEVERITY</option>
              <option value="critical">CRITICAL</option>
              <option value="high">HIGH</option>
              <option value="medium">MEDIUM</option>
              <option value="low">LOW</option>
            </select>
          </div>

          {caseLoading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="w-8 h-8 animate-spin text-cyber-primary" />
            </div>
          ) : caseError ? (
            <div className="text-cyber-danger text-center py-4">{caseError}</div>
          ) : cases.length === 0 ? (
            <div className="text-center py-8">
              <AlertCircle className="w-12 h-12 text-cyber-muted mx-auto mb-4" />
              <p className="text-cyber-muted">No cases found. Create your first forensic case.</p>
            </div>
          ) : (
            <>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-cyber-primary/30 text-left text-sm text-cyber-muted">
                      <th className="pb-2 pr-4">CASE #</th>
                      <th className="pb-2 pr-4">TITLE</th>
                      <th className="pb-2 pr-4">SEVERITY</th>
                      <th className="pb-2 pr-4">STATUS</th>
                      <th className="pb-2 pr-4">EVIDENCE</th>
                      <th className="pb-2 pr-4">OPENED</th>
                      <th className="pb-2">ACTIONS</th>
                    </tr>
                  </thead>
                  <tbody>
                    {cases.map((c) => (
                      <tr key={c.id} className="border-b border-cyber-primary/10 hover:bg-cyber-primary/5 transition-colors cursor-pointer"
                          onClick={() => setSelectedCase(c)}>
                        <td className="py-3 pr-4 font-mono text-cyber-primary">{c.case_number}</td>
                        <td className="py-3 pr-4 text-cyber-text max-w-xs truncate">{c.title}</td>
                        <td className="py-3 pr-4">
                          <span className={`px-2 py-1 rounded text-xs font-mono ${SEVERITY_COLORS[c.severity]}`}>
                            {c.severity.toUpperCase()}
                          </span>
                        </td>
                        <td className="py-3 pr-4">
                          <span className={`px-2 py-1 rounded text-xs font-mono ${STATUS_COLORS[c.status]}`}>
                            {c.status.toUpperCase()}
                          </span>
                        </td>
                        <td className="py-3 pr-4 text-cyber-muted">{c.evidence_count}</td>
                        <td className="py-3 pr-4 text-cyber-muted text-sm">
                          {new Date(c.opened_at).toLocaleDateString()}
                        </td>
                        <td className="py-3">
                          <button
                            onClick={(e) => { e.stopPropagation(); loadCaseDetail(c.id); setShowCaseDetail(true); }}
                            className="text-cyber-primary hover:text-cyber-accent text-sm font-mono"
                          >
                            DETAILS
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div className="flex items-center justify-between mt-4">
                <div className="text-sm text-cyber-muted">
                  Page {casePage} of {caseTotalPages} — {caseTotal} total
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => setCasePage((p) => Math.max(1, p - 1))}
                    disabled={casePage === 1}
                    className="terminal-button-ghost px-3 py-1 text-sm"
                  >
                    <ChevronLeft className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => setCasePage((p) => Math.min(caseTotalPages, p + 1))}
                    disabled={casePage === caseTotalPages}
                    className="terminal-button-ghost px-3 py-1 text-sm"
                  >
                    <ChevronRight className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </>
          )}
        </div>

        {selectedCase && (
          <div className="terminal-card">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-orbitron font-bold text-cyber-primary">
                EVIDENCE — {selectedCase.case_number}
              </h2>
              <button
                onClick={() => { setEvidenceError(''); setShowCreateEvidence(true); }}
                className="terminal-button px-4 py-2"
              >
                <Plus className="w-4 h-4 mr-2" /> ADD EVIDENCE
              </button>
            </div>

            {evidenceLoading ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="w-8 h-8 animate-spin text-cyber-primary" />
              </div>
            ) : evidenceError ? (
              <div className="text-cyber-danger text-center py-4">{evidenceError}</div>
            ) : evidence.length === 0 ? (
              <div className="text-center py-8">
                <FileText className="w-12 h-12 text-cyber-muted mx-auto mb-4" />
                <p className="text-cyber-muted">No evidence items. Add your first piece of evidence.</p>
              </div>
            ) : (
              <div className="space-y-3">
                {evidence.map((ev) => (
                  <div key={ev.id} className="bg-cyber-bg/50 border border-cyber-primary/20 rounded-lg p-4">
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-3 mb-2">
                          <p className="font-mono text-cyber-primary text-lg">{ev.name}</p>
                          <span className={`px-2 py-1 rounded text-xs font-mono ${STATUS_COLORS[ev.status]}`}>
                            {ev.status.toUpperCase()}
                          </span>
                          <span className="px-2 py-1 rounded text-xs font-mono bg-cyber-primary/20 text-cyber-primary">
                            {ev.category.toUpperCase()}
                          </span>
                        </div>
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-sm text-cyber-muted">
                          {ev.hash_sha256 && (
                            <p><span className="font-mono">HASH:</span> {ev.hash_sha256.substring(0, 32)}...</p>
                          )}
                          {ev.size_bytes != null && (
                            <p><span className="font-mono">SIZE:</span> {ev.size_bytes} bytes</p>
                          )}
                          {ev.source_host && (
                            <p><span className="font-mono">HOST:</span> {ev.source_host}</p>
                          )}
                          <p><span className="font-mono">ID:</span> {ev.id.substring(0, 8)}...</p>
                        </div>
                        {ev.notes && (
                          <p className="text-cyber-muted text-sm mt-2">{ev.notes}</p>
                        )}
                      </div>
                      <div className="flex items-center gap-2 ml-4">
                        {ev.status !== 'verified' && (
                          <button
                            onClick={() => handleUpdateEvidenceStatus(ev.id, 'verified')}
                            className="terminal-button-ghost px-3 py-1 text-sm text-green-400 hover:bg-green-500/10"
                          >
                            <CheckCircle className="w-4 h-4 mr-1" /> VERIFY
                          </button>
                        )}
                        {ev.status !== 'compromised' && (
                          <button
                            onClick={() => handleUpdateEvidenceStatus(ev.id, 'compromised')}
                            className="terminal-button-ghost px-3 py-1 text-sm text-red-400 hover:bg-red-500/10"
                          >
                            <AlertCircle className="w-4 h-4 mr-1" /> COMPROMISE
                          </button>
                        )}
                        <button
                          onClick={() => {
                            const action = prompt('Action (e.g., collected, analyzed, transferred):');
                            const actor = prompt('Actor (analyst name):');
                            const notes = prompt('Notes (optional):');
                            if (action && actor) handleAddTimeline(ev.id, action, actor, notes || '');
                          }}
                          className="terminal-button-ghost px-3 py-1 text-sm"
                        >
                          <Activity className="w-4 h-4 mr-1" /> TIMELINE
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}