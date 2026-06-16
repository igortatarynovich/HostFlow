# Reference Layer And Applicability Packs (HostFlow)

## Status
Proposed (target architecture for modular HostFlow platform).

## Context
HostFlow is moving from a monolith to independent modules/plugins. Current implementation has partial catalogs, mixed ownership, and tenant-scoped `document_types` rows that are synchronized from code defaults.

Current state in codebase:
- System-like countries model exists but is not the main runtime source: `backend/app/models/country.py`.
- Main countries/languages/dial codes are served from hardcoded constants: `backend/app/constants/catalogs.py` and `backend/app/api/v1/catalogs.py`.
- Document types are tenant-scoped (`tenant_id + code`) in `backend/app/models/document_type.py` and synced via `backend/app/modules/documents/crud.py::list_document_types`.

This creates long-term risks for cross-module consistency, analytics, compliance automation, and legal-country expansion.

## Decision
HostFlow adopts a layered reference architecture:

Normative document type contract for this architecture:
- `docs/specs/architecture/document-type-model-standard.md`

1. **System Reference Layer** (global source of truth)
- Stores full platform encyclopedia:
  - countries, ISO codes, citizenships
  - languages, currencies
  - document categories and document types
  - legal stay/work permit/visa/contract/tax/social/ZUS/driver/medical/payroll entities
  - country-specific legal variants
- Owned by platform, not by tenant, not by business modules.

2. **Country/Legal Applicability Layer**
- Maps what is applicable in each country/legal regime:
  - country -> applicable reference objects
  - field requirements
  - validity/expiry semantics
  - dependency graph
  - conditional rules (EU/non-EU, position, contract type, etc.)
- Implemented as versioned packs/profiles.

3. **Tenant Enabled Set Layer**
- Tenant does not select from the full encyclopedia.
- Tenant enables predefined packs and optionally applies constrained overrides.
- Tenant visibility is filtered by country/industry/business model scope.

4. **Business Module Runtime Layer**
- Recruitment/HR/Documents/Fleet keep only references and instances.
- Runtime engines compute required checklist per person context.
- End users see process steps, not global dictionaries.

## Invariants
- Modules do not own reference dictionaries.
- Reference entities are globally stable, versioned, and auditable.
- Tenant overrides cannot break legal-required constraints in active packs.
- Runtime checklist is deterministic for identical input context and reference snapshot version.

## Data Model (target)

### A. System Reference
- `ref_domain`
  - `id`, `code` (`country`, `document_type`, `contract_type`, `tax_form`, `social_form`, ...)
- `ref_item`
  - `id`, `domain_id`, `code`, `status`, `version_from`, `version_to`, `is_deprecated`
  - `title_i18n`, `description_i18n`, `aliases`, `meta`
  - unique: `(domain_id, code, version_from)`
- `ref_relation`
  - `id`, `from_item_id`, `relation_type`, `to_item_id`, `meta`
  - for semantic links (`document_type -> category`, `visa_type -> legal_basis`, etc.)

### B. Specialized System Registries
- `ref_country`
  - `item_id (FK ref_item)`, `iso2`, `iso3`, `numeric_code`, `eu_member`, `schengen_member`
- `ref_currency`
  - `item_id`, `iso4217`, `minor_units`
- `ref_language`
  - `item_id`, `iso639_1`, `iso639_3`
- `ref_document_type`
  - `item_id`, `category_item_id`, `process_group`, `validity_model`, `eligibility_role`, `compliance_role`
  - contains system metadata contract currently split across `metadata_schema`, `required_files`, `expiry_rule`

### C. Country/Legal Packs
- `ref_pack`
  - `id`, `code` (e.g. `pl_hr_core`, `pl_driver_core`, `pl_non_eu_employment`), `country_item_id`, `industry_code`, `status`
  - `version`, `published_at`
- `ref_pack_rule`
  - `id`, `pack_id`, `priority`, `condition_expr`, `effect_type`, `effect_payload`
  - effect examples: `require_document`, `set_field_required`, `set_expiry_policy`, `block_transition`
- `ref_pack_item`
  - `id`, `pack_id`, `item_id`, `role` (`required`, `optional`, `conditional`, `derived`)

### D. Tenant Enabled Sets
- `tenant_ref_pack_enablement`
  - `id`, `tenant_id`, `pack_id`, `enabled`, `effective_from`, `effective_to`
- `tenant_ref_item_override`
  - `id`, `tenant_id`, `item_id`, `scope_type`, `scope_id`, `override_type`, `override_payload`
  - allowed override examples: reminder windows, internal owner role, optional->required within legal bounds

## Custom Document Type Governance
Default policy: **strict mode**.

- `strict`:
  - tenant cannot create custom document types directly
  - tenant can only submit `requested document type` for platform review
- `limited` (explicitly enabled per tenant by platform):
  - max `2` active custom document types per tenant (recommended hard cap)
  - custom type allowed only when all checks pass:
    - no equivalent in system catalog (code/alias/fuzzy-name collision check)
    - tenant-local operational need
    - does not participate in legal/work eligibility/compliance gates
    - not used by critical automation rules

Document type origin/status model:
- `system`: fully supported in rules engine, eligibility, compliance, analytics.
- `tenant_custom`: tenant-local, limited logic, excluded from critical gates.
- `requested`: tenant proposal pending platform decision (`approved_to_system` or `rejected_or_local_only`).

Hard deny-list for `tenant_custom` (must be system-owned only):
- passport / ID / identity documents
- visas
- work permits
- residence permits/cards
- driver licenses
- tachograph card
- code 95 / professional qualification
- ZUS and social-security forms
- employment contracts affecting legal/work status
- medical certificates
- psychotests
- any document used by legal/compliance/rules-engine decisions

Required controls:
- canonical-name normalization for request dedup (`Passport`, `Pasport`, `Паспорт`, etc.)
- immutable audit trail for create/update/archive actions
- migration path from `tenant_custom` to `system` when platform approves a new catalog item

### E. Runtime Derived Requirements
- `person_requirement_snapshot`
  - `id`, `tenant_id`, `person_id`, `context_hash`, `ref_snapshot_version`, `computed_at`
- `person_requirement_item`
  - `id`, `snapshot_id`, `item_id`, `state`, `reason_code`, `due_at`, `dependency_state`
- `person_document_instance`
  - keeps actual uploaded/verified documents; references `ref_document_type.item_id`

## Rules Engine Contract
Input context (minimum):
- citizenship
- work country
- legal stay status
- position family (driver/non-driver/etc.)
- contract type
- tenant enabled packs

Output:
- required checklist
- conditional blockers
- due/reminder schedule
- explainability trail (`which pack/rule produced requirement`)

## UX Contract
- UI never shows full global dictionary to ordinary users.
- UI presents only runtime-applicable checklist for given person context.
- Admin setup is package-first (`enable pack`) not raw dictionary browsing.
- Advanced dictionary screens are restricted to platform/superadmin/internal roles.

## Module/Plugin Boundary Contract
For independent modules/plugins:
- Read contract:
  - `ReferenceProvider.ResolveItems(...)`
  - `ReferenceProvider.ResolveApplicableChecklist(...)`
- Write contract:
  - modules write only instance/state tables (documents, verification actions, HR transitions)
  - modules cannot mutate system reference records
- Deployment options:
  - in-process reference module (monolith mode)
  - dedicated reference service (distributed mode)
  - local read-model cache with version pinning for isolated plugins

## API Surface (target)
- `GET /api/v1/reference/domains/{domain}/items`
- `GET /api/v1/reference/document-types`
- `GET /api/v1/reference/packs?country=PL&industry=transport`
- `POST /api/v1/reference/resolve-checklist` (context -> required items + reasoning)
- `GET /api/v1/tenant/reference/packs`
- `PUT /api/v1/tenant/reference/packs/{pack_code}` (enable/disable)

## Migration Plan From Current Implementation

### Phase 1: Build reference source of truth
- Add `ref_*` tables and seed from existing constants and document definitions.
- Preserve existing endpoints; implement dual-read shadow checks.
- Keep current tenant `document_types` operational.

### Phase 2: Introduce pack engine
- Create country/legal packs for first rollout:
  - `Poland HR Pack`
  - `Poland Driver Pack`
  - `Poland Non-EU Employment Pack`
- Add checklist resolver endpoint and compare with legacy checklist behavior.

### Phase 3: Tenant enablement switch
- Add tenant pack enablement UI/API.
- Filter visible document types and requirements by enabled packs.
- Keep legacy manual per-tenant rules behind feature flag for rollback.

### Phase 4: Repoint document instances
- Replace `documents.doc_type` free code usage with FK to `ref_document_type` (or stable ref ID).
- Migrate `document_types` tenant table into compatibility view or deprecated layer.

### Phase 5: Remove dictionary ownership from modules
- Recruitment/HR/Documents/Fleet read from reference contract only.
- Remove hardcoded countries/languages constants from runtime paths.
- Keep static constants only as emergency fallback for local dev.

## Backward Compatibility Requirements
- Existing tenant behavior must remain stable during migration.
- Existing API payloads keep legacy fields (`doc_type`, `code`, `name`) while adding canonical reference IDs.
- Existing analytics dimensions keep compatibility mapping until all modules consume canonical IDs.

## Initial Packs (recommended)
- `pl_transport_recruitment`
- `pl_internal_hr`
- `pl_eu_driver`
- `pl_non_eu_driver`
- `pl_fleet_compliance`

Each pack should reference lower-level legal packs and expose business-facing preset names.

## Non-goals
- No free-form tenant editing of system dictionary rows.
- No flat giant dropdown of all global document types for operational users.
- No per-module private copies of countries/document types.
- No unlimited tenant custom document type creation.

## Acceptance Criteria
- A manager creating/updating a candidate sees only applicable checklist items for that context.
- Checklist output is explainable by pack/rule traces.
- Two modules (e.g. Recruitment + HR) reference same canonical country/document objects.
- Analytics can aggregate by canonical IDs without alias normalization hacks.
- Tenant custom documents are either disabled (`strict`) or capped (`limited`, max 2) and excluded from critical compliance/legal flows.

Implementation SQL/ORM mapping:
- `docs/specs/architecture/document-type-model-sql-orm-target.md`
