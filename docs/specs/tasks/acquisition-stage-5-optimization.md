# Acquisition Stage 5 — Optimization

**Status:** Active — **PR-1 locked** (Optimization signals / pause recommendation — read-only)  
**Canon:** [ADR-024](../architecture/ADR-024-acquisition-campaigns-intake-routing.md) §14 · §14.1  
**Depends on:** Stage **4** complete ✅ (Flight Runtime #136 / #148–#151)  
**Parents:** [Stage 4 — Flight Runtime](acquisition-stage-4-flight-runtime.md) · Stage 3E Timeline  
**Branch:** `feat/acquisition-stage-5-pr1-optimization-signals` · worktree TBD  
**Deferred (not Stage 5):** [acquisition-stage-3e-deferred.md](acquisition-stage-3e-deferred.md) (D1–D5 remain Instrumentation)  
**Next horizon:** Stage 6 Analytics (do not open while 5 incomplete)

> **Improve** rung of the maturity ladder — assisted / automatic optimization **on top of** Stage 4 controls + 3E Timeline.  
> Does **not** redefine Runtime commands or Timeline append contract.

---

## Acquisition maturity ladder

| Stage | Layer | Verb | Status |
|-------|--------|------|--------|
| **3E** | Observability | See | **DONE** (#130–#133) |
| **4** | Operations | Control | **DONE** (#136 / #148–#151) |
| **5** | Optimization | Improve | **This epic (PR-1 locked)** |
| **6** | Analytics | Decide | Future horizon |

---

## PR sequence (initial)

| PR | Scope |
|----|--------|
| **PR-1** | Optimization signals + pause recommendation (read-only) — **locked** |
| **PR-2+** | TBD after PR-1 — auto-apply policies only with explicit operator/safety contract |

---

## PR-1 — Optimization signals / pause recommendation (locked)

Minimal first Product PR. **Read-only** — no auto Launch/Pause/Resume writes.  
**Architectural ban:** the signal may **explain and recommend only**. It must never mutate Campaign or Flight. No Activity append on GET.

### IN

1. **Signals contract** — typed Flight optimization signals composed from Stage 4 `get_flight_runtime_snapshot` (identity / status / KPI strip) + **windowed** Timeline counts (allowlist subset of Live Intake Monitor). No second metrics ledger.
2. **HTTP read** — `GET /api/v1/platform/campaigns/{campaign_id}/flights/{flight_id}/optimization?window_hours=` returning `assessment`, `recommended_action`, `reason_codes`, `signals`, window counters, KPI strip, and locked `thresholds`.
3. **Tests** — threshold boundaries, zero spend/intake, paused/completed flight, company scope, repeat GET without side effects.
4. **Thin UI (optional in same PR if tiny)** — Marketing detail badge/banner “Consider pause” when recommendation present; no auto-button that bypasses existing Stage 4 commands.

### Locked inputs (PR-1)

| Input | Source |
|-------|--------|
| Campaign / Flight identity | Stage 4 runtime snapshot |
| Current runtime status (`campaign_status`, `flight_status`) | Stage 4 runtime snapshot |
| Delivery + intake counters (windowed) | Timeline: `SubmissionReceived`, `RoutingCompleted`, `RoutingFailed`, `DeliveryErrorOccurred` |
| KPI spend / leads (informational) | Stage 4 runtime KPI aggregate — **not** used for pause thresholds in PR-1 |
| Observation window | `window_hours` query (default **24**, clamp **1…168**) |
| Minimum data volume | `decision_volume` = sum of the four windowed counters |

### Locked assessments / actions

| `assessment` | `recommended_action` | When |
|--------------|----------------------|------|
| `insufficient_data` | `none` | Flight not `active`, or `decision_volume` < min volume |
| `healthy` | `none` | Active + enough volume + within thresholds |
| `suggest_pause` | `suggest_pause` | Active + enough volume + any pause threshold met |

### Locked thresholds (PR-1)

| Constant | Value | Rule |
|----------|-------|------|
| `MIN_DECISION_VOLUME` | **5** | Below → `insufficient_data` |
| `MIN_ROUTING_SAMPLE` | **5** | `routing_completed + routing_failed` |
| `ROUTING_FAIL_RATE_THRESHOLD` | **0.50** | Inclusive (`>=`) when sample ≥ min |
| `DELIVERY_ERROR_THRESHOLD` | **3** | Inclusive absolute `DeliveryErrorOccurred` count in window |

Pause recommendation applies **only** while `flight_status == active`. Paused / completed / planned → `insufficient_data` + `flight_not_active` (never auto-suggest pause for a non-active flight).

### Activity events

Stage 5 PR-1 does **not** define a recommendation Activity type. **Do not** emit Activity on GET. Repeat GET must leave Timeline row count and Flight/Campaign status unchanged.

### OUT

- Auto-executing Pause/Resume/Complete without operator confirmation  
- Workers / schedulers / auto-pause policies (candidate for later PR only)  
- AI / LLM recommendations  
- Stage 6 ROI / cohort analytics  
- Flight Cancel · Ads Manager · Meta D2 full path  
- New event store · changing 3E ASC list canon  
- Budget automation as a product suite  
- Activity emit on every optimization read  

### Implementation bias

Compose Stage 4 `runtime_read` + Timeline window counts (same family as `live_intake_monitor`). Prefer pure `evaluate_flight_optimization` over new tables. If persistence is required later, open a separate ownership note — default KEEP MODULE / no System Layer dictionaries.

---

## Out of scope (Stage 5 epic initial)

- Stage 6 strategic dashboards as substitute for Timeline  
- Provider Ads Manager replacement  
- Reopening Stage 4 command matrix  

---

## History

- 2026-07-23: Opened after Stage 4 DONE merge (#148–#151); **PR-1 locked** as read-only optimization signals.
- 2026-07-23: Locked PR-1 inputs/thresholds/assessments; no Activity on GET; compose runtime + windowed Timeline only.
