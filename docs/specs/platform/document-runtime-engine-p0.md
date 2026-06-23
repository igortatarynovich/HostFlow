# Document Runtime Engine — platform capability canon (P0)

**Status:** Accepted (architecture canon). **Implementation:** P0 canon only — **no runtime unification in this slice**.  
**Hierarchy:** L2 operating canon — platform layer. **Lifecycle runtime** for document *instances* (distinct from Document Hub storage and Requirement Rules evaluation).  
**Owner:** Architecture canon + platform core team.

**Opened:** 2026-06-23 — immediately after **Requirement Rules Engine v1 closed** ([`requirement-rules-engine-p0.md`](requirement-rules-engine-p0.md) §20).

**Related canon (must stay consistent):**

| Document | Relationship |
|----------|--------------|
| [`ADR-009`](../architecture/ADR-009-document-hub-platform-layer.md) | Document Hub owns storage, types, links, verification workflow shell |
| [`requirement-rules-engine-p0.md`](requirement-rules-engine-p0.md) | Requirement Engine evaluates *what must exist*; Document Runtime evaluates *instance lifecycle state* |
| [`entity-profile-definition-registry.md`](entity-profile-definition-registry.md) | Entity Profile references `document_pack_code`; does not own per-document lifecycle |
| [`process-engine.md`](process-engine.md) | Stage transitions consume readiness + document satisfaction signals |

---

## 1. Purpose

The **Document Runtime Engine** answers:

> What is the canonical lifecycle state of this document instance right now — and what operational signals does that produce for readiness, gates, notifications, and dashboards?

Transport recruitment and HR are **document-centric** control domains. HostFlow already knows **which documents are required** (Requirement Rules Engine v1). The next foundation gap is **how each document instance lives over time** after upload.

| Responsibility | Detail |
|----------------|--------|
| **Lifecycle states** | Canonical states for a document instance (uploaded → review → approved/rejected → expiry → replacement) |
| **Runtime evaluation** | Pure function: document snapshot + type policy → `document_runtime_v1` |
| **Expiry dimension** | `valid`, `expiring_soon`, `expired`, `missing_expiry` (orthogonal to workflow status) |
| **Replacement / supersession** | When a new file replaces an old one without breaking entity links |
| **Consumer signals** | Normalized output for Requirement Engine, Readiness, Process Engine, Notifications, Dashboard |

**Main canon (non-negotiable):**

| Layer | Question |
|-------|--------|
| **Document Hub** | Where is the file, who owns it, who can access it? |
| **Requirement Rules Engine** | What document types must be present / verified for this entity profile and stage? |
| **Document Runtime Engine (this)** | What is the **lifecycle state** of each required document instance? |

---

## 2. Non-goals (P0)

Document Runtime Engine is **not**:

| Non-goal | Where it belongs instead |
|----------|--------------------------|
| File storage / upload UX | Document Hub |
| Required document *sets* / packs | Entity Profile + Document Pack + Requirement Rules |
| Stage transition orchestration | Process Engine |
| Reminder task tables | Activity & Notification Operating Layer ([`ADR-012`](../architecture/ADR-012-activity-notification-operating-layer.md)) |
| Reference pack applicability | Reference / applicability resolver |
| Custom lifecycle scripts per tenant | Forbidden — same class of drift as Requirement Rules custom expressions |

---

## 3. Position in architecture

### 3.1 Platform stack (post–Requirement Rules v1)

```
Field Registry
        ↓
Entity Profile (composition)
        ↓
Requirement Rules Engine v1  ← what must exist
        ↓
Document Hub (instances, files, links)
        ↓
Document Runtime Engine      ← instance lifecycle state
        ↓
┌──────────────┬─────────────┬──────────────┬────────────────┐
│ Readiness    │ Process     │ Notifications│ Dashboard /    │
│              │ Engine      │              │ HR queues      │
└──────────────┴─────────────┴──────────────┴────────────────┘
```

Requirement Engine **consumes** document snapshots; Document Runtime **defines** how those snapshots are interpreted into lifecycle states.

### 3.2 Current code (partial — not yet unified)

| Area | Path | Role today |
|------|------|------------|
| Expiry evaluation | `backend/app/services/document_expiry_engine.py` | Per-document expiry states |
| Workflow statuses | `backend/app/models/enums.py` (`DocumentStatus`) | Operational status enum |
| Owner summary buckets | `backend/app/modules/documents/owner_summary.py` | ready / in_progress / problem / missing |
| Requirement satisfaction | `backend/app/requirement_rules/evaluator.py` | `_document_satisfied()` — tactical, not lifecycle canon |

**P0 goal:** unify lifecycle vocabulary and evaluation contract — not rewrite all consumers in P0.

---

## 4. Canonical lifecycle dimensions (P0 sketch)

### 4.1 Workflow status (verification path)

Canonical workflow states (minimum set for v1 runtime):

| State | Meaning |
|-------|---------|
| `missing` | Required type absent or placeholder only |
| `uploaded` | File present; not yet reviewed |
| `pending_review` | Awaiting verifier action |
| `approved` | Accepted for operational use |
| `rejected` | Not acceptable; may require re-upload |
| `replaced` | Superseded by a newer instance (link preserved) |
| `superseded` | Older instance after replacement |

Existing `DocumentStatus` enum may map into this canon during P1 — P0 defines vocabulary only.

### 4.2 Expiry status (time dimension)

| State | Meaning |
|-------|---------|
| `valid` | Not expired; outside expiring-soon window |
| `expiring_soon` | Within configured threshold |
| `expired` | Past expiry date |
| `missing_expiry` | Type requires expiry date but none recorded |

Already partially implemented in `document_expiry_engine.py`.

### 4.3 Combined runtime output (target contract)

```yaml
document_runtime_v1:
  document_id: ...
  document_type_code: passport
  workflow_status: approved
  expiry_status: expiring_soon
  satisfies_requirement: true   # input to Requirement Engine re-evaluation
  blockers: []
  evaluated_at: ...
```

---

## 5. Consumers (target)

| Consumer | Uses runtime for |
|----------|------------------|
| **Requirement Rules Engine** | `_document_satisfied()` replacement — verification + expiry aware |
| **Readiness / Transfer policy** | Package ready, handoff allowed |
| **Process Engine** | Transition gates beyond field/doc presence |
| **Document Hub UI** | Summary buckets, missing/expiring tabs |
| **Notifications** | Expiry reminders, rejection follow-ups |
| **HR / workforce queues** | Verification backlog |

---

## 6. Hard rules (P0 gate)

Document lifecycle logic **must not** be duplicated ad hoc in:

| Forbidden location | Reason |
|--------------------|--------|
| Requirement Rules registry / overrides | Requirements ≠ instance state |
| Frontend components | Client display only; call runtime API |
| Transfer policy one-off status sets | Migrate to runtime evaluator |
| Per-tenant Python scripts | Same anti-pattern as Requirement Rules scripting |

**Allowed:** Document Runtime evaluator + type/policy registry + Document Hub as instance source.

---

## 7. P0 deliverables (this document)

| # | Deliverable | Status |
|---|-------------|--------|
| 1 | Purpose and boundary vs Hub / Requirement Rules | **Done** (this doc) |
| 2 | Lifecycle vocabulary (workflow + expiry) | **Done** (§4) |
| 3 | Architecture position + consumer map | **Done** (§3, §5) |
| 4 | Current-code inventory / gap | **Done** (§3.2) |
| 5 | Target output contract sketch | **Done** (§4.3) |
| 6 | Hard rules | **Done** (§6) |

**Next implementation step (P1):** `document_runtime_v1` evaluator module; map existing `DocumentStatus` + expiry engine into unified output; wire Readiness consumer first (strangler).

---

## 8. Explicitly not next (avoid architecture bloat)

Same discipline as Requirement Rules post-v1:

- Custom lifecycle expressions per tenant  
- Visual lifecycle designer UI  
- Per-client lifecycle overrides  
- Replacing Document Hub storage model  
- Requirement Rules P4 / v2 feature creep  

---

## Changelog

- 2026-06-23: P0 accepted — Document Runtime Engine canon opened as next foundation layer after Requirement Rules Engine v1 closure.
