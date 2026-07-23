# Threat Model — Marketing Sources (Acquisition UI Cutover C-3)

## Assets

- Read-only Sources inventory HTTP surface  
  `GET /api/v1/platform/marketing/sources`
- Aggregation of existing IntakeSourceProfile, bindings, Campaign/Flight links, Meta webhook/credential signals, mapping_rules, Activity last submission/error, and `needs_routing` waiting projection  
  (`backend/app/acquisition/sources_read.py`)
- Marketing Sources UI (`/app/marketing/sources`) — display + deep-links only

## Trust boundaries

- Authenticated tenant operator → platform Sources read (JWT + `X-Tenant-Id` + RLS)
- Frontend Marketing Sources page → browser session only; CTAs navigate to existing setup/mapping/settings paths
- No public/unauthenticated surface in this slice

## Угрозы

| ID | Угроза | Вектор |
|----|--------|--------|
| MS-1 | Cross-tenant Sources leak | Missing tenant filter / RLS bypass on GET sources |
| MS-2 | Privilege escalation via write | Treating read projection as a mutation / reprocess path |
| MS-3 | Side-effect on read | GET mutating Lead / Campaign / Flight or emitting Activity |
| MS-4 | PII over-exposure in list | Dumping raw Meta payloads / field values into Sources rows |
| MS-5 | Spoofed “waiting” reason | Client inventing `missing_campaign_flight` without server projection |

## Митигации (C-3)

- Endpoint is **GET-only**; no Sources write API in this PR
- Aggregation always filters by `tenant_id` from `get_db_with_tenant`
- RBAC via existing platform read roles (`require_roles` on the router)
- Projection exposes counts, timestamps, Ad ID, routing issue **code/message**, and SPA deep-links — not raw submission payloads
- Waiting / routing issue fields are server-derived from Lead + bindings; UI does not invent reasons
- Runtime ingest / `profile_default` / Ad→Flight binding **unchanged** in C-3 (separate runtime PR)

## Тесты

- `backend/tests/api/test_acquisition_c3_marketing_sources.py`
- `hostflow-frontend/src/app/__tests__/acquisitionC3SourcesScopeScan.test.ts`

## Связанные спеки

- [`docs/specs/tasks/acquisition-ui-cutover.md`](../../specs/tasks/acquisition-ui-cutover.md) (C-3 + locked Ad ID→Flight contract for follow-up)
- [`docs/security/threat-models/acquisition-activity-timeline.md`](./acquisition-activity-timeline.md)
- [`docs/security/threat-models/acquisition-flight-runtime.md`](./acquisition-flight-runtime.md)
