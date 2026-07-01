# REF-4 Phase 1 Canonical Catalog Architecture

Status: draft-for-gate  
Date: 2026-05-28  
Scope: architecture definition only (canonical platform layer)

Related:
- `docs/specs/gates/ref4_enforcement_baseline_snapshot.md`
- `docs/specs/gates/ref4_core_catalog_completion_gate_plan.md`
- `docs/specs/reference_delivery_contract_standard.md`
- `docs/specs/gates/system_layers_information_flow_audit.md`

## 1. Scope Guardrails

Allowed in Phase 1:
1. canonical catalogs
2. ownership model
3. registry composition
4. versioning model
5. facade delivery contracts
6. tenant override model
7. validation contracts
8. seed strategy
9. migration strategy
10. reference schemas

Forbidden in Phase 1:
1. HR runtime logic changes
2. Recruitment workflow changes
3. UI changes
4. new operational behavior
5. consumer-specific hacks
6. module rewrites

## 2. Catalog Domains

Canonical domains for REF-4 Phase 1:

1. `countries`
2. `citizenships`
3. `document_types`
4. `permit_types`
5. `visa_types`
6. `legal_statuses`
7. `workforce_categories`
8. `employment_types`
9. `transport_modes`
10. `language_codes`
11. `field_schema_registry`
12. `document_rule_packs`

## 3. Canonical Ownership Model

| Domain | Owner |
|---|---|
| `countries` | `platform-reference` |
| `citizenships` | `platform-reference` |
| `document_types` | `platform-reference` |
| `permit_types` | `platform-reference` |
| `visa_types` | `platform-reference` |
| `legal_statuses` | `platform-reference` |
| `workforce_categories` | `platform-reference` |
| `employment_types` | `platform-reference` |
| `transport_modes` | `platform-reference` |
| `language_codes` | `platform-reference` |
| `field_schema_registry` | `platform-reference` |
| `document_rule_packs` | `policy-reference` |

Ownership rules:
1. module teams are consumers, not owners, of canonical semantics;
2. tenant admins own only bounded overlays, never canonical identity;
3. ownership changes require gate update before implementation.

## 4. Delivery Contracts

| Domain | Delivery type |
|---|---|
| `countries` | facade resolver |
| `citizenships` | facade resolver |
| `document_types` | typed registry |
| `permit_types` | typed registry |
| `visa_types` | typed registry |
| `legal_statuses` | typed registry |
| `workforce_categories` | typed registry |
| `employment_types` | typed registry |
| `transport_modes` | typed registry |
| `language_codes` | typed registry |
| `field_schema_registry` | schema contract registry |
| `document_rule_packs` | policy contract |

Contract rules:
1. module access path is `module -> facade/API -> canonical DTO`;
2. direct table/import coupling is forbidden for consumer runtime;
3. contract fields must be stability-tagged (`stable` / `experimental` / `deprecated`).

## 5. Versioning Model

| Entity | Versioned? |
|---|---|
| `document_rule_packs` | yes |
| `field_schema_registry` | yes |
| `document_types` | yes |
| `permit_types` | yes |
| `visa_types` | yes |
| `legal_statuses` | yes |
| `workforce_categories` | yes |
| `employment_types` | yes |
| `transport_modes` | yes |
| `language_codes` | yes |
| `countries` (ISO identity) | no/rare |
| `citizenships` (ISO-linked identity) | no/rare |

Versioning rules:
1. immutable identity keys do not churn unless standards change;
2. behavioral/policy catalogs require explicit lifecycle (`draft|active|deprecated`);
3. every breaking change requires new contract or version channel.

## 6. Tenant Override Policy

| Domain surface | Tenant override |
|---|---|
| display labels | yes |
| ordering/presentation | yes |
| required docs | scoped |
| reminder/instruction metadata | scoped |
| policy enablement by pack | scoped |
| ISO country codes | no |
| canonical document type identity | no |
| compliance criticality semantics | no |

Policy rules:
1. overrides are bounded by policy and validated before projection;
2. tenant override cannot redefine canonical meaning;
3. all overrides are auditable and reversible.

## 7. Validation Model

Unified validation contract pipeline:

1. `normalize` — canonical input normalization for codes/keys/types;
2. `validate` — strict schema + constraints + policy boundaries;
3. `resolve` — facade-level canonical resolution with context;
4. `compatibility_check` — backward compatibility for DTO/version consumers.

Validation outputs:
1. `valid` flag
2. `errors[]` with codes
3. `warnings[]` with non-blocking issues
4. `reference_version` / `contract_version` echo

## 8. Registry Composition Model

Registry layers in REF-4 Phase 1:

1. `static registry` — immutable baseline dictionaries (ISO-like anchors);
2. `DB-backed registry` — versioned mutable canonical catalogs;
3. `hybrid registry` — static anchors + DB extensions under one domain contract;
4. `cached facade registry` — read-optimized facade projection with version-aware cache invalidation.

Composition rules:
1. source-of-truth per domain must be singular and documented;
2. hybrid domains must define precedence (`static identity` > `db extension`);
3. cache layer cannot become independent source-of-truth.

## 9. Migration + Seed Strategy

| Type | Strategy |
|---|---|
| immutable catalogs | deterministic migrations + idempotent seeds |
| mutable business catalogs | DB-managed versioned rows |
| tenant overlays | tenant-scoped tables + policy validation |

Execution rules:
1. seed runs must be deterministic and replay-safe;
2. migration order follows dependency graph (`identity -> types -> schemas -> packs -> overlays`);
3. rollback path required for each migration batch;
4. compatibility windows required for deprecated versions.

## 10. Reference Schemas

Phase 1 defines schema contracts (not consumer behavior) for:

1. canonical code identity (`code`, `status`, `display`, `metadata`)
2. versioned profile payloads (`valid_from`, `valid_to`, `replacement_code`, `reason`)
3. field schema registry (`field_id`, `value_type`, `normalization`, `validation`, `ui_metadata`)
4. rule pack schema (`conditions`, `effects`, `criticality`, `override_policy`, `priority`)
5. tenant overlay schema (`scope`, `allowed_changes`, `audit`)

## 11. Phase 1 Exit Criteria

REF-4 Phase 1 architecture definition is complete when:

1. all domains above have owner + delivery type + version policy;
2. tenant override boundaries are policy-locked;
3. validation contract (`normalize/validate/resolve/compatibility_check`) is approved;
4. registry composition model is approved per domain;
5. migration + seed strategy is approved with rollback and observability;
6. no runtime-consumer behavior changes are bundled into this phase.

