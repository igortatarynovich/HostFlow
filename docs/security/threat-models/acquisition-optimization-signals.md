# Threat Model — Acquisition Optimization Signals (Stage 5 PR-1)

## Assets

- Read-only Flight optimization HTTP surface  
  `GET /api/v1/platform/campaigns/{campaign_id}/flights/{flight_id}/optimization`
- Composition of Stage 4 runtime snapshot + windowed Timeline counters  
  (`backend/app/acquisition/ops/optimization_signals.py`)
- Marketing detail UI banner that surfaces `suggest_pause` (display only)

## Trust boundaries

- Authenticated tenant operator → platform optimization read (JWT + `X-Tenant-Id` + RLS)
- Company-scoped roles → may only read optimization for campaigns bound to their company
- Frontend Marketing page → browser session only; recommendation is advisory, not a write path

## Угрозы

| ID | Угроза | Вектор |
|----|--------|--------|
| AOS-1 | Cross-tenant optimization read | Missing tenant filter / RLS bypass on GET optimization |
| AOS-2 | Cross-company IDOR inside tenant | Operator reading another company's flight optimization |
| AOS-3 | Privilege escalation via “recommendation” | Treating `suggest_pause` as an implicit write / auto-pause |
| AOS-4 | Side-effect on read | GET appending Activity or mutating Campaign/Flight status |
| AOS-5 | Metric forgery / second ledger | Inventing unscoped KPI store outside Timeline + Stage 4 runtime |

## Митигации (Stage 5 PR-1)

- Reuses Stage 4 runtime ownership / company-scope checks (`get_flight_runtime_snapshot`)
- Windowed Timeline counts always filter by `tenant_id` + campaign + flight
- Endpoint is `_READ` only; no Launch/Pause/Resume/Complete from this path
- No Activity emit on GET; repeat GET must not change Timeline row count
- Signal may only explain/recommend — operator pauses via existing Stage 4 commands
- No new public/unauthenticated surfaces

## Тесты

- `backend/tests/api/test_stage_5_pr1_optimization_signals.py`

## Связанные спеки

- [`docs/specs/tasks/acquisition-stage-5-optimization.md`](../../specs/tasks/acquisition-stage-5-optimization.md)
- [`docs/security/threat-models/acquisition-flight-runtime.md`](./acquisition-flight-runtime.md)
- [`docs/security/threat-models/acquisition-activity-timeline.md`](./acquisition-activity-timeline.md)
