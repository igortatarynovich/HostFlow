# Intake Runtime Split V1

**Status:** **ACTIVE** (R1–R5 COMPLETE · **Communication Context NEXT**)  
**Prerequisite:** Canonical Input Matrix **ACCEPTED / FROZEN** · Matrix epic **COMPLETE**  
**Matrix SoT:** [`../architecture/intake-canonical-input-matrix.md`](../architecture/intake-canonical-input-matrix.md)  
**L0 boundary:** [`intake-r35-flights-dispatch-boundary.md`](intake-r35-flights-dispatch-boundary.md)  
**Decision gate:** [`../architecture/decision-priority-rule.md`](../architecture/decision-priority-rule.md) · **INV-16** (`#67`)  
**R5 gate:** [`intake-r5-provenance-gate.md`](intake-r5-provenance-gate.md) · **COMPLETE** (`#69`)  
**Communication epic:** [`intake-domain-separation-communication-context-v1.md`](intake-domain-separation-communication-context-v1.md) · [`intake-communication-context-c1-c6-gate.md`](intake-communication-context-c1-c6-gate.md)  
**Parents:** [`ADR-023`](../architecture/ADR-023-recruitment-sales-module-separation.md) · [`ADR-024`](../architecture/ADR-024-acquisition-campaigns-intake-routing.md) · [`intake-routing-foundation.md`](../modules/intake-routing-foundation.md)  
**Unlocks:** Flights / Intake Routing runtime (**UNLOCKED**) · Communication Context Resolver (**READY** — C1–C6)  
**Still LOCKED:** Forms P3–P5 · Queues/UI until **C1–C5**  

---

## Current status

| Stage | Status |
|-------|--------|
| R1 fail-closed routing | **COMPLETE** |
| R2 destination registry | **COMPLETE** |
| R3 intermediate split | **COMPLETE** |
| R3.5 Flights-owned boundary | **COMPLETE** — `#66` |
| R4 independent result objects | **COMPLETE** |
| Decision priority gate / INV-16 | **COMPLETE** — `#67` |
| R5 provenance / exactly-once | **COMPLETE** — `#69` |
| Communication Context Resolver | **NEXT** — C5 (C1–C4 ✅) |
| Queues/UI | **LOCKED** |
| Forms P3–P5 | **LOCKED** |

---

## Canonical intake chain (frozen)

```text
Forms → Flights → destination contract → module intake adapter → module-owned result
```

| Segment | Owner |
|---------|-------|
| Submission and handoff | **Forms** |
| Routing decision and dispatch provenance | **Flights** |
| Destination contract | **Published inter-module boundary** |
| Recruitment adapter | **Recruitment** |
| Sales adapter | **Sales** |
| Application | **Recruitment** |
| SalesInquiry | **Sales** |

Flights does **not** own Application or SalesInquiry and does not know how they are created internally.  
Recruitment and Sales do **not** know Forms, Flight bindings, or routing internals.

Routing SoT (only):

| `route_intent` | Destination |
|----------------|-------------|
| `candidate_application` | Recruitment intake |
| `sales_inquiry` | Sales intake |

Not routing SoT: FormPurpose · Goal Type · Outcome · `application_kind` · `lead_type` · `lead_target_type` · UI · URL · legacy flags.

---

## Implementation order (mandatory)

| Step | Title | Status |
|------|-------|--------|
| **R1** | Fail-closed route resolution | ✅ COMPLETE (`#63`) |
| **R2** | Destination registry | ✅ COMPLETE (`#63`) |
| **R3** | Intent split (intermediate) | ✅ COMPLETE (`#64`) — corrected by R3.5 |
| **R4** | Independent result objects | ✅ COMPLETE (`#65`) |
| **R3.5** | Flights-owned dispatch boundary (L0) | ✅ COMPLETE (`#66`) |
| **INV-16** | Decision Priority Rule | ✅ COMPLETE (`#67`) |
| **R5** | Provenance / exactly-once (Flights ledger) | ✅ COMPLETE (`#69`) |
| **C1–C6** | Communication Context | **NEXT** — [`intake-communication-context-c1-c6-gate.md`](intake-communication-context-c1-c6-gate.md) |
| **R6** | Physically separate queues / APIs | LATER · **LOCKED** until C1–C5 |

**Do not start R6 (queues/UI) before Communication Context C1–C5.**

### R5 — summary

Provenance: `handoff_id → route_intent → destination → dispatcher_id → result_type → result_id`.

Exactly-once via **idempotent contract + Flights dispatch ledger + repeatable delivery** — **not** a shared cross-module DB transaction.

Opaque Flights reference only: `module_owner` · `result_type` · `result_id`.

---

## Negative tests (DoD — accumulate across R1–R6)

- [x] `sales_inquiry` never creates Application  
- [x] `candidate_application` never creates SalesInquiry  
- [x] missing intent does not go to Recruitment (R1)  
- [x] unknown intent does not enter a shared dispatch path (R1/R2)  
- [x] incompatible source profile rejected (R2)  
- [x] Sales↔Recruitment package imports forbidden (R3)  
- [x] Flights dispatchers (`flights.*`) own routing metadata (R3.5)  
- [x] Flights package forbids destination ORM/services (R3.5)  
- [x] Replay does not call module adapter twice after confirmed result (R5)  
- [x] Missing/ambiguous result fail-closed; no Recruitment fallback (R5)  
- [x] No cross-module shared transaction on dispatch path (R5)  
- [ ] Recruitment API does not return Sales Inquiry (R6)  
- [ ] Sales API does not return Candidate Application (R6)  
- [ ] changing `application_kind` / FormPurpose / URL does not change route  

---

## Gates

| Artifact | Status |
|----------|--------|
| Canonical Input Matrix | **ACCEPTED / FROZEN** |
| Intake Canonical Input Matrix epic | **COMPLETE** |
| Intake Runtime Split V1 | **ACTIVE** (R5 complete · Communication Context C1–C6 next) |
| Decision Priority / INV-16 | **COMPLETE** (`#67`) |
| Communication Context V1 | **ACTIVE** (C1–C6 gate) |
| Flights / Intake Routing runtime | **UNLOCKED** |
| Forms P3–P5 | **LOCKED** |
| Queues/UI | **LOCKED** until C1–C5 |

---

## History

- 2026-07-19: Opened READY after matrix acceptance; first PR = R1 + R2 only.
- 2026-07-19: R1+R2 COMPLETE (`#63`); R3 handlers opened.
- 2026-07-19: R3 COMPLETE (`#64`); R4 result objects (`#65`).
- 2026-07-19: **L0 correction** — R3.5 Flights boundary (`#66`); INV-16 Decision Priority (`#67`).
- 2026-07-19: Status freeze + R5 gate conditions accepted (provenance Flights-owned; no cross-domain monolith transaction).
