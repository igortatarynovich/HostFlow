# Threat Model — Acquisition Stage 6 Analytics (PR-1 Flight compare)

## Assets

- Read-only Flight wave compare HTTP surface  
  - `GET /api/v1/platform/campaigns/{campaign_id}/analytics/flight-compare`  
  (`backend/app/api/v1/platform/campaigns.py` ·  
  `backend/app/acquisition/ops/flight_compare.py`)
- Compose over Stage 3D KPI aggregates + Flight identity (`code` / `name` / `status`)
- Marketing Campaign Detail compare table (SPA)

## Trust boundaries

- Authenticated tenant operator → platform campaigns read (JWT + `X-Tenant-Id` + company scope + RLS)
- Roles: same `_READ` as Campaign KPI endpoints
- No write path; no Activity append on GET

## Угрозы

| ID | Угроза | Вектор |
|----|--------|--------|
| S6-1 | Cross-tenant / cross-company KPI leak | Missing company scope on compare GET |
| S6-2 | Parallel metrics ledger | New analytics tables forking 3D KPI |
| S6-3 | Side-effect on read | GET mutating Campaign / Flight / Activity |
| S6-4 | Analytics as Runtime control | Treating compare as authority to pause/launch |

## Митигации (PR-1)

- `get_campaign` company scope before compose (404 cross-company)
- Reuses `aggregate_campaign_kpi` only — no new KPI store
- Read-only HTTP; UI is display-only
- Timeline remains SoT for audit; compare is decision aid only

## Тесты

- `backend/tests/api/test_stage_6_pr1_flight_compare.py`

## Связанные спеки

- [`docs/specs/tasks/acquisition-stage-6-analytics.md`](../../specs/tasks/acquisition-stage-6-analytics.md)
- [`docs/security/threat-models/acquisition-optimization-signals.md`](./acquisition-optimization-signals.md)
