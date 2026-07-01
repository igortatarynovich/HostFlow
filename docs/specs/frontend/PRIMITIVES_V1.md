# PRIMITIVES_V1

Status: **Locked (Layer 2 — all primitive families)**  
Draft date: 2026-05-29  
Locked date: 2026-05-31 (Input lock — Layer 2 closed)  
Governance: Approved (REF-UI-000 Layer 2 complete)  
Input: `STATUS_BADGE_V1.md`, `CHIP_V1.md`, `SELECT_V1.md`, `BUTTON_V1.md`, `INPUT_V1.md`, `PRIMITIVES_ENFORCEMENT_AND_MIGRATION_PLAN.md`  
Supersedes: `PRIMITIVES_V1_DRAFT.md`

## Question Answered

> Что официально разрешено использовать для primitive components в HostFlow?

**Layer 2 (Primitives) is closed.** Checkbox/Radio/Toggle and form layout are **not** part of this lock — separate streams if needed.

---

## Governance

| Rule | Detail |
|---|---|
| Authority | `REF-UI-*` only |
| New code | Must use allowed primitives below |
| Legacy | Migrate on touch — no new legacy in edited files |
| Changes | Explicit governance decision in `REF-UI-*` |
| Enforcement | `PRIMITIVES_ENFORCEMENT_AND_MIGRATION_PLAN.md` |
| Foundation | `npm run foundation:check` on all PR diffs |

---

## 1) StatusBadge

Spec: `STATUS_BADGE_V1.md` | Implementation: `components/ui/StatusBadge.tsx`

Semantics: `success`, `warning`, `danger`, `info`, `neutral`, `brand`  
Sizes: `sm`, `md` | Shapes: `default`, `pill`

---

## 2) Chip

Spec: `CHIP_V1.md` | Implementation: `components/ui/Chip.tsx`

Behaviors: `static`, `dismissible`, `selectable`, `action`  
Sizes: `sm`, `md`

---

## 3) Select

Spec: `SELECT_V1.md` | Implementation: `Combobox.tsx`, `MultiCombobox.tsx`

| Scenario | Use |
|---|---|
| Simple enum | native `<select className="input">` |
| Searchable single | `Combobox` |
| Multi dropdown | `MultiCombobox` |

---

## 4) Button

Spec: `BUTTON_V1.md` | Implementation: `Button.tsx` + `.btn-*` CSS

Variants: `primary`, `secondary`, `danger`, `ghost`, `link`, `icon`  
Sizes: `md`, `sm`, `xs`

---

## 5) Input (CSS-first — no wrapper)

Spec: `INPUT_V1.md` | Implementation: **`styles/components.css`** — no `Input.tsx`

| Role | Allowed |
|---|---|
| Text / email / number / password | `<input className="input">` |
| Search | `<input className="input" type="search">` |
| Date | `<input className="input" type="date">` |
| Multiline | `<textarea className="textarea">` |
| Label | `<div className="label">` |

**Architectural note:** Input is intentionally CSS-only at V1. Button and Select have React components because they add semantics or non-native behavior. Input does not — see `INPUT_V1` Wrapper Justification Decision.

---

## 6) Implemented / Canonical Summary

| Family | Canon | React component |
|---|---|---|
| Badge | Semantic API | ✅ `StatusBadge` |
| Chip | 4 behaviors | ✅ `Chip` |
| Select | Scenario tree | ✅ `Combobox`, `MultiCombobox` |
| Button | Variant + size | ✅ `Button` |
| Input | `.input` / `.textarea` | ❌ None (by design) |

---

## 7) Explicitly Not in Layer 2

| Topic | Status |
|---|---|
| Form System / field layout | Out of scope |
| Validation framework | Out of scope |
| Checkbox / Radio / Toggle V1 | Deferred |
| Masked input | Deferred (governance trigger) |

---

## 8) Chain Status

| Artifact | Status |
|---|---|
| Audit → Inventory → Benchmark (per family) | ✅ |
| `PRIMITIVES_ENFORCEMENT_AND_MIGRATION_PLAN.md` | ✅ |
| `STATUS_BADGE_V1` / `CHIP_V1` / `SELECT_V1` / `BUTTON_V1` / `INPUT_V1` | ✅ All locked |
| **`PRIMITIVES_V1.md`** | ✅ **Layer 2 locked** |

---

## 9) Next Steps (Layer 3+)

Layer 2 is **closed**. Further UI standardization follows `REF-UI-000-ui-standardization-roadmap.md`:

- Layer 3 composites (`FILTER_BAR_V1`, `MODAL_V1`, …)
- Layer 4 layouts
- Layer 5 page templates
- Optional: primitive CI grep (Phase 2)
- Optional: Checkbox/Toggle family if product requires

Do not reopen Input wrapper without governance trigger documented in `INPUT_V1.md`.
