# Admit policy / ruleset separation (`employment_start_allowed.v1`)

**Status:** **PASS** (2026-09-15)  
**Layer:** L3 work item — **not** Full Spine PASS · **not** evidence/Hub gap · **not** kernel bypass  
**Phase class:** platform  
**Opened:** 2026-09-15  
**Closed:** 2026-09-15  
**Defect class (ADR-042 §6):** **policy / rule**  
**Parent STOP:** [`baseline-full-spine-kernel-proof.md`](baseline-full-spine-kernel-proof.md) — preflight STOP 2026-09-15  
**Architecture:** [`ADR-042`](../architecture/ADR-042-spine-policy-separation.md) (**Accepted**) · inventory [`spine-policy-separation-inventory.md`](spine-policy-separation-inventory.md)  
**Amends:** [`employment-start-allowed.md`](../architecture/employment-start-allowed.md) — process-policy contract vs PEM-1 ruleset  
**Named gate:** `admit-policy-ruleset-separation-gate`  
**Does not open:** Kernel walk · PEM-1 composition proof · Hub type spam · Hiring E2E · Release Readiness · P1 Ready changes

> Goal was **not** “make Full Spine green.”  
> Goal was remove an **ADR-042 violation**: Admit was a PEM-1 policy dressed as a general process evaluator.

---

## Original Goal → Completion Proof

**Problem this fix permanently removed:**

`employment_start_allowed.v1` mixed two levels:

| Level | Should be | Was |
|-------|-----------|-----|
| **Process contract** | Employment answers: may this person transition to Start? | Collapsed into PEM-1 checklist |
| **Policy composition** | Ruleset for a given employment context (PEM-1 = Contract + Medical + BHP + facts) | **Hardcoded** as the evaluator body |

**Required semantics (ADR-042) — now runtime:**

```text
start_allowed = active Admit policy evaluated to allowed
```

PEM-1 is **one ruleset** — not the structure of the evaluator.

**Architectural conclusion (preserve):**  
Zero-requirement policy is **not** a special kernel feature. It is a **mandatory property** of a composable policy engine.

**Completion proof (machine — PASS):**

```text
employment_start_allowed.v1 = process-policy contract
  → Employment context
  → resolve_admit_ruleset_v1  (separate authority)
  → resolved ruleset
  → rule evaluators + aggregator → verdict
  → start_allowed = (verdict == allowed)

Three compositions — one evaluate path:
  []              → allowed / start_allowed=true
  PEM-1 + missing → missing
  PEM-1 + satisfied → allowed / start_allowed=true

Gate: admit-policy-ruleset-separation-gate
  + employment-start-allowed-gate (regression)
```

---

## Technical lock (sealed) — resolver ≠ evaluator

**Hard lock:** ruleset **resolution** is a **separate authority** from evaluation.

`evaluate_employment_start_allowed_v1` does **not** decide “this is a driver → therefore PEM-1.”

### Pipeline (frozen)

```text
Employment context
  → Admit policy / ruleset resolver
  → resolved ruleset
  → rule evaluators
  → aggregator → verdict
  → start_allowed   (derivative only: verdict == allowed)
```

### Responsibilities

| Authority | Owns | Must not own |
|-----------|------|----------------|
| **Resolver** (`resolve_admit_ruleset_v1`) | Which Admit composition applies — including штатный `[]` via `admit_ruleset_id=empty` | Evidence checks; verdict aggregation |
| **Ruleset** | Requirement set (PEM-1 = Contract + Medical + BHP + facts/exceptions) | Process topology |
| **Rule evaluators** | Individual rule satisfaction | Selecting the ruleset |
| **Aggregator** | `allowed` / `blocked` / `missing` / `unsupported_context` + `next_action` | Ruleset selection |
| **`start_allowed`** | Pure derivative of verdict (`== allowed`) | Independent policy decision |

### `unsupported_context`

| Meaning | Forbidden meaning |
|---------|-------------------|
| Resolver **cannot determine** an applicable Admit policy | “We don’t have PEM-1” / empty composition |
| | штатный `[]` treated as unsupported |

If the resolver returns `[]`, result is **`allowed`**.

---

## Runtime surface

| Symbol | Role |
|--------|------|
| `resolve_admit_ruleset_v1` | Separate authority |
| `evaluate_employment_start_allowed_v1` | resolve → evaluate → aggregate |
| `admit_ruleset_id` | Context key for explicit composition (`empty` / `PEM-1`); else PEM-1 axes inference |
| Evidence / typed exceptions / ESO-5 Confirm | **Unchanged** |

---

## Hard bans (honoured)

| Ban | Status |
|-----|--------|
| `neutral=true` / `kernel_mode` / `skip_requirements` | Absent |
| Evaluator chooses ruleset | AST-enforced: evaluate calls resolve; does not call `is_pem1_context` |
| Treating `[]` as `unsupported_context` | Gate proves `[]` → allowed |
| Opening Kernel walk | **Not opened** |
| Touching P1 Ready | **Not touched** |

---

## PASS / STOP

| Outcome | Evidence |
|---------|----------|
| **PASS** | Gate green; L2 amended; three compositions on one path; resolver ≠ evaluator |
| **STOP** | n/a — closed PASS |

**Current:** **PASS** — dual zero-policy preflight is **next** (not auto-started).

---

## Next (STOP here for this item)

1. Dual zero-policy preflight — [`dual-zero-policy-preflight.md`](dual-zero-policy-preflight.md) (**STOP** 2026-09-15: P4 PASS · P1 STOP).  
2. Classified Ready composability (separate) until dual preflight **PASS**.  
3. Resume [`baseline-full-spine-kernel-proof.md`](baseline-full-spine-kernel-proof.md) only after dual **PASS**.  
4. PEM-1 composition only after kernel PASS.

**Do not** jump from Admit PASS straight to Kernel walk.
