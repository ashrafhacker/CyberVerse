# CyberVerse Admin Mission — Phase A Verification Findings

Branch: `feat/admin-system` (from `ca24ee1`)
Verification suite: `backend/tests/test_admin_rbac.py` — 52 tests (auth matrices, hierarchy/self
guards, audit coverage, flags, settings, announcements, tickets, bulk ops, filters, enrichment).
Baseline: existing backend suite **81 passed, exit 0** (unchanged by this work).

Status labels: every finding below is **VERIFIED** by a failing test against the current code
(test-harness bugs fixed first so failures map 1:1 to backend defects).

## Bugs (existing endpoints broken)

- **F1. `GET /admin/tickets` → 500.** `response_model=APIResponse[dict]` but endpoint returns a
  list → pydantic validation error on every call. (tests: unauth matrix, super-admin reads,
  ticket list)
- **F2. `GET /admin/subscriptions` → 500.** Same `APIResponse[dict]`-vs-list mismatch.
- **F3. Audit metadata silently dropped.** `AuditService.log` passes `metadata=meta` but the
  `AuditLog` model column is `meta_data`; SQLAlchemy swallows the unknown kwarg → audit rows
  lose all metadata (data loss, no error).
- **F4. Malformed UUID path params → 500.** `UUID(...)` conversion inside handlers raises
  `ValueError` → 500 instead of 422. Affects role/status/flag/setting/ticket paths.

## Security gaps (RBAC enforcement)

- **F5. Self role change allowed** (`PATCH /admin/users/{id}/role` and users-router equivalent)
  → must be 400.
- **F6. Self status change allowed** → must be 400.
- **F7. Admin can deactivate a super admin** (`status` endpoints) → must be 403.
- **F8. Equal-rank admins can modify each other** → must be 403 (actor rank must be strictly
  greater than target rank; super_admin non-self always allowed).
- **F9. `users.py` role/status/delete have no self or hierarchy guards** — the `/users` router
  exposes a second, unprotected surface for the same mutations (admin router guards are
  bypassable via `/api/v1/users/{id}/role` etc.).
- **F10. Missing audit logging** for: admin role change (partial), admin status change, users-
  router role/status/delete, feature-flag update, setting update/create, announcement
  create/update/delete, ticket reply/update, bulk status.

## Missing functionality (admin console needs it)

- **F11. `POST /admin/users/bulk-status`** missing (404). Needs ≤50 ids, per-item skip reasons
  (self, protected rank, unknown id), single `user.bulk_status_updated` audit row.
- **F12. `POST /admin/settings`** missing (405).
- **F13. Announcement `PATCH`/`DELETE`** missing (405/404). Delete = soft delete
  (`is_active=False`).
- **F14. Admin ticket management**: `GET /admin/tickets/{id}` detail, staff reply, and
  `PATCH` (status/priority/assignee) all missing. Reply must set `first_response_at`;
  resolving must set `resolved_at`.
- **F15. Audit-log query filters** (`user_id`, `action`, `resource_type`, `resource_id`,
  `start_date`, `end_date`) ignored — returns everything.
- **F16. Audit-log rows don't expose** `before`/`after`/`metadata` detail fields.
- **F17. Users list**: no `status` filter; response lacks `total`/`page`/`page_size`.
- **F18. Subscriptions list** lacks `user_email`/`plan_name` enrichment (frontend can't render
  meaningful rows).
- **F19. Public announcements read endpoint** missing — `GET /notifications/announcements`
  returns 405 (path caught by `DELETE /{notification_id}`). Drafts must never be exposed.
- **F20. No admin event stream** (WS/SSE) for live dashboard updates.

## Decided target-state contracts (locked for tests + frontend)

- Guards: self → **400**; actor rank > target rank → allow; actor `super_admin` (non-self) →
  allow; otherwise **403**. Applied identically on admin router and users router.
- Bulk: max 50 ids, 422 on overflow/empty, per-item `skipped` reasons, audit once.
- Invalid path ids: UUID-typed params → **422** (never 500).
- Audit actions: `user.role_updated`, `user.status_updated`, `user.bulk_status_updated`,
  `user.deleted`, `feature_flag.updated`, `setting.created`, `setting.updated`,
  `announcement.created`, `announcement.updated`, `announcement.deleted`,
  `ticket.replied`, `ticket.updated`.
- Announcements: `GET /api/v1/notifications/announcements` public, `is_draft=False` only.
- WS: `WS /api/v1/admin/stream?token=`, accept-then-close 4401/4403, in-process
  `AdminEventHub` fed by `AuditService.log`.
