# CyberVerse Game Design

## Vision

CyberVerse is an **educational cybersecurity simulation platform**: an interactive adventure where learners play as "agents" in a fictional cyber agency. Every hands-on activity happens inside CyberVerse's own simulated environments — a safe, legal sandbox where mistakes are learning opportunities.

> **Core promise**: Learn cybersecurity by doing — without touching anything real.

## Design Pillars

1. **Safety first** — All hosts, networks, targets, and data are fictional. No real-world systems are ever involved. Explicit rules and warnings at every sandbox boundary.
2. **Learn by doing** — Content is mission-driven: read a concept, immediately apply it in the sandbox, get feedback.
3. **Progression as motivation** — XP, levels, streaks, badges, titles, and leaderboards reward consistency, not just completion.
4. **Community** — Teams, DMs, and shared missions make learning social.
5. **Accessibility** — Free core content; premium tier adds advanced labs and AI tutoring.

## Player Journey

```
Onboarding → Foundations path → First sandbox mission → Daily challenges
     → Specialization (offense / defense / forensics) → Certificates → Teams & competitions
```

## Narrative Frame

- **Setting**: The "CyberVerse Agency" — a fictional international cyber defense organization.
- **Player role**: Recruit → Analyst → Specialist → Commander (rank ladder mirrors level).
- **Missions**: Recruit briefings ("Operation Darknet", "The Leaky API") — fictional scenarios with real teaching payloads.
- **Tone**: professional, encouraging, zero glorification of harm; every mission opens with a **legal & ethical briefing**.

## Learning Paths

| Path | Level | Focus |
|------|-------|-------|
| Cybersecurity Foundations | Beginner | Networks, protocols, cryptography basics, threat modeling |
| Offensive Security | Intermediate | Recon, enumeration, vulnerability discovery, exploitation **in sandbox only** |
| Defensive Security | Advanced | Detection, hardening, incident response, forensics |
| Cyber Investigations | Intermediate | Log analysis, OSINT on fictional data, reporting |

Each path = LearningPath → Courses → Modules → Lessons (+ quizzes) → certificate.

## Mission Format

Each mission contains:

1. **Briefing** — story context + legal/ethical framing
2. **Objectives** — 2–6 concrete, verifiable steps (validated by `mission_objectives.validation` rules)
3. **Simulated environment** — flags/tokens captured via the sandbox, validated server-side
4. **Debrief** — what you did, why it works in the real world, and where the line is
5. **Rewards** — XP, coins, badges, mission completion count

## Gamification System

| System | Mechanics |
|--------|-----------|
| XP | Lessons +50, quizzes +50, mission objectives +20–50, mission completion bonus, daily check-in 10–100 (streak scaling) |
| Levels | `level = floor(sqrt(xp/100)) + 1`; level gates premium missions |
| Coins | Quiz rewards + missions; future cosmetics/inventory |
| Streaks | Daily check-in; bonus grows with consecutive days (capped) |
| Badges/Titles | Achievement criteria engine (lessons, missions, quizzes, social) |
| Leaderboard | Weekly rotation, rebuilt by Celery, all-time fallback |
| Certificates | Course completion → verifiable certificate (UUID, issue date) |

## Sandbox Design (Key Rule)

- Simulated environments are **self-contained**: containerized VMs/webs with fictional domains (`*.sandbox.cyberverse`), fake credentials, and fabricated data
- No live internet access from sandboxes; no real credentials ever used
- Flags are random tokens; validation happens server-side against `validation` rules, never by client-side trust
- Enforcement: ethical use policy in onboarding, activity watermarking, moderation queue

## AI Integration

- **Quiz generation** — topic → practice questions (OpenAI, fallback templates)
- **Hints** — progressive hints on demand (premium)
- **Explainers** — plain-language concept explanations
- **Progress analysis** — personalized recommendations
- All AI output is educational and reviewed for safety prompts

## Premium Tier

| Tier | Price (placeholder) | Features |
|------|---------------------|----------|
| Free | $0 | Core paths, daily challenges, leaderboard |
| Premium | $9/mo (TBD) | Advanced labs, AI tutor, unlimited attempts, early content |

## Future (UE5 Game Client)

Long-term vision: an Unreal Engine 5 client rendering the "verse" as a 3D space — players navigate a facility, enter training rooms, and run sandbox missions visually. The API + XP/achievement systems are designed to be client-agnostic so the UE5 client can reuse the entire backend.

## Content Rules

- All names, companies, domains, and scenarios are fictional
- No real exploits beyond foundational concepts; no weaponization
- Every mission includes legal/ethical framing
- Instructor-authored content must pass moderation before publish
