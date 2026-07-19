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

A proposal is **architecturally wrong** (regardless of runtime behavior) if it requires any of:

| Signal | Why |
|--------|-----|
| Direct knowledge of another module’s internals | Breaks independence |
| Cross-package import of domain models/services | Hidden coupling |
| Shared domain object as product SoT across modules | Ownership collision |
| Hidden fallback across destinations (e.g. Sales → Recruitment) | Boundary erasure |

---

## Application to Intake / Flights epic

Correct boundary (frozen by R3.5):

```text
Flights-owned routing → published destination contract → module-owned adapter
```

Incorrect (even if it “works”):

```text
Forms / Shared Intake → Recruitment/Sales handler directly
```

**R3 retrospective:** placing dispatch callables inside Recruitment/Sales as the *routing owner* failed this gate. Isolation of intents was valuable; **dispatch ownership** was wrong. **R3.5** corrected the boundary before further communication/queue work. Result objects (R4) remain valid **behind** module adapters, not as a reason to reintroduce cross-module knowledge.

Going forward: any PR in this epic that reintroduces Forms→Recruitment/Sales create calls, Flights→ORM imports, or destination fallback is rejected under this rule.

---

## History

- 2026-07-19: Adopted as mandatory decision priority after L0 correction on Intake Runtime Split (R3.5).
