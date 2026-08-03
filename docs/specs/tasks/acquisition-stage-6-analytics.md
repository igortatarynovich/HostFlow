# Acquisition Stage 6 — Analytics

**Status:** **PR-1 DONE** ✅ [#213](https://github.com/igortatarynovich/HostFlow/pull/213) · **PR-2 DONE** ✅ [#214](https://github.com/igortatarynovich/HostFlow/pull/214) · **PR-3 IN PROGRESS**  
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
| **6** | Analytics | Decide | **PR-1/2 DONE** · **PR-3 active** |

---

## PR sequence

| PR | Scope | Status |
|----|--------|--------|
| **PR-1** | Flight wave **compare** within a Campaign (read-only compose over 3D KPI + Flight identity) | **DONE** (#213) |
| **PR-2** | Windowed **day cohorts** + CAC proxy (`cost_per_outcome`) from attribution/spend/outcome timestamps | **DONE** (#214) |
| **PR-3** | **Week** cohort buckets (`bucket=day\|week`) on the same cohorts endpoint + UI toggle | **Active** |
| **PR-4+** | Cross-campaign portfolio / month buckets / revenue ROI | Not opened |

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

## PR-3 — Week cohort buckets

### IN

1. Extend cohorts compose with `bucket=day|week` (UTC Monday-start weeks; partial weeks clipped to window)  
2. HTTP query `bucket` on `GET …/analytics/cohorts` (default `day`)  
3. Marketing Campaign Detail Day/Week toggle  
4. Tests + threat model note  

### OUT

- Month buckets  
- Cross-campaign portfolio  
- Revenue ROI / LTV  
- Charting libraries  

### Acceptance (PR-3)

- [x] `bucket=week` returns Monday-start UTC week rows with same metrics as day mode  
- [x] Invalid `bucket` → 422  
- [x] UI toggle Day / Week reloads cohorts  
- [x] No new ledger / no GET side effects  

---

## Later backlog

- Month bucket granularity  
- Cross-campaign portfolio view  
- Revenue ROI once commercial outcome value contracts exist  

---

## History

- 2026-08-03: PR-2 ✅ #214; Product Track → **Stage 6 PR-3 week buckets**.  
- 2026-08-03: PR-1 ✅ #213; Product Track → Stage 6 PR-2 windowed cohorts.  
- 2026-08-03: Product Track → Stage 6 PR-1 Flight wave compare after Source Diagnostics PR9 ✅ #212.  
