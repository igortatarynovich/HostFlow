# Threat Model — Acquisition Source Diagnostics (PR1–PR5)

## Assets

- Read-only Marketing diagnostics HTTP surface  
  - `GET /api/v1/platform/marketing/diagnostics/submissions`  
    (optional filters: `source`, `flight_id`, `failed_only`)  
  - `GET /api/v1/platform/marketing/diagnostics/submissions/{lead_id}`  
  (`backend/app/api/v1/platform/marketing_diagnostics.py` ·  
  `backend/app/acquisition/ops/source_diagnostics.py`)
- Ingest stamp `mapping_applied_v1` on Lead.normalized (Meta/webhook reprocess paths)  
  (`backend/app/acquisition/mapping_applied_stamp.py`)
- Marketing Diagnostics UI — list / case / filters / duplicate / Mapping Health / drift

## Trust boundaries

- Authenticated tenant operator → platform diagnostics read (JWT + `X-Tenant-Id` + RLS)
- Roles: administrator / supervisor / recruiter / client_manager / viewer / hr_officer / superadmin (`_READ`)
- Frontend Marketing page → browser session only; no write / replay / reprocess from this surface
- Mapping stamp is written only on authorized ingest / reprocess paths (not on Diagnostics GET)
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
| ASD-7 | Filter bypass / enumeration | `flight_id` / `source` filters used to probe other tenants |
| ASD-8 | Cross-tenant Source mapping read | Resolving `intake_source_profile_id` without tenant scope |
| ASD-9 | Tampered mapping stamp | Client-supplied fingerprint without ingest authority |

## Митигации (PR1–PR5)

- List / case tenant-scoped; filters AND-narrowing; UUID validation on `flight_id`
- Mapping compose uses tenant-scoped Sources façade; missing profile → `profile_missing`
- `mapping_applied_v1` written only in server ingest/reprocess after validated rules
- Drift is a read-time comparison of fingerprints — no auto remapping
- Endpoints remain `_READ` only on Diagnostics; no replay/export in this slice
- No new public / unauthenticated surfaces

## Тесты

- `backend/tests/api/test_marketing_diagnostics.py`
- `backend/tests/acquisition/test_mapping_applied_stamp.py`
- `hostflow-frontend/src/app/__tests__/marketingDiagnosticsRoute.test.ts`

## Связанные спеки

- [`docs/specs/tasks/acquisition-source-diagnostics.md`](../../specs/tasks/acquisition-source-diagnostics.md)
- [`docs/security/threat-models/acquisition-marketing-sources.md`](./acquisition-marketing-sources.md)
- [`docs/security/threat-models/acquisition-activity-timeline.md`](./acquisition-activity-timeline.md)
