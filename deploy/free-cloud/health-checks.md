# Health Checks (Read-Only — No Mock Health; Real Queries Only)

ENDPOINTS (all read-only, admin RBAC-guarded):
GET /api/v1/admin/production-readiness
GET /api/v1/admin/production-readiness/backup
GET /api/v1/admin/production-readiness/clerk
GET /api/v1/admin/production-readiness/backend
GET /api/v1/admin/production-readiness/database
GET /api/v1/admin/production-readiness/dns
GET /api/v1/admin/production-readiness/clerk-webhooks
GET /api/v1/admin/production-readiness/cors
GET /api/v1/admin/production-readiness/security

READ-ONLY VERIFICATION RULES (from checkpoint):
- DB endpoint executes real SELECT 1 (verified; result (1,)).
- Clerk endpoint returns accurate status (`not_checked` when no verified connection; never claims false connectivity).
- Webhook endpoint returns `not_checked` when no delivery evidence exists; never treats audit logs as proof.
- Backup = `not_checked` without metadata (never invents backup proof).
- Aggregate precedence correct for blocked/degraded/warning/not_checked/operational.
- Security endpoint never exposes secrets/connection strings.

BUILD / TEST COMMANDS:
- Backend tests: `cd backend && PYTHONPATH=. .venv/bin/python -m pytest tests/test_admin_rbac.py -v`
- Frontend vitest: `cd frontend && npx vitest run app/admin/production-readiness/page.test.tsx`
- TypeScript: `cd frontend && npx tsc --noEmit`
- Next.js build: `cd frontend && npm run build`
- Secret scan: `grep -rni -E 'CLERK_WEBHOOK_SECRET|connection_string' backend/app/ frontend/app/ --exclude-dir=node_modules --exclude-dir=.git | grep -v 'getattr\|Guard\|secret = getattr'` (clean if only guard references remain)
