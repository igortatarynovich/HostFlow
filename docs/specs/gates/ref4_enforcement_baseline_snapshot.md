# REF-4 Enforcement Baseline Snapshot

Status: baseline-fixed  
Date: 2026-05-28  
Gate state: `REF-4 Entry Gate = PASS_WITH_ENFORCEMENT`

Related:
- `docs/specs/gates/system_layers_information_flow_audit.md`
- `docs/specs/gates/system_direct_access_exceptions_registry.md`
- `docs/specs/gates/ref4_blocker_remediation_plan.md`
- `docs/specs/gates/ref4_preimplementation_direct_access_scan_report.md`

## 1. Final Blocker State

| EXC | Final status |
|---|---|
| `EXC-003` | `PASS WITH BASELINE NOTE` |
| `EXC-004` | `PASS` |
| `EXC-007` | `PASS WITH BASELINE NOTE` |
| `EXC-009` | `PASS` |

## 2. Allowed Temporary Exceptions

Only the following remain temporary-allowed at this checkpoint:

| EXC | Owner | Removal milestone |
|---|---|---|
| `EXC-005` | Documents/Platform | `REF-4.1` |
| `EXC-006` | Recruitment + Document Hub | `REF-4.2` |
| `EXC-008` | Recruitment + Document Hub | `REF-4.2` |
| `EXC-010` | Platform | `REF-5` |

Rule:
- no new temporary exception without registry entry (`owner + milestone + migration/PASS/STOP conditions`).

## 3. Current Enforcement Guarantees

| Guarantee | State |
|---|---|
| No direct reference imports in remediated consumers (`EXC-003`, `EXC-004`) | `enforced` |
| No cross-domain documents access in remediated consumers (`EXC-007`, `EXC-009`) | `enforced` |
| Facade-only normalization path for remediated reference taxonomy calls | `enforced` |
| Delivery-contract boundary introduced for remediated document read/summary paths | `enforced` |
| Blocker guard-scan rerun completed before gate transition | `enforced` |

## 4. Known Accepted Limitations

Accepted and tracked at this baseline:

1. pre-existing unrelated branch changes in remediated files with explicit baseline notes (`EXC-003`, `EXC-007` contexts);
2. one non-blocking pre-existing failing test in full file run (`test_create_attempt_skips_stage_when_workforce_locked`) excluded from blocker verification pack by targeted selector;
3. temporary exceptions not yet remediated: `EXC-005`, `EXC-006`, `EXC-008`, `EXC-010`.

Guardrail:
- limitations above are not REF-4 scope expansion triggers and must not be mixed into Phase 1 catalog work unless explicitly promoted via gate update.

## 5. REF-4 Start Condition

This snapshot confirms enforcement stabilization is complete enough to start REF-4 Phase 1 under enforcement mode:

1. canonical catalogs;
2. ownership model;
3. versioning;
4. facade delivery contracts;
5. tenant override model;
6. registry composition;
7. seed/migration strategy;
8. validation contracts;
9. consumer rollout plan.

