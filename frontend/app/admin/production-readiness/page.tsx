"use client";
import { useState, useCallback, useEffect } from "react";
import { useRequireAuth } from "@/lib/auth";
import { isAdmin } from "@/lib/roles";

const STATUS_COLORS: Record<string, string> = {
  pass: "bg-emerald-100 text-emerald-800 border-emerald-200",
  warning: "bg-amber-100 text-amber-800 border-amber-200",
  degraded: "bg-rose-100 text-rose-800 border-rose-200",
  blocked: "bg-red-100 text-red-800 border-red-200",
  not_checked: "bg-slate-100 text-slate-700 border-slate-200",
  operational: "bg-emerald-100 text-emerald-800 border-emerald-200",
};

const STATUS_LABEL: Record<string, string> = {
  pass: "PASS",
  warning: "WARNING",
  degraded: "DEGRADED",
  blocked: "BLOCKED",
  not_checked: "NOT CHECKED",
  operational: "OPERATIONAL",
};

const SECTIONS = [
  { key: "backup", label: "Backup Verification", endpoint: "/api/v1/admin/production-readiness/backup" },
  { key: "clerk_auth", label: "Clerk Auth Health", endpoint: "/api/v1/admin/production-readiness/clerk" },
  { key: "backend", label: "FastAPI Backend Health", endpoint: "/api/v1/admin/production-readiness/backend" },
  { key: "database", label: "Neon PostgreSQL Health", endpoint: "/api/v1/admin/production-readiness/database" },
  { key: "dns", label: "DNS Verification", endpoint: "/api/v1/admin/production-readiness/dns" },
  { key: "clerk_webhooks", label: "Clerk Webhook Health", endpoint: "/api/v1/admin/production-readiness/clerk-webhooks" },
  { key: "cors", label: "CORS Configuration", endpoint: "/api/v1/admin/production-readiness/cors" },
  { key: "security", label: "Security Audit", endpoint: "/api/v1/admin/production-readiness/security" },
];

export default function ProductionReadinessPage() {
  const { user, loading: authLoading, error: authErr } = useRequireAuth();
  const [data, setData] = useState<any>(null);
  const [dataLoading, setDataLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    setDataLoading(true); setErr(null);
    try {
      const res = await fetch("/api/v1/admin/production-readiness", { credentials: "include" });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const json = await res.json();
      setData(json.data ?? json);
    } catch (e: any) {
      setErr(e?.message || "Failed to load readiness data");
    } finally {
      setDataLoading(false);
    }
  }, []);

  // Load readiness data on mount
  useEffect(() => {
    fetchData();
  }, [fetchData]);

  if (authLoading || !user) return <div className="p-10">Loading auth...</div>;
  if (!user || typeof user === "string" || !user.id || !isAdmin(user.role)) return <div className="p-10 text-red-600">Admin access required.</div>;

  if (dataLoading && !data) return (
    <div className="p-10"><h1 className="text-2xl font-bold mb-4">Production Readiness Center</h1><div className="text-slate-500">Loading readiness status...</div></div>
  );

  const checks = data?.checks || {};
  const overall = data?.overall_status || "unknown";

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-3xl font-extrabold tracking-tight">Production Readiness Center</h1>
        <button onClick={fetchData} className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm font-medium">Refresh</button>
      </div>

      <div className={`mb-6 p-4 rounded-xl border text-lg font-semibold ${STATUS_COLORS[overall] || STATUS_COLORS.not_checked}`}>
        Overall Status: {STATUS_LABEL[overall] || overall.toUpperCase()}
      </div>

      {err && <div className="mb-4 p-3 bg-red-50 text-red-700 rounded-lg border border-red-200">{err}</div>}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {SECTIONS.map((s) => {
          const check = checks[s.key] || {};
          const status = check.status || "not_checked";
          const details = check.details || "No details available.";
          return (
            <div key={s.key} className="bg-white rounded-xl border p-5 shadow-sm">
              <div className="flex items-center justify-between mb-2">
                <h3 className="font-bold text-base">{s.label}</h3>
                <span className={`text-xs font-bold px-2 py-0.5 rounded-full border ${STATUS_COLORS[status] || STATUS_COLORS.not_checked}`}>{STATUS_LABEL[status] || status}</span>
              </div>
              <p className="text-sm text-slate-600 mb-2">{details}</p>
              {check.warning && <p className="text-xs text-amber-700 font-medium">Warning: {check.warning}</p>}
              <a href={s.endpoint} target="_blank" rel="noopener noreferrer" className="text-xs text-blue-600 hover:underline">View detailed logs →</a>
            </div>
          );
        })}
      </div>
    </div>
  );
}
