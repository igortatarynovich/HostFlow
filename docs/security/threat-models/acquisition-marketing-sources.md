# Threat Model — Marketing Sources (Acquisition UI Cutover C-3 / C-4 / C-5)

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
- **C-5 mapping / routing-preview façade** (`backend/app/acquisition/sources_mapping.py`)  
  - `GET /api/v1/platform/marketing/sources/{source_id}/mapping`  
  - `PUT …/mapping` (writes `IntakeSourceProfile.mapping_rules` only)  
  - `POST …/mapping/routing-preview` (dry-run; `creates_entities=false`)
  - Marketing Mapping UI (`/app/marketing/sources/:sourceId/mapping`)

## Trust boundaries

- Authenticated tenant operator → platform Sources read (JWT + `X-Tenant-Id` + RLS)
- Frontend Marketing Sources page → browser session only; CTAs navigate to existing setup/mapping/settings paths
- Campaign Detail Source cards → same authenticated Campaign read; no new public surface
- C-4 sample write/preview → administrator / supervisor / superadmin only (`_WRITE`); sample GET uses existing `_READ` roles
- C-5 mapping PUT + routing-preview → same `_WRITE` roles; mapping GET uses `_READ`
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
| MS-11 | Cross-tenant mapping read/write | `source_id` from another tenant on mapping endpoints |
| MS-12 | Mapping PUT invents parallel SoT | Writing rules outside `IntakeSourceProfile.mapping_rules` |
| MS-13 | Routing preview creates funnel entities | Preview path inserting Candidate / Application / Lead |

## Митигации (C-3)

- List endpoint is **GET-only**; no Sources list write API
- Aggregation always filters by `tenant_id` from `get_db_with_tenant`
- RBAC via existing platform read roles (`require_roles` on the router)
- Projection exposes counts, timestamps, Ad ID, routing issue **code/message**, and SPA deep-links — not raw submission payloads
- Waiting / routing issue fields are server-derived from Lead + bindings; UI does not invent reasons

## Follow-up surface — C-3.1 Sources list column completeness

**Additive read fields on the same GET Sources list** (still no write API):

| Field | Source of truth |
|-------|-----------------|
| `page_id` / `page_name` | Same donor as Campaign Detail cards — `campaign_source_cards.parse_meta_page_id` / mapping `page_id`; `page_name` only if present in SoT (**no** live Graph call in C-3.1) |
| `provider_form` | `humanize_meta_profile_name` + `MetaLeadFormMapping.form_name` / binding label / HostFlow form `title` |
| `destination` / `destination_label` | `IntakeSourceProfile.route_intent` (+ `lead_target_type` fallback) via `compute_destination` — no parallel destination registry |

**Security properties:**

- Remains **GET-only**; tenant filter + RLS unchanged
- Does **not** expose raw Meta payloads or mapping sample values
- Does **not** invent account/portfolio labels without SoT (column stays deferred)

## Митигации (C-4)

- All sample endpoints load `IntakeSourceProfile` by `(tenant_id, source_id)` → **404** cross-tenant
- `sample/preview` uses `normalize_meta_payload` only; response includes `creates_entities=false`; no Lead/Candidate/Application INSERT
- UI-facing samples go through `mask_sample_value` / `mask_payload_for_ui`
- Paste path enforces JSON object + size cap (`MAX_PASTE_BYTES`)
- Capture-next only arms TTL metadata; lazy sample seed on GET may persist discovery state **without** creating funnel entities

## Митигации (C-5)

- Mapping GET/PUT/routing-preview load profile by `(tenant_id, source_id)` → **404** cross-tenant
- PUT writes only `IntakeSourceProfile.mapping_rules` (enriched via existing `enrich_mapping_rules_for_storage`) — no Meta form mapping overwrite, no new registry
- Routing preview reuses C-4 `preview_source_sample` + destination/health projection; response forces `creates_entities=false`
- Unmapped / empty rules → `needs_review=true` (no silent drop in preview note + `unmapped_fields`)
- `_WRITE` required for PUT and routing-preview; `_READ` for GET

## Follow-up surface — Connect Source Meta picker enrichment

**Surface:** `GET /api/v1/platform/campaigns/intake-source-options` (+ Marketing Connect Source UI)

| Concern | Mitigation |
|---------|------------|
| Cross-tenant options | Same company-scoped profile list as before |
| Graph hydrate | Uses existing **page access tokens** only; fail-soft if Graph denies; no tokens in API response |
| Cache `form_name` | Writes `MetaLeadFormMapping.form_name` only — must **not** wipe `mapping_rules` |
| PII | Returns form/page/ad **names** and IDs — not lead field samples |

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
- `backend/tests/api/test_acquisition_c5_source_mapping.py`
- `backend/tests/api/test_acquisition_flight_ad_binding.py`
- `backend/tests/acquisition/test_campaign_source_cards.py`
- `hostflow-frontend/src/app/__tests__/acquisitionC3SourcesScopeScan.test.ts`
- `hostflow-frontend/src/app/__tests__/acquisitionC4TestLeadUiScan.test.ts`
- `hostflow-frontend/src/app/__tests__/acquisitionC5MappingUiScan.test.ts`
- `hostflow-frontend/src/pages/marketing/__tests__/sourceCardPresentation.test.ts`

## Связанные спеки

- [`docs/specs/tasks/acquisition-ui-cutover.md`](../../specs/tasks/acquisition-ui-cutover.md)
- [`docs/specs/tasks/acquisition-ui-cutover-c4-test-lead-field-discovery.md`](../../specs/tasks/acquisition-ui-cutover-c4-test-lead-field-discovery.md)
- [`docs/specs/tasks/acquisition-ui-cutover-c5-mapping-workspace.md`](../../specs/tasks/acquisition-ui-cutover-c5-mapping-workspace.md)
- [`docs/security/threat-models/acquisition-activity-timeline.md`](./acquisition-activity-timeline.md)
- [`docs/security/threat-models/acquisition-flight-runtime.md`](./acquisition-flight-runtime.md)
