# Goal Completion Gate

**Status:** **NORMATIVE** (L2 operating — mandatory for platform phase close)  
**Date:** 2026-08-20  
**Trusted base:** `integration/release-product-a-b`  
**Parents:** [Architecture Review Checklist](../architecture/architecture-review-checklist.md) · [Sequential queue](../tasks/sales-to-comms-sequential-queue.md) · [Platform Completion Roadmap](../architecture/platform-completion-roadmap.md) · [Hierarchy of Truth](../../governance/hierarchy-of-truth.md)  
**First application:** [Platform Scope Completeness Audit](platform-scope-completeness-audit.md) · [Workspace Capability Platform Completion](../tasks/workspace-capability-platform-completion.md) · [G1–G5 close-out](workspace-capability-platform-g1-g5-closeout.md)

> A phase may be **brief-complete** and still **goal-incomplete**.  
> Named CI that checks the approved brief does **not** prove the original problem is gone.  
> This gate asks the original question again at close-out.

---

## Why this gate exists

Entity Workspace D1–D9 passed every named D gate. Each brief was consistent with the previous brief. The original goal was not:

> shell + D2 slots + named consumers

It was:

> After D, a new screen can be assembled from the platform without new local rails, notes, consent, actions, widgets, or page-specific composition logic.

D substituted a weaker architecture (chrome + surfaces; inner functions stay module-owned) and then tested itself against that substitution. The inner-capability gap was therefore invisible until after D9.

That class of error can repeat anywhere acceptance is written as deliverables instead of residual capability.

---

## When it is mandatory

Apply this gate when **any** of the following would be claimed:

- Product Track marks a platform phase / epic **COMPLETE**  
- Maturity marks **Foundation ✅** in a way that means “next layer may consume this platform”  
- A slice is sold as “the platform is now sufficient for the next consumer”

Do **not** use this gate to reopen a slice that only claimed a documented residual (`PASS_WITH_CONSTRAINTS` with named constraints is valid **if** those constraints were the original goal’s leftovers, not a silent goal swap).

A **docs brief merge** may proceed without filling G4 evidence. It **may not** omit the brief-time section below. A **feat that closes the phase** may not skip G1–G5.

---

## Brief-time control (mandatory on every platform phase brief)

Every **platform phase brief** (`docs/specs/tasks/*.md` with `**Phase class:** platform`) must contain a dedicated heading:

```text
## Original Goal → Completion Proof
```

Not a list of deliverables. A direct test, filled **when the brief opens**:

| Field | Required content |
|-------|------------------|
| **Problem this phase must permanently remove** | The pre-decomposition problem this stage exists to **eliminate forever** for the next consumer |
| **Completion proof (named consumer)** | Which **real** screen/path will prove it; what that consumer must **not** fork |

Close-out then applies G1–G5 against **this section**, not against the latest decomposed AC.

**Reject the brief** if this section is missing, restates deliverables (“typed slots”, “named CI”, “component kit”), or names a proof that still allows the original local fork.

Worked example: [Workspace Capability Platform Completion](../tasks/workspace-capability-platform-completion.md). D1–D9 failed this test: they proved brief-internal consistency, not the original Entity Shell goal.

---

## The five questions (normative)

| # | Question | Fail if |
|---|----------|---------|
| **G1** | What **original** business/architecture problem was this phase created to remove? Quote the pre-decomposition goal, not the last brief. | The close-out only restates the latest brief |
| **G2** | After this phase, which **local implementations are forbidden**? Name the forks that must not appear in the next consumer. | Forbidden list is empty, or only restates “don’t invent a fifth shell” while inner forks remain legal |
| **G3** | Can the **next real consumer** be assembled **without a new platform primitive**? | Next consumer still needs a new slot kind, registry, rail, runtime, or glue that the phase was supposed to provide |
| **G4** | Is there **at least one end-to-end consumer** that proves G3? Binding constants / CompositionHost wrappers are not enough. | Proof is a catalog freeze, a `data-` attribute, or a consumer that still stuffs module widgets |
| **G5** | Which **workarounds remain allowed**, and **why**? Owner + expiry or next named slice. | Silent leftovers; or leftovers that recreate the original problem |

**Pass outcomes** (same vocabulary as other HostFlow gates):

| Outcome | Meaning |
|---------|---------|
| **PASS** | G1–G5 answered; next consumer can proceed without a new primitive for this concern |
| **PASS_WITH_CONSTRAINTS** | Original goal still incomplete; residuals named; next layer may proceed **only** for concerns outside those residuals |
| **STOP** | Goal was substituted, or residuals are the original problem in disguise — do not start the next platform expansion that would multiply the fork |

Brief-complete + goal-incomplete **without** this gate → process fail.

---

## What this gate is not

- Not a substitute for the [Architecture Review 10 questions](../architecture/architecture-review-checklist.md) (ownership / adapter / Catalog). Those stay. This gate is **orthogonal**: original goal vs substituted brief.  
- Not a licence to reopen Vocabulary Canon or L0 Catalog.  
- Not a demand that every deferred item (P3–P5, R6, C2.4) be finished before any next slice — those are valid **if G5 names them**.  
- Not Entity Workspace D10 (another consumer cutover).

---

## Evidence bar

For G4, acceptable proof is a **shipped screen** that:

1. uses only contracted platform capabilities / contributions for the concern, and  
2. would fail a gate if a module-local duplicate of that concern were added.

Unacceptable as sole proof: typed allowlists, named CI greps for constants, “first consumer bound to slots,” docs-only ADRs.

---

## Template (copy into the closing PR)

```text
Goal Completion Gate — <phase>
G1 Original problem: (quote Original Goal → Completion Proof)
G2 Now forbidden local implementations:
G3 Next consumer without new primitive? (yes/no + consumer name)
G4 End-to-end proof (path + what it does not fork):
G5 Remaining allowed workarounds (owner / until):
Outcome: PASS | PASS_WITH_CONSTRAINTS | STOP
```

Brief-open template (must appear under `## Original Goal → Completion Proof`):

```text
**Problem this phase must permanently remove:**
**Completion proof (named consumer):**
```

---

## History

- 2026-08-20: Introduced after D1–D9 brief-completion vs original Entity Shell goal. First use: [platform-scope-completeness-audit.md](platform-scope-completeness-audit.md).  
- 2026-08-20: Brief-time control — every platform phase brief must include **Original Goal → Completion Proof** (lint: `phase-brief-missing-goal-proof`).
- 2026-08-21: First program close-out: [Workspace Capability G1–G5](workspace-capability-platform-g1-g5-closeout.md) **PASS_WITH_CONSTRAINTS**. G4 PASS on Recruitment Application. Program **not COMPLETE** (G1 dual-host runtime). Documents E2 stays locked. Next: [host runtime-equivalence](../tasks/workspace-capability-host-runtime-equivalence.md).
