# Security Model

## Boundaries
- All offensive-security content targets only CyberVerse-owned labs, local sandboxes,
  and intentionally vulnerable containers. No functionality attacks third-party systems.
- Docker socket is never exposed to end users. A future `lab-orchestrator` service
  owns Docker access and enforces per-user authorization, TTLs, and resource limits.
- XP/flags/scores are validated server-side only; the client is never trusted.

## Controls (current)
- JWT auth (python-jose), bcrypt password hashing
- RBAC roles: USER, INSTRUCTOR, MODERATOR, ADMIN, SUPERADMIN
- Rate limiting via Redis
- Audit logging service
- CORS/headers configuration in `app/main.py`
- Secrets via environment variables only (`.env` gitignored)

## Threat model (summary)
| Threat | Mitigation |
|---|---|
| Lab container escape / abuse | isolated networks, resource caps, auto-destroy on TTL, no host mounts |
| XP/leaderboard cheating | server-side scoring, no client-supplied XP |
| Credential theft | bcrypt, JWT expiry, refresh tokens |
| Injection (SQLi/XSS) | SQLAlchemy parameterization, React escaping, CSP headers |
| SSRF via lab targets | labs resolved from allowlisted images only |
| Secrets in repo | `.env` ignored, `.env.example` with placeholders |

## TODO
- CSRF token on cookie-based flows (if cookies are adopted)
- CSP header tightening after audit
- Container seccomp/AppArmor profiles for labs
- WebSocket auth hardening for Phase 8
