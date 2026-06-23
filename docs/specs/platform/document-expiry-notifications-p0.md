# Document Expiry Notifications — platform capability canon (P0)

**Status:** Accepted (architecture canon). **Implementation:** P0 canon + **P1 Evaluator** + **P2 Event Registry** complete (2026-06-24). No dispatch or Notification Center UI yet.  
**Hierarchy:** L2 operating canon — platform layer. **Downstream consumer** of Document Runtime Engine v1 — emits notification *events*, not messages.  
**Owner:** Architecture canon + platform core team.

**Opened:** 2026-06-23 — immediately after **Document Runtime Engine v1 closed** ([`document-runtime-engine-p0.md`](document-runtime-engine-p0.md) §20).

**Next implementation step (post-P2 gate):** **P3 — Notification Center read UI** — consume stored open events; still no email/WhatsApp/cron/dispatch adapters.

**Related canon (must stay consistent):**

| Document | Relationship |
|----------|--------------|
| [`document-runtime-engine-p0.md`](document-runtime-engine-p0.md) | **Single upstream source** — `document_runtime_v1` + delivery contract |
| [`ADR-012`](../architecture/ADR-012-activity-notification-operating-layer.md) | Notification Center storage (`Notification` table) — **delivery sink**, not event source |
| [`activity-notification-operating-layer.md`](../architecture/activity-notification-operating-layer.md) | Activity vs Notification boundary; expiry types exist historically — migrate via this engine |
| [`ADR-009`](../architecture/ADR-009-document-hub-platform-layer.md) | Document Hub owns instances; does **not** own expiry notification logic |
| [`requirement-rules-engine-p0.md`](requirement-rules-engine-p0.md) | Requirement Engine defines *what is required*; does **not** trigger expiry notifications |

---

## 1. Purpose

The **Document Expiry Notification Engine** answers:

> Given canonical document runtime state, which **notification events** should exist for expiry-related attention — without deciding channels, templates, or delivery?

It does **not** notify about everything. It reacts **only** to states already computed in `document_runtime_v1`.

| Responsibility | Detail |
|----------------|--------|
| **Event evaluation** | Map runtime expiry signals → canonical notification events |
| **Idempotent event records** | Deduplicated event intent in `notification_events` (P2) |
| **Scope gate** | P0: `expiring_soon`, `expired` only |

**Main canon (non-negotiable):**

| Layer | Question |
|-------|----------|
| **Document Runtime Engine** | What is lifecycle + expiry state of this document instance? |
| **Document Expiry Notifications (this)** | Should an expiry-related **notification event** exist for this runtime state? |
| **Notification Center / channels** | How is the event shown or delivered to a user? (later) |

---

## 2. Non-goals (P0)

Document Expiry Notifications P0 is **not**:

| Non-goal | Where it belongs instead |
|----------|--------------------------|
| Email / WhatsApp / webhooks | Channel delivery layer (post-P1+) |
| Message templates | Presentation / i18n layer |
| Cron scheduler implementation | Platform scheduler / job runner |
| Escalation / SLA / digests | Activity & Notification Operating Layer policies |
| Tasks / Activities | ADR-012 `Activity` — separate from Notification events in P0 |
| Manager / supervisor routing | Assignment + notification routing (later) |
| Recurring reminder campaigns | Automation product scope |
| Re-evaluating expiry dates | Document Runtime evaluator + `document_expiry_engine.py` |
| Required document sets | Requirement Rules Engine |
| Document storage / upload UX | Document Hub |

**P0 rule:** If it sends a message, schedules a job, or creates a task — it is **out of scope**. P0 defines **events only**.

---

## 3. Position in architecture

### 3.1 Platform stack (post–Document Runtime v1)

```
Field Registry v1
        ↓
Entity Profile Registry v1
        ↓
Requirement Rules Engine v1     ← what must exist
        ↓
Document Hub (instances)
        ↓
Document Runtime Engine v1    ← lifecycle + expiry state
        ↓
Document Runtime Delivery Contract
        ↓
Document Expiry Notification Engine   ← expiry events (this)
        ↓
Notification Center (in-app)          ← P0 consumer
        ↓
(future) Email / Tasks / Webhooks     ← not P0
```

### 3.2 Delivery model — events first, not messages

```
Document Runtime
        ↓
Expiry Notification Engine (evaluate)
        ↓
Notification Event (canonical record / intent)
        ↓
Notification Center (persist + display)
        ↓
(future) channel adapters
```

**Hard rule:** The engine produces **`notification_event_v1`** (or equivalent canonical event DTO). It does **not** produce email bodies, WhatsApp text, or Activity rows in P0.

---

## 4. Source of truth

**Single upstream source:**

| Source | Role |
|--------|------|
| [`document_runtime/delivery_contract.py`](../../backend/app/document_runtime/delivery_contract.py) | Canonical `document_runtime_v1` per instance / required type |
| [`document_runtime/evaluator.py`](../../backend/app/document_runtime/evaluator.py) | Lifecycle + expiry evaluation (only place that defines `expiring_soon` / `expired`) |

**Forbidden upstream sources:**

| Forbidden | Why |
|-----------|-----|
| Document Hub owner-summary buckets | Legacy presentation; not runtime canon |
| Frontend expiry badges | Client display only |
| Requirement Engine blockers | Requirements ≠ notification triggers |
| Direct `expire_date` reads in notification code | Bypasses runtime contract |
| Ad-hoc cron SQL on `documents.expire_date` | Duplicates expiry logic |

---

## 5. Event model (P0)

### 5.1 Runtime state → notification event mapping

| Runtime `expiry_status` | Runtime `runtime_signal` | P0 notification event | P0 scope |
|-------------------------|--------------------------|----------------------|----------|
| `expiring_soon` | `expiring_soon` | `document_expiring_soon` | ✅ |
| `expired` | `expired` | `document_expired` | ✅ |
| `valid` | — | *(no event)* | — |
| `no_expiry` | — | *(no event)* | — |

### 5.2 Lifecycle states — deferred (not P0)

| Runtime `workflow_status` | Potential future event | P0 |
|---------------------------|------------------------|-----|
| `approved` | — | ❌ |
| `rejected` | `document_rejected` | ❌ optional future |
| `uploaded` / `pending_review` | — | ❌ |
| `missing` | — | ❌ (Requirement / Readiness domain) |

**P0 emits events only for expiry dimension**, not lifecycle verification path.

### 5.3 Target event contract (sketch)

```yaml
notification_event_v1:
  event_code: document_expiring_soon   # or document_expired
  source_layer: document_expiry_notifications
  tenant_id: ...
  owner_type: candidate                # or employee
  owner_id: ...
  document_id: ...
  document_type_code: passport
  document_runtime:                    # embedded snapshot from delivery contract
    evaluation_version: document_runtime_v1
    workflow_status: approved
    expiry_status: expiring_soon
    expires_on: ...
  severity: warning                    # expiring_soon → warning; expired → critical
  evaluated_at: ...
```

P1 evaluator outputs a list of these events — still **no dispatch**. Implemented in `document_expiry_notifications/evaluator.py` (`evaluate_document_expiry_events`).

---

## 6. Consumers (P0)

| Consumer | P0 | Role |
|----------|:--:|------|
| **Notification Center** (in-app) | ✅ | Persist + display expiry events |
| **Tasks / Activity** | ❌ | ADR-012 — later if product requires action items |
| **Email** | ❌ | Channel adapter — later |
| **WhatsApp** | ❌ | Channel adapter — later |
| **Webhooks** | ❌ | Integration adapter — later |

**P0 consumer rule:** Notification Center reads **evaluated events** from the Expiry Notification Engine. It does not re-derive expiry from Document Hub.

---

## 7. Hard rules (P0 gate)

Expiry notification logic **must not** be implemented in:

| Forbidden location | Reason |
|--------------------|--------|
| Document Hub router / owner_summary | Storage + legacy buckets only |
| Document Runtime evaluator | Runtime state only — not notification intent |
| Requirement Rules Engine | Requirements ≠ notifications |
| Frontend components | Display consumer |
| Transfer policy / Readiness | Already consume runtime for gates — not notification emission |
| Per-tenant scripts | Same anti-pattern as Requirement Rules scripting |

**Allowed:** Expiry Notification evaluator + event registry + Notification Center adapter.

---

## 8. P0 deliverables (this document)

| # | Deliverable | Status |
|---|-------------|--------|
| 1 | Purpose and boundary vs Runtime / Hub / ADR-012 | **Done** (this doc) |
| 2 | Source of truth (delivery contract only) | **Done** (§4) |
| 3 | Event model (`expiring_soon`, `expired` only) | **Done** (§5) |
| 4 | Events-first delivery model | **Done** (§3.2) |
| 5 | P0 consumer map (Notification Center only) | **Done** (§6) |
| 6 | Non-goals (no templates, cron, escalation) | **Done** (§2) |
| 7 | P1 scope gate | **Done** (§9) |

**Do not implement notification dispatch, templates, or schedulers until P0 is accepted.**

---

## 9. P1 implementation status (2026-06-23)

| Milestone | Scope | Status | Location |
|-----------|-------|--------|----------|
| **P1** | Expiry Event Evaluator | ✅ Done | `document_expiry_notifications/evaluator.py`, `document_expiry_notifications_delivery_contract.py` |

**P1 acceptance:**

| # | Criterion | Status |
|---|-----------|--------|
| 1 | Expired document → `document_expired` | ✅ |
| 2 | Expiring soon → `document_expiring_soon` | ✅ |
| 3 | Valid outside window → no event | ✅ |
| 4 | `no_expiry` → no event | ✅ |
| 5 | Rejected document → no expiry event | ✅ |
| 6 | One runtime snapshot → deterministic `event_key` | ✅ |
| 7 | No delivery / dispatch | ✅ |

**P1 chain:**

```
Document Runtime Delivery Contract
        ↓
evaluate_document_expiry_events()
        ↓
notification_event_v1[]
        ↓
(P2: Event Registry / Store — done)
        ↓
(P3: Notification Center read UI — next)
```

---

## 10. P2 implementation status (2026-06-24)

| Milestone | Scope | Status | Location |
|-----------|-------|--------|----------|
| **P2** | Notification Event Registry / Store | ✅ Done | `notification_events` table, `event_registry.py`, `api/v1/platform/notification_events.py` |

**P2 acceptance:**

| # | Criterion | Status |
|---|-----------|--------|
| 1 | Expired/expiring events persist | ✅ |
| 2 | Repeated evaluator run → no duplicates | ✅ |
| 3 | `event_key` unique per tenant | ✅ |
| 4 | List open events (read API) | ✅ |
| 5 | Mark event `resolved` or `ignored` | ✅ |
| 6 | No message dispatch | ✅ |

**P2 chain:**

```
evaluate_document_expiry_events()
        ↓
sync_document_expiry_events() / upsert_notification_events()
        ↓
notification_events (status: open | resolved | ignored)
        ↓
GET /platform/notification-events?status=open
        ↓
(P3: Notification Center read UI — next)
```

**Table:** `notification_events` — unique `(tenant_id, event_key)`; separate from ADR-012 `notifications` delivery sink.

---

## 11. P3 scope (after P2 gate)

**P3 — Notification Center read UI** (display consumer only):

| Deliverable | Description |
|-------------|-------------|
| Read UI | In-app list of open expiry events for assigned users |
| Input | Stored `notification_events` rows (`status=open`) |
| Output | Notification Center presentation — no channel dispatch |

**Explicitly out of P3:**

- Email / WhatsApp / webhooks
- Cron / scheduler jobs
- Templates and i18n (beyond minimal display)
- Escalation, digests, manager copies
- Activity / Task creation
- ADR-012 `notifications` row creation (optional later adapter)

---

## 12. Explicitly not next (avoid second Process Engine)

Without P0 discipline, expiry notifications become a second orchestration engine. **Forbidden early expansion:**

- Daily digest emails  
- Recurring reminder campaigns  
- Multi-step escalation ladders  
- SLA timers on expiry events  
- Per-tenant notification rule builder  
- Custom expression triggers  

These belong to **downstream product tracks** after P3 Notification Center read UI proves the event model.

---

## 13. Reference architecture context

HostFlow platform foundation layers closed before this track:

| Layer | Status |
|-------|--------|
| Field Registry v1 | ✅ Closed |
| Entity Profile Registry v1 | ✅ Closed |
| Requirement Rules Engine v1 | ✅ Closed |
| Document Runtime Engine v1 | ✅ Closed |
| **Document Expiry Notifications** | **P0 + P1 + P2 complete** (this doc) |

---

## Changelog

- 2026-06-24: **P2 complete** — `notification_events` registry; idempotent upsert on `event_key`; open/resolved/ignored status; read API; 8 tests; no dispatch.
- 2026-06-23: **P1 complete** — `evaluate_document_expiry_events()`; delivery-contract input only; deterministic `event_key`; 9 tests; no dispatch.
- 2026-06-23: P0 accepted — Document Expiry Notifications canon opened as downstream consumer of Document Runtime v1; events-first model; P1 evaluator scope gate.
