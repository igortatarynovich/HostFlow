# Threat Model — Acquisition Source Diagnostics (PR1)

## Assets

- Read-only Marketing diagnostics HTTP surface  
  - `GET /api/v1/platform/marketing/diagnostics/submissions`  
  - `GET /api/v1/platform/marketing/diagnostics/submissions/{lead_id}`  
  (`backend/app/api/v1/platform/marketing_diagnostics.py` ·  
  `backend/app/acquisition/ops/source_diagnostics.py`)
- Marketing Diagnostics UI (`/app/marketing/diagnostics`) — list + case detail
- Composed views over existing SoT: **Lead** (`payload` / `normalized`) + **Acquisition Activity** timeline

## Trust boundaries

- Authenticated tenant operator → platform diagnostics read (JWT + `X-Tenant-Id` + RLS)
- Roles: administrator / supervisor / recruiter / client_manager / viewer / hr_officer / superadmin (`_READ`)
- Frontend Marketing page → browser session only; no write / replay / reprocess from this surface (PR1)
- Case detail may expose intake **payload** and **normalized** blocks to authorized operators (ops need)

## Угрозы

| ID | Угроза | Вектор |
|----|--------|--------|
| ASD-1 | Cross-tenant lead / activity read | Missing tenant filter / RLS bypass on list or case GET |
| ASD-2 | Cross-tenant Activity join | Timeline fetched by `submission_id` without tenant scope |
| ASD-3 | Privilege escalation via “repair” | Treating Diagnostics as a write / replay / mapping mutate path |
| ASD-4 | Side-effect on read | GET appending Activity or mutating Lead / Campaign / Flight |
| ASD-5 | Parallel SoT / second ledger | New submissions table forking routing or mapping engines |
| ASD-6 | Excess PII exposure outside RBAC | Case JSON returned without authenticated tenant-scoped `_READ` |

## Митигации (PR1)

- List filters `Lead.tenant_id` + presence of `acquisition_routing_v1` in `normalized`
- Case loads Lead by `tenant_id` + `lead_id`; Activity via existing tenant-scoped `list_activity_events`
- Endpoints are `_READ` only; no replay / export / mapping write in this slice
- No Activity emit and no Lead mutation on GET
- Reuses Lead + Acquisition Activity — no new submissions store
- No new public / unauthenticated surfaces

## Тесты

- `backend/tests/api/test_marketing_diagnostics.py`
- `hostflow-frontend/src/app/__tests__/marketingDiagnosticsRoute.test.ts`

## Связанные спеки

- [`docs/specs/tasks/acquisition-source-diagnostics.md`](../../specs/tasks/acquisition-source-diagnostics.md)
- [`docs/security/threat-models/acquisition-marketing-sources.md`](./acquisition-marketing-sources.md)
- [`docs/security/threat-models/acquisition-activity-timeline.md`](./acquisition-activity-timeline.md)
