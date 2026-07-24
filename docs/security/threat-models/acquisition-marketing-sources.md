# Threat Model — Marketing Sources (Acquisition UI Cutover C-3 / C-4)

## Assets

- Read-only Sources inventory HTTP surface  
  `GET /api/v1/platform/marketing/sources`
- Aggregation of existing IntakeSourceProfile, bindings, Campaign/Flight links, Meta webhook/credential signals, mapping_rules, Activity last submission/error, and `needs_routing` waiting projection  
  (`backend/app/acquisition/sources_read.py`)
- Marketing Sources UI (`/app/marketing/sources`) — display + deep-links only
- Campaign Detail Source cards compose (Acquisition UI PR2) — human-readable fields on existing Campaign read  
  (`GET /api/v1/platform/campaigns/{id}` via `_campaign_out` + `backend/app/acquisition/campaign_source_cards.py`)
- **C-4 sample / discovery façade** (`backend/app/acquisition/sources_sample.py`)  
  - `GET /api/v1/platform/marketing/sources/{source_id}/sample`  
  - `POST …/sample/from-payload`  
  - `POST …/sample/capture-next`  
  - `POST …/sample/preview`  
  - Discovery state under `publication_config_v1.mapping_discovery_v1` (sample blob + capture-next arm; policy resolver ignores unknown keys)

## Trust boundaries

- Authenticated tenant operator → platform Sources read (JWT + `X-Tenant-Id` + RLS)
- Frontend Marketing Sources page → browser session only; CTAs navigate to existing setup/mapping/settings paths
- Campaign Detail Source cards → same authenticated Campaign read; no new public surface
- C-4 sample write/preview → administrator / supervisor / superadmin only (`_WRITE`); sample GET uses existing `_READ` roles
- No public/unauthenticated surface in this slice

## Угрозы

| ID | Угроза | Вектор |
|----|--------|--------|
| MS-1 | Cross-tenant Sources leak | Missing tenant filter / RLS bypass on GET sources |
| MS-2 | Privilege escalation via write | Treating read projection as a mutation / reprocess path |
| MS-3 | Side-effect on read | GET mutating Lead / Campaign / Flight or emitting Activity |
| MS-4 | PII over-exposure in list | Dumping raw Meta payloads / field values into Sources rows |
| MS-5 | Spoofed “waiting” reason | Client inventing `missing_campaign_flight` without server projection |
| MS-6 | Technical ID / form metadata leak beyond need | Campaign Detail cards exposing Meta form/page IDs or raw payloads as primary UI |
| MS-7 | Cross-tenant sample / preview | `source_id` from another tenant on sample endpoints |
| MS-8 | Preview creates production entities | Dry-run path calling test-ingest / process_normalized_lead |
| MS-9 | PII over-exposure in discovery UI | Returning unmasked email/phone/name samples or full raw payload |
| MS-10 | Oversized / hostile paste payload | Mode C JSON paste DoS or unexpected normalizer input |

## Митигации (C-3)

- List endpoint is **GET-only**; no Sources list write API
- Aggregation always filters by `tenant_id` from `get_db_with_tenant`
- RBAC via existing platform read roles (`require_roles` on the router)
- Projection exposes counts, timestamps, Ad ID, routing issue **code/message**, and SPA deep-links — not raw submission payloads
- Waiting / routing issue fields are server-derived from Lead + bindings; UI does not invent reasons

## Митигации (C-4)

- All sample endpoints load `IntakeSourceProfile` by `(tenant_id, source_id)` → **404** cross-tenant
- `sample/preview` uses `normalize_meta_payload` only; response includes `creates_entities=false`; no Lead/Candidate/Application INSERT
- UI-facing samples go through `mask_sample_value` / `mask_payload_for_ui`
- Paste path enforces JSON object + size cap (`MAX_PASTE_BYTES`)
- Capture-next only arms TTL metadata; lazy sample seed on GET may persist discovery state **without** creating funnel entities
- Mapping persist / routing preview remain C-5 — not exposed here

## Follow-up surface — FlightAdBinding (runtime)

- Write: `POST/PATCH/DELETE /api/v1/platform/campaigns/.../ad-bindings`
- Assets: `acq_flight_ad_bindings` (tenant + provider + provider_ad_id unique when active)
- Threats: cross-tenant Ad bind, binding forging another company's Flight, unbounded reprocess storm
- Mitigations: campaign company-scope + `_WRITE` roles; Flight must belong to Campaign/tenant; auto-reprocess limited to `missing_campaign_flight` + exact Ad ID + no Candidate; webhook never creates bindings

## Follow-up surface — Campaign Detail Source cards (UI PR2)

**What is read (composed, not stored in Acquisition):**

| Field | Source of truth |
|-------|-----------------|
| `display_title` / `lead_form_name` | `MetaLeadFormMapping.form_name`, binding label, or profile name (technical `Meta form {id}` stripped when possible) |
| `page_id` / `page_name` | Binding `external_key_secondary` / mapping `page_id`; `page_name` only if present in SoT (no live Graph call) |
| `binding_status`, `active_binding_count`, `profile_is_active` | `IntakeSourceBinding` + `IntakeSourceProfile` |
| Form `publication_status`, `is_public`, `form_is_active` | `TenantLeadForm` |
| `last_submission_at` | Latest `SubmissionReceived` / `LeadCreated` on form or intake_source endpoint in Activity Timeline |

**Security properties:**

- Still **read-only** compose inside existing Campaign GET — no new tables, no write path, no reprocess
- Tenant-scoped JOINs only; no cross-tenant Meta mapping / Form / Activity reads
- Does **not** return raw Meta lead payloads, field mapping sample values, or PII from submissions
- Technical IDs (`form_id`, `meta_form_id`, `page_id`, profile id) are secondary; UI keeps them behind «Подробнее»
- OAuth credentials remain Integrations SoT — cards never embed tokens

## Тесты

- `backend/tests/api/test_acquisition_c3_marketing_sources.py`
- `backend/tests/api/test_acquisition_c4_source_sample.py`
- `backend/tests/api/test_acquisition_flight_ad_binding.py`
- `backend/tests/acquisition/test_campaign_source_cards.py`
- `hostflow-frontend/src/app/__tests__/acquisitionC3SourcesScopeScan.test.ts`
- `hostflow-frontend/src/pages/marketing/__tests__/sourceCardPresentation.test.ts`

## Связанные спеки

- [`docs/specs/tasks/acquisition-ui-cutover.md`](../../specs/tasks/acquisition-ui-cutover.md)
- [`docs/specs/tasks/acquisition-ui-cutover-c4-test-lead-field-discovery.md`](../../specs/tasks/acquisition-ui-cutover-c4-test-lead-field-discovery.md)
- [`docs/security/threat-models/acquisition-activity-timeline.md`](./acquisition-activity-timeline.md)
- [`docs/security/threat-models/acquisition-flight-runtime.md`](./acquisition-flight-runtime.md)
