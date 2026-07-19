# Decision Priority Rule (L0 gate)

**Status:** **NORMATIVE** · mandatory for every ADR, epic gate, and PR  
**Parents:** [`L0-platform-architecture.md`](L0-platform-architecture.md) · [`architecture-invariants.md`](architecture-invariants.md) · [`architecture-review-checklist.md`](architecture-review-checklist.md)  
**Date:** 2026-07-19  

---

## Mandatory rule

Any local decision, PR, shortcut, or simplification is **unacceptable** if it violates:

- **L0** / platform constitution  
- **module independence**  
- **approved architectural boundaries** (ownership, published contracts, ADRs)

Functional success does **not** override this rule.

---

## Priority of review (strict order)

Before coding convenience or local design taste, check in this order:

1. **L0 and fundamental principles** (module independence; no module is built around another).  
2. **Canonical L1 / ADR and ownership** (who owns the object / decision).  
3. **Contracts between independent modules** (published ports/adapters only).  
4. **Only then** local implementation and developer convenience.

Skipping earlier steps is an architecture fail even if later steps look clean.

---

## Automatic reject signals

A proposal is **architecturally wrong** (regardless of tests / runtime behavior) if it requires any of:

| Signal | Why |
|--------|-----|
| Direct knowledge of another module’s internal models or services | Breaks independence |
| Cross-package domain imports | Hidden coupling |
| Shared domain SoT for independent modules | Ownership collision |
| Hidden fallback into another domain (e.g. Sales → Recruitment) | Boundary erasure |
| Building one module as an internal part of another | Violates L0 module independence |
| Bypassing a published contract with a direct implementation call | Contract is the only legal edge |
| Inferring ownership from UI, URL, form, or legacy flags | Non-SoT masquerading as routing/ownership |

Lower layers (implementation convenience, speed) **cannot** override or bypass higher layers (L0 → ownership → contracts).

---

## Application to Intake / Flights epic

Correct boundary (frozen by R3.5 `#66`):

```text
Forms → Flights → destination contract → module intake adapter → module-owned result
```

| Segment | Owner |
|---------|-------|
| Submission and handoff | Forms |
| Routing decision and dispatch provenance | Flights |
| Destination contract | Published inter-module boundary |
| Recruitment / Sales adapters | Recruitment / Sales |
| Application / SalesInquiry | Recruitment / Sales |

Incorrect (even if it “works”):

```text
Forms / Shared Intake → Recruitment/Sales handler directly
```

**R3 retrospective:** placing dispatch callables inside Recruitment/Sales as the *routing owner* failed this gate. **R3.5** corrected ownership. **R5** must keep provenance Flights-owned and must **not** use a shared cross-module DB transaction as exactly-once (see [`../tasks/intake-r5-provenance-gate.md`](../tasks/intake-r5-provenance-gate.md)).

---

## History

- 2026-07-19: Adopted as mandatory decision priority after L0 correction on Intake Runtime Split (R3.5).
- 2026-07-19: Expanded reject signals; linked R5 gate (no cross-domain transactional monolith).
