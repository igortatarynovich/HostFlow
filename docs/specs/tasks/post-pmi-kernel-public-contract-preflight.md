# Post-PMI Kernel Public-Contract Preflight

**Status:** **PASS** (retry 2026-09-17 — all five `*.public.*` steps)  
**Date opened:** 2026-09-16  
**Date closed (prior attempt):** 2026-09-17 (**STOP** Recruitment)  
**Date closed (this attempt):** 2026-09-17 (**PASS**)  
**Parents:** [`platform-modularization-isolation-cutover.md`](platform-modularization-isolation-cutover.md) · [`platform-modularization-isolation-cutover-gate.md`](../gates/platform-modularization-isolation-cutover-gate.md) · [`ADR-042`](../architecture/ADR-042-spine-policy-separation.md) · [`pmi-x-program-exit-inventory.md`](pmi-x-program-exit-inventory.md)  
**Module-local fix (closed):** [`recruitment-ready-policy-composition-separation.md`](recruitment-ready-policy-composition-separation.md) (**PASS**)  
**Named gate:** `post-pmi-kernel-public-contract-preflight-gate`  
**Next:** [`dual-zero-policy-preflight.md`](dual-zero-policy-preflight.md) retry (not P1→P6 / PEM-1)  
**Does not:** reopen PMI · dig module internals from outside · bypass `*.public.*` facades · start PEM-1 / Full Spine / P1→P6 witness · prove internal module correctness

---

## Results (prior attempt 2026-09-17 — STOP)

| Step | Module | Result | Notes |
|------|--------|--------|-------|
| 1 | Recruitment | **STOP** | Public Ready could not express zero-requirement composition |
| 2–5 | — | **not executed** | First substantial red |
| **Preflight** | — | **STOP** | Dual zero-policy / P1→P6 / PEM-1 **not opened** |

### STOP record (prior)

| Field | Content |
|-------|---------|
| `failing_public_contract` | `recruitment.public.ready` |
| `expected_process_result` | policy composition (incl. zero-requirement) → transition permission |
| `actual_result` | no composition selector; Ready composition PARKED; cold import circular |
| `defect_class` | missing composition expression / contract gap |
| `module_owner` | Recruitment |

**Remediation:** Ready composition separation **PASS** 2026-09-17. Retry below.

---

## Results (retry 2026-09-17 — PASS)

| Step | Module | Result | Notes |
|------|--------|--------|-------|
| 1 | Recruitment | **PASS** | `ready_composition_id=empty` → `evaluate_ready_transfer` → `decision=allowed` / `transfer_allowed=true`; cold import standalone; selector ≠ capability list |
| 2 | Employment | **PASS** | `employment.public.commands.evaluate_start_allowed_for_handoff` (+ accept / start apply); `employment_context` on public evaluate; Admit rulesets stay private |
| 3 | Boundary | **PASS** | `boundary.public.ready` validates RFE package (`ready_for_employment.v1`) without Recruitment internals; handoff + emit surfaces published |
| 4 | Documents | **PASS** | `documents.public.evidence` exposes evidence facts; no Ready/Admit/Started lifecycle authorities on `documents.public.*` |
| 5 | Workforce | **PASS** | `workforce.public.started` continuity consumer (`find_employee_by_candidate` / `ensure_hr_profiles_bundle` / `get_work_eligibility_profile`); no Ready/Admit re-eval |
| **Preflight** | — | **PASS** | Kernel prep does not require module internals; dual zero-policy is next (not P1→P6) |

**Evidence:** public-surface probes + `backend/tests/platform/test_post_pmi_kernel_public_contract_preflight_gate.py`. Internals not used for the PASS verdict.

---

## Question answered (only this)

Are the **published process contracts** of the five isolated spine modules **sufficient to prepare Kernel proof**?

This preflight does **not** prove that modules are internally correct. It answers whether Kernel can be approached **from outside** using only `*.public.*` contracts and their verdicts / transition permissions.

## Why this is not the old dual preflight

| Old dual preflight | This artifact |
|--------------------|---------------|
| Explored how modules implement Ready / slots / package / engines | Checks whether **published contracts** suffice for Kernel prep |
| Could diagnose via internals | May use **published process contracts only** |
| Often continued scanning for a full defect inventory | **First substantial red → STOP** (no defect shopping list) |
| Remediation assumed cross-cutting internals access | Defect → **classified STOP** → **module-owned** work item only |

## Development mode after PMI-X (normative)

- **Outward:** process contracts + verdicts / transition permissions  
- **Inward:** only the module owner, and only after a **classified STOP**  
- PMI must not become endless cleanup; residual debt stays shrink-only  

## Execution order (mandatory)

Execute **in this order**. Do not reorder to “get more evidence.” At the **first substantial red**, stop the preflight.

| # | Module | Probe (public only) | Process-level ask |
|---|--------|---------------------|-------------------|
| 1 | **Recruitment** | `recruitment.public.*` | Can Kernel obtain **transition permission** for a **zero-requirement** policy composition via the public contract? |
| 2 | **Employment** | `employment.public.*` | Analogously: can Kernel obtain the **Admit** (accept / admit-path) process result via the public contract? |
| 3 | **Boundary** | `boundary.public.*` | Can Boundary **accept** the published Recruitment output and form the **RFE / handoff** contract without reading Recruitment internals? |
| 4 | **Documents** | `documents.public.*` | Are **evidence facts** available only through the public contract, with **no** lifecycle decision authority attributed to Documents? |
| 5 | **Workforce** | `workforce.public.*` | Does a **public consumer** exist for the **Started Employee** contract (accept continuity without reconstructing Ready/Admit/evidence)? |

### First substantial red → STOP

- Do **not** continue the remaining steps to assemble a list of potential defects.  
- Do **not** enter the owning module’s internals from this proof.  
- Open a **separate** module-local work item from the STOP record below.

## STOP record (required fields)

| Field | Content |
|-------|---------|
| `failing_public_contract` | Concrete `*.public.*` surface / contract id that failed |
| `expected_process_result` | Process-level verdict / transition permission / handoff / evidence / continuity result expected |
| `actual_result` | What the public contract returned (or could not express) |
| `defect_class` | e.g. contract gap / wrong authority / missing composition expression / consumer missing |
| `module_owner` | Recruitment \| Boundary \| Employment \| Documents \| Workforce |

That set is **sufficient** to open the module-local item. No internals dump required.

## PASS criterion — absence of internals dependency

**Not needing internals is itself part of the proof.**

If the needed process-level result is obtainable **only because** the proof knows an internal helper, private module, or internal state structure — that is **not** a public-contract PASS, **even if** the eventual verdict value looks correct.

PASS requires: policy/input → `*.public.*` → expected process result, with the proof remaining ignorant of module internals.

## Canonical external chain (Recruitment)

```
policy composition → recruitment.public.* → verdict / transition permission
```

This is the Recruitment **public process contract** path for Kernel (incl. zero-requirement). If it cannot express the composition → **STOP** → **Recruitment-owned**.

Forbidden external probes (non-exhaustive): `recruitment_package`, `VERIFICATION_SLOT_DEFS`, `requirement_engine`, any non-`public` import or facade bypass.

## Symmetric spine rule

Kernel checks **contracts between modules**, not module machinery. Same forbid on every step: no neighbour-internals dig; no silent cross-module patch.

| Module | External chain | On STOP owner |
|--------|----------------|---------------|
| Recruitment | policy composition → `recruitment.public.*` → verdict / transition permission | Recruitment |
| Employment | Admit inputs → `employment.public.*` → admit/accept process result | Employment |
| Boundary | published Recruitment output → `boundary.public.*` → RFE/handoff contract | Boundary |
| Documents | evidence queries → `documents.public.*` → evidence facts (not lifecycle decisions) | Documents |
| Workforce | Started Employee → `workforce.public.*` → post-start continuity consumer | Workforce |

## Allowed probe surfaces

| Module | May probe |
|--------|-----------|
| Recruitment | `backend/app/modules/recruitment/public/**` only |
| Boundary | `backend/app/modules/boundary/public/**` only |
| Employment | `backend/app/modules/employment/public/**` only |
| Documents | `backend/app/modules/documents/public/**` only |
| Workforce | `backend/app/modules/workforce/public/**` only |

## Cycle position (do not dilute)

```
PMI-0 → PMI-1 → R → B → E → D → W → UI → PMI-X   ← CLOSED

→ Public-contract Kernel preflight   ← THIS (PASS 2026-09-17 retry)
  → classified module-local fix ONLY on STOP
       → recruitment-ready-policy-composition-separation  ← PASS (prior STOP)
  → dual zero-policy proof            ← NEXT (not P1→P6)
  → P1→P6 Kernel witness
  → PEM-1 policy composition
```

After **this** preflight **PASS**, the next step remains **dual zero-policy proof** — **not** an immediate jump to P1→P6.

Ready composition separation is **PASS**. No further Recruitment polish from this preflight.

## PASS / STOP summary

| Outcome | Meaning |
|---------|---------|
| **PASS** | Steps 1–5 succeed via `*.public.*` only; Kernel prep does not require internals knowledge |
| **STOP** | First substantial red + STOP record (five fields) + separate module-local work item |

## Explicit non-goals

- Proving internal correctness of Recruitment / Boundary / Employment / Documents / Workforce  
- Continuing after first red to inventory all defects  
- PMI allowlist / debt “дочистка”  
- Rewriting Ready before a classified Recruitment STOP  
- Skipping dual zero-policy to jump to P1→P6 / PEM-1  
- Treating historical dual-preflight remediation plans as still authoritative
