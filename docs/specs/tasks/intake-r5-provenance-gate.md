# Intake Runtime Split — R5 Gate (Flights provenance / exactly-once)

**Status:** **READY FOR IMPLEMENTATION** · gated by INV-16  
**Prerequisite:** R3.5 Flights-owned boundary **COMPLETE** (`#66`) · Decision Priority **COMPLETE** (`#67`)  
**Parents:** [`intake-runtime-split-v1.md`](intake-runtime-split-v1.md) · [`intake-r35-flights-dispatch-boundary.md`](intake-r35-flights-dispatch-boundary.md) · [`../architecture/decision-priority-rule.md`](../architecture/decision-priority-rule.md)  
**Unlocks after R5:** Communication Context Resolver  
**Still LOCKED:** Queues / UI (R6) · Forms P3–P5  

---

## Goal

Immutable Flights-owned dispatch provenance with exactly-once semantics **without** merging Flights and destination modules into one transactional monolith.

```text
handoff_id → route_intent → destination → dispatcher_id → result_type → result_id
```

Flights stores only an **opaque** result reference after confirmed adapter response.

---

## Mandatory gate conditions (all required)

R5 is acceptable **only** if every condition holds:

| # | Condition |
|---|-----------|
| 1 | **Provenance belongs to Flights** — ledger / decision record is Acquisition-owned, not Recruitment/Sales-owned. |
| 2 | **Idempotency is not built on foreign ORM identity** — keys are Flights/handoff/dispatch ids (or contract tokens), not `Application.id` / `SalesInquiry.id` as the sole SoT for “already done”. |
| 3 | **Destination response passes through the published contract** — no direct service/ORM calls from Flights into module internals. |
| 4 | **Opaque result reference only:** `module_owner` · `result_type` · `result_id` (plus Flights provenance fields). No embedding of destination domain graphs. |
| 5 | **Confirmed result ⇒ no second adapter invoke** — redelivery returns existing provenance / opaque ref; module adapter is not called again after confirmed success. |
| 6 | **Missing or ambiguous result ⇒ fail-closed** — unresolved disposition; no silent create; **no Recruitment fallback**. |
| 7 | **No cross-domain shared DB transaction** as the consistency mechanism between Flights and a destination module. Exactly-once is achieved via **idempotent contract + dispatch ledger + repeatable delivery**, not by binding independent modules into one ACID unit. |

Condition **7** is critical: a “shared transaction that touches Flights tables and Application/SalesInquiry tables together” is an L0/INV-16 reject even if it makes tests green.

---

## Allowed patterns

- Flights dispatch ledger row (pending → dispatched → confirmed / failed)  
- Idempotency key scoped to handoff / dispatch attempt  
- Adapter returns contract response → Flights writes opaque ref  
- At-least-once delivery with exactly-once effect via ledger check before adapter call  
- Destination module may use its own local transaction for its own result object  

## Forbidden patterns

- `SELECT … FOR UPDATE` spanning Flights + Recruitment/Sales tables as cross-module lock  
- Flights importing `RecruitmentApplication` / `SalesInquiry` ORM to “check if exists”  
- Fallback `sales_inquiry` → Recruitment path  
- Treating Lead / UI / FormPurpose as provenance SoT  

---

## DoD slice (R5)

- [ ] Provenance row written for every routed handoff  
- [ ] Replay with same idempotency key does not call adapter twice after confirmed result  
- [ ] Fail-closed path for missing/ambiguous result  
- [ ] Architectural test: Flights still forbids destination ORM/services  
- [ ] No cross-module shared transaction in dispatch path  

---

## History

- 2026-07-19: Opened as NEXT after INV-16 / R3.5 freeze; gate conditions accepted.
