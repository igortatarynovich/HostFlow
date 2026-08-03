# Acquisition Stage 6 — Analytics

**Status:** **PR-1 DONE** ✅ [#213](https://github.com/igortatarynovich/HostFlow/pull/213) · **PR-2 IN PROGRESS**  
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
| **6** | Analytics | Decide | **PR-1 DONE** · **PR-2 active** |

---

## PR sequence

| PR | Scope | Status |
|----|--------|--------|
| **PR-1** | Flight wave **compare** within a Campaign (read-only compose over 3D KPI + Flight identity) | **DONE** (#213) |
| **PR-2** | Windowed **day cohorts** + CAC proxy (`cost_per_outcome`) from attribution/spend/outcome timestamps | **Active** |
| **PR-3+** | Cross-campaign portfolio / week buckets / revenue ROI | Not opened |

**Hard ban (Stage 6):** new metrics ledger tables; Timeline as dashboard SoT; auto-pause / Runtime writes from analytics; Forms/BI ownership of KPI; ad-provider spend sync as new SoT.

---

## PR-1 — Flight wave compare ✅ #213

### Acceptance (PR-1)

- [x] Authenticated `_READ` compare endpoint; company scope same as Campaign KPI  
- [x] Reuses `aggregate_campaign_kpi` — no parallel KPI store  
- [x] UI shows per-flight spend / leads / CPL + best-CPL marker when ≥2 flights  
- [x] Repeat GET has no write / Activity side effects  

---

## PR-2 — Windowed day cohorts + CAC proxy

### IN

1. Tenant + company-scoped read compose: UTC day buckets over a capped window (`window_days`, default 14, max 90)  
2. Per bucket from existing SoT only:  
   - **leads** — unique Attribution `(result_type, result_id)` by `created_at`  
   - **spend** — sum of `CampaignFlightSpendEntry.amount` by `created_at`  
   - **outcomes_completed** — Outcomes with `status=completed` by `completed_at` (fallback `created_at`)  
   - **cost_per_lead** / **cost_per_outcome** (CAC proxy) via same Decimal ratio rules as 3D KPI  
3. HTTP: `GET /api/v1/platform/campaigns/{campaign_id}/analytics/cohorts?window_days=`  
4. Thin Marketing Campaign Detail cohort strip (table; no charting library)  
5. Tests + threat model update  

### OUT

- Revenue ROI / LTV  
- Week/month buckets (later)  
- Cross-campaign portfolio  
- Ad-provider spend sync  
- New Activity events on GET  
- Charting libraries / export BI  

### Acceptance (PR-2)

- [x] Authenticated `_READ` cohorts endpoint; company scope same as Campaign KPI  
- [x] No parallel KPI store — buckets from Attribution / Spend / Outcome rows only  
- [x] UI shows day series + window totals including CPL / cost_per_outcome  
- [x] Repeat GET has no write / Activity side effects  

---

## Later backlog

- Week / month bucket granularity  
- Cross-campaign portfolio view  
- Revenue ROI once commercial outcome value contracts exist  

---

## History

- 2026-08-03: PR-1 ✅ #213; Product Track → **Stage 6 PR-2 windowed cohorts**.  
- 2026-08-03: Product Track → Stage 6 PR-1 Flight wave compare after Source Diagnostics PR9 ✅ #212.  
