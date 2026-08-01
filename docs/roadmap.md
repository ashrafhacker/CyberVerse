# CyberVerse Roadmap

## MVP (v0.1) — Launch for ~50 users ✅ (targeting completion)

- [x] Auth: register, login, refresh, logout, 2FA, sessions, devices
- [x] Profiles, XP/levels/coins, streaks, leaderboard
- [x] Learning paths, courses, modules, lessons, quizzes
- [x] Missions with objective validation
- [x] Notifications, support tickets, FAQ
- [x] Admin console (users, moderation, feature flags, announcements)
- [x] Instructor content authoring API
- [x] Celery tasks (leaderboard rebuild, challenge rotation, cleanup)
- [x] Docker + CI/CD + security scans
- [ ] Seed data (paths, courses, missions, achievements, plans)
- [ ] Backend + frontend test suites
- [ ] Email delivery verification (SendGrid)
- [ ] Stripe live keys + webhook endpoint

## v0.2 — Content & Engagement

- [ ] 3 full learning paths with 20+ lessons each
- [ ] 10 sandbox missions + objective validation rules
- [ ] Daily/weekly challenge rotation UI
- [ ] Achievements + badge gallery page
- [ ] AI quiz generator UI (instructor + student)
- [ ] Team challenges and leaderboards
- [ ] Certificate generation + verification page
- [ ] PWA support (offline reading of lessons)

## v0.3 — Scale & Monetization

- [ ] Stripe production billing + invoice emails
- [ ] Premium content gating across UI
- [ ] Redis caching layer for hot reads (courses, leaderboards)
- [ ] Search improvements (trigram index)
- [ ] Email digest / weekly progress reports
- [ ] Admin analytics dashboards (charts)
- [ ] Load test to 1k concurrent users

## v1.0 — Public Launch

- [ ] Marketing site + SEO pass
- [ ] Onboarding tutorial mission
- [ ] Referral/invite program
- [ ] SOC2-aligned security documentation
- [ ] Community moderation tools (reports, bans)
- [ ] Translation framework (i18n)
- [ ] **Neo Analysis v1** — virtual internet generator (10 industries, seeded worlds), AI scenario briefings, encyclopedia integration

## v1.5 — Neo Analysis: Safe Labs

- [ ] Lab agent + registration flow (`lab_environments`, `lab_authorizations` tables)
- [ ] Ownership proof + scope declaration + consent recording
- [ ] Red-line enforcement (refuse out-of-scope targets)
- [ ] Lab health checks + mission templates for own environments
- [ ] Lab activity audit trail

## v2.0 — Game Client (UE5) + Living World

- [ ] Unreal Engine 5 prototype: agency facility hub
- [ ] Sandbox rooms rendered as 3D scenes
- [ ] API client integration (auth, missions, XP)
- [ ] Multiplayer team missions
- [ ] Cosmetics shop (coins economy)
- [ ] **Neo Analysis v2** — living timelines: help-desk simulation, causal incident chains, dynamic threat campaigns

## North Star

Help 100,000 people become security-literate — safely — by making practice feel like play.
