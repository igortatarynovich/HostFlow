# Stage 3 — Convert entrypoints (slice 2)

**Status:** Implementation slice (product queue Stage 3)  
**Branch:** `fix/sales-pipeline-v1-convert-entrypoints`  
**Base:** `integration/release-product-a-b` @ `cdaccd48`  
**Parents:** [Sequential queue](sales-to-comms-sequential-queue.md) · Stage 3 slice 1 product wiring

## Scope

One product conversion engine for both HTTP entrypoints; Lead route is a compatibility wrapper.

| Required | Done via |
|----------|----------|
| Lead `POST /leads/{id}/convert-client` → mapping | `run_product_convert_via_mapping` |
| Sales `POST /sales/inquiries/{id}/convert-client` → mapping | same helper |
| Review SoT on both | `convert_sales_inquiry_mapping` |
| Preserve Lead HTTP response contract | return `LeadOut` after shared convert |
| No direct product call to `convert_client_lead` | Lead router no longer imports conversion writer |
| Frontend uses sales helper | `ClientInquiryWorkPage`, `LeadDetailPage` → `convertSalesInquiryToClient` |
| Remove unused legacy FE helper | deleted `convertClientLeadToClient` |

## Out of scope

- Communication  
- entity-profile `outcome_executor`  
- intake auto-outcomes  
- internal writer `convert_client_lead`  
- SalesInquiry / Lead facade architecture rewrite  

## Engine

```
HTTP (Sales | Lead facade) → run_product_convert_via_mapping
  → convert_sales_inquiry_mapping → convert_client_lead (shared writer)
```

## Tests

- `backend/tests/modules/sales/test_convert_entrypoints_contract.py`
- `backend/tests/api/test_sales_targeted_advertising_intake.py` (readiness seed before Lead convert)
- Staging runbook: convert readiness + Sales/Lead replay same `client_account_id`
