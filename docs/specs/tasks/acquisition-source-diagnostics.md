# Source Diagnostics — Marketing ops console (Product Epic)

**Status:** **PR1–PR5 DONE** · later backlog remains  
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

## PR1–PR4 ✅

- PR1 #196 list + case · PR2 #199 filters · PR3 #200 duplicate · PR4 #201 Mapping Health

---

## PR5 — Ingest mapping stamp + drift ✅ #202

### IN

1. Stamp `mapping_applied_v1` on Lead.normalized at Meta/webhook ingest (rules fingerprint, count, source, stamped_at)  
2. Diagnostics `mapping.historical_version_available=true` when stamp present  
3. `mapping.drift` when current Source rules fingerprint ≠ applied fingerprint  
4. UI shows applied fingerprint + drift flag  

### OUT

- Replay / export  
- Alerting / webhook on drift (Phase 7 style)  

### Acceptance (PR5)

- [x] Ingest path writes `mapping_applied_v1`  
- [x] Case with stamp + changed profile rules → `drift=true`  
- [x] Case without stamp → historical false / drift n/a  

---

## Later epic backlog

- Mapping Health drift alerts (notification / detection)  
- replay submission  
- export payload  

---

## History

- 2026-07-29: PR5 merged (#202); Product Track → Stage 5 PR-2 explainability / operator ack-dismiss.
- 2026-07-29: PR4 merged (#201); Product Track → PR5 ingest mapping stamp + drift.
- 2026-07-29: PR3 merged (#200); Product Track → PR4 mapping context.
- 2026-07-29: PR2 merged (#199); Product Track → PR3 duplicate decision surface.
- 2026-07-29: PR1 merged (#196); Product Track → PR2 filters.
- 2026-07-29: Epic brief opened; Product Track → Source Diagnostics PR1 (Ad-ID bind UI closed #187).
