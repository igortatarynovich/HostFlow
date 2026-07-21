# Acquisition Stage 4 — Flight Runtime

**Status:** Queued (next Product horizon after Stage 3E) — **not active**  
**Canon:** [ADR-024](../architecture/ADR-024-acquisition-campaigns-intake-routing.md) §14 (post-3E)  
**Depends on:** Stage **3E** complete (Activity Timeline PR-1…PR-4)  
**Parents:** [Stage 3E — Activity Timeline](acquisition-stage-3e-activity-timeline.md) · Epic P / 3D ✅

> **Operations layer** for Acquisition — Campaign / Flight day-to-day control.  
> Uses Stage 3E Activity Timeline as **observability infrastructure**; does **not** redefine it.

---

## Boundary vs Stage 3E

| Stage | Layer | Delivers |
|-------|--------|----------|
| **3E** | Observability | Universal Activity Timeline (foundation → instrumentation → read API → thin UI) |
| **4** | Operations | Flight Runtime — CRUD, launch controls, intake monitor, basic metrics, runtime actions |

**Do not** put Launch / Pause / Resume, budget edits, or Flight management controls into Stage 3E PR-4 UI. Those belong here.

---

## In scope (Stage 4 — draft epic)

1. Campaign CRUD (operator-facing)  
2. Flight CRUD  
3. Endpoint Management  
4. Launch / Pause / Resume  
5. Live Intake Monitor  
6. Basic Metrics (submissions, leads, candidates, CPL)  
7. Runtime actions (operator controls that emit Timeline events via existing append contract)

## Out of scope (initial Stage 4)

- Full analytics / Intelligence suite  
- Multi-Flight wave compare (V2)  
- CampaignTemplate catalog  
- Provider Ads Manager replacement  
- Redefining Activity Timeline schema or public append/list contract  

---

## Activation rule

Promote to **Product Track active** only after Stage 3E DoD is met and PR-4 is merged. Until then this file is the locked next-horizon pointer for the Product Queue.

---

## History

- 2026-07-21: Opened as **queued** epic — Stage 3E = observability only; Stage 4 = operations (Flight Runtime).
