# PMI-X Inventory — Program exit verification

**Status:** CLOSED with PMI-X PASS (2026-09-16)  
**Nature:** joint verification only — **not** a remediation slice  
**Gate:** [`platform-modularization-isolation-cutover-gate.md`](../gates/platform-modularization-isolation-cutover-gate.md)  
**Checker:** `scripts/architecture/check_pmi_x_program_exit.py`  
**Next artifact:** [`baseline-full-spine-kernel-proof.md`](baseline-full-spine-kernel-proof.md) (authorized by dual zero-policy **PASS** 2026-09-17)

---

## Hard locks (normative)

1. **PMI-X fixes nothing.** Any defect discovered at exit = **STOP** with classification + **separate work item**. No in-exit cleanup, allowlist edit, or “small fix.”
2. **PASS is HEAD-simultaneous.** Historical PMI-R/B/E/D/W/UI stamps are insufficient. The full enforcement suite must pass **together on one revision** (`head` in checker JSON).
3. **Ready is not auto-unfrozen.** PMI-X does **not** reopen Ready composition. Next cycle starts only at public-contract Kernel preflight; only that preflight’s STOP may classify a Recruitment-owned policy fix.

## Criteria (all machine-checked on HEAD)

| Criterion | Result |
|-----------|--------|
| Five backend cards ISOLATED (R/B/E/D/W) + UI card | **PASS** |
| B/E/D/W foreign→internals = 0 | **PASS** |
| Recruitment spine foreign→internals = 0 | **PASS** |
| Spine traffic only via `*.public.*` | **PASS** |
| PMI-1 ratchet 2006→1557 (−449); no growth | **PASS** |
| One UI authority; UI debt 8 shrink-only | **PASS** |
| New decision reconstructors forbidden | **PASS** (UI checker) |
| All checkers green **together** on HEAD | **PASS** |
| Ready / dual-preflight / Kernel / PEM-1 not smuggled | **PASS** |
| Ready not auto-unfrozen | **PASS** |
| No active exception reopening spine ISOLATED | **PASS** |

## Explicit non-criteria

- Backend debt 1557 → 0  
- UI debt 8 → 0  
- Non-spine Recruitment residual (≤63) → 0  
- Full Spine / Kernel witness / PEM-1  
- Auto-resume of pre-PMI Ready remediation  

## Program boundary (closed)

```
PMI-0 map → PMI-1 freeze → R → B → E → D → W → UI → PMI-X
```

## Proof cycle after PMI (different program)

```
Public-contract Kernel preflight
  → classified module-local fix ONLY on STOP
  → dual zero-policy proof
  → P1→P6 Kernel witness
  → PEM-1 policy composition
```

External Recruitment question is only: can `recruitment.public.*` fulfill its process contract?  
Forbidden external probes include `recruitment_package`, `VERIFICATION_SLOT_DEFS`, `requirement_engine`.

## Debt posture after exit

| Bucket | Ceiling | Rule |
|--------|--------:|------|
| Backend PMI-1 debt | 1557 | shrink-only |
| UI isolation debt | 8 | shrink-only |
| Recruitment non-spine residual | 63 | shrink-only; spine owners = 0 |
