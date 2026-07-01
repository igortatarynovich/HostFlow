# REF-4 Phase 1 Gate Iterations

Status: 1A-passed / 1B-passed / 1C-passed  
Date: 2026-05-28  
Intent: execution-gated rollout of Phase 1 as a Platform Reference System

Related:
- `docs/specs/gates/ref4_phase1_implementation_workpackages.md`
- `docs/specs/gates/ref4_phase1_canonical_catalog_architecture.md`
- `docs/specs/gates/ref4_enforcement_baseline_snapshot.md`
- `docs/specs/gates/ref4_phase1a_pass_gate.md`
- `docs/specs/gates/ref4_phase1b_start_gate.md`
- `docs/specs/gates/ref4_phase1b_pass_gate.md`
- `docs/specs/gates/ref4_phase1c_start_gate.md`

## 1. Gate Sequence (Hard Order)

Mandatory order:
1. Phase `1A` must pass before opening `1B`.
2. Phase `1B` must pass before opening `1C`.

Hard controls:
1. no mixing of delivery contracts with runtime behavior changes;
2. no consumer rollout inside Phase 1;
3. no iteration skipping.

## 2. Phase 1A — Foundation Core

Purpose:
- establish immutable canonical layer + single delivery path + enforcement baseline before domain expansion.

Included WP:
1. `WP-1` Core immutable catalogs
2. `WP-8` Facade delivery contracts
3. `WP-10` Enforcement + tests

Explicitly blocked scope:
1. legal/person domain expansion (`WP-2`)
2. document catalogs beyond immutable base (`WP-3`)
3. runtime rules/workflow behavior
4. UI/module consumer changes

Required enforcement checks:
1. no direct reference imports in remediated consumers remain enforced;
2. no direct cross-domain document access in remediated consumers remains enforced;
3. facade-only contract path checks enabled;
4. guard-scan policy active in CI.

Required tests:
1. immutable seed idempotency tests;
2. facade DTO contract conformance + stability checks;
3. no-direct-access guard tests;
4. baseline registry integrity tests.

Migration boundary:
1. immutable identity migrations/seeds only;
2. no mutable policy/tenant overlay migrations.

PASS criteria:
1. immutable catalogs published through facade contracts;
2. enforcement gates green;
3. contract version/reference version baseline fixed;
4. no blocked-scope changes detected.

STOP criteria:
1. direct-access guard violations;
2. missing/unstable facade contract;
3. non-idempotent immutable seed behavior;
4. any runtime-consumer behavior bundled into 1A.

Current 1A execution evidence (2026-05-28):
1. `WP-1` implemented baseline files:
   - `backend/app/reference/core_immutable_catalogs.py`
   - `backend/app/reference/core_immutable_catalogs_seed.py`
2. `WP-8` implemented baseline files:
   - `backend/app/services/reference_service_facade.py`
   - `backend/app/schemas/reference_core_immutable.py`
3. `WP-10` implemented baseline tests:
   - `backend/tests/services/test_core_immutable_catalogs.py`
   - `backend/tests/services/test_core_immutable_catalogs_seed.py`
   - `backend/tests/services/test_reference_service_facade.py`
   - `backend/tests/services/test_phase1a_enforcement_guards.py`
4. Targeted gate test command:
   ```bash
   cd /opt/HostFlow && pytest -q \
     backend/tests/services/test_core_immutable_catalogs.py \
     backend/tests/services/test_core_immutable_catalogs_seed.py \
     backend/tests/services/test_reference_service_facade.py \
     backend/tests/services/test_phase1a_enforcement_guards.py
   ```
5. Latest result: `12 passed`.
6. Gate state: `1B` remains blocked until explicit 1A PASS record.

## 3. Phase 1B — Legal + Document Reference Layer

Purpose:
- extend canonical legal/document reference domains on top of 1A delivery/enforcement baseline.

Included WP:
1. `WP-2` Legal/person catalogs
2. `WP-3` Document catalogs
3. `WP-5` (partial) field schema registry core for legal/document domains

Explicitly blocked scope:
1. runtime rules execution logic
2. workflow logic / operational automations
3. document automation behavior
4. consumer rollout and module rewrites

Required enforcement checks:
1. all new domains exposed only via Phase 1A facade contracts;
2. no new direct table/import reads in consumers;
3. schema contract compatibility checks active.

Required tests:
1. legal/document catalog version lifecycle tests;
2. field schema compatibility tests (partial scope);
3. facade read/resolve validation tests for 1B domains;
4. guard-scan delta tests for new domain files.

Migration boundary:
1. legal/document catalog migrations + deterministic seeds;
2. partial schema registry migrations for included 1B fields;
3. no tenant overlay migrations yet.

PASS criteria:
1. WP-2/WP-3 catalogs versioned and contract-delivered;
2. partial WP-5 schema registry core approved for 1B domains;
3. blocked scope untouched;
4. enforcement checks remain green.

STOP criteria:
1. runtime rule/workflow behavior introduced;
2. domain catalogs accessible outside facade path;
3. incompatible schema changes without version channel;
4. failing guard-scan on direct access patterns.

Current 1B execution evidence (2026-05-28):
1. `WP-2`: implemented
2. `WP-3`: implemented
3. `WP-5 partial`: implemented
4. Tests: `14 passed`
5. Runtime rollout: none
6. UI/workflow changes: none
7. Consumer integration: none
8. Gate status: `PHASE_1B_READY_FOR_PASS`

## 4. Phase 1C — Extensible Policy Foundation

Purpose:
- complete extensibility foundations (policy skeletons, overlays, remaining schema/migration strategy) without runtime execution engine.

Included WP:
1. `WP-4` Workforce/transport catalogs
2. `WP-6` Rule pack foundation
3. `WP-7` Tenant override foundation
4. `WP-5` (remaining) full field schema registry completion
5. `WP-9` Seed + migration strategy finalization

Explicitly blocked scope:
1. runtime execution engine for rules
2. automated decision application in operations
3. consumer-specific rollout logic
4. UI/behavior changes in modules

Required enforcement checks:
1. tenant override boundaries enforced by policy constraints;
2. rule-pack skeletons remain non-executing metadata;
3. facade/validation-only access for all added domains;
4. no bypass of registry composition precedence.

Required tests:
1. tenant override boundary tests (allow/deny matrix);
2. rule-pack schema/lifecycle tests (non-runtime);
3. full schema registry compatibility tests;
4. migration dry-run + rollback simulation + replay idempotency.

Migration boundary:
1. workforce/transport catalogs;
2. tenant overlay tables + constraints;
3. rule-pack metadata tables;
4. final migration dependency graph and rollback playbook.

PASS criteria:
1. extensible foundations complete without runtime behavior coupling;
2. tenant overlays bounded/auditable;
3. full schema registry and migration strategy approved;
4. enforcement and guard scans remain green across all Phase 1 domains.

STOP criteria:
1. any runtime execution behavior introduced for rules/packs;
2. tenant overrides able to alter canonical semantics;
3. migration strategy lacks rollback or deterministic replay;
4. consumer rollout logic mixed into Phase 1.

Current 1C execution evidence (2026-05-28):
1. `WP-4`: implemented
2. `WP-5 remaining`: implemented
3. `WP-7`: implemented
4. `WP-6`: implemented
5. `WP-9`: implemented
6. Tests: `29 passed`
7. DB migration: none
8. Runtime execution: none
9. Consumer rollout: none
10. UI/workflow: none
11. Decision: `PHASE_1C_PASS`

## 5. Architectural Control Notes

REF-4 Phase 1 is governed as a `Platform Reference System`, not a catalog dump.

Control invariants:
1. platform reference first, consumers later;
2. delivery/enforcement first, domain expansion second;
3. extensibility foundation before runtime execution;
4. no gate promotion without explicit PASS decision.
