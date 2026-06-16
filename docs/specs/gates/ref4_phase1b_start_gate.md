# REF-4 Phase 1B Start Gate

Status: PHASE_1B_READY_FOR_PASS  
Date: 2026-05-28  
Target: authorize Phase 1B implementation only

Related:
- `docs/specs/gates/ref4_phase1a_pass_gate.md`
- `docs/specs/gates/ref4_phase1_gate_iterations.md`
- `docs/specs/gates/ref4_phase1_implementation_workpackages.md`
- `docs/specs/gates/ref4_phase1_canonical_catalog_architecture.md`

## 1. Phase 1B Scope Lock

Included WP only:
1. `WP-2` legal/person catalogs
2. `WP-3` document catalogs
3. `WP-5` partial (field schema registry for legal/document domains only)

Blocked in this gate:
1. runtime rules/decision execution;
2. workflow logic or operational automation;
3. consumer rollout;
4. UI/module rewrites;
5. tenant overlay foundation (`WP-7`, Phase 1C scope).

## 2. Source of Truth and Delivery Rules

Mandatory rules:
1. catalog data source-of-truth must be canonical reference layer artifacts (registry + deterministic seed/migration path);
2. delivery only through facade/API contract surfaces established in Phase 1A;
3. no direct domain-table reads by independent consumers;
4. no new legacy wrappers.

## 3. Pre-Code File Boundary

Phase 1B file boundary:
1. `backend/app/reference/` (legal/document canonical registries and schema mapping);
2. `backend/app/services/reference_service_facade.py` (contract extension only);
3. `backend/app/schemas/` (DTO/schema contracts for legal/document catalogs);
4. `backend/alembic/versions/` (deterministic migration/seed artifacts for 1B scope);
5. `backend/tests/` (contract, compatibility, and enforcement tests);
6. `docs/specs/gates/` (gate evidence updates).

Out of scope file changes:
1. runtime module behavior files (`hr`, `recruitment`, `workforce`, automations);
2. frontend/UI files.

## 4. Required Enforcement Checks

Before Phase 1B PASS all checks must be green:
1. no direct access regressions to reference/config/policy internals;
2. all new legal/document catalogs consumed through facade path only;
3. schema compatibility checks for WP-5 partial registry;
4. no runtime decision behavior introduced.

## 5. Required Test Groups

Mandatory test groups:
1. catalog integrity tests (uniqueness, deterministic ordering, version markers);
2. facade contract tests (read/resolve/validate for 1B domains);
3. schema compatibility tests (partial WP-5 scope);
4. guard tests for forbidden direct imports/DB/raw config paths.

## 6. Migration/Seed Boundary

Allowed:
1. legal/document catalog migrations + deterministic seeds;
2. partial field schema registry migrations for legal/document domains.

Blocked:
1. tenant overlay tables;
2. runtime rule execution structures;
3. workflow state mutations outside reference layer.

## 7. PASS / STOP Criteria

PASS (open path to Phase 1C) requires all:
1. only 1B workpackage scope touched;
2. legal/document catalogs versioned and delivered via facade contracts;
3. WP-5 partial schema registry compatible and validated;
4. enforcement tests and guard scan green.

STOP if any:
1. runtime behavior mixed into Phase 1B diff;
2. direct-access path introduced for new catalogs;
3. incompatible schema change without version channel;
4. migration/seed is non-deterministic.

## 8. Phase 1B Execution Evidence

| Block | Value |
|---|---|
| `WP-2` | implemented |
| `WP-3` | implemented |
| `WP-5 partial` | implemented |
| Tests | `14 passed` |
| Runtime rollout | none |
| UI/workflow changes | none |
| Consumer integration | none |
| Gate status | `PHASE_1B_READY_FOR_PASS` |

Evidence test command:

```bash
cd /opt/HostFlow && pytest -q \
  backend/tests/services/test_reference_field_schema_registry.py \
  backend/tests/services/test_legal_document_catalogs.py \
  backend/tests/services/test_reference_service_facade.py \
  backend/tests/services/test_phase1a_enforcement_guards.py
```
