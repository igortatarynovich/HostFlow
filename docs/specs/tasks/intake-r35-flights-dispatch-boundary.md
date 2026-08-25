# Intake Runtime Split — R3.5 Flights-owned Dispatch Boundary

**Status:** **COMPLETE** (`6571c3a7` / [PR #66](https://github.com/igortatarynovich/HostFlow/pull/66))  
**L0 rule:** Modules are independent. No module is built around another. Interactions only via published contracts/adapters.  
**Decision gate:** [`../architecture/decision-priority-rule.md`](../architecture/decision-priority-rule.md) · **INV-16**  
**Corrects:** R3 physical placement of create handlers inside Recruitment/Sales as the *dispatch* boundary (useful isolation, wrong ownership — failed L0 gate).  
**Parents:** [`intake-runtime-split-v1.md`](intake-runtime-split-v1.md) · [`intake-canonical-input-matrix.md`](../architecture/intake-canonical-input-matrix.md) · ADR-024  

---

## Canonical chain (normative)

```text
Forms Platform → Marketing/Acquisition/Flights → destination contract → module intake port → result object
```

**Not:**

```text
Forms Platform → Recruitment/Sales handler
```

| Intent | Flights dispatcher | Target port | Result (module-owned) |
|--------|-------------------|-------------|------------------------|
| `candidate_application` | `flights.candidate_application_dispatch` | RecruitmentIntakePort | Application |
| `sales_inquiry` | `flights.sales_inquiry_dispatch` | SalesIntakePort | SalesInquiry |

---

## Ownership matrix

| Object / rule | Owner |
|---------------|-------|
| Form draft / publication / submission / handoff | **Forms Platform** |
| Source Profile, Provider Binding, Campaign/Flight, published binding | **Acquisition / Flights** |
| `route_intent`, routing decision, transport, unresolved disposition, idempotency of dispatch | **Acquisition / Flights** |
| Destination registry + dispatcher | **Acquisition / Flights** |
| Candidate / Sales destination *adapters* (inbound ports) | **Recruitment / Sales** (implement Flights contract) |
| Application | **Recruitment** |
| SalesInquiry | **Sales** |
| Communication context after handoff | Result object + owning module |

---

## L0 laws (non-negotiable)

1. No module imports another module's internals (Recruitment ↛ Sales; Flights ↛ Recruitment/Sales ORM).  
2. Flights is an independent module — not “central business logic”.  
3. Ownership ≠ dependency: Flights chooses direction; target module owns create semantics.  
4. Contract is not owned by the consumer: Flights → Destination Contract → Adapter → Domain.  
5. After handoff, Flights does not own Application/SalesInquiry lifecycle.

---

## What R3/R4 remain useful for

- Split Candidate vs Sales intents  
- Removed Recruitment-owned sales handler + fallback  
- Physical Application / SalesInquiry result rows (R4)  

**But:** R3 must be read as **intermediate isolation**, not final architecture. Dispatch ownership moves to Flights in R3.5.

---

## Implementation (this PR)

1. `backend.app.acquisition.flights` owns registry + dispatcher + destination contract + ports.  
2. Registry registers `flights.*` dispatchers (not `recruitment.*` / `sales.*` create handlers).  
3. Public submit → Flights dispatcher only (via existing `intake_submit_service` façade).  
4. Thin `port_adapter.py` in Recruitment/Sales implement inbound ports; domain create stays in module services.  
5. Forms metadata shows Flights dispatcher ids; Forms still does not import Flights implementations beyond registry resolve for publication view.  
6. Architectural test: Flights package forbids Sales/Recruitment ORM/services/handler imports.

---

## Revised roadmap after R3.5

| Step | Title | Status |
|------|-------|--------|
| R1–R2 | Fail-closed + registry | ✅ |
| R3 | Intent/handler split (intermediate) | ✅ |
| R4 | Result objects (started; keep) | ✅ (creation ownership OK; dispatch ownership fixed in R3.5) |
| **R3.5** | **Flights-owned dispatch boundary** | ✅ COMPLETE (`#66`) |
| R5 | Transactional/idempotent provenance ledger | ✅ COMPLETE (`#69`) |
| then | Communication Context Resolver (C1–C6) | **NEXT** |
| R6 | Separate APIs/queues | AFTER C1–C5 |

Optional rename going forward: treat “Module Boundary Contracts” as the L0 framing for R3.5+; result objects stay module-owned behind ports.

---

## History

- 2026-07-19: Opened after L0 correction — Forms↛Recruitment/Sales; Flights owns acquisition intake through destination adapters.
- 2026-07-19: COMPLETE `#66`; Decision Priority Rule (**INV-16**) adopted as mandatory accept gate.
