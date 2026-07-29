# Source Diagnostics — Marketing ops console (Product Epic)

**Status:** **ACTIVE** — PR6 implementing (PR1–PR5 ✅)  
**Date:** 2026-07-29  
**Product Track:** Source Diagnostics PR6 (Stage 5 PR-2 ✅ #203)  
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

## PR1–PR5 ✅

- PR1 #196 list + case · PR2 #199 filters · PR3 #200 duplicate · PR4 #201 Mapping Health · PR5 #202 mapping stamp + drift

---

## PR6 — Case export payload (this slice)

### IN

1. `GET /api/v1/platform/marketing/diagnostics/submissions/{lead_id}/export` — JSON attachment of case compose (routing / decision / duplicate / mapping / payload / normalized / timeline)  
2. Emit export security events (`export.requested` / `export.generated` / `export.denied`) with `contains_class3=true`, `bulk_operation=false`  
3. Case UI — **Export JSON** download button  

### OUT

- Bulk export / zip of many cases  
- Replay / remapping write paths  
- Drift alerting  

### Acceptance (PR6)

- [ ] Authenticated `_READ` export returns `application/json` attachment with schema `hostflow.marketing_diagnostics_export`  
- [ ] Missing lead → 404 + `export.denied`  
- [ ] FE downloads file from case view  

---

## Later epic backlog

- Mapping Health drift alerts (notification / detection)  
- replay submission  

---

## History

- 2026-07-29: Stage 5 PR-2 merged (#203); Product Track → Source Diagnostics PR6 case export.
- 2026-07-29: PR5 merged (#202); Product Track briefly → Stage 5 PR-2 explainability / operator ack-dismiss.
- 2026-07-29: PR4 merged (#201); Product Track → PR5 ingest mapping stamp + drift.
- 2026-07-29: PR3 merged (#200); Product Track → PR4 mapping context.
- 2026-07-29: PR2 merged (#199); Product Track → PR3 duplicate decision surface.
- 2026-07-29: PR1 merged (#196); Product Track → PR2 filters.
- 2026-07-29: Epic brief opened; Product Track → Source Diagnostics PR1 (Ad-ID bind UI closed #187).
