# CyberVerse Architecture

> Generated during repository audit (Phase 1). Describes what actually exists today.

## Current State

CyberVerse is a full-stack educational cybersecurity platform. The current codebase is a
**web platform** (Next.js + FastAPI + PostgreSQL + Redis) with gamified learning features.
The 3D game (Godot) does **not** exist yet — the `/game` web pages are challenge/CTF UIs.

```
┌──────────────────────────────────────────────────────┐
│ Next.js 15 frontend (frontend/)                      │
│  app/ — dashboard, missions, courses, labs, ctf,     │
│        soc, leaderboard, admin, game/ (web pages)    │
│  lib/api.ts — typed API client                       │
└──────────────────────┬───────────────────────────────┘
                       │ REST / JSON  /api/v1
┌──────────────────────▼───────────────────────────────┐
│ FastAPI backend (backend/app)                        │
│  api/v1/endpoints: auth, users, profile, missions,   │
│  courses, lessons, labs, ctf, skill, leaderboard,    │
│  soc, arsenal, threat_intel, ai, chat, admin, ...    │
│  services/: auth_service, lab_service, ctf_service,  │
│  game_service, progression_service, soc_service, ... │
│  Celery tasks, Redis cache/rate-limit                │
└──────┬───────────────────────┬───────────────────────┘
       │                       │
┌──────▼───────┐       ┌──────▼──────┐
│ PostgreSQL 16│       │ Redis 7     │
│ (alembic     │       │ cache,      │
│  migrations) │       │ celery      │
└──────────────┘       └─────────────┘
```

## Planned Target Architecture

```
apps/web (Next.js, existing frontend/)
game/    (Godot 4 — NEW, to be built)
backend/ (existing FastAPI app)
services/lab-orchestrator/ (to be built)
labs/    (intentionally-vulnerable training containers)
docker/  (existing compose stacks: core/labs/monitoring profiles — to add)
docs/
```

- Godot game talks to the same FastAPI backend (`/api/v1`) for auth, missions, XP, labs.
- Labs are started on demand via the lab orchestrator; containers have resource limits
  and expire/destroy automatically.
- CTFd integration stays behind a clean adapter (`ctf_service`), never hard-coded.

## Component Map (current)

| Area | Location | Status |
|---|---|---|
| Web UI | `frontend/app` | Working |
| API | `backend/app/api/v1/endpoints` | Working (most routes) |
| Models | `backend/app/models` | Working, migrated via alembic |
| Auth | `backend/app/api/v1/endpoints/auth.py`, `services/auth_service.py` | JWT-based |
| Labs | `labs.py`, `services/lab_service.py` | Partial (metadata; real Docker orchestration pending) |
| CTF | `ctf.py`, `services/ctf_service.py` | Partial |
| SOC | `soc.py`, `services/soc_service.py` | Partial |
| 3D Game | *none* | NOT IMPLEMENTED |
| Godot project | `game/` (new) | Scaffold to be added |
| Docker compose | `docker/` | Exists, needs profiles |
| Monitoring | — | NOT IMPLEMENTED |
