# Acquisition Stage 4 — Flight Runtime

**Status:** Queued (next Product horizon after Stage 3E) — **not active**  
**Canon:** [ADR-024](../architecture/ADR-024-acquisition-campaigns-intake-routing.md) §14 · §14.1  
**Depends on:** Stage **3E** complete (Activity Timeline PR-1…PR-4)  
**Parents:** [Stage 3E — Activity Timeline](acquisition-stage-3e-activity-timeline.md) · Epic P / 3D ✅  
**Next horizons:** Stage 5 Optimization · Stage 6 Analytics (see ladder below; not opened)

> **Operations layer** for Acquisition — Campaign / Flight day-to-day control.  
> Uses Stage 3E Activity Timeline as **observability infrastructure**; does **not** redefine it.

---

## Acquisition maturity ladder

| Stage | Layer | Verb | Status |
|-------|--------|------|--------|
| **3E** | Observability | See | Active → DONE after Timeline PR-4 |
| **4** | Operations | Control | **This epic (queued)** |
| **5** | Optimization | Improve | Future horizon |
| **6** | Analytics | Decide | Future horizon |

Normative detail: [ADR-024 §14.1](../architecture/ADR-024-acquisition-campaigns-intake-routing.md).

After Stage 4: operator can **control** Flights. Stages 5–6 add automatic improvement and strategic analytics on the same Timeline + Runtime facts — without rewriting 3E/4 contracts.

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

- Stage 5 Optimization (auto pause/resume policies, AI recommendations, anomaly-driven actions as a product suite)  
- Stage 6 full analytics / Intelligence suite (ROI, cohort compare, strategic dashboards)  
- Multi-Flight wave compare (V2)  
- CampaignTemplate catalog  
- Provider Ads Manager replacement  
- Redefining Activity Timeline schema or public append/list contract  

---

## Activation rule

Promote to **Product Track active** only after Stage 3E DoD is met and PR-4 is merged. Until then this file is the locked next-horizon pointer for the Product Queue.

Do **not** open Stage 5 or Stage 6 Product slices while Stage 4 is incomplete, unless the maturity ladder in ADR-024 §14.1 is explicitly amended.

---

## History

- 2026-07-21: Opened as **queued** epic — Stage 3E = observability only; Stage 4 = operations (Flight Runtime).  
- 2026-07-21: Linked to maturity ladder — Operations → then Optimization (5) → Analytics (6).
