# Source Diagnostics — Marketing ops console (Product Epic)

**Status:** **PR1–PR4 DONE** · later backlog remains  
**Date:** 2026-07-29  
**Product Track (next):** [Acquisition Stage 5 PR-2](acquisition-stage-5-optimization.md)  
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

## PR1 — Recent submissions + case detail ✅ #196

### Acceptance (PR1)

- [x] Operator opens Marketing → Diagnostics without developer  
- [x] Sees recent Acquisition-stamped submissions (name / status / source / time)  
- [x] Opens one case: routing summary + activity timeline + payload blocks  
- [x] No new SoT tables; tests cover list/detail compose  

---

## PR2 — List filters ✅ #199

### Acceptance (PR2)

- [x] Filter by source narrows list  
- [x] Filter by flight_id (UUID) narrows to stamped Flight  
- [x] failed_only excludes clean routed/processed rows  
- [x] Invalid flight_id → 422  

---

## PR3 — Duplicate decision surface ✅ #200

### Acceptance (PR3)

- [x] Case with duplicate stamp returns `duplicate.active=true` + match fields  
- [x] Clean routed case returns `duplicate.active=false`  
- [x] UI shows panel only when active; Resolve in Lead CTA present  

---

## PR4 — Mapping context / Mapping Health ✅ #201

### Acceptance (PR4)

- [x] Case with `intake_source_profile_id` returns `mapping.active=true` + health  
- [x] Missing profile → `profile_missing=true` (no 500)  
- [x] UI shows Mapping Health panel + Open Mapping CTA  

---

## Later epic backlog

- historical mapping version stamp at ingest  
- Mapping Health drift alerts  
- replay submission  
- export payload  

---

## History

- 2026-07-29: Epic brief opened; Product Track → Source Diagnostics PR1 (Ad-ID bind UI closed #187).
- 2026-07-29: PR1 merged (#196); Product Track → PR2 filters.
- 2026-07-29: PR2 merged (#199); Product Track → PR3 duplicate decision surface.
- 2026-07-29: PR3 merged (#200); Product Track → PR4 mapping context / Mapping Health.
- 2026-07-29: PR4 merged (#201); Product Track → Stage 5 PR-2 explainability / operator ack-dismiss.
