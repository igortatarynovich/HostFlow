# Intake Runtime Split V1

**Status:** **ACTIVE** (R1+R2 COMPLETE · R3 IN THIS PR)  
**Prerequisite:** Canonical Input Matrix **ACCEPTED / FROZEN** · Matrix epic **COMPLETE**  
**Matrix SoT:** [`../architecture/intake-canonical-input-matrix.md`](../architecture/intake-canonical-input-matrix.md)  
**Communication epic:** [`intake-domain-separation-communication-context-v1.md`](intake-domain-separation-communication-context-v1.md) · Stage 1 audit [`../architecture/intake-communication-context-audit-v1.md`](../architecture/intake-communication-context-audit-v1.md)  
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
| **R1** | Fail-closed route resolution | ✅ COMPLETE (`#63` / `41e83eae`) |
| **R2** | Destination registry | ✅ COMPLETE (`#63`) |
| **R3** | Split handlers (Sales-owned; no cross-module imports) | **IN THIS PR** |
| **R4** | Independent result objects (Application / SalesInquiry) | NEXT |
| **R5** | Transactional dispatch + idempotent redelivery | LATER |
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

### R4–R6 (next PRs)

- **R4:** Recruitment → Application; Sales → SalesInquiry. Lead may remain transport/legacy only — not destination result.  
- **R5:** Resolve binding → pinned intent → compatibility → one destination → one result → routing decision → mark handoff processed; redelivery returns existing result.  
- **R6:** Recruitment API/queue reads only Application; Sales only SalesInquiry; no shared `type=` filter endpoint.

---

## Negative tests (DoD for runtime close — accumulate across R1–R6)

- [ ] `sales_inquiry` never creates Application  
- [ ] `candidate_application` never creates SalesInquiry  
- [x] missing intent does not go to Recruitment (R1)  
- [x] unknown intent does not enter a shared dispatch path (R1/R2)  
- [x] incompatible source profile rejected (R2)  
- [ ] repeat handoff does not create a second object (R5)  
- [x] Sales handler cannot register as Recruitment-owned (R2)  
- [x] `sales_inquiry` invokes only `sales.inquiry_draft` (R3)  
- [x] `candidate_application` invokes only `recruitment.lead_draft` (R3)  
- [x] Sales↔Recruitment package imports forbidden (R3)  
- [x] Removing Sales handler callable → unresolved, not Recruitment fallback (R3)  
- [x] Handler cannot return foreign domain result (R3)  
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
| Intake Runtime Split V1 | **ACTIVE** (R3) |
| Communication Context V1 | **READY** (Stage 1 audit + R3) |
| Flights / Intake Routing runtime | **UNLOCKED** |
| Forms P3–P5 | **LOCKED** |

---

## History

- 2026-07-19: Opened READY FOR IMPLEMENTATION after matrix acceptance; first PR = R1 + R2 only.
- 2026-07-19: R1+R2 COMPLETE (`#63`); R3 destination-owned handlers + Communication Context epic opened.
