# ADR-021: Unified Intake Resolution Model

**Status:** Accepted  
**Date:** 2026-07-15  
**Accepted:** 2026-07-24 (Architecture — hard gates 1–8 PASS; see [review checklist](ADR-021-review-checklist.md) and [PR #21 review comment](https://github.com/igortatarynovich/HostFlow/pull/21#issuecomment-5069747606))  
**Layer of change:** Domain | Product surface | Constitution  
**Authors:** Product + Platform architecture  
**Supersedes / clarifies:** partial product behaviour documented across [ADR-013](ADR-013-public-intake-strategy.md), [ui-constitution-v1.md](ui-constitution-v1.md), [applications-operating-model.md](applications-operating-model.md), [lead-intake-resolution-and-activity-continuity.md](../workflows/lead-intake-resolution-and-activity-continuity.md)

**Related (not replaced):** [ADR-020](ADR-020-sales-to-engagement-commercial-model.md) (Sales-to-Engagement commercial model), [ADR-007](ADR-007-forms-platform-capability.md) (Forms Platform), [ADR-022](ADR-022-intake-form-purpose-and-submission-policy-model.md) (Form Purpose + Submission Policy — Intake Platform entry contract; **still Proposed** — see process note below), [entity-profile-definition-registry.md](../platform/entity-profile-definition-registry.md) (Decision Layer / Outcome Executor), [module-catalog-and-routing-map.md](module-catalog-and-routing-map.md), [mapping-authority-contract.md](mapping-authority-contract.md) (who may write source→canonical placement; `mapping_authority.v1` / MA-1)

**Review artifact:** [ADR-021-review-checklist.md](ADR-021-review-checklist.md)

> **Process note (tracked, not a silent ratification):** Accepting ADR-021 does **not** accept [ADR-022](ADR-022-intake-form-purpose-and-submission-policy-model.md). ADR-022 Phase 1 backend already exists on `integration/release-product-a-b` while ADR-022 remains **Proposed**. That drift is tracked separately and requires its own sign-off before Phase 1A/1B contracts treat ADR-022 as settled canon.

> **Terminology (обязательно):** **`Lead`** — внутренний transport intake (как OAuth token / message envelope). **Не product object.** В UI — только продуктовые проекции (**Отклик**, **Обращение**, **Заявка на услугу**, **Заявка на разбор**). Оператор **никогда** не работает с универсальным объектом «Лид».

---

## 1. Context

### 1.1 What already exists (backend)

HostFlow already runs a **single technical intake pipeline** for Meta, import, public forms, and constructor-bound sources:

```text
Intake event (external signal)
  → Provider binding / IntakeSourceProfile
  → IntakeRouter (route_intent)
  → Lead (transport record)
  → ingest_envelope_v1
  → Decision Layer
  → Outcome Executor
  → Candidate | ClientAccount | ServiceOrder | review_queue | lead_only
```

Implementation references: `backend/app/services/intake_router.py`, `backend/app/entity_profile/ingest_runtime.py`, `backend/app/entity_profile/decision_layer.py`, `backend/app/entity_profile/outcome_executor.py`.

### 1.2 What diverges (product)

Operational surfaces are **not unified**:

| Surface | Role today | Problem |
|---------|------------|---------|
| `/app/leads` | Meta/CSV intake workspace | Competes with module inboxes; exposes Lead as product object |
| `/app/recruitment/inbox` | Recruitment Application facade | Correct direction; incomplete channel parity |
| `/app/sales` | Sales Inquiry facade | Correct direction; questionnaire answers not always in unified review contract |
| Channel-specific client acquisition | Meta B2B invite, public forms | Different review semantics per channel |
| *(future)* Services inbox | `service_request` route | Executor exists; no Application Workspace |
| `review_queue` disposition | Decision Layer output | No dedicated Intake Review workspace |

**Risk:** moving panels, decision rails, or answer viewers **without** a single L1 contract produces another partial workspace and a new legacy surface.

### 1.3 Decision

**Chosen:** Any inbound signal becomes an **Application projection** (operational case for decision-making), enters **one module-owned operational inbox**, passes **human or policy-driven review**, and closes with an **explicit, auditable Decision Outcome**.

**Not chosen (for Phase 1):**

- New `applications` database table — facade over existing Lead transport is sufficient until contract stress proves otherwise.
- Operator edits to **submitted** user answers — immutable snapshot + separate **reviewed** layer (§5).
- Point fixes to `/app/leads` or per-channel UI patches without inbox ownership consolidation.

---

## 2. Unit of inbound work

### 2.1 Rules (canonical)

| Rule | Statement |
|------|-----------|
| **New signal → new Application** | Each **new external intake event** that represents a distinct operational case creates a **separate Application projection**. |
| **Clarification → same Application** | Re-submission of the **same questionnaire / scoped clarification link** **supplements** the existing Application (new Submission, §3). |
| **Match ≠ merge** | Identity match with an existing Candidate or ClientAccount **does not** automatically merge or close other Applications. |
| **Multi-Application per entity** | One domain entity (Candidate, ClientAccount) **may have many Applications over time** — each records a distinct intent / cycle / channel event. |

**Anti-pattern (forbidden):** matching logic that collapses inbound history by attaching all signals to the newest Application or auto-closing prior open Applications.

**Rationale:** preserve inquiry history, SLA, attribution, and operator accountability. Matching informs **decision**, not **record consolidation**.

### 2.2 When to create vs supplement

| Scenario | Application behaviour |
|----------|----------------------|
| New Meta lead (new `external_id`) | New Application |
| New public form session (new draft token) | New Application |
| Questionnaire invite re-open / clarification on same lead | Same Application; new Submission |
| Duplicate webhook retry (same idempotency key) | Same Application; no duplicate Submission |
| Operator-initiated «request clarification» | Same Application; awaiting new Submission |

---

## 3. Application, Submission, Intake event

Even without an `applications` table in Phase 1, the **semantic contract** must distinguish three layers:

### 3.1 Intake event

| Property | Definition |
|----------|------------|
| What | Raw external signal: Meta webhook, Telegram message, CSV row, API POST, import batch item |
| Role | Transport ingress; may create or update Lead |
| Identity | `intake_event_id`, provider, `external_id`, idempotency key |
| UI | Never shown to operators |

### 3.2 Application

| Property | Definition |
|----------|------------|
| What | **Operational case** for review and decision — the object in Application Workspace |
| Role | Lifecycle, ownership, matching, decisions, outcomes |
| Identity | `application_id` (Phase 1: maps to Lead transport id) |
| Cardinality | One Application **may contain many Submissions** and many Intake events |

### 3.3 Submission

| Property | Definition |
|----------|------------|
| What | One **completed send** of form data (public apply submit, questionnaire submit, clarification reply) |
| Role | Immutable `submitted_data` snapshot (§5) |
| Identity | `submission_id`, `submitted_at`, `presentation_code` |
| Cardinality | Append-only list on Application; never overwrites prior snapshots |

```text
Intake event(s) → Application (1)
                    ├── Submission #1 (initial)
                    ├── Submission #2 (clarification)
                    └── reviewed_data (operator layer, §5)
```

**Phase 1 storage note:** Submission history may live in `Lead.normalized.submissions_v1[]` or equivalent append-only structure — **not** by mutating a single `Lead.normalized` overwrite. Current overwrite behaviour is **legacy**; Phase 2 storage contract must correct it.

---

## 4. Technical vs product objects

### 4.1 Lead (transport only)

| Property | Rule |
|----------|------|
| Storage | `leads` table, `normalized`, `payload`, `ingest_envelope_v1` |
| UI exposure | **Forbidden** in operational CRM navigation and copy |
| Role | Binds Intake events, Submissions, and Application projection in Phase 1 |
| Analytics | Allowed internally; product reports use Application projection |

### 4.2 Application (product projection / facade)

**Application** is the **operational decision case** shown in Application Workspace. Phase 1: read model + mutation API over Lead transport.

Minimum projection fields:

| Field group | Purpose |
|-------------|---------|
| Identity | `application_id`, `tenant_id`, `created_at` |
| Routing | `route_intent`, `module_owner`, `entity_profile_code`, `presentation_code`, `intake_source_profile_id` |
| Ownership | current `module_owner` + `routing_history[]` (§6) |
| Contact | denormalized contact block |
| Lifecycle | `lifecycle_status` (§7) |
| Resolution | `resolution_code` when resolved (§7) |
| Submissions | ordered `submissions[]` (§5.1) |
| Review | `reviewed_data` field map (§5.2) |
| Entity outcome | `entity_data` refs (§5.3) |
| Matching | `match_result` (§8) — informational, non-destructive |
| Decision | `decision_records[]` + execution status (§9) |
| Extensions | module stage hints — **secondary** |

Existing API facade: `backend/app/modules/applications/` (Lead → `ApplicationOut`).

### 4.3 Route intent → product object → module → inbox

| `route_intent` | Product object (RU) | Product object (EN) | Module | Primary inbox (canonical) |
|----------------|----------------------|---------------------|--------|---------------------------|
| `candidate_application` | **Отклик** | Application | Recruitment | `/app/recruitment/inbox` |
| `sales_inquiry` | **Обращение** | Inquiry | Sales | `/app/sales` |
| `service_request` | **Заявка на услугу** | Service Request | Services | `/app/services/inbox` *(Phase 3)* |
| `unknown` / ambiguous | **Заявка на разбор** | Intake Review | Platform / Intake | `/app/intake/review` *(Phase 3)* |
| `partner_inquiry` | **Партнёрский запрос** | Partner Inquiry | *(module TBD)* | module inbox when defined |

---

## 5. Three data layers (mandatory)

### 5.1 `submitted_data` — per Submission (immutable)

Each Submission stores a **self-contained snapshot**. Operators **must never mutate** it.

| Field | Required |
|-------|----------|
| `submission_id` | ✓ |
| `submitted_at` | ✓ |
| `schema_version` / `entity_profile_code` | ✓ |
| `presentation_code` / `presentation_version` | ✓ |
| `source` | provider, channel, campaign, form slug |
| `raw_values` | provider-native payload fragment |
| `normalized_values` | mapped presentation / ingest values |
| `attachments` | refs to uploaded files |
| `consent_metadata` | consents, terms, cookies flags |
| `ingest_envelope_v1` | copy or ref at submit time |

**Rule:** later Submissions **append**; they do not replace `Lead.normalized` in place. Relying solely on current `Lead.normalized` is **non-compliant** if it is overwritten by the next submit.

### 5.2 `reviewed_data` — field-level (Phase 2)

Structured **per qualified field**, not an opaque JSON blob:

```json
{
  "qualified_code": "service_sales.targeted_advertising.contact_phone",
  "original_value": "+48123456789",
  "reviewed_value": "+48111222333",
  "review_status": "confirmed | corrected | needs_clarification",
  "source_of_correction": "operator | policy | import",
  "actor_user_id": "uuid",
  "reviewed_at": "iso8601",
  "reason": "string | null"
}
```

| Rule | Statement |
|------|-----------|
| API (Phase 2) | `PATCH /applications/{id}/reviewed-values` — field entries, not whole-form replace |
| Clarification | `needs_clarification` triggers scoped re-entry → new Submission |
| Diff UI | shows `original_value` → `reviewed_value` |

Phase 1: `reviewed_data` may be empty; structure is **normative** for Phase 2.

### 5.3 `entity_data` (outcome layer)

Values **actually applied** by Outcome Executor to Candidate / ClientAccount / ServiceOrder at decision time.

| Rule | Statement |
|------|-----------|
| Source priority | `reviewed_data` (if field present) → else latest Submission `normalized_values` |
| Immutability | Frozen when `lifecycle_status` becomes `resolved` |
| Linkage | `decision_record.input_snapshot_version` + `target_entity_id` |

---

## 6. Routing and ownership

### 6.1 Single owner invariant

At any moment an Application has **exactly one `module_owner`** and appears in **exactly one primary operational inbox**.

| Invariant | Rule |
|-----------|------|
| No dual inbox | Same Application **must not** appear in Sales **and** Recruitment inboxes simultaneously |
| Unknown route | Ambiguous / `unknown` `route_intent` → **Intake Review** inbox until classified |
| Canonical routes | See §4.3 |

### 6.2 Reroute

| Property | Rule |
|----------|------|
| Effect | Changes `module_owner`, `route_intent`, and primary inbox |
| Application identity | **Same** `application_id` — reroute does **not** create a new Application |
| History | Append `routing_history[]` entry: `{ from_module, to_module, from_intent, to_intent, actor, at, reason }` |
| Lifecycle | May reset to `reviewing` or `ready_for_decision` per target module policy |
| Resolution | `resolution_code=routed` only when Application closes without entity outcome in source module |

**L0 INV-09 (non-conflict):** [INV-09](architecture-invariants.md) (“routing once at Lead create; continuation inherits context”) governs the **IntakeRouter** binding at transport create. Operator **reroute** (§6.2) is a later ownership change on the same Application — it does **not** re-run IntakeRouter and does not violate INV-09. Phase 1A contracts must keep `resolution_code=routed` (source-module closed perspective) distinct from the destination inbox still showing the same `application_id`.

### 6.3 Matching vs routing

Matching (§8) suggests entity candidates; **routing** decides module inbox. They are orthogonal: strong ClientAccount match on a recruitment Application does **not** auto-move to Sales without explicit reroute decision.

---

## 7. Lifecycle and resolution (separated)

### 7.1 `lifecycle_status` (process state)

```text
new → reviewing → waiting_for_information → ready_for_decision → resolved
```

| `lifecycle_status` | Meaning |
|--------------------|---------|
| `new` | Application created; no operator touch |
| `reviewing` | Active triage |
| `waiting_for_information` | Clarification outstanding |
| `ready_for_decision` | Sufficient data; primary outcome available |
| `resolved` | **Process closed** — no further operator actions |

**`resolved` is not an outcome.** It means the review process finished.

### 7.2 `resolution_code` (decision result)

Set when `lifecycle_status` becomes `resolved`:

| `resolution_code` | Meaning |
|-------------------|---------|
| `converted` | New entity created |
| `linked` | Attached to existing entity |
| `rejected` | Explicit reject |
| `duplicate` | Absorbed as duplicate intake |
| `spam` | Spam / abuse |
| `routed` | Closed via reroute to another module (source module perspective) |

**Projection rule:** UI shows `lifecycle_status=resolved` + `resolution_code` together — never conflate into one enum.

### 7.3 Module stages (secondary)

Module stages (`contacted`, `qualified`, `won`, …) live in `extensions` and **must not** replace `lifecycle_status` in shared inbox tabs.

---

## 8. Matching contract

Matching is **informational** for operator decision (§2.1). It **must not** delete or merge Application history.

### 8.1 Search dimensions

| `route_intent` | Search targets |
|----------------|----------------|
| `candidate_application` | Candidate (phone, email, name, docs per policy) |
| `sales_inquiry` | ClientAccount, Company party, open Inquiries |
| `service_request` | ClientAccount, active ServiceOrder |
| `unknown` | All above + route hints |

### 8.2 `match_result_v1`

```json
{
  "status": "none | possible | strong | conflict",
  "candidates": [{
    "entity_type": "candidate | client_account | service_order",
    "entity_id": "uuid",
    "confidence": 0.0,
    "reason": "..."
  }],
  "suggested_action": "none | review | link | block",
  "operator_ack_required": true
}
```

### 8.3 Match ≠ merge (restatement)

| Allowed | Forbidden |
|---------|-----------|
| Surface match in UI | Auto-close other Applications for same entity |
| Suggest `link` in decision rail | Auto-merge Submission history across Applications |
| `resolution_code=linked` after explicit decision | Silent collapse on `strong` match without decision_record |

---

## 9. Decision contract and idempotency

### 9.1 `decision_record_v1`

```json
{
  "decision_id": "uuid",
  "decision_code": "create_candidate | create_client | create_service_order | link_existing | reject | mark_duplicate | mark_spam | route | request_information",
  "target_entity_type": "candidate | client_account | service_order | null",
  "target_entity_id": "uuid | null",
  "reason_code": "string | null",
  "notes": "string | null",
  "actor_user_id": "uuid",
  "decided_at": "iso8601",
  "input_snapshot_version": "submission:{id} | reviewed@vN",
  "route_intent": "...",
  "application_id": "uuid",
  "execution_status": "pending | executing | completed | failed",
  "execution_error": "string | null",
  "idempotency_key": "uuid"
}
```

### 9.2 Idempotency rules

| Rule | Requirement |
|------|-------------|
| Single outcome | One `decision_id` + `idempotency_key` must not create two Candidates / ClientAccounts |
| Replay | Re-invoking Outcome Executor with same `decision_id` returns same `target_entity_id` |
| Failed execution | `execution_status=failed` **preserves** decision intent; operator may retry |
| Ordering | Record decision **before** executor; update `execution_status` after |

### 9.3 Separation of concerns

| Layer | Responsibility |
|-------|----------------|
| **decision_record** | Auditable **intent** — immutable after write (`decision_code`, targets, actor, `idempotency_key`, snapshot ref). `execution_status` / `execution_error` / `target_entity_id` may advance on retry |
| **Outcome Executor** | Idempotent side effects |
| **Application projection** | Denormalized current state for UI |

**Legacy freeze:** `LeadIntakeDecisionRail` — deprecated; no new features (Phase 1A).

---

## 10. Auto-processing policy (granular)

A single `auto_decision` flag is **non-compliant**. Policies are **independent dimensions**:

| Policy | Risk level | What it may do |
|--------|------------|----------------|
| **auto-routing** | Low | Assign `route_intent` / module from binding when unambiguous |
| **auto-matching** | Low | Compute and attach `match_result` without operator |
| **auto-link** | Medium | `resolution_code=linked` to existing entity when policy + strong match + gates pass |
| **auto-create** | High | `resolution_code=converted` via executor without operator |
| **auto-reject** | Medium | `resolution_code=rejected` or `spam` when rules fire |

### 10.1 Default (canonical)

```text
submit → inbox (lifecycle_status=new) → review → decision → resolved + resolution_code
```

### 10.2 Gates per high-risk policy

`auto-create` and `auto-link` require **all**:

- explicit tenant + intake-profile policy flag for that dimension
- unambiguous `route_intent`
- valid required data in active snapshot
- no `conflict` match / open duplicate review
- audit `decision_record` written (even for policy-driven decisions)

### 10.3 Migration

ADR-013 P5C instant candidate create = **`auto-create` compatibility** until migrated. New constructor forms: inbox-first; each auto dimension opt-in separately.

---

## 11. Application facade (Phase 1 — no new table)

Phase 1 uses Lead-backed facade if it exposes §3–§9 contracts at the API/projection layer.

| Capability | Phase 1 |
|------------|---------|
| List by module inbox | ✓ existing |
| `lifecycle_status` + `resolution_code` split | **Add** mapping |
| `submissions[]` read model | **Add** (may backfill from current normalized) |
| `reviewed_data` | Empty stub |
| `decision_records[]` + execution status | **Add** |
| `routing_history[]` | **Add** on reroute |
| Matching block | Surface existing Decision Layer signals |

**Trigger for `applications` table:** concurrent open Applications per contact, decoupled lifecycle from Lead transport, or Submission storage cannot be made append-only on Lead — see [applications-operating-model.md](applications-operating-model.md).

---

## 12. Implementation roadmap (ordered)

| Phase | Scope | Out of scope |
|-------|-------|--------------|
| **ADR-021** | L1 approval (this document) | Code |
| **Phase 1A** | Inbox ownership, nav, redirects, legacy freeze | Data model, decision API changes |
| **Phase 1B** | Unified review surface (read-only submitted, match, decision rail) | `reviewed_data` writes |
| **Phase 2** | `reviewed_data`, clarification, `PATCH …/reviewed-values` | Services inbox |
| **Phase 3** | Services inbox + Intake Review Queue | Telegram |
| **Phase 4** | Telegram + channels via ingestion contracts | — |

**Phase 1A and 1B must not ship in one implementation PR.**

---

## 13. Consequences

### Positive

- Preserved inquiry history; matching no longer destroys Applications.
- Clear Submission audit trail independent of Lead.normalized overwrites.
- Separated lifecycle vs resolution semantics.
- Granular auto-policy reduces accidental auto-create.

### Negative / cost

- Submission append-only storage may require Lead.normalized migration.
- Public form auto-create tenants need explicit `auto-create` policy migration.
- Routing history and dual status fields add projection complexity.

### Guardrails

1. New external case → new Application (§2).
2. No PATCH to `submitted_data` — only `reviewed-values` (§5.2).
3. No executor side effect without `decision_record` (§9).
4. No dual inbox visibility (§6).
5. No single `auto_decision` flag (§10).

---

## 14. Acceptance criteria (ADR approval)

- [x] Architecture review: §2 unit-of-work rules approved
- [x] Architecture review: Application / Submission / Intake event separation (§3)
- [x] Architecture review: `lifecycle_status` vs `resolution_code` (§7)
- [x] Architecture review: routing ownership + reroute (§6)
- [x] Architecture review: Submission snapshot fields (§5.1)
- [x] Architecture review: field-level `reviewed_data` (§5.2)
- [x] Architecture review: decision idempotency (§9)
- [x] Architecture review: granular auto-policy (§10)
- [ ] Product: module inbox mapping accepted *(countersignature tracked on accepting PR)*
- [ ] Engineering: Phase 1 feasible without `applications` table *(countersignature tracked on accepting PR)*
- [ ] Security: tenant isolation on decision + submission audit *(countersignature tracked on accepting PR)*

**After Architecture acceptance:** Phase 1A and Phase 1B implementation contracts in `docs/specs/tasks/` (do not treat ADR-022 as Accepted until its own sign-off).

---

## 15. Links

| Document | Relationship |
|----------|--------------|
| [ADR-021-review-checklist.md](ADR-021-review-checklist.md) | Architecture review checklist |
| [ui-constitution-v1.md](ui-constitution-v1.md) | Product objects, Application Workspace |
| [applications-operating-model.md](applications-operating-model.md) | Long-term Application entity |
| [ADR-013-public-intake-strategy.md](ADR-013-public-intake-strategy.md) | Lead-first transport |
| [entity-profile-definition-registry.md](../platform/entity-profile-definition-registry.md) | Decision Layer, Outcome Executor |
| [lead-intake-conversion-flow-audit.md](../workflows/lead-intake-conversion-flow-audit.md) | Gap evidence |
| [ingestion-contract-template.md](../workflows/ingestion-contract-template.md) | Per-channel contracts |
| [mapping-authority-contract.md](mapping-authority-contract.md) | Mapping write authority (`mapping_authority.v1` / MA-1); does not replace this ADR |
