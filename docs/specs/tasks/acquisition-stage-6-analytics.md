# Acquisition Stage 6 — Analytics

**Status:** **PR-1 IN PROGRESS** (Product Track)  
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
| **6** | Analytics | Decide | **PR-1 active** |

---

## PR sequence

| PR | Scope | Status |
|----|--------|--------|
| **PR-1** | Flight wave **compare** within a Campaign (read-only compose over 3D KPI + Flight identity) | **Active** |
| **PR-2+** | Cohorts / cross-campaign compare / ROI–CAC with richer spend SoT | Not opened |

**Hard ban (Stage 6):** new metrics ledger tables; Timeline as dashboard SoT; auto-pause / Runtime writes from analytics; Forms/BI ownership of KPI.

---

## PR-1 — Flight wave compare

### IN

1. Tenant + company-scoped read compose: all Flights of a Campaign with identity (`code`, `name`, `status`, `is_current`) + 3D KPI fields  
2. Relative decision helpers: `lead_share`, `cpl_delta` vs campaign CPL, `is_best_cpl` among flights with defined CPL  
3. HTTP: `GET /api/v1/platform/campaigns/{campaign_id}/analytics/flight-compare`  
4. Thin Marketing Campaign Detail UI table (compare, not ops substitute)  
5. Tests + threat model  

### OUT

- ROI / CAC / LTV modeling  
- Cohorts / date-bucket series  
- Cross-campaign dashboards  
- Ad-provider spend sync as new SoT  
- New Activity events on GET  
- Charting libraries / export BI  

### Acceptance (PR-1)

- [x] Authenticated `_READ` compare endpoint; company scope same as Campaign KPI  
- [x] Reuses `aggregate_campaign_kpi` — no parallel KPI store  
- [x] UI shows per-flight spend / leads / CPL + best-CPL marker when ≥2 flights  
- [x] Repeat GET has no write / Activity side effects  

---

## Later backlog

- Windowed / cohort compare  
- Cross-campaign portfolio view  
- ROI / CAC once spend + outcome cost contracts expand  

---

## History

- 2026-08-03: Product Track → **Stage 6 PR-1 Flight wave compare** after Source Diagnostics PR9 ✅ #212.  
