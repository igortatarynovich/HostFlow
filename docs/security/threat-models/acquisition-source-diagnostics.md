# Threat Model — Acquisition Source Diagnostics (PR1–PR8)

## Assets

- Read-only Marketing diagnostics HTTP surface  
  - `GET /api/v1/platform/marketing/diagnostics/submissions`  
    (optional filters: `source`, `flight_id`, `failed_only`, `drift_only`)  
  - `GET /api/v1/platform/marketing/diagnostics/submissions/{lead_id}`  
  - `GET /api/v1/platform/marketing/diagnostics/submissions/{lead_id}/export`  
    (JSON attachment of case compose; audited CLASS3 export)  
  (`backend/app/api/v1/platform/marketing_diagnostics.py` ·  
  `backend/app/acquisition/ops/source_diagnostics.py`)
- Ingest stamp `mapping_applied_v1` on Lead.normalized (Meta/webhook reprocess paths)  
  (`backend/app/acquisition/mapping_applied_stamp.py`)
- Marketing Diagnostics UI — list / case / filters / duplicate / Mapping Health / drift alerts / Export JSON / Replay CTA
- Replay CTA invokes existing Leads write: `POST /api/v1/leads/{lead_id}/process`  
  (`backend/app/modules/leads/router.py` · `reprocess_stored_lead_payload`)

## Trust boundaries

- Authenticated tenant operator → platform diagnostics read (JWT + `X-Tenant-Id` + RLS)
- Roles (Diagnostics GET): administrator / supervisor / recruiter / client_manager / viewer / hr_officer / superadmin (`_READ`)
- Replay is **not** a Diagnostics writer — UI calls Leads `process` (admin/manager/recruiter RBAC + existing audit/`manual_process` activity)
- Mapping stamp is written only on authorized ingest / reprocess paths (not on Diagnostics GET)
- Case detail and export may expose intake **payload** and **normalized** blocks to authorized operators (ops need)
- Export emits `export.requested` / `export.generated` / `export.denied` with `contains_class3=true`

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
| ASD-10 | Unaudited CLASS3 download | Export without export security events / actor attribution |
| ASD-11 | Drift filter as write / remap | Treating `drift_only` as authority to mutate mapping_rules |
| ASD-12 | Replay bypasses Leads RBAC | Fake Diagnostics writer that reprocesses without process roles |

## Митигации (PR1–PR8)

- List / case / export tenant-scoped; filters AND-narrowing; UUID validation on `flight_id` / `lead_id`
- Mapping compose uses tenant-scoped Sources façade; missing profile → `profile_missing`
- `mapping_applied_v1` written only in server ingest/reprocess after validated rules
- Drift is a read-time comparison of fingerprints — no auto remapping
- `drift_only` only narrows the read list (scan cap); does not mutate Lead / Source / Flight
- Diagnostics HTTP remains `_READ` only; export is read-only attachment (no remapping)
- Replay CTA uses existing `POST /leads/{id}/process` (Leads RBAC + `manual_process` audit) — no Diagnostics write route
- Export path emits `emit_export_security_event_v1` (`contains_class3`, single-lead scope, no bulk)
- No new public / unauthenticated surfaces

## Тесты

- `backend/tests/api/test_marketing_diagnostics.py`
- `backend/tests/acquisition/test_mapping_applied_stamp.py`
- `hostflow-frontend/src/app/__tests__/marketingDiagnosticsRoute.test.ts`

## Связанные спеки

- [`docs/specs/tasks/acquisition-source-diagnostics.md`](../../specs/tasks/acquisition-source-diagnostics.md)
- [`docs/security/threat-models/acquisition-marketing-sources.md`](./acquisition-marketing-sources.md)
- [`docs/security/threat-models/acquisition-activity-timeline.md`](./acquisition-activity-timeline.md)
