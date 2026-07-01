# REF-4 Phase 1A Start Gate

Status: closed (superseded by Phase 1A PASS gate)  
Date: 2026-05-28  
Target: authorize Phase 1A implementation only

Related:
- `docs/specs/gates/ref4_phase1_gate_iterations.md`
- `docs/specs/gates/ref4_phase1_implementation_workpackages.md`
- `docs/specs/gates/ref4_phase1_canonical_catalog_architecture.md`
- `docs/specs/gates/ref4_enforcement_baseline_snapshot.md`
- `docs/specs/gates/ref4_phase1a_pass_gate.md`

## 1. Phase 1A Scope Lock

Included WP only:

| WP | Scope |
|---|---|
| `WP-1` | core immutable catalogs |
| `WP-8` | facade delivery contracts |
| `WP-10` | enforcement + tests |

Blocked in this gate:
1. `WP-2` legal/person catalogs
2. `WP-3` document catalogs
3. any runtime-consumer behavior changes
4. any UI/workflow/module rewrites

## 2. Pre-Code File Plan

Files to create/modify in Phase 1A must stay within these groups:

1. Canonical reference constants/registry files (immutable catalogs only) under `backend/app/constants/` and/or `backend/app/services/`.
2. Facade contract surfaces under `backend/app/services/reference_service_facade.py` and contract schemas under `backend/app/schemas/`.
3. Enforcement/guard tests under `backend/tests/` (service/api guard and contract tests).
4. Deterministic seed/migration artifacts under `backend/alembic/versions/` and seed helpers under `backend/app/services/`.
5. Gate evidence docs under `docs/specs/gates/`.

Phase 1A change policy:
- if a file is outside these groups, it is out-of-scope unless explicitly approved by gate update.

## 3. Source of Truth (WP-1)

WP-1 source-of-truth model:

1. immutable identity anchors: canonical static registry definitions (ISO/country/language identity keys);
2. canonical persisted projection: deterministic DB seed/migration output;
3. facade response is delivery path, not source-of-truth.

Hard rule:
- no module runtime may treat local ad-hoc dictionaries as source-of-truth.

## 4. Public Facade Names (WP-8)

Phase 1A public facade contract names (must remain stable in this phase):

1. `ReferenceServiceFacade.get_reference_bundle(...)`
2. `ReferenceServiceFacade.get_country_profile(...)`
3. `ReferenceServiceFacade.get_applicable_documents(...)`
4. `ReferenceServiceFacade.get_document_type_profile(...)`
5. `ReferenceServiceFacade.get_document_runtime_profile(...)`
6. `ReferenceServiceFacade.normalize_reference_code(...)`

Contract rules:
1. all reads through facade/API DTO path;
2. contract fields stability-tagged and version-echoed (`contract_version`, `reference_version`);
3. no consumer-specific branching inside facade contract layer.

## 5. Guard Tests (WP-10)

Required guard tests in Phase 1A:

1. no-direct-reference-import guard for remediated consumers (`EXC-003`, `EXC-004`);
2. no-direct-cross-domain-doc-access guard for remediated consumers (`EXC-007`, `EXC-009`);
3. facade contract conformance/stability tests for Phase 1A surfaces;
4. immutable seed idempotency tests;
5. registry consistency tests (unique canonical codes, deterministic ordering where required).

## 6. Forbidden Imports and Access Patterns

Forbidden during Phase 1A implementation:

1. direct imports of internal reference foundations in consumers (bypass facade);
2. direct module-to-module reads of document internals from remediated consumers;
3. direct runtime reads of reference DB tables from module consumers;
4. introducing new raw config/dictionary decision paths in module runtime.

## 7. Migration/Seed Boundary

Allowed migration/seed work in Phase 1A:

1. immutable catalog migration + deterministic seed only;
2. contract-supporting schema updates strictly for facade delivery;
3. replay-safe and rollback-documented migration steps.

Blocked in Phase 1A:
1. mutable legal/document domain expansion migrations (`WP-2`/`WP-3` scope);
2. tenant overlay table expansion;
3. runtime rule-pack execution structures.

## 8. PASS / STOP Criteria

PASS (open path to Phase 1B) requires all:

1. only `WP-1`, `WP-8`, `WP-10` scope touched;
2. immutable catalogs seeded idempotently and exposed via facade contracts;
3. guard tests green and enforcement checks active;
4. no blocked-scope artifacts (WP-2/WP-3) introduced.

STOP if any:

1. any WP-2/WP-3 domain work starts before Phase 1A PASS;
2. runtime-consumer behavior changes bundled into Phase 1A;
3. direct-access guard regressions appear;
4. seed/migration is non-deterministic or missing rollback path;
5. facade contract instability or undocumented shape changes.

## 9. Authorization Note

This gate authorizes implementation start for Phase 1A only.

Next gate dependency:
- Phase 1B cannot start until explicit Phase 1A `PASS` decision is recorded.

## 10. Phase 1A Baseline Snapshot (Current Branch)

Concrete files in active Phase 1A scope:

1. `backend/app/reference/core_immutable_catalogs.py` (new, WP-1)
2. `backend/app/reference/core_immutable_catalogs_seed.py` (new, WP-1/WP-9 boundary helper)
3. `backend/app/services/reference_service_facade.py` (new/updated, WP-8)
4. `backend/app/schemas/reference_core_immutable.py` (new, WP-8)
5. `backend/tests/services/test_core_immutable_catalogs.py` (new, WP-10)
6. `backend/tests/services/test_core_immutable_catalogs_seed.py` (new, WP-10)
7. `backend/tests/services/test_reference_service_facade.py` (new/updated, WP-10)
8. `backend/tests/services/test_phase1a_enforcement_guards.py` (new, WP-10)

WP-1 source-of-truth in this baseline:

1. Canonical immutable Python registry for country/language identity anchors.
2. Deterministic seed payload/checksum helper for replay-safe projection.
3. Facade outputs as delivery contract only.

Active Phase 1A facade/public contract surfaces:

1. `ReferenceServiceFacade.get_reference_bundle(...)`
2. `ReferenceServiceFacade.get_country_profile(...)`
3. `ReferenceServiceFacade.normalize_reference_code(...)`
4. `ReferenceServiceFacade.get_core_immutable_snapshot(...)`
5. `ReferenceServiceFacade.compatibility_check_core_immutable_snapshot(...)`

Current guard/enforcement test command:

```bash
cd /opt/HostFlow && pytest -q \
  backend/tests/services/test_core_immutable_catalogs.py \
  backend/tests/services/test_core_immutable_catalogs_seed.py \
  backend/tests/services/test_reference_service_facade.py \
  backend/tests/services/test_phase1a_enforcement_guards.py
```

Latest result: `12 passed` (2026-05-28).
