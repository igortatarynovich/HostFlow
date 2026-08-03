# Source Diagnostics — Marketing ops console (Product Epic)

**Status:** **PR1–PR9 DONE** ✅ (#196–#212)  
**Date:** 2026-08-03  
**Product Track (next):** [Acquisition Stage 6 PR-1 — Flight wave compare](acquisition-stage-6-analytics.md)  
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

## PR1–PR8 ✅

| PR | Deliverable | Merge |
|----|-------------|-------|
| PR1 | List + case | #196 |
| PR2 | List filters | #199 |
| PR3 | Duplicate decision | #200 |
| PR4 | Mapping Health | #201 |
| PR5 | Mapping stamp + drift | #202 |
| PR6 | Case export JSON | #205 |
| PR7 | Drift list alerts | #206 |
| PR8 | Replay via Leads process | #210 |
| PR9 | In-app drift-summary | #212 |

---

## PR8 — Replay submission ✅ #210

### Delivered

1. Case UI **Replay** → `POST /api/v1/leads/{lead_id}/process`  
2. Success reloads Diagnostics case compose  
3. Errors via recovery banner; no Diagnostics write route  

### Acceptance (PR8)

- [x] `data-testid="marketing-diagnostics-replay"`  
- [x] Uses `processLead` / Leads process façade  
- [x] Success refreshes case; failure shows recovery banner  

---

## PR9 — Drift notification Wave-1 ✅

### IN

1. Tenant-scoped summary: count of recent Acquisition leads with `mapping_drift=true` (reuse PR7 compare; capped window)  
2. Surface on Diagnostics page header / Sources health strip (in-app only)  
3. Deep-link to Diagnostics list with `drift_only=1`  

### OUT

- Email / webhook / push providers  
- Auto remapping  
- Dry-run normalize preview  
- New Activity event type  

### Acceptance (PR9)

- [x] Authenticated `_READ` `GET …/diagnostics/drift-summary` (windowed count + scan meta)  
- [x] UI shows count + link to filtered Diagnostics list (`?drift_only=1`) on Diagnostics + Sources  
- [x] No notification channel outside the SPA  

---

## Later epic backlog

- Dry-run / remapping preview without entity writes  
- Dedicated Activity event for operator replay (optional observability)  
- Email / webhook drift notifications (after Wave-1)  

---

## History

- 2026-08-03: PR9 ✅ #212; Product Track → Stage 6 Analytics PR-1.  
- 2026-08-02: PR9 drift-summary + in-app banner (#212); epic Wave-1 notifications closed.  
- 2026-08-02: PR8 merged (#210); Product Track → **PR9 drift notification Wave-1**.  
- 2026-08-01: PR7 merged (#206); Product Track → PR8 replay.  
- 2026-08-01: PR6 closed as ✅ #205; Product Track → PR7.  
- 2026-07-29: Stage 5 PR-2 merged (#203); Product Track → Source Diagnostics PR6.  
- 2026-07-29: PR5–PR1 merges (#202…#196); epic opened after Ad-ID bind UI #187.
