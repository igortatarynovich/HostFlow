# Intake Runtime Split — R5 Gate (Flights provenance / exactly-once)

**Status:** **COMPLETE** · [PR pending] · gated by INV-16  
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

## Implementation (this slice)

| Artifact | Role |
|----------|------|
| `acq_flight_dispatch_ledger` | Flights-owned provenance table |
| `acquisition/flights/dispatch_ledger.py` | Claim / confirm / fail-closed |
| `acquisition/flights/dispatcher.py` | Registry → ledger → port → confirm |
| `OpaqueResultRef` | `module_owner` · `result_type` · `result_id` |

Idempotency key (Flights-scoped):

```text
flights.dispatch:{tenant}:{handoff_or_transport}:{route_intent}:{dispatcher_id}
```

Replay after `status=confirmed` returns ledger opaque ref and **does not** call the module adapter again.

---

## Mandatory gate conditions (all required)

| # | Condition | Status |
|---|-----------|--------|
| 1 | Provenance belongs to Flights | ✅ |
| 2 | Idempotency not on foreign ORM identity | ✅ |
| 3 | Destination response via published contract | ✅ |
| 4 | Opaque result reference only | ✅ |
| 5 | Confirmed ⇒ no second adapter invoke | ✅ |
| 6 | Missing/ambiguous ⇒ fail-closed; no Recruitment fallback | ✅ |
| 7 | No cross-domain shared DB transaction as consistency mechanism | ✅ |

Condition **7**: exactly-once via **idempotent contract + dispatch ledger + repeatable delivery**. Destination modules keep local transactions for their own result objects.

---

## DoD slice (R5)

- [x] Provenance row written for every routed handoff (when `db` present)
- [x] Replay with same idempotency key does not call adapter twice after confirmed result
- [x] Fail-closed path for missing/ambiguous result
- [x] Architectural test: Flights still forbids destination ORM/services
- [x] No cross-module shared transaction helpers in Flights dispatch path

---

## History

- 2026-07-19: Opened as NEXT after INV-16 / R3.5 freeze; gate conditions accepted.
- 2026-07-19: Implemented Flights ledger + opaque refs + replay short-circuit.
