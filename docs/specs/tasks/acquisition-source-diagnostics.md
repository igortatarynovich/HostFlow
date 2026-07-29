# Source Diagnostics — Marketing ops console (Product Epic)

**Status:** **ACTIVE** — PR2 implementing (PR1 ✅ #196)  
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

### IN

1. Path `marketingDiagnostics` → `/app/marketing/diagnostics` (+ `/:leadId` detail)  
2. Marketing rail sibling (after Sources / Forms; before or beside Activity)  
3. **List:** recent Leads with Acquisition routing stamp (`acquisition_routing_v1`), person row (reuse Live Intake applicant projection)  
4. **Detail:** Lead routing / decision / raw+normalized + Acquisition Activity timeline by `submission_id` when uniquely resolvable  
5. Deep-link to CRM Lead Detail for full repair actions  

### OUT (later PRs)

- Replay / export product actions  
- Mapping-version stamp per submission  
- Mapping Health drift alerts on the case  
- Meta-only unmapped console as Diagnostics home  
- Comms DeliveryDiagnostics patterns  

### Acceptance (PR1)

- [x] Operator opens Marketing → Diagnostics without developer  
- [x] Sees recent Acquisition-stamped submissions (name / status / source / time)  
- [x] Opens one case: routing summary + activity timeline + payload blocks  
- [x] No new SoT tables; tests cover list/detail compose  

---

## PR2 — List filters (this slice)

### IN

1. Query filters on list: `source`, `flight_id`, `failed_only`  
2. `failed_only` = Lead `status=failed` **or** routing stamp `status=unresolved` **or** non-empty `Lead.error`  
3. Marketing Diagnostics filter bar (URL query sync)  

### OUT

- Duplicate decision surface  
- Mapping-version / Mapping Health  
- Replay / export  

### Acceptance (PR2)

- [ ] Filter by source narrows list  
- [ ] Filter by flight_id (UUID) narrows to stamped Flight  
- [ ] failed_only excludes clean routed/processed rows  
- [ ] Invalid flight_id → 422  

---

## Later epic backlog

- duplicate decision surface  
- mapping version used  
- warnings / Mapping Health drift  
- replay submission  
- export payload  

---

## History

- 2026-07-29: Epic brief opened; Product Track → Source Diagnostics PR1 (Ad-ID bind UI closed #187).
- 2026-07-29: PR1 merged (#196); Product Track → PR2 filters.
