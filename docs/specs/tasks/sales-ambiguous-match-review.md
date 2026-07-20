# SalesInquiry ambiguous match review (ADR-022 Phase 2 slice 3)

**Status:** implementation contract (L3)  
**Date:** 2026-07-20  
**Trusted base:** `integration/release-product-a-b` @ `f75c1b9d`+  
**Canon:** [`../workflows/adr022-phase2-sales-only-capability-flow.md`](../workflows/adr022-phase2-sales-only-capability-flow.md) §4.4  
**Branch:** `feat/sales-ambiguous-match-review`  
**Entry:** `backend.app.modules.sales.services.ambiguous_match_review`

---

## Sole goal

SalesInquiry-owned review state for ambiguous ClientAccount match evidence.

## SoT

`SalesInquiry.meta.ambiguous_match_review_v1` (+ `SalesInquiry.status=review_required` while open).

Not Lead · not Flights · not Recruitment · not frontend-local state.

## States

`not_required` · `required` · `resolved_match` · `resolved_create_new` · `cancelled`

## API (service only — no new HTTP routes)

| Function | Purpose |
|----------|---------|
| `open_ambiguous_match_review` | ≥2 ClientAccount candidates → `required` |
| `mark_unique_match_not_required` | unique match → `not_required` |
| `resolve_ambiguous_match_review` | Sales decision + optimistic `expected_version` |
| `review_blocks_convert` | Convert gate (wired into convert mapping) |

## Non-goals

UI · wizard · Capability · Recruitment review · Traceability UI · new routes · shared review engine · changing Flights destination.

## Next after merge

**Traceability implementation** (no UI) — then Sales Phase 2 domain seal; Capability UI last.
