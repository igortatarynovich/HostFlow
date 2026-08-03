# Acquisition Stage 6 — Analytics

**Status:** **PR-1…PR-4 DONE** · **PR-5 IN PROGRESS**  
**Canon:** [ADR-024](../architecture/ADR-024-acquisition-campaigns-intake-routing.md) §14 · §14.1  
**Depends on:** Stage **5** DONE (#153 / #203) · Source Diagnostics Wave-1 DONE (#196–#212) · Stage **3D** KPI SoT  
**Parents:** [sales-to-comms-sequential-queue.md](sales-to-comms-sequential-queue.md) · Stage 5 [optimization](acquisition-stage-5-optimization.md)

> **Decide** rung of the maturity ladder — strategic efficiency from existing attribution/KPI facts.  
> Does **not** redefine Timeline (audit), Runtime commands, or Optimization auto-apply.

---

## Acquisition maturity ladder

| Stage | Layer | Verb | Status |
|-------|--------|------|--------|
| **3E** | Observability | See | **DONE** |
| **4** | Operations | Control | **DONE** |
| **5** | Optimization | Improve | **DONE** (#153 / #203) |
| **6** | Analytics | Decide | **PR-1…4 DONE** · **PR-5 active** |

---

## PR sequence

| PR | Scope | Status |
|----|--------|--------|
| **PR-1** | Flight wave **compare** within a Campaign | **DONE** (#213) |
| **PR-2** | Windowed **day cohorts** + CAC proxy | **DONE** (#214) |
| **PR-3** | **Week** cohort buckets | **DONE** (#215) |
| **PR-4** | Cross-campaign **portfolio** KPI | **DONE** (#216) |
| **PR-5** | **Month** cohort buckets (`bucket=day\|week\|month`) | **Active** |
| **PR-6+** | Revenue ROI (needs commercial outcome value contract) | Not opened |

**Hard ban (Stage 6):** new metrics ledger tables; Timeline as dashboard SoT; auto-pause / Runtime writes from analytics; Forms/BI ownership of KPI; ad-provider spend sync as new SoT.

---

## PR-1…PR-4 ✅

Acceptance closed in #213–#216 (compare, day/week cohorts, portfolio).

---

## PR-5 — Month cohort buckets

### IN

1. Extend cohorts compose with `bucket=month` (UTC calendar months; partial months clipped to window)  
2. HTTP query allows `day|week|month`  
3. Marketing Campaign Detail Month toggle  
4. Tests + threat model note  

### OUT

- Revenue ROI / LTV  
- Charting libraries  
- Ad-provider spend sync  

### Acceptance (PR-5)

- [x] `bucket=month` returns month-start UTC rows with same metrics as day/week  
- [x] Invalid `bucket` → 422  
- [x] UI toggle Day / Week / Month  
- [x] No new ledger / no GET side effects  

---

## Later backlog

- Revenue ROI once commercial outcome value contracts exist  

---

## History

- 2026-08-03: PR-4 ✅ #216; Product Track → **Stage 6 PR-5 month buckets**.  
- 2026-08-03: PR-3 ✅ #215; Product Track → Stage 6 PR-4 portfolio.  
- 2026-08-03: PR-2 ✅ #214; Product Track → Stage 6 PR-3 week buckets.  
- 2026-08-03: PR-1 ✅ #213; Product Track → Stage 6 PR-2 windowed cohorts.  
- 2026-08-03: Product Track → Stage 6 PR-1 after Source Diagnostics PR9 ✅ #212.  
