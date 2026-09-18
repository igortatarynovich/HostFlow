# Recruitment Ready policy / composition separation (`transfer_policy_v1`)

**Status:** **PASS** (2026-09-17)  
**Layer:** L3 work item — **not** Full Spine PASS · **not** five layer gap-fixes · **not** kernel bypass  
**Phase class:** platform  
**Opened:** 2026-09-16 (PARKED) · **Authorized / Active:** 2026-09-17 · **Closed:** 2026-09-17  
**Named gate:** `recruitment-ready-policy-composition-separation-gate`  
**Defect class (ADR-042 §6):** **policy / rule** (with **policy → topology leak** on unconditional layers) · public-contract class: **missing composition expression**  
**Parent STOP (authorizing):** [`post-pmi-kernel-public-contract-preflight.md`](post-pmi-kernel-public-contract-preflight.md) — Recruitment step 1 **STOP** 2026-09-17  
**Prior evidence STOP:** [`dual-zero-policy-preflight.md`](dual-zero-policy-preflight.md) — P1 full Ready **STOP** 2026-09-15 (internals-facing; not the authorization trigger after PMI-X)  
**Architecture:** [`ADR-042`](../architecture/ADR-042-spine-policy-separation.md) (**Accepted**) · inventory [`spine-policy-separation-inventory.md`](spine-policy-separation-inventory.md)  
**Analog:** [`admit-policy-ruleset-separation.md`](admit-policy-ruleset-separation.md) **PASS** (P4)  
**Amends:** [`transfer-policy.md`](../workflows/transfer-policy.md) — process-policy contract vs pluggable Ready composition  
**Does not open:** Kernel walk · dual-preflight retry as this slice · PEM-1 composition · Hub type spam · Hiring E2E · Admit rewrite · five parallel gap-fixes  
**Public-contract obligation:** **met** — `recruitment.public.ready` accepts stable external selector/context, resolves composition privately, returns canonical Ready verdict (incl. `[]`), cold-import standalone.

> Goal is **not** “make Full Spine green.”  
> Goal is remove an **ADR-042 violation**: Ready today is several policy machines AND-ed as topology, with **no** authority that selects the active composition.  
> **Kernel is not this slice.**  
> Scope is **one** missing architectural authority — composition selection — **not** five symptom remediations.

---

## Original Goal → Completion Proof

**Problem this fix must permanently remove:**

`TransferPolicyResolver` / PE Ready evaluate mix two levels:

| Level | Should be | Today |
|-------|-----------|--------|
| **Process contract** | Recruitment answers: may this person leave Recruitment (Ready / Transfer)? | Collapsed into unconditional AND of every layer |
| **Policy composition** | Which rules apply for this Recruitment context (empty / driver / warehouse / …) | **No resolver** — R5 overlay empties only one layer; package, confirmations, fields, slots, ops still fire |

Current semantics (wrong):

```text
transfer_allowed = eligibility ∧ package.ready ∧ ¬confirmations ∧ ops_ready ∧ …
                  (each layer independently mandatory)
```

Required semantics (ADR-042 — same as Admit after PASS):

```text
transfer_allowed = active Ready policy evaluated to allowed
```

**Preserve layers as capabilities.** Do **not** declare `recruitment_package`, confirmations, fields, engine, ops, or R5 “bad.”  
The defect is **unconditional applicability**: they participate in Ready whether or not the selected composition includes them.

**Architectural conclusion (preserve from dual preflight):**  
Zero-requirement is a mandatory property of a **composable** policy engine. `r5_required_set=∅` alone ≠ Ready `[]`. If empty composition cannot yield штатный `allowed` on the **full** aggregator, remaining layers are still topology.

**Completion proof (named consumer):**

```text
public context / policy selection
  → recruitment.public.ready
  → Recruitment-owned resolver          (selects composition; private)
  → private composition (may be [])
  → existing evaluators (only applicable rules)
  → aggregator → canonical Ready verdict
  → transfer_allowed = (verdict == allowed)   # derivative only

Three states — one architecture (machine gate):
  []                         → allowed / transfer_allowed=true
                               (requirements NOT invoked — not fixture-green)
  production driver + missing → missing (+ next_action / actionable)
  same production + satisfied → allowed / transfer_allowed=true

Regression (same pipeline):
  production driver composition still emits current driver requirements
  destinations / routing remain topology-integration (not policy requirements)
  cold-process import of recruitment.public.ready succeeds (no process_engine pre-import)
```

---

## Implementation locks (normative — 2026-09-17)

Hard constraints for this slice. Violating any of these = **not PASS**, even if `transfer_allowed` looks green.

### 1. Public contract must not accept internal ruleset structure

`recruitment.public.ready` accepts a **stable external selector / context** only.  
Recruitment-owned resolver chooses the composition. Composition **contents** stay private.

```text
CORRECT:
  public context / policy selection
    → Recruitment resolver
    → private composition
    → evaluators
    → public verdict

FORBIDDEN:
  Kernel → ["package", "r5", "confirmations", …] → Recruitment
```

Publishing capability lists (package / R5 / confirmations / fields / ops / slots) as public input is a **new internals leak**, not a contract fix.  
`composition_id="empty"` (or equivalent) is a **registered policy composition** selected by the same resolver — **not** a Kernel-passed inventory of absences.

### 2. One canonical Ready verdict object

After cutover, the **only** external process authority from Ready is a single verdict:

| Field | Role |
|-------|------|
| `decision` | `allowed` \| `missing` \| `blocked` \| `unsupported_context` |
| `next_action` | Present where applicable (`missing` / actionable paths) |
| `transfer_allowed` | **Derived only:** `decision == allowed` |

`readiness_ok`, `docs_ready`, `pkg.ready`, confirmation lists, ops flags, and similar may remain **internal evidence for the aggregator**. They must **not** remain peer process authorities on the public surface.

### 3. `[]` → `allowed` proves absence of invoked requirements

Gate must catch “pipeline still runs package / fields / confirmations / ops, but a stuffed fixture happens to be green.”

For the empty-composition proof:

- Candidate / fixture is **minimal** and does **not** satisfy legacy driver requirements.  
- PASS requires evidence that policy-owned evaluators for package / fields / confirmations / ops / slots / R5 were **not invoked as requirements** for `[]` (applicability empty), not merely that the final boolean is true.  
- Stuffing contacts / docs / confirmations to green `[]` remains **forbidden**.

### 4. Cold-import circularity is in this work item

Parent STOP requires a **usable** `recruitment.public.ready`.  
If the facade only works after a prior `process_engine` import, it is not a standalone public contract.

PASS **includes**: cold-process import / probe of `recruitment.public.ready` with **no** import-order dependency on `process_engine` (or other adjacency tricks). This is not a separate cosmetic bug.

### 5. Production regression = three states of one architecture

Not only the missing case. Machine gate must prove:

| Composition | State | Required result |
|-------------|-------|-----------------|
| `[]` (empty) | minimal unsatisfied-vs-driver fixture | `allowed` + no requirement invocation |
| production driver | unsatisfied | `missing` + expected actionable `next_action` |
| same production composition | satisfied | `allowed` |

This blocks the false cutover “empty works, real Ready broken.”

### Empty ≠ new `kernel_mode`

The most dangerous failure mode: `composition_id="empty"` (or `zero_requirement`) as a renamed bypass.

Empty composition **must**:

- be an ordinary registered policy composition;  
- pass through the **same** resolver → evaluator → aggregator path as production;  
- have **no** special short-circuit, `neutral`, `skip_requirements`, or second Ready spine.

---

## Technical lock (before runtime) — resolver ≠ evaluator

**Hard lock:** composition **resolution** is a **separate authority** from evaluation — same lock as Admit.

`TransferPolicyResolver.resolve` / PE `evaluate_transition` **must not** themselves decide “this is a driver → therefore pack slots + confirmations + first_contact.” That would only migrate hardcode from AND-formula into implicit selection.

### Pipeline (frozen)

```text
public context / policy selection
  → Ready policy / composition resolver     # separate authority
  → resolved private composition (may be [])
  → existing evaluators as rule/evidence sources for that composition only
  → aggregator → canonical Ready verdict
  → transfer_allowed   (derivative only: verdict == allowed)
```

### Responsibilities (clean split)

| Authority | Owns | Must not own |
|-----------|------|----------------|
| **Public selector / context** | Stable external policy selection inputs | Internal capability lists; ruleset structure |
| **Resolver** | Which Ready **composition** applies — including штатный `[]` | Evidence checks; AND-ing every capability unconditionally; leaking composition contents outward |
| **Composition / ruleset** | Which capabilities are **applicable** (docs, fields, confirmations, ops, slots, …) — **private** | Process topology; choosing itself; becoming public Kernel input |
| **Existing evaluators** | Whether an applicable rule’s condition holds (package, PE fields, R5, ops, confirmations, engine) | Selecting the composition; inventing a second Ready spine; acting when not applicable |
| **Aggregator** | Canonical `allowed` / `blocked` / `missing` / `unsupported_context` + `next_action` | Forging `transfer_allowed` without verdict; publishing peer layer flags as authorities |
| **`transfer_allowed`** | Pure derivative of verdict (`== allowed`) | Operator flag / kernel_mode / special empty bypass |

### Capability ≠ applicability

| Capability (keep) | Wrong use today | Right use after this fix |
|-------------------|-----------------|---------------------------|
| `recruitment_package` / dossier slots | Always in `pkg.ready` for Ready | Rule/evidence source **if** composition includes those slots |
| `recruiter_confirmation` | Always pending confirmations after blocks go `ready` | Applicable only when composition requires confirmation of those blocks |
| `field_requirements` | PE phone/email/address always gate Ready | Applicable fields for this composition only |
| `requirement_engine` pack slots | Fire even when R5 is empty | Slots belong to composition, not to process existence |
| `operational_requirements` | `first_contact_completed` always for some profiles | Ops rules only if composition lists them |
| R5 / `document_packs` | Partial overlay — only one emptiable layer | Documents as rules inside the **same** composition |

If resolver штатно returns `[]`, **policy-owned** requirements from the table above are **absent** → same aggregator → **`allowed`**.  
Stuffing a candidate with contacts/docs/confirmations to green `[]` is **forbidden**.

### `unsupported_context`

| Meaning after this fix | Forbidden meaning |
|------------------------|-------------------|
| Resolver **cannot determine** an applicable Ready composition | “We still have package/ops” / empty composition |
| | `[]` treated as unsupported |

### Routing stays topology / integration

`process_engine_handoff_rules` / `tenant_link` / `destinations_allowed` / `handoff_create_allowed` are **not** Ready policy requirements.

- `transfer_allowed` = Ready process-policy verdict (may this person be Ready).  
- Destination / create-handoff remain routing + integration; they must **not** be folded into the empty composition as fake policy items.  
- Regression: destination semantics **must still exist** after separation.

---

## What is broken (evidence — dual preflight + public-contract STOP)

| Fact | Source |
|------|--------|
| No Ready analog of `admit_ruleset_id=empty` on a composition resolver | `TransferPolicyResolver`; dual-zero gate |
| Public Ready has no external selector → private composition path | public-contract preflight STOP 2026-09-17 |
| Cold import of `recruitment.public.ready` fails without `process_engine` first | public-contract preflight gate |
| `r5_required_set=∅` expressible; full Ready not | R5 overlay vs AND formula |
| Unconditional conjuncts | `transfer_allowed = handoff_allowed ∧ readiness_ok ∧ docs_ready ∧ pkg.ready ∧ ¬confirmations ∧ ops_ready` |
| Hardwired dossier | `VERIFICATION_SLOT_DEFS` / `_HANDOFF_REQUIRED_DATA_BLOCKS` in package readiness |
| Peer layer flags act as process authorities | public surface / transfer report shape |

P1 Ready is therefore **not** a composable policy engine in the ADR-042 sense — it is an **aggregate of several policy machines without a composition authority**.

---

## Hard bans (this slice)

| Ban | Why |
|-----|-----|
| Five separate gap-fixes (package / confirmations / fields / slots / ops) | Bottom-up; repeats Admit-as-checklist error |
| Declaring those capabilities illegitimate | Capability ≠ applicability |
| Kernel / public input = list of internal Ready capabilities | Internals leak through the new contract |
| `neutral=true` / `kernel_mode` / `skip_requirements` / empty-as-bypass | Second path; ADR-042 §4a; renamed bypass |
| Forged `transfer_allowed` / operator Ready flag | False continuity |
| Peer public authorities (`docs_ready`, `pkg.ready`, …) alongside verdict | Multiple process truths |
| Evaluator chooses composition (“driver → slots”) inside resolve-AND | Hardcode migrates |
| Treating `[]` as `unsupported_context` | Empty composition is valid → `allowed` |
| Green `[]` via stuffed fixture while requirements still invoke | Masks leak; fails lock §3 |
| Leaving cold-import cycle for “later” | Parent STOP requires usable public Ready |
| Folding destinations into policy requirements | Routing ≠ Ready ruleset |
| Opening Kernel walk or dual-preflight retry mid-slice | Premature |
| Candidate mint / evidence stuffing to green `[]` | Masks leak |
| Touching P4 Admit / ESO-5 | Wrong surface |
| Post-PASS Recruitment polish before re-entering preflight | Breaks STOP-driven discipline |

---

## Target design (minimal)

```text
public context / policy selection
  → recruitment.public.ready
  → Ready policy / composition resolver   ← separate authority (Recruitment-owned)
  → private composition (may be [])
  → evaluate applicable rules via existing engines
  → aggregate → canonical Ready verdict
  → transfer_allowed = (verdict == allowed)
```

| Composition | Contents (illustrative, **private**) | Same pipeline? |
|-------------|--------------------------------------|----------------|
| `[]` (empty) | No policy-owned requirements | **Yes** → `allowed` (no requirement invocation) |
| Driver / default (production) | Qualification/docs/fields/confirmations/ops as **today’s** driver Ready | **Yes** → missing if unsatisfied; allowed if satisfied |
| Other vacancy | Different applicable set on the **same** Ready process contract | **Yes** — not a second spine |

Process contract remains Recruitment-owned Ready / Transfer. Driver product policy stays valid as **composition**, not evaluator topology.

---

## Out of scope for this slice

- Dual zero-policy **retry** (after this PASS **and** public-contract preflight PASS only)  
- P1→P6 Kernel witness  
- PEM-1 Policy Composition proof  
- Changing P2 destination / tenant-link **ownership** (keep; don’t policy-ify)  
- Admit / ESA rewrite  
- Evidence Hub identity work  
- Further Recruitment remediation beyond this one authority  

---

## Sequence lock

```text
Kernel NOT PASS
  → Admit ruleset separation PASS
  → Dual zero-policy preflight STOP (P4 PASS · P1 STOP)
  → PMI program PASS (Ready still not auto-unfrozen)
  → Public-contract Kernel preflight STOP (Recruitment step 1)  ← authorizing
  → THIS: Ready policy / composition separation                 ← ACTIVE
  → THIS PASS
  → Re-enter Post-PMI Public-Contract Preflight at step 1       ← immediate; no Recruitment polish
       (only if Recruitment green via public surface → Employment → Boundary → Documents → Workforce)
  → Dual zero-policy preflight retry (full Ready [] + Admit [])
  → New person P1→P6 Baseline Kernel witness
  → PEM-1 composition proof
```

Do **not** jump from this OPEN/PASS straight to Kernel walk or dual zero-policy.  
Do **not** continue improving Recruitment after this PASS — return to preflight step 1.

---

## PASS / STOP

| Outcome | When |
|---------|------|
| **PASS** | All implementation locks §1–§5 hold; resolver separate from evaluate; three-state machine gate green on one architecture; `[]` proves non-invocation on minimal fixture; canonical Ready verdict is the sole public process authority (`transfer_allowed` derived); cold-process import/probe of `recruitment.public.ready` with no import-order dependency; empty is ordinary composition not bypass; routing/destination semantics preserved; no banned path; L2 `transfer-policy` amended |
| **STOP** | Named hole + keep class **policy / rule** (or reclassify if evidence shows otherwise) |

**Current:** **PASS** (2026-09-17). Gate: `test_recruitment_ready_policy_composition_separation_gate.py`.

---

## Next

1. ~~Implement / seal Ready process-policy + composition boundary~~ **PASS**.  
2. **Immediate:** re-enter [`post-pmi-kernel-public-contract-preflight.md`](post-pmi-kernel-public-contract-preflight.md) at **step 1**. No further Recruitment polish. Continue to Employment / Boundary / Documents / Workforce **only** if Recruitment passes through the public surface.  
3. After full preflight **PASS**: retry [`dual-zero-policy-preflight.md`](dual-zero-policy-preflight.md) until **both** P1 and P4 `[]` → allowed.  
4. Resume [`baseline-full-spine-kernel-proof.md`](baseline-full-spine-kernel-proof.md).  
5. PEM-1 composition only after kernel PASS.
