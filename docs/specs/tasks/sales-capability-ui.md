# Sales Capability UI — display-only Pipeline v1 spine

**Status:** SUPERSEDED (operator UI removed)  
**Branch:** `feat/sales-capability-ui`  
**Queue:** [`sales-to-comms-sequential-queue.md`](sales-to-comms-sequential-queue.md) Stage 1  
**Parents:** Pipeline v1 seal · Creation Origins · Phase 2 Flow Spec

## Scope

Thin read of existing Sales Domain Pipeline v1 state (API remains for domain/debug consumers):

| Surface | Source |
|---------|--------|
| Capability | `SalesInquiry.entity_profile_code` as **proxy** (`decided=false` until a real decision stamp exists) |
| Review | `meta.ambiguous_match_review_v1` + `review_blocks_convert` |
| Convert availability / result | Domain convertible rules + `meta.convert_mapping_v1` |
| Traceability | `meta.sales_inquiry_lineage_v1` |

## Delivery

- `GET /api/v1/sales/inquiries/{application_id}/capability-spine` — **API kept**
- Operator Sales rail (`ApplicationSalesDetailPanel`) **does not** show the spine. Daily work surface: contact phone, call notes, questionnaire, timeline.

## Forbidden (this slice)

- Matching / review write / ClientAccount create  
- Bypass Convert Mapping  
- Communication changes  
- New Lead-as-SoT paths  

## Non-goal honesty

Product `POST .../convert-client` may still use Lead convert (Pipeline GAP §3). Capability spine is a domain projection, not a sales-manager tool.
