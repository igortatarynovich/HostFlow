# ADR-039: State / Lifecycle Inventory (Object Kind slice)

**Status:** Accepted  
**Date:** 2026-08-13  
**Layer of change:** Vocabulary (States & Transitions) | Inventory  
**Trusted base:** `integration/release-product-a-b`  
**Related:** [`ADR-037`](ADR-037-platform-object-kind-catalog.md) · [`ADR-038`](ADR-038-platform-standardization-model.md) · [`ADR-009`](ADR-009-document-hub-platform-layer.md) · [`ADR-018`](ADR-018-requirement-policy-evaluation-model.md) · [`ADR-019`](ADR-019-automation-capability-entitlement-control-plane.md) · [`../platform/object-kind-catalog.md`](../platform/object-kind-catalog.md) · [`../platform/document-runtime-engine-p0.md`](../platform/document-runtime-engine-p0.md) · L2 inventory [`../platform/state-lifecycle-inventory.md`](../platform/state-lifecycle-inventory.md)

**L0 checklist:** No new L0 P-rule; does not rewrite Passport/Manifest; fills ADR-038 area `states_transitions` with an **inventory**, not a shared status enum; Design Semantic Visual Language remains out of scope (ADR-011).

---

## Context

ADR-038 marked **States & Transitions** as `next` and forbade treating `approved`, `active`, `blocked`, `running`, and `published` as one vocabulary. Without an inventory of **which objects have which state dimensions**, any shared status or color mapping would recreate the original confusion.

ADR-037 already classified objects. This ADR inventories **state dimensions** for the Documents / Requirements / Automation / Templates slice only.

---

## Decision

### 1. Inventory first — no shared status bag

This ADR defines the **inventory contract** and dimension kinds. Observed values in the L2 inventory are **descriptive** (what exists in code/docs today). They are **not** yet a platform-canonical enum for reuse across ObjectKinds.

**Forbidden until a later ADR:** one platform-wide status vocabulary that merges publication, instance lifecycle, execution, and evaluation outcomes.

### 2. Chain (mandatory)

```text
ObjectKind → Object → State dimension → State owner → Transition owner
```

| Link | Meaning |
|------|---------|
| ObjectKind | From ADR-037 |
| Object | `object_code` in object-kind-catalog |
| State dimension | One orthogonal axis on that object |
| State owner | Who owns the SoT of values on that axis |
| Transition owner | Who may change the value (may differ from state owner) |

### 3. Dimension kinds (closed for this inventory)

| Dimension | Answers |
|-----------|---------|
| `publication` | Is this definition/version publishable / active / deprecated? |
| `configuration` | Which policy/version/config pin applies? |
| `instance_lifecycle` | Where is this runtime instance in its operational workflow? |
| `review` | What is the verification/review decision in context? |
| `validity_expiry` | Is the instance valid / expiring / expired in time? |
| `execution` | Where is an automation execution in its run lifecycle? |
| `outcome` | What is the computed evaluation/satisfaction result? |
| `decision` | What was the rule decision (fire/skip/…)? |
| `enablement` | Is the rule/pack/feature enabled for this tenant/scope? |
| `none` | Object is not stateful on any dimension (explicit completeness) |

An object may have **multiple** dimensions. Do not collapse Document workflow + expiry + review into one field.

### 4. Hard classifications

| Object | Dimension(s) | Must not be treated as |
|--------|--------------|------------------------|
| `RequirementEvaluation` | `outcome` only | instance_lifecycle / readiness process |
| `RequirementPolicy` | `configuration` (± publication of policy artifact) | readiness / blocker outcome |
| `DocumentType` | `publication` | instance lifecycle of a file |
| `Document` | `instance_lifecycle` + `review` + `validity_expiry` | single merged status |
| `AutomationExecution` | `execution` | domain policy truth |
| `CommunicationAutomationDecision` | `decision` | send/delivery status |

### 5. State owner vs transition owner

- **State owner** = capability/module that owns the SoT values for the dimension.
- **Transition owner** = who is allowed to mutate that dimension (API, evaluator, orchestrator, human role).
- Automation may **react** to a state change; it must not become state owner of domain outcomes (ADR-019).

### 6. Scope

Only `object_code` values already listed in [`../platform/object-kind-catalog.md`](../platform/object-kind-catalog.md). Candidate / Lead / Vacancy / Employee / Campaign lifecycles are **out of scope** (later slices).

### 7. Out of scope (explicit)

- Shared meaning tokens for Design (`positive` / `warning` / `blocking`) and Semantic Visual Language — ADR-011 / Design area.
- Color or badge mapping.
- Runtime or DB changes.
- Naming canon / DocumentType code alignment.

### 8. Explicit next (after inventory settles)

Optional later ADR: **shared meaning classes** (not value enums) that Design can map — still not `green = approved`. Next platform standardization follow-on from ADR-038 sequence remains **Naming & Identifiers** unless product prioritizes Design SVL.

---

## Architecture Review Checklist (L0)

- [x] P-01…P-05 respected — no new capability Passport
- [x] Does not invent a cross-ObjectKind status SoT
- [x] Aligns with ADR-037 / ADR-038 Platform-first
- [x] Design tokens not smuggled into Vocabulary
- [x] L0 freeze untouched

---

## Consequences

- Positive: States & Transitions area becomes `exists` as inventory; orthogonal dimensions prevent collapsing Document / Evaluation / Automation into one status list; owners of state vs transition are explicit.
- Negative: inventory must be updated when new object-kind-catalog rows appear in this slice.
- Follow-on: Naming & Identifiers (ADR-038 sequence); optional meaning-class ADR; Design SVL after meaning classes exist.

---

## Alternatives considered

1. **Ship a universal status enum now** — rejected; recreates the original problem.
2. **Inventory all HostFlow entities (Candidate, Campaign, …)** — rejected; one PR — one slice.
3. **Map colors in the same PR** — rejected; Design area, not Vocabulary inventory.

---

## Cross-references (updated in same change set)

- [`../platform/state-lifecycle-inventory.md`](../platform/state-lifecycle-inventory.md) — L2 inventory rows
- [`../platform/platform-standardization-model.md`](../platform/platform-standardization-model.md) — area `states_transitions` → `exists`
- [`ADR-038-platform-standardization-model.md`](ADR-038-platform-standardization-model.md) — next-pointer update
- [`../platform/object-kind-catalog.md`](../platform/object-kind-catalog.md) · [`architecture-guide.md`](architecture-guide.md) · [`module-catalog-and-routing-map.md`](module-catalog-and-routing-map.md)
