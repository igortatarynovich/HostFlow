# Recruitment Ready policy / composition separation (`transfer_policy_v1`)

**Status:** **PARKED** (classified fix — **policy / rule** — do not start until [`platform-modularization-isolation-cutover.md`](platform-modularization-isolation-cutover.md) **PASS**)  
**Layer:** L3 work item — **not** Full Spine PASS · **not** five layer gap-fixes · **not** kernel bypass  
**Phase class:** platform  
**Opened:** 2026-09-16  
**Defect class (ADR-042 §6):** **policy / rule** (with **policy → topology leak** on unconditional layers)  
**Parent STOP:** [`dual-zero-policy-preflight.md`](dual-zero-policy-preflight.md) — P1 full Ready **STOP** 2026-09-15  
**Architecture:** [`ADR-042`](../architecture/ADR-042-spine-policy-separation.md) (**Accepted**) · inventory [`spine-policy-separation-inventory.md`](spine-policy-separation-inventory.md)  
**Analog:** [`admit-policy-ruleset-separation.md`](admit-policy-ruleset-separation.md) **PASS** (P4)  
**Amends (when done):** [`transfer-policy.md`](../workflows/transfer-policy.md) — process-policy contract vs pluggable Ready composition  
**Does not open:** Kernel walk · dual-preflight retry as this slice · PEM-1 composition · Hub type spam · Hiring E2E · Admit rewrite · five parallel gap-fixes

> Goal is **not** “make Full Spine green.”  
> Goal is remove an **ADR-042 violation**: Ready today is several policy machines AND-ed as topology, with **no** authority that selects the active composition.  
> **Kernel is not this slice.**

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
transfer_policy_v1 = process-policy contract
  → Recruitment context
  → Ready policy / composition resolver  (separate authority)
  → active ruleset / composition
  → existing rule evaluators (package, confirmations, fields, engine, ops, R5)
  → aggregator → verdict
  → transfer_allowed = (verdict == allowed)

Three compositions — one Ready pipeline (machine gate):
  []                         → allowed / transfer_allowed=true
  driver/default + missing   → missing (+ next_action)
  driver/default + satisfied → allowed / transfer_allowed=true

Regression (same pipeline):
  production driver composition still emits current driver requirements
  destinations / routing remain topology-integration (not policy requirements)
```

---

## Technical lock (before runtime) — resolver ≠ evaluator

**Hard lock:** composition **resolution** is a **separate authority** from evaluation — same lock as Admit.

`TransferPolicyResolver.resolve` / PE `evaluate_transition` **must not** themselves decide “this is a driver → therefore pack slots + confirmations + first_contact.” That would only migrate hardcode from AND-formula into implicit selection.

### Pipeline (frozen)

```text
Recruitment context
  → Ready policy / composition resolver
  → resolved composition (may be [])
  → existing evaluators as rule/evidence sources for that composition
  → aggregator → verdict
  → transfer_allowed   (derivative only: verdict == allowed)
```

### Responsibilities (clean split)

| Authority | Owns | Must not own |
|-----------|------|----------------|
| **Resolver** | Which Ready **composition** applies — including штатный `[]` | Evidence checks; AND-ing every capability unconditionally |
| **Composition / ruleset** | Which capabilities are **applicable** (docs, fields, confirmations, ops, slots, …) | Process topology; choosing itself |
| **Existing evaluators** | Whether an applicable rule’s condition holds (package, PE fields, R5, ops, confirmations, engine) | Selecting the composition; inventing a second Ready spine |
| **Aggregator** | `allowed` / `blocked` / `missing` / `unsupported_context` + `next_action` | Forging `transfer_allowed` without verdict |
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

## What is broken (evidence — dual preflight)

| Fact | Source |
|------|--------|
| No Ready analog of `admit_ruleset_id=empty` | `TransferPolicyResolver`; dual-zero gate |
| `r5_required_set=∅` expressible; full Ready not | R5 overlay vs AND formula |
| Unconditional conjuncts | `transfer_allowed = handoff_allowed ∧ readiness_ok ∧ docs_ready ∧ pkg.ready ∧ ¬confirmations ∧ ops_ready` |
| Hardwired dossier | `VERIFICATION_SLOT_DEFS` / `_HANDOFF_REQUIRED_DATA_BLOCKS` in package readiness |
| Kernel blocked | Dual preflight STOP; P4 Admit already PASS |

P1 Ready is therefore **not** a composable policy engine in the ADR-042 sense — it is an **aggregate of several policy machines without a composition authority**.

---

## Hard bans (this slice)

| Ban | Why |
|-----|-----|
| Five separate gap-fixes (package / confirmations / fields / slots / ops) | Bottom-up; repeats Admit-as-checklist error |
| Declaring those capabilities illegitimate | Capability ≠ applicability |
| `neutral=true` / `kernel_mode` / `skip_requirements` | Second path; ADR-042 §4a |
| Forged `transfer_allowed` / operator Ready flag | False continuity |
| Evaluator chooses composition (“driver → slots”) inside resolve-AND | Hardcode migrates |
| Treating `[]` as `unsupported_context` | Empty composition is valid → `allowed` |
| Folding destinations into policy requirements | Routing ≠ Ready ruleset |
| Opening Kernel walk or dual-preflight retry mid-slice | Premature |
| Candidate mint / evidence stuffing to green `[]` | Masks leak |
| Touching P4 Admit / ESO-5 | Wrong surface |

---

## Target design (minimal)

```text
Recruitment context
  → Ready policy / composition resolver   ← separate authority
  → resolved composition (may be [])
  → evaluate applicable rules via existing engines
  → aggregate → allowed | blocked | missing | unsupported_context
  → transfer_allowed = (verdict == allowed)
```

| Composition | Contents (illustrative) | Same pipeline? |
|-------------|-------------------------|----------------|
| `[]` (empty) | No policy-owned requirements | **Yes** → `allowed` |
| Driver / default (production) | Qualification/docs/fields/confirmations/ops as **today’s** driver Ready | **Yes** → missing if unsatisfied; allowed if satisfied |
| Other vacancy | Different applicable set on the **same** Ready process contract | **Yes** — not a second spine |

Process contract remains Recruitment-owned Ready / Transfer. Driver product policy stays valid as **composition**, not evaluator topology.

---

## Out of scope for this slice

- Dual zero-policy **retry** (after this PASS only)  
- P1→P6 Kernel witness  
- PEM-1 Policy Composition proof  
- Changing P2 destination / tenant-link **ownership** (keep; don’t policy-ify)  
- Admit / ESA rewrite  
- Evidence Hub identity work  

---

## Sequence lock

```text
Kernel NOT PASS
  → Admit ruleset separation PASS
  → Dual zero-policy preflight STOP (P4 PASS · P1 STOP)
  → THIS: Ready policy / composition separation
  → Dual zero-policy preflight retry (full Ready [] + Admit [])
  → New person P1→P6 Baseline Kernel witness
  → PEM-1 composition proof
```

Do **not** jump from this OPEN/PASS straight to Kernel walk.

---

## PASS / STOP

| Outcome | When |
|---------|------|
| **PASS** | Resolver is a **separate authority** from evaluate; one pipeline proves `[]` → `allowed`, driver/default + missing → `missing`, same composition + satisfied → `allowed`; production driver requirements regress; routing/destination semantics preserved; no banned bypass; L2 `transfer-policy` amended |
| **STOP** | Named hole + keep class **policy / rule** (or reclassify if evidence shows otherwise) |

**Current:** **PARKED** — do not implement until [`platform-modularization-isolation-cutover.md`](platform-modularization-isolation-cutover.md) **PASS**.

---

## Next

0. [`platform-modularization-isolation-cutover.md`](platform-modularization-isolation-cutover.md) **PASS**.  
1. Then implement / seal Ready process-policy + composition boundary (this brief) — **one** item, not five.  
2. Retry [`dual-zero-policy-preflight.md`](dual-zero-policy-preflight.md) until **both** P1 and P4 `[]` → allowed.  
3. Resume [`baseline-full-spine-kernel-proof.md`](baseline-full-spine-kernel-proof.md).  
4. PEM-1 composition only after kernel PASS.
