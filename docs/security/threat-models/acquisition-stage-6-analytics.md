# Threat Model — Acquisition Stage 6 Analytics (PR-1…PR-6)

## Assets

- Read-only Flight wave compare  
  - `GET /api/v1/platform/campaigns/{campaign_id}/analytics/flight-compare`  
- Read-only windowed day/week/month cohorts + CAC proxy (`cost_per_outcome`) + ROI  
  - `GET /api/v1/platform/campaigns/{campaign_id}/analytics/cohorts?window_days=&bucket=day|week|month`  
- Read-only company portfolio (+ ROI)  
  - `GET /api/v1/platform/campaigns/analytics/portfolio?limit=`  
  (`backend/app/api/v1/platform/campaigns.py` ·  
  `backend/app/acquisition/ops/flight_compare.py` ·  
  `backend/app/acquisition/ops/cohort_analytics.py` ·  
  `backend/app/acquisition/ops/portfolio_analytics.py` ·  
  `backend/app/acquisition/kpi_aggregates.py`)
- Outcome commercial value snapshot (PR-6a)  
  - `PUT|GET /api/v1/platform/campaigns/{campaign_id}/outcomes/{outcome_id}/commercial-value`  
  (`backend/app/acquisition/contracts/outcome_commercial_value.py`)
- Marketing Campaign Detail compare/cohort/ROI tables + value declaration form + Marketing list portfolio strip (SPA)

## Trust boundaries

- Authenticated tenant operator → platform campaigns read (JWT + `X-Tenant-Id` + company scope + RLS)
- Roles: same `_READ` as Campaign KPI endpoints; value write uses `_WRITE`
- Analytics GETs: no write path; no Activity append on GET
- Commercial value write: only completed Outcomes; amount > 0; ISO currency; contract-only column writer
- ROI null when value missing or spend ≤ 0; mixed value/spend currencies → 422
- Cohort window capped (1–90 days); UTC day / Monday-start week / calendar month buckets
- Portfolio campaign scan capped (`limit` ≤ 100)

## Угрозы

| ID | Угроза | Вектор |
|----|--------|--------|
| S6-1 | Cross-tenant / cross-company KPI leak | Missing company scope on analytics GET |
| S6-2 | Parallel metrics ledger | New analytics tables forking 3D KPI |
| S6-3 | Side-effect on read | GET mutating Campaign / Flight / Activity |
| S6-4 | Analytics as Runtime control | Treating compare/cohorts/portfolio as authority to pause/launch |
| S6-5 | Unbounded historical / portfolio scan | Large `window_days` or uncapped portfolio DoS |
| S6-6 | Invented commercial value | Analytics compose inventing ROI amounts without Outcome contract |

## Митигации (PR-1…PR-6)

- `get_campaign` / `list_campaigns` company scope before compose
- Compare/portfolio reuse `aggregate_campaign_kpi`; cohorts read Attribution / Spend / Outcome only
- `window_days` Query ge=1 le=90; portfolio `limit` ge=1 le=100
- Read-only analytics HTTP; UI display-only for KPI surfaces
- Timeline remains SoT for audit; analytics is decision aid only
- Commercial value only via Outcome contract (`declared_v1`); no SalesOrder invent in analytics
- Value write scoped to campaign company; non-completed / invalid amount/currency → 422
- ROI formula locked: `(outcome_value − spend) / spend`

## Тесты

- `backend/tests/api/test_stage_6_pr1_flight_compare.py`
- `backend/tests/api/test_stage_6_pr2_cohort_analytics.py`
- `backend/tests/api/test_stage_6_pr4_portfolio.py`
- `backend/tests/api/test_stage_6_pr6a_outcome_commercial_value.py`
- `backend/tests/api/test_stage_6_pr6b_roi_compose.py`

## Связанные спеки

- [`docs/specs/tasks/acquisition-stage-6-analytics.md`](../../specs/tasks/acquisition-stage-6-analytics.md)
- [`docs/modules/acquisition/outcome-commercial-value-ownership.md`](../../modules/acquisition/outcome-commercial-value-ownership.md)
- [`docs/security/threat-models/acquisition-optimization-signals.md`](./acquisition-optimization-signals.md)
