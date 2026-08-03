# Threat Model — Acquisition Stage 6 Analytics (PR-1…PR-4)

## Assets

- Read-only Flight wave compare  
  - `GET /api/v1/platform/campaigns/{campaign_id}/analytics/flight-compare`  
- Read-only windowed day/week cohorts + CAC proxy (`cost_per_outcome`)  
  - `GET /api/v1/platform/campaigns/{campaign_id}/analytics/cohorts?window_days=&bucket=day|week`  
- Read-only company portfolio  
  - `GET /api/v1/platform/campaigns/analytics/portfolio?limit=`  
  (`backend/app/api/v1/platform/campaigns.py` ·  
  `backend/app/acquisition/ops/flight_compare.py` ·  
  `backend/app/acquisition/ops/cohort_analytics.py` ·  
  `backend/app/acquisition/ops/portfolio_analytics.py`)
- Marketing Campaign Detail compare/cohort tables + Marketing list portfolio strip (SPA)

## Trust boundaries

- Authenticated tenant operator → platform campaigns read (JWT + `X-Tenant-Id` + company scope + RLS)
- Roles: same `_READ` as Campaign KPI endpoints
- No write path; no Activity append on GET
- Cohort window capped (1–90 days); UTC day or Monday-start week buckets
- Portfolio campaign scan capped (`limit` ≤ 100)

## Угрозы

| ID | Угроза | Вектор |
|----|--------|--------|
| S6-1 | Cross-tenant / cross-company KPI leak | Missing company scope on analytics GET |
| S6-2 | Parallel metrics ledger | New analytics tables forking 3D KPI |
| S6-3 | Side-effect on read | GET mutating Campaign / Flight / Activity |
| S6-4 | Analytics as Runtime control | Treating compare/cohorts/portfolio as authority to pause/launch |
| S6-5 | Unbounded historical / portfolio scan | Large `window_days` or uncapped portfolio DoS |

## Митигации (PR-1…PR-4)

- `get_campaign` / `list_campaigns` company scope before compose
- Compare/portfolio reuse `aggregate_campaign_kpi`; cohorts read Attribution / Spend / Outcome only
- `window_days` Query ge=1 le=90; portfolio `limit` ge=1 le=100
- Read-only HTTP; UI display-only
- Timeline remains SoT for audit; analytics is decision aid only
- No revenue ROI inventing commercial value outside Outcome contract

## Тесты

- `backend/tests/api/test_stage_6_pr1_flight_compare.py`
- `backend/tests/api/test_stage_6_pr2_cohort_analytics.py`
- `backend/tests/api/test_stage_6_pr4_portfolio.py`

## Связанные спеки

- [`docs/specs/tasks/acquisition-stage-6-analytics.md`](../../specs/tasks/acquisition-stage-6-analytics.md)
- [`docs/security/threat-models/acquisition-optimization-signals.md`](./acquisition-optimization-signals.md)
