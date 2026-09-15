# Admit policy / ruleset separation (`employment_start_allowed.v1`)

**Status:** **OPEN** (classified fix — **policy / rule**)  
**Layer:** L3 work item — **not** Full Spine PASS · **not** evidence/Hub gap · **not** kernel bypass  
**Phase class:** platform  
**Opened:** 2026-09-15  
**Defect class (ADR-042 §6):** **policy / rule**  
**Parent STOP:** [`baseline-full-spine-kernel-proof.md`](baseline-full-spine-kernel-proof.md) — preflight STOP 2026-09-15  
**Architecture:** [`ADR-042`](../architecture/ADR-042-spine-policy-separation.md) (**Accepted**) · inventory [`spine-policy-separation-inventory.md`](spine-policy-separation-inventory.md)  
**Amends (when done):** [`employment-start-allowed.md`](../architecture/employment-start-allowed.md) — process-policy contract vs PEM-1 ruleset  
**Does not open:** Kernel walk · PEM-1 composition proof · Hub type spam · Hiring E2E · Release Readiness

> Goal is **not** “make Full Spine green.”  
> Goal is remove an **ADR-042 violation**: Admit today is a PEM-1 policy dressed as a general process evaluator.

---

## Original Goal → Completion Proof

**Problem this fix must permanently remove:**

`employment_start_allowed.v1` mixes two levels:

| Level | Should be | Today |
|-------|-----------|--------|
| **Process contract** | Employment answers: may this person transition to Start? | Collapsed into PEM-1 checklist |
| **Policy composition** | Ruleset for a given employment context (PEM-1 = Contract + Medical + BHP + facts) | **Hardcoded** as the evaluator body |

Current semantics (wrong):

```text
start_allowed = PEM-1 requirements satisfied
```

Required semantics (ADR-042):

```text
start_allowed = active Admit policy evaluated to allowed
```

PEM-1 becomes **one ruleset** of that policy — not the structure of the evaluator.

**Architectural conclusion (preserve):**  
Zero-requirement policy is **not** a special kernel feature. It is a **mandatory property** of a composable policy engine. If the engine cannot correctly evaluate an empty composition, rules are still part of its topology.

**Completion proof (named consumer):**

```text
employment_start_allowed.v1 = process-policy contract
  → policy context → resolve ruleset → evaluate rules → aggregate verdict
  → allowed | blocked | missing | unsupported_context (+ next_action)
  → start_allowed derived from verdict

ruleset []     → same pipeline → allowed (no rule forbids transition)
ruleset PEM-1  → same pipeline → Contract + Medical + BHP rules → same verdict contract

machine gate: empty ruleset + PEM-1 ruleset on one evaluator
  → no neutral=true / skip_requirements / kernel_mode / test-only path
```

---

## What is broken (evidence)

| Fact | Source |
|------|--------|
| Evaluator has **no** ruleset / configuration parameter | `evaluate_employment_start_allowed_v1` signature |
| PEM-1 triad inline hardcoded | `REQ_CONTRACT` / `REQ_MEDICAL` / `REQ_BHP` list inside evaluate |
| Non-PEM-1 → `unsupported_context`, not empty-ruleset `allowed` | preflight 2026-09-15 |
| Kernel proof STOP | Cannot express zero-requirement on Admit without bypass |

P4 Admit is therefore **not** a policy engine in the ADR-042 sense — it is a **PEM-1 policy composition** presented as the general process evaluator.

---

## Hard bans (this slice)

| Ban | Why |
|-----|-----|
| `neutral=true` / `kernel_mode` / `skip_requirements` | Second path; violates ADR-042 §4a |
| Separate test-only Admit evaluator | Shadow spine |
| Tenant flag “no BHP for kernel” | Bypass |
| Optional flags on Contract/Medical/BHP inside current function | Leaves PEM-1 as architectural skeleton with switches |
| Opening Kernel walk mid-slice | Premature |
| Framing as Hub/evidence fix | Wrong class |

---

## Target design (minimal)

```text
policy context
  → resolve active Admit ruleset (by employment context / authority)
  → evaluate each rule
  → aggregate → allowed | blocked | missing | unsupported_context
  → start_allowed = (verdict == allowed)
```

| Ruleset | Contents | Same evaluator? |
|---------|----------|-----------------|
| `[]` (empty) | No rules | **Yes** → `allowed` because nothing forbids |
| `PEM-1` | Contract + Medical + BHP (+ listed exceptions / planned_start facts as today) | **Yes** → same verdict contract |

Process contract remains Employment-owned admit-to-work. PEM-1 product decision stays valid as **composition**, not as evaluator topology.

---

## Out of scope for this slice

- Full Ready (P1) multi-layer zero-policy (separate preflight after this)  
- P1→P6 Kernel witness  
- PEM-1 Policy Composition proof  
- Changing ESO-5 Confirm semantics (still requires `start_allowed=true`)  
- Evidence Hub identity work (already classified elsewhere)

---

## Sequence lock (after this OPEN)

```text
Kernel NOT PASS
  → THIS: Admit policy / ruleset separation (policy/rule)
  → Short dual preflight: full Ready evaluator + Admit evaluator
       each with zero-requirement composition → штатный allowed
  → New person P1→P6 Baseline Kernel witness
  → PEM-1 composition proof
```

Do **not** jump from this fix straight to Kernel walk.

### P1 reminder (not this slice)

`r5_required_set = ∅` via overlay remove is **not** yet neutral Recruitment policy. Ready aggregates multiple layers (eligibility, package, field requirements, requirement engine). After Admit separation: **short policy preflight** must prove:

1. **Recruitment:** full Ready evaluator (not R5 alone) + zero-requirement composition → `allowed`  
2. **Employment:** Admit evaluator + zero-requirement composition → `allowed` / `start_allowed=true`

Only then spend a new person on P1→P6.

---

## PASS / STOP

| Outcome | When |
|---------|------|
| **PASS** | Process-policy contract + ruleset resolve on one evaluator; `[]` → allowed штатно; PEM-1 ruleset → same pipeline; machine gate; no banned bypass; L2 `employment-start-allowed` amended accordingly |
| **STOP** | Named hole + keep class **policy / rule** (or reclassify if evidence shows otherwise) |

**Current:** **OPEN** / not PASS.

---

## Next

1. Implement / seal Admit process-policy + ruleset boundary (this brief).  
2. Dual zero-policy preflight (P1 full Ready + P4 Admit).  
3. Resume [`baseline-full-spine-kernel-proof.md`](baseline-full-spine-kernel-proof.md).  
4. PEM-1 composition only after kernel PASS.
