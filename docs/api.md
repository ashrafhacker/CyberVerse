# CyberVerse API Reference

Base URL: `https://api.cyberverse.io/api/v1` (dev: `http://localhost:8000/api/v1`)

## Conventions

- **Auth**: `Authorization: Bearer <access_token>`
- **Envelope**: all responses are `{ "success": bool, "message": str, "data": T }` (`APIResponse`)
- **Errors**: `{ "detail": "message" }` with standard HTTP status codes
- **Pagination**: `?page=1&page_size=20` â†’ `{ "total", "page", "size", "items" }`
- **Roles** (ascending): guest, student, premium_student, instructor, moderator, administrator, developer, super_admin

## Authentication

| Method | Path | Description | Min Role |
|--------|------|-------------|----------|
| POST | `/auth/register` | Create account (returns tokens) | public |
| POST | `/auth/login` | Email + password login | public |
| POST | `/auth/refresh` | Exchange refresh token | public |
| POST | `/auth/logout` | Revoke current session | student |
| GET | `/auth/me` | Current user | student |
| POST | `/auth/verify-email` | Verify email with token | public |
| POST | `/auth/resend-verification` | Resend verification email | student |
| POST | `/auth/forgot-password` | Request password reset | public |
| POST | `/auth/reset-password` | Reset password with token | public |
| POST | `/auth/change-password` | Change own password | student |
| POST | `/auth/2fa/enable` | Start 2FA (returns TOTP secret + otpauth URI) | student |
| POST | `/auth/2fa/verify` | Confirm 2FA activation | student |
| POST | `/auth/2fa/disable` | Disable 2FA | student |
| GET | `/auth/sessions` | List active sessions | student |
| DELETE | `/auth/sessions/{id}` | Revoke a session | student |
| GET | `/auth/devices` | List devices | student |
| GET | `/auth/login-history` | Login history | student |

### Login request/response

```json
POST /auth/login
{ "email": "agent@cyberverse.io", "password": "s3cret" }

200 OK
{
  "success": true,
  "message": "Login successful",
  "data": {
    "access_token": "eyJ...",
    "refresh_token": "eyJ...",
    "token_type": "bearer",
    "user": { "id": "...", "email": "...", "full_name": "...", "role": "student", "status": "pending", "is_verified": false, "is_2fa_enabled": false, "provider": "email", "created_at": "...", "updated_at": "..." }
  }
}
```

## Users

| Method | Path | Description | Min Role |
|--------|------|-------------|----------|
| GET | `/users/` | List users (search, filter) | moderator |
| GET | `/users/{id}` | User detail | moderator |
| PATCH | `/users/{id}` | Update user (name, role, status) | moderator |
| DELETE | `/users/{id}` | Delete user | administrator |

## Profile & Progress

| Method | Path | Description | Min Role |
|--------|------|-------------|----------|
| GET | `/profile/` | Own profile (XP, coins, level, badges) | student |
| PATCH | `/profile/` | Update username/bio/settings | student |
| PATCH | `/profile/avatar` | Set avatar URL | student |
| GET | `/profile/level` | Level progress info | student |
| GET | `/profile/{user_id}` | Public profile | student |
| GET | `/progress/overview` | Player progress summary | student |
| GET | `/progress/lessons` | Lesson progress list | student |
| POST | `/progress/lessons/{id}` | Update lesson progress (status, %): `not_started\|in_progress\|completed` | student |
| GET | `/progress/recommendations` | AI learning recommendations | student |
| POST | `/progress/streak/checkin` | Daily check-in (streak + bonus XP) | student |
| POST | `/progress/xp` | Award XP/coins (game callback) | student |

## Courses & Lessons

| Method | Path | Description | Min Role |
|--------|------|-------------|----------|
| GET | `/courses/` | List/search published courses | student |
| GET | `/courses/learning-paths` | Published learning paths | student |
| GET | `/courses/{id}` | Course structure (modules + lessons) | student |
| POST | `/courses/{id}/enroll` | Enroll | student |
| GET | `/courses/{id}/quiz` | Course quiz | student |
| GET | `/lessons/{id}` | Lesson content | student |
| GET | `/lessons/{id}/quiz` | Quiz questions | student |
| POST | `/lessons/{id}/quiz/submit` | Submit answers â†’ score, pass/fail, XP | student |
| GET | `/lessons/{id}/quiz/attempts` | Attempt history | student |

### Quiz submission

```json
POST /lessons/{id}/quiz/submit
{ "answers": { "question_id": ["option_a"], "question_id_2": "option_b" } }

200 OK
{
  "data": {
    "score": 80, "max_score": 100, "passed": true,
    "xp_earned": 50, "coins_earned": 20,
    "feedback": { "q1": "Correct â€” OWASP Top 10..." }
  }
}
```

## Library

| Method | Endpoint | Description | Access |
|--------|----------|-------------|--------|
| GET | /library/ | Browse published resources (filters: search, category, esource_type, difficulty, paginated) | any authenticated user |
| GET | /library/filters | Available category/type/difficulty filter values | any authenticated user |
| GET | /library/{id} | Resource detail (increments view count) | any authenticated user |
| POST | /library/ | Add a resource (url or ile_path required) | moderator/administrator |

## Missions

| Method | Path | Description | Min Role |
|--------|------|-------------|----------|
| GET | `/missions/` | List missions (filter: `mission_type`) | student |
| GET | `/missions/daily` | Today's daily challenges | student |
| GET | `/missions/weekly` | Weekly challenges | student |
| GET | `/missions/{id}` | Mission detail + objectives | student |
| POST | `/missions/{id}/start` | Start mission | student |
| POST | `/missions/{id}/objectives/submit` | Submit objective result | student |
| GET | `/missions/{id}/progress` | Mission progress | student |

## AI

| Method | Path | Description | Min Role |
|--------|------|-------------|----------|
| POST | `/ai/quiz` | Generate quiz from topic | premium_student |
| POST | `/ai/hint` | Mission hint | premium_student |
| POST | `/ai/explain` | Concept explanation | student |
| POST | `/ai/analyze` | Progress analysis | student |
| GET | `/ai/recommendations` | Recommendations | student |

## Social & Notifications

| Method | Path | Description | Min Role |
|--------|------|-------------|----------|
| GET | `/chat/conversations` | DM conversations | student |
| GET | `/chat/messages/{peer_id}` | DM history | student |
| POST | `/chat/messages` | Send message | student |
| POST | `/chat/teams` | Create team | student |
| GET | `/chat/teams` | My teams | student |
| POST | `/chat/teams/{id}/join` | Join team | student |
| GET | `/notifications/` | My notifications (paginated) | student |
| GET | `/notifications/unread-count` | Unread count | student |
| POST | `/notifications/{id}/read` | Mark read | student |
| POST | `/notifications/read-all` | Mark all read | student |
| DELETE | `/notifications/{id}` | Delete | student |
| GET | `/leaderboard/?type=weekly\|monthly\|all_time` | Rankings + my rank | student |
| GET | `/leaderboard/top` | Top N players | student |

## Premium & Billing

| Method | Path | Description | Min Role |
|--------|------|-------------|----------|
| GET | `/premium/plans` | Subscription plans | public |
| GET | `/premium/status` | My subscription | student |
| GET | `/premium/billing-history` | Payments | student |
| POST | `/premium/checkout` | Stripe checkout session | student |
| POST | `/premium/coupons/redeem` | Validate coupon | student |

## Settings & Support

| Method | Path | Description | Min Role |
|--------|------|-------------|----------|
| GET | `/settings/` | My settings | student |
| PATCH | `/settings/` | Update settings | student |
| PUT | `/settings/privacy` | Privacy preferences | student |
| GET | `/settings/public` | Public platform settings | public |
| POST | `/support/tickets` | Create ticket | student |
| GET | `/support/tickets` | My tickets | student |
| GET | `/support/tickets/{id}` | Ticket detail | student |
| POST | `/support/tickets/{id}/reply` | Reply | student |
| GET | `/support/faq` | FAQ list | public |

## Instructor (content authoring)

| Method | Path | Description | Min Role |
|--------|------|-------------|----------|
| GET | `/instructor/stats` | Author stats + course list | instructor |
| POST | `/instructor/courses` | Create course (draft) | instructor |
| PUT | `/instructor/courses/{id}` | Update course | instructor* |
| POST | `/instructor/courses/{id}/publish` | Publish course | instructor* |
| POST | `/instructor/courses/{id}/modules` | Add module | instructor* |
| POST | `/instructor/modules/{id}/lessons` | Add lesson | instructor* |
| PUT | `/instructor/lessons/{id}` | Update lesson | instructor* |
| POST | `/instructor/lessons/{id}/quiz` | Attach quiz | instructor* |
| POST | `/instructor/quizzes/{id}/questions` | Add question | instructor* |
| GET | `/instructor/lessons/{id}/progress` | Lesson analytics | instructor* |

*Ownership enforced â€” authors can only edit their own courses (super_admin bypass).

## Admin

| Method | Path | Description | Min Role |
|--------|------|-------------|----------|
| GET | `/admin/overview` | Dashboard stats + health | administrator |
| GET | `/admin/users` | All users (search/filter) | administrator |
| PATCH | `/admin/users/{id}/role` | Change role | super_admin |
| PATCH | `/admin/users/{id}/status` | Suspend/activate | administrator |
| GET | `/admin/audit-logs` | Audit trail | administrator |
| GET | `/admin/tickets` | All tickets | administrator |
| GET | `/admin/subscriptions` | Subscriptions | administrator |
| GET | `/admin/feature-flags` | Feature flags | administrator |
| PATCH | `/admin/feature-flags/{id}` | Update flag (rollout %) | administrator |
| GET | `/admin/settings` | App settings | administrator |
| PUT | `/admin/settings/{id}` | Update setting | administrator |
| POST | `/admin/announcements` | Create announcement | administrator |
| GET | `/admin/announcements` | List announcements | administrator |

## Analytics (admin)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/analytics/overview` | Platform KPIs |
| GET | `/analytics/dau` | Daily active users |
| GET | `/analytics/events` | Event analytics |
| GET | `/analytics/progression` | XP distribution |
| GET | `/analytics/revenue` | Revenue summary |

## Operational Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Liveness (no auth) |
| GET | `/health/db` | Database connectivity |
| GET | `/docs` | Swagger UI (dev) |
