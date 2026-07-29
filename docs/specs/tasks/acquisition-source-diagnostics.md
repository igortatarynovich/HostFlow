# Source Diagnostics — Marketing ops console (Product Epic)

**Status:** **ACTIVE** — PR3 implementing (PR1 ✅ #196 · PR2 ✅ #199)  
**Date:** 2026-07-29  
**Product Track:** after FlightAdBinding Ad-ID bind UI (**DONE** #187)  
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

## PR3 — Duplicate decision surface (this slice)

### IN

1. Case API field `duplicate` composed from `decision_result_v1` + `duplicate_match_v1` + Lead status  
2. Marketing case panel: match level, reasons, HR blockers, suggested candidate, deep-links to Lead / Candidate  
3. **Read-only** — no attach/create/ignore writes from Diagnostics (resolve in CRM Lead)

### OUT

- Mapping-version stamp / Mapping Health drift  
- Replay / export  
- Writing duplicate decisions from Diagnostics  

### Acceptance (PR3)

- [ ] Case with duplicate stamp returns `duplicate.active=true` + match fields  
- [ ] Clean routed case returns `duplicate.active=false`  
- [ ] UI shows panel only when active; Resolve in Lead CTA present  

---

## Later epic backlog

- mapping version used  
- warnings / Mapping Health drift  
- replay submission  
- export payload  

---

## History

- 2026-07-29: Epic brief opened; Product Track → Source Diagnostics PR1 (Ad-ID bind UI closed #187).
- 2026-07-29: PR1 merged (#196); Product Track → PR2 filters.
- 2026-07-29: PR2 merged (#199); Product Track → PR3 duplicate decision surface.
