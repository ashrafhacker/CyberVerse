# CyberVerse X — Architecture, Gap Analysis & Phase 1–2 Roadmap

> This document turns the "CyberVerse X" master build prompt into an actionable,
> incremental plan on top of the **existing** CyberVerse codebase at
> `/storage/4E21-0000/CyberVerse` — rather than a from-scratch rewrite.
>
> The existing project already implements a meaningful subset of the spec
> (FastAPI + PostgreSQL + Redis backend, Next.js frontend, auth/MFA/RBAC, labs
> with scenario generation and evidence custody, AI mentor with provider
> failover, admin/instructor/organization groundwork). This doc maps each spec
> section to reality, lists the gaps, and sequences work into phases.

---

## 1. Spec → Existing 1:1 Map

| Spec section | Status | Where it lives today |
|---|---|---|
| **2. Frontend** (Next/React/TS/Tailwind) | ✅ Done | `frontend/` |
| **3. Backend** (FastAPI, modular) | ✅ Done | `backend/app/api/v1/`, `services/` |
| **4. Database** (PostgreSQL) | ✅ Done | `backend/app/models/`, `backend/alembic/`, `database/schema.sql` |
| **4. Redis** (cache/rate-limit/queue) | ✅ Done | `backend/app/core/redis.py`, `celery_app.py` |
| **5. Auth** (JWT, MFA/TOTP, RBAC, hashing) | ✅ Done | `security.py`, `auth_service.py`, `auth.py` |
| **6–7. 3D world + NPCs** | ⬜ Gap | None (UE5/Godot not started) |
| **8. Missions** (story-driven, MITRE mapping) | 🟡 Partial | `lab_missions.py`, `labs.py` missions; MITRE tagging partially present |
| **9–10. Cyber Range + lab categories** | 🟡 Partial | `lab_service.py`, `lab_scenario_gen.py` (7 facility types); no real VM/container orchestration |
| **11. AI Security Copilot** | 🟡 Partial | `ai_service.py` (mentor, hints, quiz, progress analysis); no RAG, no CVE/evidence analysis |
| **12. Multi-agent AI** | ⬜ Gap | None (orchestrator/specialists not built) |
| **13. SOC simulator** | ✅ Implemented | `models/soc.py` (alert/incident lifecycle + notes), `services/soc_service.py`, `api/.../soc.py` (`/soc`), `seed_soc.py`, `frontend/app/soc/` + Neo correlation (alerts→incident statuses New→Closed) |
| **14. Knowledge graph** | ⬜ Gap | None |
| **15. Threat intelligence** | ✅ Implemented | `models/threat_intel.py` (CVE/CWE/MITRE/indicators), `services/threat_intel_service.py`, `api/.../threat_intel.py` (`/threat-intel`), `seed_threat_intel.py`, `frontend/app/threat-intel/` |
| **16–17. Free tools directory** | ✅ Implemented | `models/tool.py`, `services/cyber_arsenal.py`, `api/.../arsenal.py` (`/cyber-arsenal`), `seed_arsenal.py` (30+ tools), `frontend/app/arsenal/` |
| **18–19. Learning system + adaptive** | ✅/🟡 | Courses/paths/quizzes done; adaptive recommender partial |
| **20. Gamification** | ✅ | XP/levels/badges/streaks/leaderboards |
| **21. CTF system** | ✅ Implemented | `models/ctf.py`, `services/ctf_service.py` (SHA-256 flags, rate limit, leaderboard), `api/.../ctf.py` (`/ctf`), `seed_ctf.py`, `frontend/app/ctf/` |
| **22. Report generator** | ✅ Implemented | `services/reports.py` (HTML + optional PDF), `GET /labs/sessions/{id}/reports` + `/export` |
| **24. RPG progression ranks** | ✅ Implemented | `RankSystem` in `services/skill_service.py` (Recruit → CyberVerse Elite) |
| **25. Skill tree** | ✅ Implemented | `models/skill.py` (SkillBranch/UserSkill), `services/skill_service.py`, `api/.../skill.py` (`/skills`), `seed_progression.py` |
| **26. Inventory** | ✅ Implemented | `InventoryItem` model + `ProgressionService` + `api/.../progression.py` (`/progression/inventory`) |
| **27. Quests** | ✅ Implemented | Daily/Weekly challenge endpoints via `DailyChallenge`/`WeeklyChallenge` (`/progression/quests/*`), exist `DailyChallenge`/`WeeklyChallenge` models |
| **23–25. Admin/instructor/organization** | 🟡 Partial | Admin console, instructor authoring, org/team groundwork |
| **26. 3D ↔ dashboard ↔ range** | ⬜ Gap | Web dashboard ↔ backend works; 3D layer absent |
| **27–28. Security architecture + safe boundaries** | ✅ | RBAC, SSRF-safe generator, reserved-only IPs/countries, safety validation |
| **29. Observability** | 🟡 Partial | Structured logs, audit logs; no metrics/traces/Sentry active |
| **30. DevSecOps** | 🟡 Partial | Docker + CI/CD + scans exist; tests incomplete |
| **31. Monorepo structure** | 🟡 Partial | `backend/` + `frontend/` + `docs/` + `docker/`; not yet `apps/`/`services/`/`packages/` |
| **32–37. UI/design/a11y/i18n/perf** | 🟡 Partial | Dark-mode-first UI done; i18n not wired; a11y partial |
| **38. License compliance** | 🟡 Partial | `THIRD_PARTY_LICENSES.md` not yet maintained |
| **40–41. Rules + acceptance** | 🟡 Partial | `.env.example`, README exist; SETUP/SECURITY/CONTRIBUTING/LICENSE missing |

Legend: ✅ implemented · 🟡 partial / groundwork · ⬜ not started

---

## 2. Prioritized Gap Analysis (highest leverage first)

Ranked by (educational value × user appeal × effort-to-implement× risk):

### Tier A — clean, self-contained additions (Phase 1)
1. **Cyber Arsenal — free tools directory** (`spec 16–17`)
   - New tables `tool_categories`, `tools`; seed with the ~30 legitimate tools listed.
   - Backend CRUD + public list/detail; search + filtering (category, OS, license).
   - Frontend directory page with tool cards (name, category, license, OS, difficulty, official site/docs, "verified" badge).
   - Lowest risk: pure content + CRUD, no simulation or AI dependency.
2. **Report generator / PDF+HTML export** (`spec 22`)
   - Build a structured report from `LabReport` + Neo analysis → HTML → PDF.
   - Deterministic; uses the Neo analysis payload we just built.
3. **CTF engine (isolated, synthetic flags)** (`spec 21`)
   - `challenges`, `flags`, `submissions` tables; automatic flag validation (hash compare).
   - Categories: web/crypto/forensics/reversing/osint/networking/linux/defensive.
   - All targets synthetic/in-DB only (safe boundary enforced).

### Tier B — AI depth (Phase 1–2)
4. **RAG for the Copilot** (`spec 11`)
   - Index OWASP/NIST/MITRE/CISA + CyberVerse content into a vector store (pgvector)
     or a simple keyword/hybrid index; ground answers; label "Verified / AI inference /
     Simulation data" provenance.
5. **Multi-agent orchestrator** (`spec 12`)
   - `neo_orchestrator.py`: route a request to SOC / Threat Intel / Code / Network /
     Forensics / Cloud / Training / Report specialist; guardrails before any tool call.

### Tier C — SOC / threat intel depth
6. **SOC simulator dashboard** ✅ built — alert queue → incident lifecycle with
   analyst notes, containment status, MITRE mapping; plus the existing Neo correlation.
7. **Threat intel + CVEs** ✅ built — `cves`, `attack_techniques`, `threat_indicators`
   tables seeded from NVD/CISA + MITRE; a visual explorer remains as follow-up.

### Tier D — 3D / multiplayer (later phases)
8. **3D Cyber City** (UE5 or Godot client) + NPC system.
9. **Organizations / instructor classroom / tournaments** to full depth.
10. **Observability + i18n + license-doc pass.**

---

## 3. Incremental Roadmap (this session and next)

### Phase 1a — Foundation modules
- [x] Add `tools` + `tool_categories` tables + Alembic migration + seed.
- [x] Add `challenges` + `submissions` tables + migration + seed (CTF).
- [x] Add report render helpers (HTML template + PDF export in `app/services/reports.py`).
- [x] Add `cves` / `attack_techniques` / `threat_indicators` tables + migration + seed.
- [x] Add `soc_alerts` / `soc_incidents` / `incident_notes` tables + migration + seed.
- [x] Add `skill_branches` / `user_skills` tables + migration (skill tree + ranks).

### Phase 1b — Backend APIs
- [x] `GET/POST /cyber-arsenal/*`.
- [x] `GET/POST /ctf/challenges`, `POST /ctf/challenges/:id/submit`, leaderboard.
- [x] `GET /labs/sessions/{id}/reports` + `/export` (HTML + PDF download).
- [x] `/threat-intel/cves|techniques|indicators`.
- [x] `/soc/alerts|incidents` lifecycle + notes.
- [x] `/skills` (tree + rank), `/progression/quests|inventory`.

### Phase 1c — Frontend
- [x] `/arsenal` page (search/filter directory).
- [x] `/ctf` page (list, detail, submit, leaderboard).
- [x] `/threat-intel` page (CVE search, severity filter).
- [x] `/soc` page (alert queue + incident lifecycle).
- [x] `/progression` page (rank + skill tree + quests + inventory).
- [ ] `/labs/[id]/report` page (structured incident report view + download).

### Phase 2 — AI depth (recommended next)
- [ ] RAG ingestion + provenance-labeled Copilot responses.
- [ ] Multi-agent orchestrator (`neo_orchestrator.py`) with role routing.
- [ ] SOC dashboard detail views (incident detail page, MITRE explorer).
- [ ] WebSocket real-time alert/notification channel (spec 48).

---

## 4. Architecture blueprints for the new modules

### Cyber Arsenal
```
users ──► GET /cyber-arsenal/tools (public-ish, auth-gated)
            │  filtering: category, os, license, difficulty
            │
Tool model: { name, category, description, license,
              open_source: bool, free_tier: bool, supported_os[],
              difficulty, official_url, docs_url, tutorial_url,
              lab_reference, verified_at }
```
Safety/quality rules:
- Only seed tools verified as open-source / free / legitimate free tier.
- Store official URLs only. Never point at unofficial/pirated downloads.
- Show `verified_at` timestamp and license badge per tool.

### CTF engine (safe)
```
challenges { id, category, title, story, difficulty, points,
             flag_sha256 (b64-bcrypt-like single hash), hint, is_active }
submissions { id, user_id, challenge_id, flag_sha256_attempt, correct, created_at }
```
- Validation = constant-time hash compare of SHA-256 of submitted flag vs stored.
- All content synthetic; flags are random tokens, not real exploits.
- Rate-limit submissions (Redis) to prevent brute force.

### Report generator
Reuse `LabReport` + `session.extra_data.neo_analysis` → render a structured HTML
(Executive Summary, Overview, Affected Assets, Timeline, Indicators, Kill Chain,
Root Cause, Impact, Containment, Remediation, Lessons Learned). Export with a
lightweight HTML→PDF path (e.g. `weasyprint` or a Chromium print in a worker/job).

---

## 5. Suggested repository/file additions

```
backend/app/
  models/tool.py            models/ctf.py          models/soc.py
  models/threat_intel.py    models/skill.py
  schemas/tool.py           schemas/ctf.py         schemas/soc.py
  schemas/threat_intel.py   schemas/skill.py
  services/cyber_arsenal.py services/ctf_service.py
  services/reports.py       services/soc_service.py
  services/threat_intel_service.py  services/skill_service.py
  services/progression_service.py
  api/v1/endpoints/arsenal.py  api/v1/endpoints/ctf.py
  api/v1/endpoints/soc.py      api/v1/endpoints/threat_intel.py
  api/v1/endpoints/skill.py    api/v1/endpoints/progression.py
alembic/versions/0004_cyber_arsenal_ctf.py
alembic/versions/0005_threat_intel_soc.py
alembic/versions/0006_skills.py
seed_arsenal.py seed_ctf.py seed_soc.py seed_threat_intel.py seed_progression.py
frontend/app/arsenal/ frontend/app/ctf/ frontend/app/soc/
frontend/app/threat-intel/ frontend/app/progression/
```

---

## 6. Acceptance criteria mapped to the new modules

For each Phase-1 module, "done" means:
- Tables exist via Alembic migration (not just `create_all`).
- Backend endpoints return `APIResponse<T>` and are covered by a pytest.
- Frontend pages render the data and handle the loading/error/empty states.
- Seed data is present so a fresh DB has useful content.
- Safety boundaries hold (no public targeting; synthetic CTF flags; official URLs).

---

## 7. Recommended next action

Build **Cyber Arsenal** + **CTF engine** first (self-contained, high value, zero
AI/runtime dependency), then the **report exporter** (reuses Neo Analysis). These
tighten the "serious platform" feel while remaining testable without a shell.
Follow with the RAG Copilot + multi-agent orchestrator for AI depth.
