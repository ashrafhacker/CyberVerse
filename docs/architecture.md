# CyberVerse Architecture

## Overview

CyberVerse is a full-stack educational cybersecurity simulation platform. Users learn offensive, defensive, and investigative security skills through guided courses and gamified missions that run **entirely inside simulated sandboxes**. Every practical activity is fictional — no real systems, networks, or third parties are ever targeted.

```
┌─────────────────────────────────────────────────────────────┐
│                        Clients                              │
│   Next.js Web App (Vercel)      UE5 Game Client (future)   │
└──────────────┬──────────────────────────────┬──────────────┘
               │ HTTPS / JSON                 │
┌──────────────▼──────────────────────────────▼──────────────┐
│                     FastAPI API (Render)                   │
│  api/v1/*  ·  JWT auth  ·  RBAC  ·  rate limits            │
│  (uvicorn, 4 workers)                                      │
└──────┬───────────────┬───────────────────────┬─────────────┘
       │               │                       │
┌──────▼───────┐ ┌─────▼──────┐        ┌───────▼──────────┐
│ PostgreSQL 16│ │ Redis 7    │        │ Celery workers   │
│ (Supabase)   │ │ cache/rate │        │ email · notify · │
│ ~30 tables   │ │ limiter    │        │ analytics ·      │
│ (Alembic)    │ │            │        │ challenge rotate │
└──────────────┘ └────────────┘        └──────────────────┘
```

## Tech Stack

| Layer      | Technology                                  |
|------------|---------------------------------------------|
| Frontend   | Next.js 15, React 19, TypeScript, Tailwind CSS, Framer Motion, SWR |
| Backend    | Python 3.12, FastAPI, SQLAlchemy 2 (async), Pydantic v2 |
| Database   | PostgreSQL 16 (Supabase in production)       |
| Cache/Queue| Redis 7, Celery 5                            |
| Auth       | JWT (access + refresh), bcrypt, TOTP 2FA, session management |
| Payments   | Stripe (plans, checkout, webhooks)           |
| Email      | SendGrid (verification, password reset)      |
| AI         | OpenAI API with deterministic fallback       |
| DevOps     | Docker, GitHub Actions, Render, Vercel, Caddy |
| Game       | Unreal Engine 5 (separate project, future)   |

## Project Layout

```
cyberverse/
├── backend/            # FastAPI application
│   ├── app/
│   │   ├── api/v1/endpoints/   # 17 endpoint modules
│   │   ├── core/               # config, security, database, redis, celery
│   │   ├── models/             # SQLAlchemy models (10 files, ~30 tables)
│   │   ├── schemas/            # Pydantic schemas
│   │   ├── services/           # business logic
│   │   └── tasks/              # Celery tasks
│   └── alembic/                # migrations
├── frontend/           # Next.js application
│   ├── app/            # App Router pages
│   ├── components/     # shared UI components
│   └── lib/            # API client, auth context, types
├── database/           # schema.sql bootstrap
├── devops/             # CI/CD, Caddyfile
├── docker/             # Dockerfiles + compose files
├── docs/               # this documentation
├── scripts/            # seed scripts, dev tooling
└── tests/              # backend/frontend tests
```

## Backend Layers

### Core (`app/core/`)
- **config.py** — pydantic-settings; all env vars centralized
- **database.py** — async engine, session factory, `Base`, `get_db` dependency
- **security.py** — password hashing, JWT create/decode, TOTP + backup codes
- **redis.py** — RedisClient + RateLimiter (fixed-window per-user/IP)
- **celery_app.py** — Celery + beat schedule (leaderboard rebuild, challenge rotation, cleanup)
- **exceptions.py** — domain exceptions mapped to HTTP responses
- **logging.py** — JSON structured logging

### API Layer (`app/api/`)
- **deps.py** — `get_current_user`, `require_role` factory, role hierarchy:
  `guest < student < premium_student < instructor < moderator < administrator < developer < super_admin`
- **schemas/base.py** — `APIResponse[T]`, `MessageResponse`, `PaginatedResponse[T]` envelope

### Domain Modules
- **auth** — register, login, refresh, logout, 2FA, sessions, devices, login history, email verification, password reset
- **users / profile / progress** — user management, gamified progression, lesson progress, streaks, XP
- **courses / lessons** — learning paths, courses, modules, lessons, quizzes (AI-assisted generation)
- **missions** — objective-driven sandbox missions with simulated validation rules
- **ai** — quiz generation, hints, concept explanations, progress analysis
- **chat** — DMs, teams
- **leaderboard / analytics** — weekly rankings, admin analytics
- **premium / support / notifications / settings / admin / instructor** — billing, tickets, alerts, config, moderation, content authoring

## CyberVerse Labs Extension

CyberVerse Labs is the Unreal Engine 5 training layer for realistic defensive cybersecurity practice. It adds a 3D training campus, SOC, enterprise network, digital forensics, malware analysis, cloud security, secure coding, and network defense facilities backed by generated fictional scenarios. See `docs/cyberverse-labs.md` for the UE5 implementation plan and `docs/cyberverse-labs-api.md` for the backend contract.

## Authentication Flow

1. Client sends `POST /auth/login` (email + password)
2. Server verifies bcrypt hash, records `LoginHistory` + `Device`, creates `Session`
3. Response: `access_token` (30 min) + `refresh_token` (30 days)
4. Client stores tokens (localStorage for MVP; HttpOnly cookies recommended for production)
5. `GET /auth/refresh` exchanges refresh token for a new pair
6. `POST /auth/logout` revokes the session
7. Optional TOTP 2FA via `pyotp`; backup codes stored hashed

## Gamification Model

- **XP / Coins** — earned from lessons, quizzes, missions, daily check-ins
- **Levels** — `level = floor(sqrt(xp / 100)) + 1` (see `LevelSystem`)
- **Streaks** — consecutive daily check-ins with escalating bonus XP (capped)
- **Leaderboard** — weekly boards rebuilt by Celery; entry points from `PlayerProgress`
- **Achievements** — criteria-driven unlocks (lessons, missions, quizzes, social)

## Data Integrity

- All tables use UUID primary keys
- Foreign keys with `ON DELETE` semantics (CASCADE for owned children, SET NULL for optional refs)
- Optimistic `updated_at` on all mutable tables
- Unique constraints on natural keys (username, slug, user+lesson, user+course)

## Security Model

See `docs/security.md` for the full threat model. Highlights:

- bcrypt password hashing (12 rounds), no plaintext storage
- JWT access tokens short-lived; refresh tokens bound to server-side sessions
- Rate limiting on auth endpoints (login, register, refresh, password reset)
- RBAC enforced at dependency level; every endpoint declares a minimum role
- SQL injection safe by construction (SQLAlchemy parameterized queries)
- Output escaping / no raw HTML rendering on the frontend
- Audit logging for admin actions (`AuditService`)
- Structured logging with PII redaction

## Scaling Path

1. **Launch (50 users)** — single Render web service, Supabase Postgres, one worker
2. **Growth (1k users)** — horizontal uvicorn workers, Redis caching of hot reads, CDN for static assets
3. **Scale (10k+)** — read replicas, Celery autoscaling, sharded leaderboards, edge caching
