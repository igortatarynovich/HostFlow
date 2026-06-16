# Document Type Model: SQL/ORM Target Mapping

## Status
Proposed implementation spec (DB + ORM + migration plan).

## Scope
Concrete target mapping from current HostFlow models:
- `document_types` (tenant-scoped)
- `documents` (`doc_type` as free code)
- `document_policies`
- `document_ruleset_versions`

to canonical system reference + applicability packs + tenant enablement.

## Current Baseline (from code)
- `document_types` is tenant-scoped (`tenant_id`, `code`) and stores mixed concerns (identity + schema + behavior).
- `documents.doc_type` is a string, no FK to canonical type.
- `document_policies` references `document_types.id` (tenant row), not global canonical type.
- rulesets are versioned per tenant but not anchored to immutable canonical type versions.

## Target SQL Model

### 1) Canonical Type Core

#### `ref_document_types`
Canonical identity and high-level semantics.

Columns:
- `id uuid pk`
- `code varchar(128) not null unique`
- `public_name varchar(255) not null`
- `status varchar(24) not null` (`draft|active|deprecated`)
- `origin varchar(24) not null` (`system|tenant_custom|requested`)
- `category_code varchar(64) not null`
- `subcategory_code varchar(64) null`
- `criticality varchar(32) not null`
  (`informational|operational|required|compliance_critical|work_blocking`)
- `description text null`
- `created_at timestamptz not null default now()`
- `updated_at timestamptz not null default now()`

Indexes:
- `uq_ref_document_types_code (code)`
- `ix_ref_document_types_status (status)`
- `ix_ref_document_types_category (category_code, subcategory_code)`
- `ix_ref_document_types_criticality (criticality)`

#### `ref_document_type_i18n`
Localized names/titles.

Columns:
- `id uuid pk`
- `document_type_id uuid fk -> ref_document_types(id) on delete cascade`
- `locale varchar(16) not null`
- `public_name varchar(255) not null`
- `aliases jsonb not null default '[]'::jsonb`
- unique `(document_type_id, locale)`

#### `ref_document_type_versions`
Immutable version snapshots for legal/history compatibility.

Columns:
- `id uuid pk`
- `document_type_id uuid fk -> ref_document_types(id) on delete cascade`
- `version_code varchar(64) not null` (e.g. `2026.1`)
- `valid_from date not null`
- `valid_to date null`
- `deprecation_reason text null`
- `replacement_document_type_id uuid fk -> ref_document_types(id) on delete set null`
- `schema_json jsonb not null` (required fields schema)
- `expiry_rules_json jsonb not null`
- `automation_flags_json jsonb not null`
- `verification_profile_json jsonb not null`
- `stage_applicability_json jsonb not null`
- `position_applicability_json jsonb not null`
- `entity_applicability_json jsonb not null`
- `business_purposes_json jsonb not null`
- `status_model varchar(32) not null default 'evidence'`
- `created_at timestamptz not null default now()`
- `created_by varchar(36) null`

Constraints:
- unique `(document_type_id, version_code)`
- check `valid_to is null or valid_to >= valid_from`

Indexes:
- `ix_ref_doc_type_versions_doc (document_type_id)`
- `ix_ref_doc_type_versions_validity (valid_from, valid_to)`

### 2) Country/Legal Applicability

#### `ref_document_type_country_applicability`

Columns:
- `id uuid pk`
- `document_type_version_id uuid fk -> ref_document_type_versions(id) on delete cascade`
- `applicability_scope varchar(32) not null` (`global|country_specific|country_group`)
- `country_codes jsonb not null default '[]'::jsonb`
- `country_group_codes jsonb not null default '[]'::jsonb`
- `issuing_country_rules_json jsonb not null default '{}'::jsonb`
- `work_country_rules_json jsonb not null default '{}'::jsonb`
- `residence_country_rules_json jsonb not null default '{}'::jsonb`

Indexes:
- `ix_ref_doc_country_scope (applicability_scope)`

### 3) Pack Layer

#### `ref_packs`
- `id uuid pk`
- `code varchar(128) unique not null`
- `country_code varchar(8) null`
- `industry_code varchar(64) null`
- `status varchar(24) not null` (`draft|active|deprecated`)
- `version int not null`
- `published_at timestamptz null`
- `meta jsonb not null default '{}'::jsonb`

#### `ref_pack_items`
- `id uuid pk`
- `pack_id uuid fk -> ref_packs(id) on delete cascade`
- `document_type_version_id uuid fk -> ref_document_type_versions(id) on delete restrict`
- `role varchar(24) not null` (`required|optional|conditional|derived`)
- unique `(pack_id, document_type_version_id)`

#### `ref_pack_rules`
- `id uuid pk`
- `pack_id uuid fk -> ref_packs(id) on delete cascade`
- `priority int not null default 100`
- `condition_expr jsonb not null`
- `effect_type varchar(64) not null`
- `effect_payload jsonb not null`

### 4) Tenant Enablement + Overrides

#### `tenant_document_pack_enablements`
- `id uuid pk`
- `tenant_id varchar(36) not null`
- `pack_id uuid fk -> ref_packs(id) on delete cascade`
- `enabled boolean not null default true`
- `effective_from timestamptz null`
- `effective_to timestamptz null`
- unique `(tenant_id, pack_id)`

#### `tenant_document_type_overrides`
- `id uuid pk`
- `tenant_id varchar(36) not null`
- `document_type_id uuid fk -> ref_document_types(id) on delete cascade`
- `scope_type varchar(24) not null` (`tenant|own_company|vacancy|client`)
- `scope_id varchar(36) null`
- `enabled boolean null`
- `required_level varchar(24) null`
- `alert_days_before_expiry int null`
- `responsible_role varchar(64) null`
- `internal_instruction text null`
- `client_specific_requirement_json jsonb null`
- `meta jsonb not null default '{}'::jsonb`

Constraint:
- `scope_type='tenant' -> scope_id is null`

### 5) Request/Review Workflow for New Types

#### `tenant_document_type_requests`
- `id uuid pk`
- `tenant_id varchar(36) not null`
- `requested_code varchar(128) not null`
- `requested_name varchar(255) not null`
- `requested_payload jsonb not null`
- `status varchar(24) not null` (`requested|approved_to_system|rejected_or_local_only`)
- `decision_note text null`
- `reviewed_by varchar(36) null`
- `reviewed_at timestamptz null`
- `created_at timestamptz not null default now()`

Indexes:
- `ix_tenant_doc_type_requests_tenant_status (tenant_id, status)`

### 6) Runtime Instance Anchoring

#### `documents` table changes (existing table)
Add columns:
- `document_type_id uuid null fk -> ref_document_types(id) on delete restrict`
- `document_type_version_id uuid null fk -> ref_document_type_versions(id) on delete restrict`

Keep legacy columns during migration:
- `doc_type` (string) stays until cutover complete.

Indexes:
- `ix_documents_document_type_id`
- `ix_documents_document_type_version_id`

Policy:
- new writes must set canonical ids.
- `doc_type` remains compatibility alias only.

### 7) Policy/Ruleset Anchoring

#### `document_policies` changes
- add `ref_document_type_id uuid null fk -> ref_document_types(id)`
- keep existing `document_type_id` temporarily
- resolve precedence to `ref_document_type_id` once backfilled

#### `document_ruleset_versions` extension
- optional metadata fields:
  - `reference_snapshot_version varchar(64) null`
  - `reference_snapshot_hash varchar(128) null`
- required for deterministic replay/explainability.

## ORM Target Modules

Add models (suggested files):
- `backend/app/models/ref_document_type.py`
  - `RefDocumentType`, `RefDocumentTypeI18n`, `RefDocumentTypeVersion`, `RefDocumentTypeCountryApplicability`
- `backend/app/models/ref_pack.py`
  - `RefPack`, `RefPackItem`, `RefPackRule`
- `backend/app/models/tenant_document_reference.py`
  - `TenantDocumentPackEnablement`, `TenantDocumentTypeOverride`, `TenantDocumentTypeRequest`

Modify existing models:
- `Document`: add `document_type_id`, `document_type_version_id`.
- `DocumentPolicy`: add `ref_document_type_id`.
- `DocumentType`: mark as legacy compatibility model (`tenant catalog mirror`) and deprecate writes.

## Enum/Validation Contract
Use canonical enums (shared module) for:
- type status
- origin
- category/subcategory catalogs
- criticality
- applicability scope
- request status

Validation gates:
- `tenant_custom` deny-list enforcement
- duplicate detection (code + alias normalization)
- override safety rules (cannot change semantics/criticality)

## Backfill Mapping Rules

### `document_types` -> `ref_document_types`
- canonical code from `document_types.code`
- names from `name`, `title`, `i18n_key`
- schema blocks from `metadata_schema`, `required_files`, `expiry_rule`
- behavior from `kind`, `requested_from`, `process_type`, `status_model`, `orderable`, `duplicate_policy`

### `documents.doc_type` -> canonical FK
- map by canonical code dictionary
- unresolved rows -> `additional_document` fallback + audit row

### `document_policies.document_type_id`
- join legacy `document_types` then map by canonical code to `ref_document_type_id`

## Migration Plan (Alembic)

### M1: Foundation
- create all `ref_*` and `tenant_*` tables
- add new nullable FK columns on `documents` + `document_policies`

### M2: Seed + canonical sync
- seed canonical types from `document_types` + `document_types.definitions`
- create first `ref_document_type_versions`

### M3: Backfill runtime references
- backfill `documents.document_type_id/document_type_version_id`
- backfill `document_policies.ref_document_type_id`

### M4: Dual-write period
- writes populate both legacy and canonical fields
- reads prefer canonical, fallback to legacy

### M5: Cutover
- enforce non-null `documents.document_type_id`
- enforce policy resolution via `ref_document_type_id`
- freeze `document_types` writes (compat view/mirror mode)

### M6: Cleanup
- remove legacy dependencies on tenant `document_types`
- keep compatibility read API fields (`doc_type`, `code`, `name`) mapped from canonical rows

## Observability & Data Quality
Metrics:
- `% documents with canonical type FK`
- `% policies with canonical type FK`
- unresolved mapping count
- requested-type approval SLA

Data quality jobs:
- alias collision detector
- illegal custom-type detector
- pack coverage gaps by country/industry

## Acceptance Criteria
- `documents` and `document_policies` resolve through canonical type IDs.
- System can replay checklist decisions by type version + reference snapshot.
- Tenant custom policy limits are enforceable at DB/service layer.
- Legacy API contracts remain backward compatible during migration window.
