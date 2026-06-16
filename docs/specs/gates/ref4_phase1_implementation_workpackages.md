# REF-4 Phase 1 Implementation Workpackages

Status: planning-only  
Date: 2026-05-28  
Scope: implementation planning only (no code changes)

Related:
- `docs/specs/gates/ref4_phase1_canonical_catalog_architecture.md`
- `docs/specs/gates/ref4_enforcement_baseline_snapshot.md`
- `docs/specs/gates/ref4_core_catalog_completion_gate_plan.md`

## 1. Phase Rule

Phase 1 builds reference foundation only.

Forbidden in all WPs:
1. HR logic
2. Recruitment logic
3. UI changes
4. consumer rollout changes
5. new workflow decisions
6. automatic runtime rule application

## 2. Mandatory Execution Order

Priority order (hard gate):
1. `WP-1` Core immutable catalogs
2. `WP-8` Facade delivery contracts
3. `WP-10` Enforcement + tests

Only after these three are approved, execute remaining domain packages.

## 3. Workpackage Matrix

| WP | Name | Goal |
|---|---|---|
| `WP-1` | Core immutable catalogs | countries, ISO, language codes |
| `WP-2` | Legal/person catalogs | citizenships, legal statuses, permit/visa types |
| `WP-3` | Document catalogs | document types, document categories, validity metadata |
| `WP-4` | Workforce/transport catalogs | workforce categories, employment types, transport modes |
| `WP-5` | Field schema registry | canonical field definitions |
| `WP-6` | Rule pack foundation | document/rule pack skeletons, no runtime decisions |
| `WP-7` | Tenant override foundation | labels/visibility/scoped overrides |
| `WP-8` | Facade delivery contracts | read/resolve/validate contracts |
| `WP-9` | Seed + migration strategy | migration order, seed ownership |
| `WP-10` | Enforcement + tests | boundary tests, registry tests, no direct access guards |

## 4. Workpackage Definitions

### WP-1 — Core Immutable Catalogs
- Scope: canonical `countries`, ISO keys, `language_codes`; immutable identity keys and baseline metadata.
- Out of scope: legal applicability logic, tenant overrides, runtime decision behavior.
- Source of truth: hybrid (`static registry` identity + DB-backed canonical projection).
- Delivery contract: facade read resolver + typed DTO.
- Migration/seed impact: yes (idempotent immutable seed + deterministic migration).
- Tests: seed idempotency; ISO uniqueness; facade read-shape contract.
- Exit criteria: all immutable identities loaded, version-tagged, and readable only through contract path.

### WP-2 — Legal/Person Catalogs
- Scope: `citizenships`, `legal_statuses`, `permit_types`, `visa_types` with canonical codes.
- Out of scope: HR/recruitment runtime branching and eligibility behavior.
- Source of truth: DB-backed canonical catalogs.
- Delivery contract: typed registry via facade read contract.
- Migration/seed impact: yes.
- Tests: canonical code validation; deprecation/version lifecycle checks; contract schema checks.
- Exit criteria: legal/person catalogs versioned and exposed via facade without consumer-side direct reads.

### WP-3 — Document Catalogs
- Scope: `document_types`, `document_categories`, validity metadata fields.
- Out of scope: document review runtime actions, module-specific checklist logic.
- Source of truth: DB-backed canonical catalogs.
- Delivery contract: typed document registry contract.
- Migration/seed impact: yes.
- Tests: type/category integrity; validity metadata schema checks; facade compatibility tests.
- Exit criteria: canonical document catalog set available through stable DTO contract.

### WP-4 — Workforce/Transport Catalogs
- Scope: `workforce_categories`, `employment_types`, `transport_modes`.
- Out of scope: assignment/routing/payroll runtime behavior.
- Source of truth: DB-backed canonical catalogs.
- Delivery contract: typed registry via facade.
- Migration/seed impact: yes.
- Tests: code normalization checks; contract shape checks; version policy checks.
- Exit criteria: workforce/transport domains canonicalized with facade delivery and no direct consumer coupling.

### WP-5 — Field Schema Registry
- Scope: canonical `field_schema_registry` definitions (`field_id`, value type, normalization, validation metadata).
- Out of scope: UI rendering behavior and module form workflow logic.
- Source of truth: DB-backed versioned schema registry.
- Delivery contract: schema contract registry + validator-facing read API.
- Migration/seed impact: yes.
- Tests: schema version lineage; compatibility checks; required-field contract tests.
- Exit criteria: schema registry versioned, queryable, and compatibility-checked through contract.

### WP-6 — Rule Pack Foundation
- Scope: rule/document pack skeleton structure and metadata only.
- Out of scope: runtime decision execution, operational blocking behavior.
- Source of truth: DB-backed policy-reference catalogs.
- Delivery contract: policy contract read model.
- Migration/seed impact: yes.
- Tests: pack schema validity; lifecycle (`draft|active|deprecated`) checks; precedence metadata checks.
- Exit criteria: rule pack foundation exists as canonical data model without runtime activation logic.

### WP-7 — Tenant Override Foundation
- Scope: bounded tenant overlays for labels/visibility/scoped requirement knobs.
- Out of scope: tenant ability to redefine canonical identity/critical semantics.
- Source of truth: tenant-scoped overlay tables + policy constraints.
- Delivery contract: override projection contract post-validation.
- Migration/seed impact: yes (tables + constraints; no broad seed requirement).
- Tests: override boundary enforcement; forbidden override rejection; audit trail checks.
- Exit criteria: policy-bounded tenant override model enforced and auditable.

### WP-8 — Facade Delivery Contracts
- Scope: canonical `read/resolve/validate` contract surfaces for all Phase 1 domains.
- Out of scope: consumer behavior rewrites and module runtime rollout.
- Source of truth: contract specs + facade boundary implementation model.
- Delivery contract: stable facade/API DTO contracts with version tags.
- Migration/seed impact: no direct seed; contract alignment impacts all seeded domains.
- Tests: DTO stability regression; nullability/stability-class checks; contract conformance tests.
- Exit criteria: phase domains have documented and test-guarded stable delivery contracts.

### WP-9 — Seed + Migration Strategy
- Scope: migration dependency graph, seed ownership, rollback/observability strategy.
- Out of scope: module-level data backfills outside reference layer.
- Source of truth: migration plan + seed manifests.
- Delivery contract: N/A (governs delivery readiness, not runtime consumer API directly).
- Migration/seed impact: yes (this WP defines it).
- Tests: dry-run/replay idempotency; ordering validation; rollback simulation checks.
- Exit criteria: approved execution order and deterministic seed/migration playbook.

### WP-10 — Enforcement + Tests
- Scope: direct-access guards, boundary scans, registry conformance, contract gate tests.
- Out of scope: business behavior tests unrelated to reference boundary.
- Source of truth: enforcement rules + guard-scan policies + registry.
- Delivery contract: enforcement checks over facade/contract boundaries.
- Migration/seed impact: no direct catalog seed; validates seeded outputs and boundaries.
- Tests: no-direct-import guards; no-raw-reference-access guards; registry integrity checks; facade-only consumption checks.
- Exit criteria: enforcement gates green and blocking policies active for Phase 1 outputs.

## 5. Phase Exit Gate (Planning)

Phase 1 planning is ready for execution when:
1. `WP-1`, `WP-8`, `WP-10` are approved first;
2. each WP has explicit scope/out-of-scope/source/delivery/tests/exit criteria;
3. no WP includes runtime-consumer logic or workflow behavior changes.

