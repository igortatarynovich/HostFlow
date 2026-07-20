# Stage 3 — Sales Pipeline product wiring (slice 1)

**Status:** Implementation slice (product queue Stage 3)  
**Branch:** `fix/sales-pipeline-v1-product-wiring`  
**Parents:** [Sequential queue](sales-to-comms-sequential-queue.md) · [Pipeline v1 seal](../architecture/sales-domain-pipeline-v1.md) · Stage 2 manual create

## Scope (this PR)

Wire **product** Sales convert to domain Convert Mapping and apply Review SoT.

| Required | Done via |
|----------|----------|
| Product convert → `convert_sales_inquiry_mapping` | `applications.mutations.convert_sales_inquiry` |
| SalesInquiry remains SoT | resolve SI from transport Lead facade; convert by `sales_inquiry_id` |
| Review decision `match_existing` / `create_new` applied | `_review_convert_decision` + bind before `convert_client_lead` |
| Review SoT fail-closed | missing / unknown review → `missing_review_decision` (no invented create_new) |
| Idempotent re-convert | existing `convert_mapping_v1` replay (no second ClientAccount) |
| Tenant / company ownership before write | match-target assert + ledger tenant filter |
| Mapping + lineage + audit one transaction | mandatory `log_activity`; audit failure rolls back the whole convert |

## Out of scope

- Communication product branches  
- Full Lead demotion across Sales UI/API (later Stage 3 slice)  
- Closing non-canonical Lead `POST /leads/{id}/convert-client` (tracked; not deleted here)  
- Manual-create UI  

## HTTP

- Facade unchanged: `POST /api/v1/sales/applications/{application_id}/convert-client`  
- Errors: `422` with `{code, reason, message, details}` from Convert Mapping fail-closed reasons  

## Tests

- `backend/tests/modules/sales/test_convert_mapping.py` (existing + match_existing apply)  
- `backend/tests/modules/sales/test_product_convert_wiring.py` (mutation → mapping)
