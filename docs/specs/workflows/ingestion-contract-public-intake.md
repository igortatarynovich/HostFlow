# Ingestion contract — Public candidate intake (web form)

**Channel:** Public candidate intake (`POST /api/v1/public/intake`, apply token flow)  
**Status:** **Accepted (2026-07-02)** — implements [ADR-013](../architecture/ADR-013-public-intake-strategy.md) Decision **(2) Lead stub on submit** via P5C Lead-first draft session.  
**Owner (engineering):** Platform / Entity Profile + Recruitment module  
**Owner (product / ops):** Recruitment agency intake

**Related:** [entity-profile-definition-registry.md](../platform/entity-profile-definition-registry.md) P5C, [public_intake_draft_session.py](../../../backend/app/entity_profile/public_intake_draft_session.py)

---

## 1. Channel

| Field | Value |
|--------|--------|
| **Name** | Public candidate intake (TenantLeadForm / Entity Profile presentation) |
| **Owner (engineering)** | Platform Core + Recruitment |
| **Owner (product / ops)** | Recruitment agency tenant admins |

---

## 2. Intake type — what is created first

| Initially created | Yes / No / N/A | Notes |
|-------------------|----------------|--------|
| Lead | **Yes** | `source=public_intake`, `stage=intake_draft` during form fill; no Candidate INSERT on create (P5C) |
| Candidate (draft or live) | **No** (create path) / **Yes** (submit outcome) | Candidate only via Decision Layer + Outcome Executor on submit |
| Standalone intake event / signal | N/A | |
| Import batch / job | N/A | |
| None (passthrough only) | N/A | |

**Legacy exception (in-flight only):** tokens bound to pre-P5C Candidate draft sessions remain supported via `resolve_public_intake_session()` fallback until TTL expiry. No new Candidate-first creates.

**Client application kind:** `application_kind=client` on submit may create/update a **client Lead** (`source=public-intake` legacy hyphen path for company inquiries) — separate from recruitment candidate flow.

---

## 3. Conversion boundary

| Action | Allowed? | Decision by | Notes |
|--------|----------|-------------|--------|
| Create Candidate | **Conditional** | **Auto** on submit when Decision Layer returns `create_candidate` | `submit_public_intake_lead_draft()` → `execute_outcome_decision()` |
| Create Application | **Conditional** | System after Candidate + vacancy/pool intent | Same rules as Meta path when `lead_id` set |
| Attach to existing Candidate | **Conditional** | System (duplicate disposition) | `blocked_duplicate` → `lead.candidate_id` attach, `status=duplicated` |
| Create / link Workforce or HR-related event | N | | |

**CRM manual convert:** `POST /leads/:id/process` and `POST /leads/:id/intake-decision` are **not** supported for `public_intake` source (readonly in CRM UI).

---

## 4. Duplicate semantics

**Identifiers:** phone, email (stable contact key → `external_id=public-intake-draft:{stable}`)

| Topic | Specification |
|--------|----------------|
| **Exact duplicate** | Decision Layer may return attach / block; lead `status=duplicated`, `candidate_id` set when attach |
| **Possible duplicate / review** | Per Decision Layer + tenant rules; no CRM intake-decision rail |
| **Replay / idempotent delivery** | Same contact reuses draft Lead while `stage=intake_draft`; submit idempotent per lead token |

---

## 5. Vacancy / intent semantics

| | |
|--|--|
| **Intent present** | vacancy (form route / field) and/or pool via Decision Layer |
| **How vacancy is determined** | public form slug → Entity Profile mapping; optional vacancy on form context |

Application rules: Application row only when vacancy or explicit pool intent after Candidate exists — same as global doctrine.

---

## 6. Assignment semantics

| Path | Y/N | Details |
|------|-----|--------|
| Lands in unassigned queue | Y | Lead visible in CRM; recruiter opens candidate when created |
| Auto-assign | N | |
| Manual claim | Y | Standard lead assignment when shown in inbox |
| HR-only review | N | |
| Routing / intake review queue | N | No Meta-style `needs_routing` manual process |

---

## 7. Intake resolution

**Actions exposed in CRM for this channel:** qualify · reject · request info · convert · pool · reroute · duplicate review → **N** (all via public form + Decision Layer on submit, not CRM rail)

| Topic | |
|--------|--|
| **Where resolved** | Public form submit + Decision Layer (headless); CRM is **audit / navigation** only |
| **Blocked states** | `intake_draft` — form in progress; CRM shows read-only guidance |

### 7.1 Lead-stage RODO (art. 14)

| Topic | Specification |
|--------|----------------|
| **Notice at source** | Public form consents → `source_provided` in intake state |
| **Auto-send on ingest** | N/A for draft create; tenant `lead_rodo_send_mode` applies if Lead enters gated CRM actions (not used for this channel's primary path) |
| **Channel missing** | Consents captured on form submit |
| **Replay idempotency** | Draft reuse by stable contact key |
| **Gated actions** | CRM intake-decision/process **not exposed** for `public_intake` |

---

## 8. Activity continuity

| Carry over on convert / attach | Y/N | Mechanism |
|--------------------------------|-----|-----------|
| Calls / comms history | N | No pre-candidate CRM work |
| Notes | Partial | Lead payload / normalized intake_state |
| Reminders / SLA | N | |
| Documents / requests | Y | `pending_documents` on draft → Outcome Executor on submit |
| Conversations | N | |

**Must not duplicate after handoff:** first-call task — Guard 1 applies when lead had operational touch before convert (typically N/A for pure public submit).

---

## 9. Allowed divergence

| Divergence | Why | Owner | ADR / spec link | Planned convergence? |
|------------|-----|-------|-----------------|----------------------|
| Legacy Candidate draft tokens | In-flight sessions pre-P5C | Eng | ADR-013 | Y — TTL expiry |
| Client inquiry `source=public-intake` (hyphen) | Company/client application kind | Product | ADR-013 § client branch | N — separate lead type |
| No CRM intake-decision rail | Decision on form submit | Product | This contract | N — by design for channel |
| Legacy `create_public_intake_draft_via_service` (Candidate-first) | Deprecated entry | Eng | [candidate-creation-entrypoints-audit.md](candidate-creation-entrypoints-audit.md) | Y — remove when no callers |

---

## 10. Guardrails (sign-off checklist)

- [x] Lead ≠ Candidate (no collapsing entities in UX or API shortcuts)
- [x] Candidate ≠ Application
- [x] No Application without **vacancy or explicit pool intent**
- [x] No silent duplicate Candidate creation (Decision Layer + idempotent submit)
- [x] No fake / duplicate operational activities for the same human intent
- [x] No undocumented divergence (§9 complete)
- [x] Automation and notifications **after** encoded semantics for this channel
- [x] Lead created: RODO via form consents (§7.1)

**Reviewers:** Direction A slice A5 **Date:** 2026-07-02
