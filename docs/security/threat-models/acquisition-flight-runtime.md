# Threat Model — Acquisition Flight Runtime (Stage 4)

## Assets

- Platform campaign / flight HTTP surface (`backend/app/api/v1/platform/campaigns.py`)
- Campaign lifecycle transitions (`complete`, `archive`; no free-form status PATCH)
- Flight dispatch / delivery failure signals (`DeliveryErrorOccurred`)
- Live Intake Monitor + flight runtime KPI read models (tenant-scoped)
- Operator Marketing detail UI calling the same platform contracts

## Trust boundaries

- Authenticated tenant operator → platform campaign/flight APIs (JWT + `X-Tenant-Id` + RLS)
- Company-scoped roles → may only see/act on campaigns bound to their company
- Dispatcher / outbox worker → append Acquisition activity events (same tenant transaction)
- Frontend Marketing pages → browser session only; no service-role keys

## Угрозы

| ID | Угроза | Вектор |
|----|--------|--------|
| AFR-1 | Cross-tenant campaign/flight read or mutate | Missing tenant filter / RLS bypass on platform routes |
| AFR-2 | Cross-company IDOR inside tenant | Operator without company scope reading another company's campaign |
| AFR-3 | Unauthorized lifecycle transition | Calling `complete` / `archive` without RBAC or from wrong status |
| AFR-4 | Status smuggling via free PATCH | Setting `status` through generic update instead of commands |
| AFR-5 | Delivery-error event forgery / leak | Emitting or reading `DeliveryErrorOccurred` outside owning tenant |
| AFR-6 | Monitor/KPI bulk disclosure | Unscoped list/cursor leaking other tenants' intake rows |

## Митигации (Stage 4)

- All platform campaign routes resolve tenant from session; DB RLS on Acquisition tables
- Company-scope enforcement + tests (`test_stage_4_pr5_rbac_company_scope.py`)
- Status changes only via explicit commands (`complete` / `archive`); free status PATCH rejected
- `DeliveryErrorOccurred` emitted from dispatcher fail path with tenant-scoped activity append
- Runtime read / Live Intake Monitor queries always filter by `tenant_id` (+ campaign/flight ownership)
- No new public/unauthenticated surfaces in Stage 4

## Тесты

- `backend/tests/api/test_stage_4_pr2_campaign_endpoint_hardening.py`
- `backend/tests/api/test_stage_4_pr3_runtime_read_monitor.py`
- `backend/tests/api/test_stage_4_pr5_rbac_company_scope.py`
- `backend/tests/api/test_stage_4_pr5_dispatch_delivery_error.py`

## Связанные спеки

- [`docs/specs/tasks/acquisition-stage-4-flight-runtime.md`](../../specs/tasks/acquisition-stage-4-flight-runtime.md)
- [`docs/security/threat-models/acquisition-activity-timeline.md`](./acquisition-activity-timeline.md)
- [`docs/security/security-ssot.md`](../security-ssot.md) (RLS / tenant context)
