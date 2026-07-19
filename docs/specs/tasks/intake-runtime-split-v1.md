# Intake Runtime Split V1

**Status:** **ACTIVE** (R1–R4 + R3.5 COMPLETE · R5 NEXT)  
**Prerequisite:** Canonical Input Matrix **ACCEPTED / FROZEN** · Matrix epic **COMPLETE**  
**Matrix SoT:** [`../architecture/intake-canonical-input-matrix.md`](../architecture/intake-canonical-input-matrix.md)  
**L0 correction:** [`intake-r35-flights-dispatch-boundary.md`](intake-r35-flights-dispatch-boundary.md) — Forms → Flights → destination port → Recruitment/Sales  
**Decision gate:** [`../architecture/decision-priority-rule.md`](../architecture/decision-priority-rule.md) · **INV-16**  
**Communication epic:** [`intake-domain-separation-communication-context-v1.md`](intake-domain-separation-communication-context-v1.md)  
**Parents:** [`ADR-023`](../architecture/ADR-023-recruitment-sales-module-separation.md) · [`ADR-024`](../architecture/ADR-024-acquisition-campaigns-intake-routing.md) · [`intake-routing-foundation.md`](../modules/intake-routing-foundation.md)  
**Unlocks:** Flights / Intake Routing runtime (**UNLOCKED**)  
**Still LOCKED:** Forms P3–P5  

---

## Goal

Split Candidate Application and Sales Inquiry at **backend routing + destination ownership**, not in UI filters.

Canonical chain (frozen):

```text
Source profile → Provider → Published form binding → route_intent → intake_handoff → Destination
```

Routing SoT (only):

| `route_intent` | Destination |
|----------------|-------------|
| `candidate_application` | Recruitment intake |
| `sales_inquiry` | Sales intake |

Not routing SoT: FormPurpose · Goal Type · Outcome · `application_kind` · `lead_type` · `lead_target_type`.

---

## Implementation order (mandatory)

| Step | Title | Status |
|------|-------|--------|
| **R1** | Fail-closed route resolution | ✅ COMPLETE (`#63`) |
| **R2** | Destination registry | ✅ COMPLETE (`#63`) |
| **R3** | Intent split (intermediate module handlers) | ✅ COMPLETE (`#64`) — corrected by R3.5 |
| **R4** | Independent result objects | ✅ COMPLETE (`#65`) |
| **R3.5** | Flights-owned dispatch boundary (L0) | ✅ COMPLETE (`#66`) |
| **R5** | Transactional dispatch + idempotent provenance | NEXT |
| **R6** | Physically separate queues / APIs | LATER |

**Do not start R6 (queues/UI) before R1–R5.** Mixing hidden only in the frontend leaves the old blend in the backend.

### R1 — Fail-closed route resolution

Remove dangerous default: `missing profile / intent → candidate_application`.

| Rule | Behavior |
|------|----------|
| No explicit `route_intent` | Submission is **not** routed |
| Typed routing failure / disposition | Created; no domain object |
| Application / SalesInquiry | **Must not** be created |

### R2 — Destination registry

Closed map: `route_intent` → `destination` → `handler`.

| Intent | Destination | Handler (V1 bootstrap) |
|--------|-------------|------------------------|
| `candidate_application` | `recruitment` | `recruitment.lead_draft` |
| `sales_inquiry` | `sales` | `sales.inquiry_draft` |

Registry **must reject**:

- unknown intent  
- incompatible source profile  
- incompatible promotion target  
- missing handler  
- duplicate intent registration  
- Sales handler registered as Recruitment-owned (and reverse)

Contract: `intake.destination_registry.v1` · package `backend.app.intake_platform.destination_registry`.

### R3 — Split handlers

| Rule | Behavior |
|------|----------|
| `sales.inquiry_draft` | Physically in `backend.app.modules.sales` |
| `recruitment.lead_draft` | Physically in `backend.app.modules.recruitment` |
| Shared Intake | Knows destination contract + dispatch only |
| Cross-package imports | Forbidden (architectural test) |
| `recruitment.client_lead_draft` | Legacy forbidden — not in runtime |
| Missing Sales callable | Unresolved disposition — **no** Recruitment fallback |
| Handler result | Must match destination domain (foreign domain rejected) |

### R4 — Independent result objects

| Rule | Behavior |
|------|----------|
| `candidate_application` | Creates **Application** (`recruitment_applications`) |
| `sales_inquiry` | Creates **SalesInquiry** (`sales_inquiries`) |
| Shared Intake / Forms | Do **not** create either object directly |
| Lead | Optional transport only — not result, not queue SoT, not communication SoT |
| Transport link | Immutable `normalized.intake_result_link_v1`; one Lead → one result type |
| Typed handler result | `result_entity_type` + `result_entity_id` (+ `result_created`) |
| Projections | `lead_to_sales_inquiry` / `lead_to_recruitment_application` marked **LEGACY** (remove in R6) |

### R5–R6 (next PRs)

- **R5:** Resolve binding → pinned intent → compatibility → one destination → one result → routing decision → mark handoff processed; redelivery returns existing result. Provenance: `handoff_id → route_intent → destination → handler → result_type → result_id`.  
- **R6:** Recruitment API/queue reads only Application; Sales only SalesInquiry; no shared `type=` filter endpoint.

---

## Negative tests (DoD for runtime close — accumulate across R1–R6)

- [x] `sales_inquiry` never creates Application (R4 transport conflict + typed result)  
- [x] `candidate_application` never creates SalesInquiry (R4)  
- [x] missing intent does not go to Recruitment (R1)  
- [x] unknown intent does not enter a shared dispatch path (R1/R2)  
- [x] incompatible source profile rejected (R2)  
- [x] repeat ensure on same transport does not create second SalesInquiry (R4; full handoff ledger = R5)  
- [x] Sales handler cannot register as Recruitment-owned (R2)  
- [x] `sales_inquiry` invokes only `sales.inquiry_draft` (R3)  
- [x] `candidate_application` invokes only `recruitment.lead_draft` (R3)  
- [x] Sales↔Recruitment package imports forbidden (R3)  
- [x] Removing Sales handler callable → unresolved, not Recruitment fallback (R3)  
- [x] Handler cannot return foreign domain result (R3/R4)  
- [x] Sales handler cannot return Application (R4)  
- [x] Recruitment handler cannot return SalesInquiry (R4)  
- [ ] Recruitment API does not return Sales Inquiry (R6)  
- [ ] Sales API does not return Candidate Application (R6)  
- [ ] changing `application_kind` does not change route  
- [ ] changing FormPurpose does not change route  

---

## Gates

| Artifact | Status |
|----------|--------|
| Canonical Input Matrix | **ACCEPTED / FROZEN** |
| Intake Canonical Input Matrix epic | **COMPLETE** |
| Intake Runtime Split V1 | **ACTIVE** (R4) |
| Communication Context V1 | **READY** (Stage 1 audit; B untouched until after R5) |
| Flights / Intake Routing runtime | **UNLOCKED** |
| Forms P3–P5 | **LOCKED** |

---

## History

- 2026-07-19: Opened READY FOR IMPLEMENTATION after matrix acceptance; first PR = R1 + R2 only.
- 2026-07-19: R1+R2 COMPLETE (`#63`); R3 destination-owned handlers + Communication Context epic opened.
- 2026-07-19: R3 COMPLETE (`#64`); R4 independent Application / SalesInquiry result objects.
- 2026-07-19: **L0 correction** — R3.5 Flights-owned dispatch boundary; Forms↛Recruitment/Sales; adapters only.
