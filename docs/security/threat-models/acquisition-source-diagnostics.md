# Threat Model — Acquisition Source Diagnostics (PR1–PR3)

## Assets

- Read-only Marketing diagnostics HTTP surface  
  - `GET /api/v1/platform/marketing/diagnostics/submissions`  
    (optional filters: `source`, `flight_id`, `failed_only`)  
  - `GET /api/v1/platform/marketing/diagnostics/submissions/{lead_id}`  
    (includes composed `duplicate` from Lead decision / match stamps)  
  (`backend/app/api/v1/platform/marketing_diagnostics.py` ·  
  `backend/app/acquisition/ops/source_diagnostics.py`)
- Marketing Diagnostics UI (`/app/marketing/diagnostics`) — list + case detail + filter bar + duplicate panel
- Composed views over existing SoT: **Lead** (`payload` / `normalized` / `decision_result_v1` / `duplicate_match_v1`) + **Acquisition Activity** timeline

## Trust boundaries

- Authenticated tenant operator → platform diagnostics read (JWT + `X-Tenant-Id` + RLS)
- Roles: administrator / supervisor / recruiter / client_manager / viewer / hr_officer / superadmin (`_READ`)
- Frontend Marketing page → browser session only; no write / replay / reprocess / duplicate attach-create from this surface
- Case detail may expose intake **payload**, **normalized**, and duplicate match hints to authorized operators (ops need)
- List filters are query params only — they never widen tenant scope
- Duplicate **resolution** remains on CRM Lead (deep-link); Diagnostics explains only

## Угрозы

| ID | Угроза | Вектор |
|----|--------|--------|
| ASD-1 | Cross-tenant lead / activity read | Missing tenant filter / RLS bypass on list or case GET |
| ASD-2 | Cross-tenant Activity join | Timeline fetched by `submission_id` without tenant scope |
| ASD-3 | Privilege escalation via “repair” | Treating Diagnostics as a write / replay / mapping mutate / duplicate-decision path |
| ASD-4 | Side-effect on read | GET appending Activity or mutating Lead / Campaign / Flight |
| ASD-5 | Parallel SoT / second ledger | New submissions table forking routing or mapping engines |
| ASD-6 | Excess PII exposure outside RBAC | Case JSON returned without authenticated tenant-scoped `_READ` |
| ASD-7 | Filter bypass / enumeration | `flight_id` / `source` filters used to probe other tenants |

## Митигации (PR1–PR3)

- List filters `Lead.tenant_id` + presence of `acquisition_routing_v1` in `normalized`
- Optional filters (`source`, `flight_id`, `failed_only`) are AND-narrowing inside that tenant set
- `flight_id` validated as UUID (422 on invalid)
- Case loads Lead by `tenant_id` + `lead_id`; Activity via existing tenant-scoped `list_activity_events`
- Duplicate panel is compose-only from existing Lead stamps; no attach/create/ignore API on Diagnostics
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
