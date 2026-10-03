# CyberVerse – Neo Analysis: Realistic Simulation System

**Status**: Design spec · **Scope**: Platform-wide simulation engine · **Owner**: Core team

Neo Analysis is the simulation layer that makes CyberVerse feel like working as a real cybersecurity professional. Every mission happens inside a **fictional digital world** — a complete virtual internet with its own companies, infrastructure, employees, and threat actors — or inside **user-controlled training environments** the player owns and explicitly authorizes.

> **Non-negotiable rule**: Neo Analysis never attacks arbitrary third-party systems. All built-in content is simulated; the only real systems involved are ones the player owns and consents to use for training.

---

## 1. Core Concept

Neo Analysis recreates the *experience* of a security operations career, not just a course:

- You are an analyst at a fictional security provider inside the virtual internet.
- Companies in the virtual world hire you (via story missions) to investigate incidents, secure infrastructure, and respond to threats.
- The world is **generative**: no two playthroughs share the same companies, incidents, or attack timelines.
- An **AI mentor** coaches you through every task, explains concepts, and adapts missions to your skill level.

## 2. The Virtual Internet

### 2.1 World entities

| Entity | Details |
|--------|---------|
| Fictional companies | Banks, hospitals, universities, airports, data centers, cloud platforms, IoT factories, smart cities, government agencies, media, retail |
| Infrastructure | Web apps, file servers, mail servers, DNS, Active Directory, VPN, databases, firewalls, IDS/IPS, backups, SCADA/ICS |
| People | Employees with names, roles, emails, access rights, habits (weak passwords, phishing susceptibility) |
| Data | Documents, emails, logs, PII (fictional), financial records, source code, credentials |
| Operations | Help-desk tickets, incident reports, maintenance windows, security alerts, change requests |
| Threat actors | Script kiddies, ransomware gangs, insider threats, APTs, hacktivists — all fictional |

### 2.2 World consistency rules

- Every organization gets: employees, email system, file servers, web applications, DNS, Active Directory, VPN, logs, security alerts, backups, and policies.
- State is **persistent and coherent**: a phishing email sent at 09:00 may appear in a user's inbox, trigger a help-desk ticket, and show up in the SIEM — one causal timeline.
- All company names, domains (`*.sim.cyberverse`), and data are procedurally generated and fictional.

## 3. Dynamic AI World

The AI world generator produces a fresh, coherent world on demand:

| Generated artifact | Description |
|--------------------|-------------|
| Companies | Name, industry, size, revenue, tech stack, geography |
| Users & devices | Employees, workstations, servers, IoT devices with owners |
| Services & configs | OS/versions, open ports, running services, patch levels |
| Security events | Alerts, detections, policy violations |
| Help-desk tickets | Incident reports, requests, SLAs |
| Logs & traffic | Network flows, auth logs, web logs, email logs |
| Threat scenarios | Campaigns with kill chains that unfold over time |

Generation is **seeded per player** so a world can be shared with a team (same seed → same world) or regenerated for replays. Deterministic seed + rules engine = reproducible, auditable scenarios.

## 4. Interactive Gameplay

Players perform real defensive and investigative workflows:

- **Investigate alerts** — triage SIEM-style alert queues, correlate events
- **Review logs** — parse auth/web/network logs, spot anomalies
- **Analyze malware** — detonate samples in an isolated sandbox, inspect behavior (simulated)
- **Secure servers** — apply hardening baselines, patch, disable unneeded services
- **Configure firewalls & IDS** — build rule sets and test them against simulated traffic
- **Respond to incidents** — contain, eradicate, recover, and write incident reports
- **Perform forensics** — timeline analysis, artifact collection, evidence chain-of-custody
- **Hunt threats** — proactive hypothesis-driven detection in the simulated SIEM
- **Complete story missions** — multi-hour campaigns with narrative arcs and stakeholders

Every action is validated server-side (same pattern as mission objectives) and feeds XP, coins, and the leaderboard.

## 5. AI Mentor

A persistent in-world mentor with these capabilities:

- Explains every task before you start
- Teaches cybersecurity concepts in context ("why does this firewall rule matter?")
- Reviews player decisions and offers constructive feedback
- Provides progressive hints (never spoils the learning moment)
- Creates **adaptive missions** tuned to observed skill gaps
- Tracks progress and recommends next steps

Backed by the existing AI service (`app/services/ai_service.py`) with deterministic fallback content so the platform works offline.

## 6. Safe Training Labs

Neo Analysis optionally connects to environments the player **owns or explicitly created for training**:

| Environment | Example |
|-------------|---------|
| Local VMs | Hyper-V/VirtualBox practice VMs |
| Docker labs | `docker run` intentionally vulnerable containers |
| Home labs | Personal homelab VLANs |
| Practice ranges | CTF platforms, authorized cyber ranges |

### 6.1 Authorization verification (mandatory)

Before any connection, Neo Analysis verifies the environment is user-controlled or explicitly authorized:

1. **Ownership proof** — player registers the environment through an authenticated flow (agent/API key generated in-app).
2. **Scope declaration** — player declares IP ranges/domains covered; only declared scope is ever touched.
3. **Consent recording** — an explicit authorization record is stored (timestamp, scope, environment ID) and shown in the player's lab profile.
4. **Red-line checks** — the engine refuses any target outside declared scope; unknown/unclaimed hosts are always off-limits.
5. **Audit trail** — every lab interaction is logged to `audit_logs` for review.

### 6.2 Lab support in-app

- Lab inventory + status (online/offline, agent version)
- Connection health checks (agent heartbeat)
- Mission templates that run against your own lab (e.g., "harden this VM")
- Auto-reports with before/after state for learning

## 7. Safety Rules

1. **No arbitrary third-party targets** — built-in missions only touch simulated entities or authorized labs.
2. **No real credentials** — all simulated credentials are fictional; real credentials never enter the platform.
3. **Sandbox isolation** — malware analysis and exploitation practice run in isolated, disposable containers with no network egress.
4. **Authorized-only automation** — any active scanning/exploitation is scoped, rate-limited, and only against declared scope.
5. **Ethical framing** — every mission opens with a legal & ethical briefing; violations of scope result in immediate revocation of lab access and review.
6. **Zero glorification** — content teaches defense-first mindset; offensive concepts are taught as necessary understanding for defenders.
7. **Fictional everything** — company names, people, domains, and data in the virtual internet are generated and fictional; similarity to real entities is coincidental.

## 8. Goal

Deliver a **AAA-quality cybersecurity simulation** that:

- Feels authentic — the world behaves like real infrastructure with real operational cadence
- Teaches real defensive skills — responders, analysts, engineers, forensics experts
- Provides a realistic career experience — from SOC analyst to incident commander
- Stays safe and authorized — every practical activity is simulated or user-owned

## 9. Integration with the Existing Platform

| Neo Analysis concept | Existing backend |
|----------------------|------------------|
| Missions & objectives | `missions`, `mission_objectives`, `mission_progress`, `objective_progress` (server-side validation rules) |
| Player state & rewards | `player_progress`, XP/level/coins system, leaderboards |
| World encyclopedia | `encyclopedia_articles` (concept database) |
| Generated events/analytics | `analytics_events` (funnel & engagement tracking) |
| AI mentor & generation | `app/services/ai_service.py` (OpenAI + deterministic fallback) |
| Lab authorization records | new tables: `lab_environments`, `lab_authorizations` (v2.0 scope) |
| Simulated world state | new module `sim/` — world generator + scenario engine (v2.0 scope) |
| Audit | `audit_logs` (every world/lab action) |

### Suggested rollout

1. **v0.2** — mission engine already supports objective validation; add AI-generated scenario briefings and the encyclopedia.
2. **v0.3** — safe lab connector (agent + authorization flow) with scope enforcement.
3. **v1.x** — Neo Analysis world generator (virtual internet v1: 10 industries, seeded worlds).
4. **v2.0** — full dynamic world with living timelines, help-desk simulation, and UE5 client rendering.
