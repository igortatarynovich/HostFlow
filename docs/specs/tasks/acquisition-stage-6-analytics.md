# Acquisition Stage 6 — Analytics

**Status:** **PR-1…PR-3 DONE** · **PR-4 IN PROGRESS**  
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
| **6** | Analytics | Decide | **PR-1…3 DONE** · **PR-4 active** |

---

## PR sequence

| PR | Scope | Status |
|----|--------|--------|
| **PR-1** | Flight wave **compare** within a Campaign | **DONE** (#213) |
| **PR-2** | Windowed **day cohorts** + CAC proxy | **DONE** (#214) |
| **PR-3** | **Week** cohort buckets (`bucket=day\|week`) | **DONE** (#215) |
| **PR-4** | Cross-campaign **portfolio** KPI (company-scoped) | **Active** |
| **PR-5+** | Month buckets / revenue ROI | Not opened |

**Hard ban (Stage 6):** new metrics ledger tables; Timeline as dashboard SoT; auto-pause / Runtime writes from analytics; Forms/BI ownership of KPI; ad-provider spend sync as new SoT.

---

## PR-1 — Flight wave compare ✅ #213

### Acceptance (PR-1)

- [x] Authenticated `_READ` compare endpoint; company scope same as Campaign KPI  
- [x] Reuses `aggregate_campaign_kpi` — no parallel KPI store  
- [x] UI shows per-flight spend / leads / CPL + best-CPL marker when ≥2 flights  
- [x] Repeat GET has no write / Activity side effects  

---

## PR-2 — Windowed day cohorts + CAC proxy ✅ #214

### Acceptance (PR-2)

- [x] Authenticated `_READ` cohorts endpoint; company scope same as Campaign KPI  
- [x] No parallel KPI store — buckets from Attribution / Spend / Outcome rows only  
- [x] UI shows day series + window totals including CPL / cost_per_outcome  
- [x] Repeat GET has no write / Activity side effects  

---

## PR-3 — Week cohort buckets ✅ #215

### Acceptance (PR-3)

- [x] `bucket=week` returns Monday-start UTC week rows with same metrics as day mode  
- [x] Invalid `bucket` → 422  
- [x] UI toggle Day / Week reloads cohorts  
- [x] No new ledger / no GET side effects  

---

## PR-4 — Cross-campaign portfolio

### IN

1. Company-scoped read compose over Campaign list + `aggregate_campaign_kpi` (limit capped)  
2. Portfolio totals + per-campaign spend / leads / CPL / `cost_per_outcome` + `is_best_cpl`  
3. HTTP: `GET /api/v1/platform/campaigns/analytics/portfolio?limit=` (static path before `/{id}`)  
4. Thin strip on Marketing campaigns list  
5. Tests + threat model  

### OUT

- Month buckets  
- Revenue ROI / LTV  
- Charting libraries  
- Ad-provider spend sync  

### Acceptance (PR-4)

- [x] Authenticated `_READ` portfolio; company isolation  
- [x] Reuses 3D KPI aggregates — no parallel store  
- [x] UI shows portfolio totals + campaign rows with best-CPL marker  
- [x] No GET side effects  

---

## Later backlog

- Month bucket granularity  
- Revenue ROI once commercial outcome value contracts exist  

---

## History

- 2026-08-03: PR-3 ✅ #215; Product Track → **Stage 6 PR-4 portfolio**.  
- 2026-08-03: PR-2 ✅ #214; Product Track → Stage 6 PR-3 week buckets.  
- 2026-08-03: PR-1 ✅ #213; Product Track → Stage 6 PR-2 windowed cohorts.  
- 2026-08-03: Product Track → Stage 6 PR-1 after Source Diagnostics PR9 ✅ #212.  
