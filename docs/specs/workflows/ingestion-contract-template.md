# Ingestion contract (template)

**Type:** lightweight governance artifact — **not** an ADR, not a full workflow spec.  
**Use:** copy this file per channel (or paste section 1–10 into a PR / ticket) and complete before merging **any new ingestion source** or **material change** to an existing one.

**Mandatory checkpoint:** code review / product sign-off must confirm sections **1–10** are filled and **§9 Allowed divergence** is honest (no undocumented “temporary” behaviour).

**Related:** [ADR-013-public-intake-strategy.md](../architecture/ADR-013-public-intake-strategy.md), [lead-intake-conversion-flow-audit.md](lead-intake-conversion-flow-audit.md), [lead-intake-resolution-and-activity-continuity.md](lead-intake-resolution-and-activity-continuity.md) §8 (incl. **§8.0.1 Lead-stage RODO**).

**Filled example:** [ingestion-contract-public-intake.md](ingestion-contract-public-intake.md) (public candidate form, ADR-013 Decision 2).

---

## 1. Channel

| Field | Value |
|--------|--------|
| **Name** | e.g. Meta Lead Ads, Telegram bot, public form, CSV import, WhatsApp, client portal, API intake, AI parsing, workforce import |
| **Owner (engineering)** | |
| **Owner (product / ops)** | |

---

## 2. Intake type — what is created first

Check one primary path (add notes if hybrid).

| Initially created | Yes / No / N/A | Notes |
|-------------------|----------------|--------|
| Lead | | |
| Candidate (draft or live) | | |
| Standalone intake event / signal | | |
| Import batch / job | | |
| None (passthrough only) | | |

---

## 3. Conversion boundary

| Action | Allowed? (Y/N/conditional) | Decision by: auto / recruiter / supervisor / HR / system rule | Notes |
|--------|---------------------------|---------------------------------------------------------------|--------|
| Create Candidate | | | |
| Create Application | | | |
| Attach to existing Candidate | | | |
| Create / link Workforce or HR-related event | | | |

---

## 4. Duplicate semantics

**Identifiers available for matching:** phone, email, telegram_id, external_id, passport, PESEL, other: ___

| Topic | Specification |
|--------|----------------|
| **Exact duplicate** | |
| **Possible duplicate / review** | |
| **Replay / idempotent delivery** (keys) | |

---

## 5. Vacancy / intent semantics

| | |
|--|--|
| **Intent present** | vacancy / pool / none (check) |
| **How vacancy is determined** | mapped campaign / recruiter selection / public route / API field / manual assignment / other: ___ |

Application rules: must align with [applications-operating-model.md](../architecture/applications-operating-model.md) — no Application without vacancy **or** explicit pool intent.

---

## 6. Assignment semantics

| Path | Y/N | Details |
|------|-----|--------|
| Lands in unassigned queue | | |
| Auto-assign (rule id / doc) | | |
| Manual claim | | |
| HR-only review | | |
| Routing / intake review queue | | |

---

## 7. Intake resolution

**Actions exposed or implied for this channel** (Y/N each): qualify · reject · request info · convert · pool · reroute · duplicate review

| Topic | |
|--------|--|
| **Where resolved** (UI / API / headless) | |
| **Blocked states** (e.g. duplicate_review) | |

### 7.1 Lead-stage RODO (art. 14) — if channel creates **Lead**

| Topic | Specification |
|--------|----------------|
| **Notice at source** | e.g. `rodo_notice_at_source`, public form consents → `source_provided`, **no duplicate outbound** |
| **Auto-send on ingest** | Platform-mandatory evaluation (art. 13/14); fulfill when required. Tenant SMTP or `info@hostflow.cc` fallback (see [§8.0.1](lead-intake-resolution-and-activity-continuity.md)) |
| **Channel missing** | `pending_channel`; gated actions blocked until manual send or source-provided |
| **Replay idempotency** | Same `external_id` must not trigger second outbound notice |
| **Gated actions** | process · request_info · contacted (and auto-on-first-action mode) |

---

## 8. Activity continuity

| Carry over on convert / attach | Y/N | Mechanism |
|--------------------------------|-----|-----------|
| Calls / comms history | | |
| Notes | | |
| Reminders / SLA | | |
| Documents / requests | | |
| Conversations (e.g. Telegram thread) | | |

**Must not duplicate after handoff:** first-call task · intro task · duplicate reminders · other: ___

---

## 9. Allowed divergence

Enterprise systems are rarely perfectly uniform on day one. The goal here is **controlled divergence** (documented, bounded, owned, with a convergence path) — not **accidental divergence** (“this endpoint temporarily does something else”).

Document **every** intentional difference from CRM Lead-first or global doctrine.

| Divergence | Why | Owner | ADR / spec link | Planned convergence? |
|------------|-----|-------|-----------------|----------------------|
| Example: Candidate created before canonical intake resolution | Public path | Product + eng | [ADR-013](../architecture/ADR-013-public-intake-strategy.md) | Y / N / TBD |

*If this table is empty, the channel must follow default doctrine with no special cases.*

---

## 10. Guardrails (sign-off checklist)

- [ ] Lead ≠ Candidate (no collapsing entities in UX or API shortcuts)
- [ ] Candidate ≠ Application
- [ ] No Application without **vacancy or explicit pool intent**
- [ ] No silent duplicate Candidate creation
- [ ] No fake / duplicate operational activities for the same human intent
- [ ] No undocumented divergence (§9 complete)
- [ ] Automation and notifications **after** encoded semantics for this channel
- [ ] If Lead is created: **RODO / art. 14** row in §7.1 complete (or explicit N/A with reason)

**Reviewers:** _________________ **Date:** _________
