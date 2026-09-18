# Platform Modularization & Isolation Cutover Gate

**Status:** **PASS** (PMI-0…PMI-X **PASS** 2026-09-16; PLATFORM_MODULARIZATION_ISOLATION_CUTOVER)
**Date:** 2026-09-16  
**Parents:** [`platform-modularization-isolation-cutover.md`](../tasks/platform-modularization-isolation-cutover.md) · [`ADR-042`](../architecture/ADR-042-spine-policy-separation.md) · [`module-ownership-coverage.md`](module-ownership-coverage.md)  
**Decision ID (when closed):** `PLATFORM_MODULARIZATION_ISOLATION_CUTOVER`  
**Does not close:** Full Spine · Ready composition · Module Independence recertification

---

## Current slice

| Slice | Gate job / test | Status |
|-------|-----------------|--------|
| **PMI-0** Fact map | `test_module_isolation_pmi0_map_gate.py` + `check_module_isolation_map.py --check` | **PASS** 2026-09-16 |
| **PMI-1** Freeze | `test_module_isolation_pmi1_freeze_gate.py` + `check_module_isolation_freeze.py` | **PASS** 2026-09-16 |
| **PMI-R** Recruitment ISOLATED | eight-row card + debt 2006→1799 + `check_recruitment_isolation.py` | **PASS** 2026-09-16 |
| **PMI-B** Boundary ISOLATED | eight-row card + debt 1799→1746 + `check_boundary_isolation.py` (0 inbound) | **PASS** 2026-09-16 |
| **PMI-E** Employment ISOLATED | eight-row card + debt 1746→1705 + `check_employment_isolation.py` (0 inbound) | **PASS** 2026-09-16 |
| **PMI-D** Documents ISOLATED | eight-row card + debt 1705→1612 + `check_documents_isolation.py` (0 inbound) | **PASS** 2026-09-16 |
| **PMI-W** Workforce ISOLATED | eight-row card + debt 1612→1557 + `check_workforce_isolation.py` (0 inbound) | **PASS** 2026-09-16 |
| **PMI-UI** Design system ISOLATED | four DoD + UI debt 8 + `check_ui_isolation.py` | **PASS** 2026-09-16 |
| **PMI-X** Program exit | joint `check_pmi_x_program_exit.py` (5+UI+freeze+parked) | **PASS** 2026-09-16 |

### PMI-0 evidence

| Property | Result |
|----------|--------|
| Every `backend/app/**/*.py` → owner \| UNASSIGNED | **PASS** (1275 files) |
| Spine required package/prefix boundaries | **PASS** (R/B/E/D/W each ≥1 file) |
| Reproducible leak set for PMI-1 | **PASS** — `module_isolation_pmi0_baseline.json` @ `844900d6` (2006 edges) |

### PMI-1 evidence

| Property | Result |
|----------|--------|
| Authority pinned to `844900d6` (sha256 lock) | **PASS** |
| Debt = 2006 structural edges; ⊆ authority | **PASS** |
| New cross-owner edge → FAIL | **PASS** (enforced) |
| Debt growth / fake shrink / ownership hide → FAIL | **PASS** (enforced) |
| No remediation / Ready / Kernel in freeze PR | **PASS** |

**Invariant:** Architectural debt may only shrink. New cross-module coupling is rejected.

---

## ISOLATED (repeatable)

A module may be marked ISOLATED only from a closed [`module_isolation_card.md`](../../modules/_template/module_isolation_card.md) with CI evidence for all eight rows. MIP `CERTIFIED` is not accepted as evidence. While foreign code imports the module’s internals, or the module imports neighbour internals instead of a public contract, the card stays **OPEN**.

### PMI-X evidence

| Property | Result |
|----------|--------|
| Five + UI cards Status ISOLATED | **PASS** |
| B/E/D/W foreign→internals = 0 | **PASS** |
| Recruitment spine foreign→internals = 0 | **PASS** (non-spine residual ≤63 shrink-only) |
| Backend debt 2006→1557 (−449); no growth | **PASS** |
| UI authority + debt 8 shrink-only | **PASS** |
| Joint checkers green **together on HEAD** | **PASS** |
| Ready/Kernel/PEM-1 not smuggled | **PASS** |
| Ready is not auto-unfrozen | **PASS** |
| Exit fixes nothing (verification only) | **PASS** |
| Debt need not be zero | **PASS** (explicit non-criterion) |

### PMI-X hard locks

1. **Exit fixes nothing.** Defect at exit → **STOP** + classification + separate work item. No in-exit cleanup.
2. **PASS is HEAD-simultaneous.** Historical slice stamps alone are insufficient; suite must pass together on one revision.
3. **Ready is not auto-unfrozen.** Next artifact = [`post-pmi-kernel-public-contract-preflight.md`](../tasks/post-pmi-kernel-public-contract-preflight.md) (public contracts only).

## Program PASS

Five spine modules ISOLATED (Recruitment, Boundary, Employment, Documents, Workforce) + PMI-UI v1 with parallel-primitive forbid + debt did not grow after PMI-1. Enforced jointly on HEAD by `check_pmi_x_program_exit.py`.

## Program STOP

Any PMI-X defect (failed checker, debt growth, active spine exception, missing hard-lock text, or in-exit remediation attempt) → **STOP** with classification + separate work item. Also: new untracked cross-module internal import, dual write authority, parallel UI primitive, or Kernel/Ready started by smuggling inside PMI.
