# Sales questionnaire — Convert mapping (ADR-022 Phase 2 slice 2)

**Status:** implementation contract (L3 — executes Convert mapping from Phase 2 Flow Spec)  
**Date:** 2026-07-20  
**Trusted base:** `integration/release-product-a-b` @ `70733762`+  
**Canon:** [`../workflows/adr022-phase2-sales-only-capability-flow.md`](../workflows/adr022-phase2-sales-only-capability-flow.md) §4.5  
**Branch:** `feat/sales-questionnaire-convert-mapping`  
**Entry point:** `backend.app.modules.sales.services.convert_mapping.convert_sales_inquiry_mapping`

---

## Sole goal

Implement the **Convert mapping** contract only.

## Explicit non-goals

| Forbidden in this PR |
|----------------------|
| Capability evaluation |
| Review UI / Review signal implementation |
| Wizard / create card |
| Traceability UI |
| Recruitment integration |
| New screens / new HTTP routes |
| Hidden fallback / auto-repair of missing destination or Flights refs |

## Allowed responsibility

1. Accept **confirmed** SalesInquiry  
2. Require **confirmed** Sales destination (`sales`)  
3. Require **opaque Flights ledger id** (confirmed provenance)  
4. Run **deterministic** convert → Sales-owned `ClientAccount`  
5. Persist **immutable** `convert_mapping_v1` on SalesInquiry.meta  
6. Return mapping + traceability refs  

## Invariants

Convert does **not**: decide, evaluate Capability, match, dispatch, create review, change destination, fallback, or import Recruitment.

## Fail-closed reasons

| Reason | When |
|--------|------|
| `missing_destination` | destination empty |
| `recruitment_destination_rejected` | destination / ledger is Recruitment |
| `missing_flights_reference` | ledger id missing or not found |
| `unconfirmed_flights_reference` | ledger not `confirmed` |
| `unresolved_review` | review-required without confirmation |
| `invalid_inquiry_state` | missing inquiry / blocked status / no transport lead |
| `destination_mismatch` / `provenance_mismatch` | ledger vs input / result_id mismatch |

## Tests

`backend/tests/modules/sales/test_convert_mapping.py`

- successful convert  
- missing destination  
- unresolved review  
- duplicate + repeated convert (idempotency)  
- invalid inquiry state  
- recruitment destination rejected  
- missing / unconfirmed Flights reference  
- immutable mapping after convert  

## Next after merge

**Traceability implementation** (no UI).
