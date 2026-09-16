# Platform Modularization & Isolation Cutover Gate

**Status:** **OPEN** (PMI-0 **PASS**; PMI-1 **PASS**; PMI-R not started)  
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
| PMI-R…W ISOLATED | eight-row card + shrinking debt; foreign internals = OPEN | queued (PMI-R next) |
| PMI-UI | primitives + **CI forbid parallel primitives** | — |
| PMI-X | this file **PASS** | blocked |

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

## Program PASS

Five spine modules ISOLATED (Recruitment, Boundary, Employment, Documents, Workforce) + PMI-UI v1 with parallel-primitive forbid + debt did not grow after PMI-1.

## Program STOP

New untracked cross-module internal import, dual write authority, parallel UI primitive, or spine/Kernel work started before this gate PASS.
