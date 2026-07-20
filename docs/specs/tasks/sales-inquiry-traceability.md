# SalesInquiry immutable lineage / traceability (ADR-022 Phase 2 slice 4)

**Status:** implementation contract (L3)  
**Date:** 2026-07-20  
**Trusted base:** `integration/release-product-a-b` @ `fb36f674`+  
**Canon:** [`../workflows/adr022-phase2-sales-only-capability-flow.md`](../workflows/adr022-phase2-sales-only-capability-flow.md) §4.6  
**Branch:** `feat/sales-inquiry-traceability`  
**Entry:** `backend.app.modules.sales.services.sales_inquiry_traceability`

---

## Sole goal

Immutable Sales lineage after convert — audit answers without recomputation.

## Chain

```text
SalesInquiry → Flights Dispatch → Review Decision? → Convert Mapping → ClientAccount
```

Each chain node has `prev` pointing at the previous link.

## SoT

`SalesInquiry.meta.sales_inquiry_lineage_v1` (Sales-owned).  
Flights keeps dispatch/provenance rows; lineage stores **opaque** `flights_ledger_id` only.

## Rules

- Written once by convert (`record_lineage_after_convert`)
- Never rewritten / deleted / dynamically rebuilt
- Review link **absent** when `not_required`
- Review link **present** after ambiguity resolve
- Fail-closed: missing inquiry / Flights ref / convert mapping / required review; provenance mismatch; cross-tenant; orphan convert; orphan trace

## Non-goals

UI · search · analytics · new screens/routes · moving ownership to Flights

## Next after merge

Sales Phase 2 domain complete. Remaining: **Capability UI** only (thin interface). Then stop for CRM-stage revision.
