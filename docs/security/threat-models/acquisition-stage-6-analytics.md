# Threat Model — Acquisition Stage 6 Analytics (PR-1 compare · PR-2 cohorts)

## Assets

- Read-only Flight wave compare  
  - `GET /api/v1/platform/campaigns/{campaign_id}/analytics/flight-compare`  
- Read-only windowed day cohorts + CAC proxy (`cost_per_outcome`)  
  - `GET /api/v1/platform/campaigns/{campaign_id}/analytics/cohorts?window_days=`  
  (`backend/app/api/v1/platform/campaigns.py` ·  
  `backend/app/acquisition/ops/flight_compare.py` ·  
  `backend/app/acquisition/ops/cohort_analytics.py`)
- Marketing Campaign Detail compare + cohort tables (SPA)

## Trust boundaries

- Authenticated tenant operator → platform campaigns read (JWT + `X-Tenant-Id` + company scope + RLS)
- Roles: same `_READ` as Campaign KPI endpoints
- No write path; no Activity append on GET
- Cohort window capped (1–90 days); UTC day buckets only in PR-2

## Угрозы

| ID | Угроза | Вектор |
|----|--------|--------|
| S6-1 | Cross-tenant / cross-company KPI leak | Missing company scope on analytics GET |
| S6-2 | Parallel metrics ledger | New analytics tables forking 3D KPI |
| S6-3 | Side-effect on read | GET mutating Campaign / Flight / Activity |
| S6-4 | Analytics as Runtime control | Treating compare/cohorts as authority to pause/launch |
| S6-5 | Unbounded historical scan | Large `window_days` DoS / PII volume via cohorts |

## Митигации (PR-1 · PR-2)

- `get_campaign` company scope before compose (404 cross-company)
- Compare reuses `aggregate_campaign_kpi`; cohorts read Attribution / Spend / Outcome only
- `window_days` Query ge=1 le=90
- Read-only HTTP; UI display-only
- Timeline remains SoT for audit; analytics is decision aid only
- No revenue ROI inventing commercial value outside Outcome contract

## Тесты

- `backend/tests/api/test_stage_6_pr1_flight_compare.py`
- `backend/tests/api/test_stage_6_pr2_cohort_analytics.py`

## Связанные спеки

- [`docs/specs/tasks/acquisition-stage-6-analytics.md`](../../specs/tasks/acquisition-stage-6-analytics.md)
- [`docs/security/threat-models/acquisition-optimization-signals.md`](./acquisition-optimization-signals.md)
