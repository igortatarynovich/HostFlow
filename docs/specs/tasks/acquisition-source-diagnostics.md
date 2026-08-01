# Source Diagnostics — Marketing ops console (Product Epic)

**Status:** **ACTIVE** — PR7 Mapping Health drift alerts (PR1–PR6 ✅)  
**Date:** 2026-08-01  
**Product Track:** Source Diagnostics PR7 (PR6 export ✅ #205 · Stage 5 PR-2 ✅ #203)  
**Parents:** [acquisition-ui-cutover.md](acquisition-ui-cutover.md) § After cutover · [sales-to-comms-sequential-queue.md](sales-to-comms-sequential-queue.md)

---

## Intent

Daily **operations** console for arrived intake — explain and repair a specific submission.  
Sibling of **Sources** (onboarding / config), not a Sources tab. Provider-agnostic (Meta + future channels).

| | Sources (onboarding) | Diagnostics (this epic) |
|--|----------------------|-------------------------|
| Goal | Connect → Ready | Casework on live submissions |
| Home | `/app/marketing/sources` | `/app/marketing/diagnostics` |
| SoT | IntakeSourceProfile / mapping_rules | **Lead** + **Acquisition Activity** |

---

## SoT lock (no parallel store)

- **Lead** — person / submission record, `normalized`, `payload`, `acquisition_routing_v1`, decision blocks  
- **Acquisition Activity** — processing timeline (`GET /platform/acquisition-activity?submission_id=`)  
- **Marketing Sources** — health entry points only (deep-link), not the list home  

Do **not** invent a submissions table or fork routing/mapping engines.

---

## PR1–PR6 ✅

- PR1 #196 list + case · PR2 #199 filters · PR3 #200 duplicate · PR4 #201 Mapping Health · PR5 #202 mapping stamp + drift · PR6 #205 case export JSON

---

## PR6 — Case export payload ✅ #205

### Delivered

1. `GET /api/v1/platform/marketing/diagnostics/submissions/{lead_id}/export` — JSON attachment (`hostflow.marketing_diagnostics_export`)  
2. Export security events (`export.requested` / `export.generated` / `export.denied`) with `contains_class3=true`, `bulk_operation=false`  
3. Case UI — **Export JSON** download button  

### Acceptance (PR6)

- [x] Authenticated `_READ` export returns `application/json` attachment with schema `hostflow.marketing_diagnostics_export`  
- [x] Missing lead → 404 + `export.denied`  
- [x] FE downloads file from case view  

---

## PR7 — Mapping Health drift alerts (this slice)

### IN

1. List query `drift_only=true` — return Acquisition leads whose `mapping_applied_v1.rules_fingerprint` ≠ current Source `mapping_rules` fingerprint (read-time compare; scan capped)  
2. List items expose `mapping_drift: true|false|null` + page `drift_alert_count`  
3. Diagnostics UI — **Только mapping drift** filter, list badge, and alert strip when the current page has drift  

### OUT

- Email / webhook / push notification channels  
- Auto remapping or rewrite of `mapping_rules`  
- Replay submission (separate later slice)  
- Bulk export of drifted cases  

### Acceptance (PR7)

- [x] `drift_only=true` returns only leads with `mapping_drift=true` (tenant-scoped `_READ`)  
- [x] Unchanged profile rules → lead with matching stamp is **not** in drift_only results  
- [x] FE filter + badge + alert strip (`data-testid` for filter / badge / alert)  

---

## Later epic backlog

- Mapping Health drift alerts — notification channels (email / in-app beyond list)  
- replay submission  

---

## History

- 2026-08-01: PR6 closed as ✅ #205 (code already merged; docs catch-up); Product Track → **PR7 Mapping Health drift alerts**.  
- 2026-07-29: Stage 5 PR-2 merged (#203); Product Track → Source Diagnostics PR6 case export.  
- 2026-07-29: PR5 merged (#202); Product Track briefly → Stage 5 PR-2 explainability / operator ack-dismiss.  
- 2026-07-29: PR4 merged (#201); Product Track → PR5 ingest mapping stamp + drift.  
- 2026-07-29: PR3 merged (#200); Product Track → PR4 mapping context.  
- 2026-07-29: PR2 merged (#199); Product Track → PR3 duplicate decision surface.  
- 2026-07-29: PR1 merged (#196); Product Track → PR2 filters.  
- 2026-07-29: Epic brief opened; Product Track → Source Diagnostics PR1 (Ad-ID bind UI closed #187).
