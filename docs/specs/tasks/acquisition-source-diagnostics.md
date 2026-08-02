# Source Diagnostics — Marketing ops console (Product Epic)

**Status:** **ACTIVE** — PR8 replay submission (PR1–PR7 ✅)  
**Date:** 2026-08-01  
**Product Track:** Source Diagnostics PR8 (PR7 drift alerts ✅ #206)  
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

## PR1–PR7 ✅

- PR1 #196 list + case · PR2 #199 filters · PR3 #200 duplicate · PR4 #201 Mapping Health · PR5 #202 mapping stamp + drift · PR6 #205 case export · PR7 #206 drift alerts

---

## PR7 — Mapping Health drift alerts ✅ #206

### Delivered

1. List query `drift_only=true` — fingerprint compare (scan capped)  
2. List items `mapping_drift` + page `drift_alert_count`  
3. Diagnostics UI filter / badge / alert strip  

### Acceptance (PR7)

- [x] `drift_only=true` returns only leads with `mapping_drift=true`  
- [x] Matching stamp not in drift_only results  
- [x] FE filter + badge + alert strip  

---

## PR8 — Replay submission (this slice)

### IN

1. Case UI **Replay** — calls existing Leads write contract `POST /api/v1/leads/{lead_id}/process` (same pipeline as CRM Process)  
2. On success, reload Diagnostics case compose (routing / mapping / timeline)  
3. Surface process errors (422 block codes / missing payload) without inventing a second remapping engine  

### OUT

- New Diagnostics HTTP write / remapping endpoint  
- New Acquisition Activity event type for replay  
- Dry-run normalize-only (no Lead mutation)  
- Bulk replay  
- Notification channels for drift  

### Acceptance (PR8)

- [x] Case view has Replay control (`data-testid="marketing-diagnostics-replay"`)  
- [x] Replay uses `processLead` → `POST /leads/{id}/process` (not a Diagnostics writer)  
- [x] Success refreshes case; failure shows recovery banner  

**Boundary lock:** Diagnostics remains a **read compose** surface. Replay is an ops CTA into the **Leads** process façade (admin/manager/recruiter RBAC on that route).

---

## Later epic backlog

- Mapping Health drift alerts — notification channels (email / in-app beyond list)  
- Dry-run / remapping preview without entity writes  
- Dedicated Activity event for operator replay (optional observability)  

---

## History

- 2026-08-01: PR7 merged (#206); Product Track → **PR8 replay submission** (Leads process façade from case UI).  
- 2026-08-01: PR6 closed as ✅ #205 (code already merged; docs catch-up); Product Track → PR7.  
- 2026-07-29: Stage 5 PR-2 merged (#203); Product Track → Source Diagnostics PR6 case export.  
- 2026-07-29: PR5 merged (#202); Product Track briefly → Stage 5 PR-2 explainability / operator ack-dismiss.  
- 2026-07-29: PR4 merged (#201); Product Track → PR5 ingest mapping stamp + drift.  
- 2026-07-29: PR3 merged (#200); Product Track → PR4 mapping context.  
- 2026-07-29: PR2 merged (#199); Product Track → PR3 duplicate decision surface.  
- 2026-07-29: PR1 merged (#196); Product Track → PR2 filters.  
- 2026-07-29: Epic brief opened; Product Track → Source Diagnostics PR1 (Ad-ID bind UI closed #187).
