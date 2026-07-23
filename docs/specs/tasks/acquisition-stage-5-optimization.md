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

### IN

1. **Signals contract** — typed Flight optimization signals composed from Stage 4 runtime snapshot + Live Intake Monitor counters + allowlisted Timeline events (e.g. elevated `routing_failed`, `DeliveryErrorOccurred` rate in a window).
2. **HTTP read** — `GET …/flights/{id}/optimization` (or equivalent under platform campaigns) returning signals + optional `recommended_action` (`none` | `suggest_pause`) with reason codes.
3. **Tests** — tenant/company scope, recommendation thresholds, no write-path side effects.
4. **Thin UI (optional in same PR if tiny)** — Marketing detail badge/banner “Consider pause” when recommendation present; no auto-button that bypasses existing Stage 4 commands.

### OUT

- Auto-executing Pause/Resume/Complete without operator confirmation  
- AI / LLM recommendations  
- Stage 6 ROI / cohort analytics  
- Flight Cancel · Ads Manager · Meta D2 full path  
- New event store · changing 3E ASC list canon  
- Budget automation as a product suite  

### Implementation bias

Compose Stage 4 `runtime_read` + `live_intake_monitor` + Timeline list. Prefer pure functions over new tables. If persistence is required later, open a separate ownership note — default KEEP MODULE / no System Layer dictionaries.

---

## Out of scope (Stage 5 epic initial)

- Stage 6 strategic dashboards as substitute for Timeline  
- Provider Ads Manager replacement  
- Reopening Stage 4 command matrix  

---

## History

- 2026-07-23: Opened after Stage 4 DONE merge (#148–#151); **PR-1 locked** as read-only optimization signals.
