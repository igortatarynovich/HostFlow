# Acquisition Stage 6 — Analytics

**Status:** **DONE** (PR-1…PR-6b)  
**Canon:** [ADR-024](../architecture/ADR-024-acquisition-campaigns-intake-routing.md) §14 · §14.1  
**Depends on:** Stage **5** DONE (#153 / #203) · Source Diagnostics Wave-1 DONE (#196–#212) · Stage **3D** KPI SoT  
**Parents:** [sales-to-comms-sequential-queue.md](sales-to-comms-sequential-queue.md) · Stage 5 [optimization](acquisition-stage-5-optimization.md)  
**Outcome value ownership:** [outcome-commercial-value-ownership.md](../../modules/acquisition/outcome-commercial-value-ownership.md)

> **Decide** rung of the maturity ladder — strategic efficiency from existing attribution/KPI facts.  
> Does **not** redefine Timeline (audit), Runtime commands, or Optimization auto-apply.

---

## Acquisition maturity ladder

| Stage | Layer | Verb | Status |
|-------|--------|------|--------|
| **3E** | Observability | See | **DONE** |
| **4** | Operations | Control | **DONE** |
| **5** | Optimization | Improve | **DONE** (#153 / #203) |
| **6** | Analytics | Decide | **DONE** (PR-1…PR-6b) |

---

## PR sequence

| PR | Scope | Status |
|----|--------|--------|
| **PR-1** | Flight wave **compare** within a Campaign | **DONE** (#213) |
| **PR-2** | Windowed **day cohorts** + CAC proxy | **DONE** (#214) |
| **PR-3** | **Week** cohort buckets | **DONE** (#215) |
| **PR-4** | Cross-campaign **portfolio** KPI | **DONE** (#216) |
| **PR-5** | **Month** cohort buckets (`bucket=day\|week\|month`) | **DONE** (#217) |
| **PR-6a** | Outcome commercial value ownership + contract + write/read | **DONE** (this PR) |
| **PR-6b** | ROI read compose (`outcome_value`, `roi`) + UI + Stage 6 seal | **DONE** (this PR) |

**Hard ban (Stage 6):** new metrics ledger tables; Timeline as dashboard SoT; auto-pause / Runtime writes from analytics; Forms/BI ownership of KPI; ad-provider spend sync as new SoT; inventing commercial value outside the Outcome value contract.

---

## Delivered

- Flight compare, day/week/month cohorts, CAC proxy (`cost_per_outcome`), company portfolio  
- Outcome commercial value `declared_v1` snapshot + contract HTTP  
- ROI: `roi = (outcome_value − spend) / spend` when spend > 0 and same-currency value present  

---

## Later backlog

- `sales_order_v2` Outcome value from Sales commercial objects (opaque refs; no Acquisition FK)

---

## History

- 2026-08-03: PR-6a+PR-6b ✅; **Stage 6 DONE**; Product Track free for next roadmap horizon.  
- 2026-08-03: PR-5 ✅ #217; Product Track → Stage 6 PR-6a Outcome commercial value.  
- 2026-08-03: PR-4 ✅ #216; Product Track → Stage 6 PR-5 month buckets.  
- 2026-08-03: PR-3 ✅ #215; Product Track → Stage 6 PR-4 portfolio.  
- 2026-08-03: PR-2 ✅ #214; Product Track → Stage 6 PR-3 week buckets.  
- 2026-08-03: PR-1 ✅ #213; Product Track → Stage 6 PR-2 windowed cohorts.  
- 2026-08-03: Product Track → Stage 6 PR-1 after Source Diagnostics PR9 ✅ #212.  
