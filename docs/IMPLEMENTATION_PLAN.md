# CyberVerse Implementation Plan

Phased plan following the master spec. Each phase is DONE only when tests, build, and docs pass.

## Phase 1 — Repository audit, docs, backend, DB, Docker (CURRENT)
- [x] Inspect structure, models, services, endpoints
- [x] Fix migration `de5d6b10489e` (invalid columns) so fresh DBs migrate
- [x] Linux `.venv`, working `npm run dev`, Postgres + Redis up
- [ ] `docs/ARCHITECTURE.md`, `docs/IMPLEMENTATION_PLAN.md`, `docs/DEPENDENCIES.md`, `docs/SECURITY.md`, `docs/STATUS.md`
- [ ] `.env.example` parity with config, `Makefile`, scripts
- [ ] Compose profiles: core / labs / monitoring

## Phase 2 — Player systems
- Player profile fields, XP, levels, ranks, streaks
- Skill tree (10 categories, prerequisites, unlock rules)
- Missions engine (JSON definitions, objectives, rewards)
- Achievements + server-side validation (no client-trusted XP)

## Phase 3 — Godot game
- Godot 4 project scaffold in `game/`
- Third-person controller, camera, sprint, interaction raycast
- SOC interior scene, NPC + dialogue, terminals
- Mission handoff to backend (login token, mission fetch, flag submit)

## Phase 4 — Lab orchestrator
- `services/lab-orchestrator` (FastAPI sidecar, no raw docker.sock to users)
- WEB-001, LINUX-001, FORENSICS-001 containers, network isolation, limits, TTL cleanup
- Endpoints: POST /labs/start, /labs/{id}/stop|reset|submit, GET /labs/{id}

## Phase 5 — CTF + leaderboard
- CTFd adapter layer, own UI, hints, scoring, anti-cheat server-side

## Phase 6 — Learning system + AI mentor
- Courses/lessons linked to labs; `AIProvider` abstraction (local models default)

## Phase 7 — Forensics / OSINT / blue team (simulated data only)

## Phase 8 — Multiplayer red/blue (realtime via Redis/WebSocket)

## Phase 9 — Hardening, perf, tests, STATUS.md

## Vertical Slice Checklist (build first, fully working)
login → dashboard → enter CyberVerse → 3D SOC → NPC → mission → terminal →
start isolated lab → complete challenge → submit flag → server validates →
XP → skill unlock → mission complete → return to city.
