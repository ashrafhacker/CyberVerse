# CyberVerse Labs API and Data Contract

This document defines the backend contract for CyberVerse Labs. It is designed for the Unreal Engine 5 client, the existing Next.js web app, instructors, admins, and future multiplayer sessions.

Base path: `/api/v1/labs`

## API Principles

- All lab APIs require an authenticated user unless explicitly marked public.
- Built-in labs use generated fictional data only.
- Home lab integration requires attestation, declared scope, and audit logging.
- Mission state is server-authoritative.
- UE5 clients may cache read models but must submit player actions as structured events.
- Objective validation is deterministic and never depends on real third-party targets.

## Core Endpoints

| Method | Path | Description | Min Role |
|---|---|---|---|
| GET | `/facilities` | List lab facilities and unlock state | student |
| GET | `/missions` | List available lab missions | student |
| GET | `/missions/{mission_id}` | Mission template detail | student |
| POST | `/sessions` | Start a generated lab session | student |
| GET | `/sessions` | List own lab sessions | student |
| GET | `/sessions/{session_id}` | Session summary and resume pointer | student |
| DELETE | `/sessions/{session_id}` | Abandon a resumable session | student |
| GET | `/sessions/{session_id}/world` | Generated world state for UE5 client | student |
| GET | `/sessions/{session_id}/tools/{tool_id}` | Tool-specific read model | student |
| POST | `/sessions/{session_id}/events` | Submit player action/event | student |
| POST | `/sessions/{session_id}/objectives/{objective_id}/submit` | Submit objective answer/action | student |
| GET | `/sessions/{session_id}/evidence` | List collected and available evidence | student |
| POST | `/sessions/{session_id}/evidence` | Collect or attach evidence | student |
| GET | `/sessions/{session_id}/timeline` | Investigation timeline | student |
| POST | `/sessions/{session_id}/notes` | Add note/bookmark | student |
| POST | `/sessions/{session_id}/report` | Submit final report | student |
| POST | `/sessions/{session_id}/complete` | Complete mission and calculate final score | student |
| GET | `/sessions/{session_id}/debrief` | Score, feedback, learning summary | student |

## AI Mentor Endpoints

| Method | Path | Description | Min Role |
|---|---|---|---|
| POST | `/sessions/{session_id}/mentor/explain` | Explain a concept using session context | student |
| POST | `/sessions/{session_id}/mentor/hint` | Request a scored hint | student |
| POST | `/sessions/{session_id}/mentor/review` | Review current investigation state | student |
| POST | `/sessions/{session_id}/mentor/quiz` | Generate post-mission quiz | student |
| GET | `/mentor/recommendations` | Lab and career recommendations | student |

## Instructor and Admin Endpoints

| Method | Path | Description | Min Role |
|---|---|---|---|
| POST | `/instructor/assignments` | Assign lab mission to class/team | instructor |
| GET | `/instructor/assignments/{id}` | Assignment progress | instructor |
| GET | `/instructor/sessions/{session_id}` | Review student session | instructor |
| POST | `/instructor/sessions/{session_id}/grade` | Grade or override score | instructor |
| POST | `/admin/templates` | Create mission template | administrator |
| PUT | `/admin/templates/{id}` | Update mission template | administrator |
| POST | `/admin/templates/{id}/validate` | Validate template and safety rules | administrator |
| POST | `/admin/scenarios/generate-preview` | Preview generated scenario | administrator |
| GET | `/admin/audit` | Lab audit events | administrator |

## Home Lab Integration Endpoints

| Method | Path | Description | Min Role |
|---|---|---|---|
| GET | `/home-labs` | List user's connection profiles | student |
| POST | `/home-labs/attestations` | Acknowledge ownership or authorization | student |
| POST | `/home-labs` | Create scoped home lab profile | student |
| POST | `/home-labs/{id}/test` | Test local agent connection | student |
| PATCH | `/home-labs/{id}` | Update scope or status | student |
| DELETE | `/home-labs/{id}` | Revoke profile | student |
| GET | `/home-labs/{id}/audit` | Connection audit log | student |

## Start Session Request

```json
{
  "mission_id": "uuid",
  "facility": "soc",
  "difficulty": "intermediate",
  "mode": "solo",
  "seed": "optional-player-visible-seed",
  "mentor_level": "guided"
}
```

## Session World Response

```json
{
  "session_id": "uuid",
  "scenario_seed": "cv-2026-soc-7Q4Z",
  "facility": "soc",
  "company": {
    "name": "Northstar Fabrication Group",
    "industry": "manufacturing",
    "size": "mid_market",
    "region": "fictional-us-east"
  },
  "assets": [
    {
      "id": "asset-001",
      "hostname": "nfg-hq-wks-014",
      "type": "windows_workstation",
      "location": "hq-floor-2",
      "criticality": "medium",
      "owner_user_id": "user-044",
      "services": ["edr_agent", "office_suite", "vpn_client"],
      "tags": ["finance", "managed"]
    }
  ],
  "identities": [],
  "alerts": [],
  "evidence": [],
  "objectives": [],
  "tool_manifest": []
}
```

## Event Contract

All player actions are submitted as structured events.

```json
{
  "event_type": "evidence.collected",
  "client_time": "2026-08-01T10:00:00Z",
  "tool_id": "soc-siem",
  "target_id": "alert-042",
  "payload": {
    "evidence_id": "ev-1001",
    "note": "Suspicious sign-in followed by impossible travel."
  }
}
```

## Objective Submission

```json
{
  "answer_type": "structured_action",
  "actions": [
    {
      "action": "disable_identity",
      "target_id": "user-044",
      "reason": "Compromised account confirmed by impossible travel and mailbox rule creation."
    },
    {
      "action": "quarantine_email",
      "target_id": "email-088"
    }
  ],
  "evidence_ids": ["ev-1001", "ev-1004", "ev-1012"]
}
```

## Debrief Response

```json
{
  "score": 86,
  "grade": "A",
  "xp_awarded": 420,
  "coins_awarded": 80,
  "strengths": [
    "Confirmed identity compromise before containment.",
    "Preserved relevant evidence before report submission."
  ],
  "missed_items": [
    "Mailbox forwarding rule should have been removed during remediation."
  ],
  "learning_summary": "You practiced alert triage, SIEM pivots, identity review, evidence handling, and containment.",
  "recommended_lessons": ["identity-security-basics", "phishing-response"],
  "career_feedback": "This maps to SOC Tier 1 and early incident response workflows."
}
```

## Scenario Generator Contract

The generator returns data that passes schema, realism, and safety validation before a session can start.

```json
{
  "template_id": "soc-phishing-compromise-v1",
  "seed": "cv-2026-soc-7Q4Z",
  "facility": "soc",
  "difficulty": "intermediate",
  "company_profile": {},
  "topology": {},
  "assets": [],
  "identities": [],
  "logs": [],
  "alerts": [],
  "evidence": [],
  "objectives": [],
  "scoring": {},
  "debrief_rubric": {},
  "safety_metadata": {
    "fictional_only": true,
    "uses_reserved_domains": true,
    "contains_real_malware": false,
    "targets_public_internet": false
  }
}
```

## Safety Validators

Scenario validation must reject:

- public IP targets except reserved documentation ranges
- real domains, real companies, or real people
- executable malware or live payloads
- instructions to attack third-party systems
- credential material that resembles real secrets
- objective types that require unauthorized access
- home lab sessions without active attestation and scope

Recommended reserved data:

- IPv4: `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `192.0.2.0/24`, `198.51.100.0/24`, `203.0.113.0/24`
- Domains: `example.test`, `cyberverse.test`, generated subdomains under owned training zones
- People: generated fictional names only

## UE5 Client Integration

- Authenticate through existing `/auth/login` and token refresh.
- Call `/labs/sessions` to create a session.
- Load facility map by `facility`.
- Call `/labs/sessions/{id}/world` after map streaming completes.
- Render workstation widgets from `tool_manifest`.
- Submit player actions through `/events`.
- Submit objective answers through `/objectives/{id}/submit`.
- Poll or subscribe to `/timeline` and `/debrief`.
- Cache session state locally for resilience but treat backend state as authoritative.
