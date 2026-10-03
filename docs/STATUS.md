# CyberVerse Status (honest)

## WORKING (tested)
- PostgreSQL + Redis running; migrations apply cleanly to a fresh DB
- Backend boots: `GET /health` returns ok, DB + Redis connected
- Frontend boots: `npm run dev` serves (port 3001 while 3000 was occupied)
- Existing FastAPI endpoints for auth, users, missions, courses, labs, ctf, soc, leaderboard, admin
- Godot 4.2.2 project scaffold in `game/` imports and runs headless without script errors
  - SOC scene loads, player controller + terminal interaction scripts parse
- Web `/game` pages (arena, challenge, teams, tournaments) exist

## PARTIALLY WORKING
- Labs API (metadata present; real Docker orchestration not wired)
- CTF service (adapter present; CTFd integration not verified)
- AI mentor (provider abstraction exists; no default local model configured)
- Leaderboard (service exists; no server-side anti-cheat enforcement audited)

## NOT IMPLEMENTED
- Godot third-person controller camera rig polish (basic controller only)
- NPC/dialogue/quest/inventory/save-load systems in Godot
- Lab Orchestrator service with Docker isolation, TTL cleanup endpoints
- CTFd live integration
- Multiplayer red/blue realtime mode
- Prometheus/Grafana monitoring profile
- Occupied 3D city (only SOC interior scene)

## Next steps
1. Finish vertical slice: Godot login → mission fetch from API → start lab via orchestrator → flag submit → XP
2. Implement `services/lab-orchestrator` with docker SDK, per-lab TTL, resource caps
3. docker-compose profiles: core / labs / monitoring

## Progression system update (this session)
- Added `xp_transactions` ledger table (migration a1b2c3d4e5f6) with idempotency unique constraint (user_id, source_type, source_id)
- `ProgressService.award_xp` now writes XP ledger entries, is idempotent per source, computes rank titles
- `LevelSystem.rank_for_level` added (Cyber Recruit → Cyberverse Elite)
- Leaderboard: added `/api/v1/leaderboard/global|weekly|monthly|me` routes (previously 404); verified 401 auth gate instead of 404
