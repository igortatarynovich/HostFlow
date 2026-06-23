# Document Runtime Engine — platform capability canon (P0)

**Status:** Accepted (architecture canon). **Implementation:** **Document Runtime Engine v1 — closed** (2026-06-23). P0 canon + P1–P4 runtime complete.  
**Hierarchy:** L2 operating canon — platform layer. **Lifecycle runtime** for document *instances* (distinct from Document Hub storage and Requirement Rules evaluation).  
**Owner:** Architecture canon + platform core team.

**Opened:** 2026-06-23 — immediately after **Requirement Rules Engine v1 closed** ([`requirement-rules-engine-p0.md`](requirement-rules-engine-p0.md) §20).

**Next platform track (post-v1 foundation):** [`document-expiry-notifications-p0.md`](document-expiry-notifications-p0.md) — Document Expiry Notifications canon (downstream). **Not** Document Runtime v2 foundation expansion.

**Related canon (must stay consistent):**

| Document | Relationship |
|----------|--------------|
| [`ADR-009`](../architecture/ADR-009-document-hub-platform-layer.md) | Document Hub owns storage, types, links, verification workflow shell |
| [`requirement-rules-engine-p0.md`](requirement-rules-engine-p0.md) | Requirement Engine evaluates *what must exist*; Document Runtime evaluates *instance lifecycle state* |
| [`entity-profile-definition-registry.md`](entity-profile-definition-registry.md) | Entity Profile references `document_pack_code`; does not own per-document lifecycle |
| [`document-expiry-notifications-p0.md`](document-expiry-notifications-p0.md) | Downstream expiry notification events (post-v1) |
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

### 3.2 Closed foundation chain (v1)

```
Document Instance (Document Hub snapshot)
        ↓
Document Runtime Evaluator     ← lifecycle + expiry (single source)
        ↓
Delivery Contract              ← document_runtime_v1 DTO (single delivery layer)
        ↓
┌──────────────┬─────────────────┬─────────────────┐
│ Readiness    │ Document Hub    │ Process Engine  │
│ (P1)         │ (P2)            │ (P3)            │
└──────────────┴─────────────────┴─────────────────┘
```

| Area | Path | Role |
|------|------|------|
| Runtime evaluator | `backend/app/document_runtime/evaluator.py` | Canonical lifecycle + expiry → `document_runtime_v1` |
| Expiry primitives | `backend/app/services/document_expiry_engine.py` | Expiry date evaluation (used by evaluator) |
| Delivery contract | `backend/app/document_runtime/delivery_contract.py` | Single runtime delivery layer for all consumers |
| Service facade | `backend/app/services/document_runtime_delivery_contract.py` | Service-layer `_via_contract` entry points |
| Readiness bridge | `backend/app/document_runtime/readiness_bridge.py` | Thin delegate to delivery contract |
| Hub bridge | `backend/app/document_runtime/hub_bridge.py` | Thin delegate + hub section overlay |
| PE bridge | `backend/app/document_runtime/pe_bridge.py` | Thin delegate + transition gate mapping |
| Requirement Engine integration | `backend/app/requirement_rules/evaluator.py` | Consumes delivery contract for document satisfaction |

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
| **Requirement Rules Engine** | Document satisfaction via delivery contract — verification + expiry aware |
| **Readiness** / Transfer policy | ✅ v1 wired — package ready, handoff signals |
| **Process Engine** | ✅ v1 wired — `ready_for_handoff` transition gate |
| **Document Hub** | ✅ v1 wired — checklist / summary runtime items |
| **Notifications** | Downstream — Document Expiry Notifications P0 (post-v1) |
| **HR / workforce queues** | Downstream — consumes contract |

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

**Next implementation step:** Superseded — **v1 closed** (§20). Next downstream track: Document Expiry Notifications P0 (after doc closure).

---

## 9. P1–P4 implementation status (2026-06-23)

| Milestone | Scope | Status | Location |
|-----------|-------|--------|----------|
| **P1** | Unified evaluator + Readiness consumer | ✅ Done | `evaluator.py`, `readiness_bridge.py`, `requirement_rules/evaluator.py` |
| **P2** | Document Hub consumer bridge | ✅ Done | `hub_bridge.py`, `document_hub_bridge.py` |
| **P3** | Process Engine transition gate (`ready_for_handoff`) | ✅ Done | `pe_bridge.py`, `transition_bridge.py` |
| **P4** | Runtime delivery contract | ✅ Done | `delivery_contract.py`, `document_runtime_delivery_contract.py` |

**P1 acceptance:** `satisfies_requirement` only when approved + not expired; uploaded/pending/rejected/expired block; expiring soon warns.

**P2 acceptance:** Document Hub checklist exposes `document_runtime_v1` per required document type; instance matching via best precedence.

**P3 acceptance:** PE transition block reasons include `source_layer=document_runtime` + nested `document_runtime_v1`.

**P4 acceptance:** Readiness / Hub / PE receive identical runtime for the same document instance via delivery contract; lifecycle + expiry defined only in evaluator.

---

## 20. Document Runtime Engine v1 — closed (2026-06-23)

**Milestone:** Document Runtime Engine **v1 foundation is closed**. Working runtime with three wired consumers and a unified delivery contract — not a concept doc.

### 20.1 Foundation chain (complete)

```
Document Instance → Document Runtime Evaluator → Delivery Contract → Consumers
```

| Layer | Question | Owner |
|-------|----------|-------|
| **Document Hub** | Where is the file / instance snapshot? | Document Hub |
| **Requirement Rules Engine** | What document types are required? | Requirement Engine |
| **Document Runtime Evaluator** | What is lifecycle + expiry state? | `document_runtime/evaluator.py` |
| **Delivery Contract** | How is `document_runtime_v1` delivered uniformly? | `document_runtime/delivery_contract.py` |

### 20.2 Runtime consumers (complete)

| Consumer | Status | Bridge |
|----------|--------|--------|
| **Readiness** / Recruitment Package | ✅ | P1 `readiness_bridge.py` |
| **Document Hub** checklist / summary | ✅ | P2 `hub_bridge.py` + `document_hub_bridge.py` |
| **Process Engine** `ready_for_handoff` gate | ✅ | P3 `pe_bridge.py` + `transition_bridge.py` |

All consumers read through **P4 delivery contract** — no separate lifecycle mappers.

Evaluation output: `document_runtime_v1` with `evaluation_version=document_runtime_v1`.

### 20.3 Post-v1 maintenance (not foundation expansion)

| Track | Scope |
|-------|--------|
| Legacy owner-summary bucket alignment | Strangler — legacy `owner_summary.py` buckets remain for non-requirement-engine paths |
| Consumer hardening | Tests, parity, fail-safe guards |
| `DocumentStatus` enum mapping | Gradual alignment to canonical workflow states |

### 20.4 Explicitly out of scope for Document Runtime v2+ foundation (do not expand now)

| Forbidden expansion | Why |
|---------------------|-----|
| Notifications / reminder dispatch | Downstream consumer — Document Expiry Notifications P0 |
| Dashboard KPIs / HR queue scoring | Downstream consumer |
| Expiry cron jobs / campaigns | Downstream scheduler — not runtime canon |
| UI redesign / status badges | Presentation layer — consumes contract |
| Tenant lifecycle policies / scripting | Same anti-pattern as Requirement Rules custom expressions |
| Auto-create document rows | Document Hub product scope |
| Advanced review workflow | Document Hub verification UX |

**Next practical downstream track:** [`document-expiry-notifications-p0.md`](document-expiry-notifications-p0.md) — Document Expiry Notifications P3 complete; **P4 scheduled sync job** next.

Requirement Engine answers *what is required*; Document Runtime answers *what state each document instance is in*; Delivery Contract answers *how all consumers read that state consistently*.

---

## 8. Explicitly not next (avoid foundation bloat)

Same discipline as Requirement Rules post-v1 — **downstream consumers only after v1 closure (§20):**

- Custom lifecycle expressions per tenant  
- Visual lifecycle designer UI  
- Per-client lifecycle overrides  
- Replacing Document Hub storage model  
- Notifications, dashboards, expiry cron (separate downstream tracks — §20.4)  
- Requirement Rules v2 feature creep  

---

## Changelog

- 2026-06-23: P0 accepted — Document Runtime Engine canon opened as next foundation layer after Requirement Rules Engine v1 closure.
- 2026-06-23: P1 complete — unified evaluator + Readiness consumer; runtime-aware requirement satisfaction.
- 2026-06-23: P2 complete — Document Hub consumer bridge; runtime checklist per required document type.
- 2026-06-23: P3 complete — Process Engine `ready_for_handoff` gate via document runtime blockers.
- 2026-06-23: P4 complete — runtime delivery contract; Readiness / Hub / PE cross-consumer consistency.
- 2026-06-23: **Document Runtime Engine v1 foundation closed** — evaluator + delivery contract + three consumers; §20 milestone record.
- 2026-06-23: Cross-link — Document Expiry Notifications P3 complete; P4 scheduled sync next.
