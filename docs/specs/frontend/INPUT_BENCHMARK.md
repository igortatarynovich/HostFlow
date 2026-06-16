# INPUT_BENCHMARK

Status: Complete  
Date: 2026-05-31  
Input: `PRIMITIVES_AUDIT.md` (§2 Inputs), `PRIMITIVES_INVENTORY.md` (P2 — Inputs), `FOUNDATION_V1.md`  
Scope: **Inputs only** — no new audit scan. Facts from existing audit/inventory.  
Purpose: classify input implementations as **Candidate**, **Legacy**, or **Deprecated** for `INPUT_V1`.

## Question Answered

> Что из текущих input-реализаций становится Candidate / Legacy / Deprecated?

## Governing Rules

| Status | Meaning | New code | Existing code |
|---|---|---|---|
| **Candidate** | Default for new work | Required | Keep |
| **Legacy / Adapt** | Allowed; migrate on touch | Discouraged | Keep until refactored |
| **Deprecated** | Forbidden pattern | Forbidden | Remove or migrate |

**Locked decisions (this benchmark):**

1. **One visual field standard** — text, textarea, date, search share foundation-compatible styling (`.input` family).
2. **Primitive layer only** — no Form System, no validation framework, no form layout canon in `INPUT_V1`.
3. **CSS-first** — React wrappers optional; `.input` / `.textarea` in `components.css` remain source of truth.
4. **Masked input** — not in scope (0 shared primitive in codebase).

---

## 1) Classification by Family

| Family | Current implementation | Audit uses | Decision | Maps to `INPUT_V1` |
|---|---|---:|---|---|
| **Text-like** | `.input` class on `<input>` | **708** | **Candidate** | `.input` on native element |
| **Multiline** | `.textarea` / `<textarea className="textarea">` | **83** | **Candidate** | `.textarea` on native element |
| **Date** | native `<input type="date">` + `.input` / context styling | **64** | **Candidate** | native + `.input` (no datepicker lib) |
| **Search** | `<input>` with search role/placeholder in filters & combobox filter row | **~26** UIs | **Candidate** | `type="search"` or text + `.input` — same visual |
| **Masked** | — | **0** | **Not in scope** | Out of V1; add only via governance |
| **Phone composite** | `PhoneInput` (country `Combobox` + input) | **2** files | **Legacy / Adapt** | Domain composite; inner input uses `.input` |
| **Document fields** | `DocumentFieldInput` + `.input-sm` | documents module | **Legacy / Adapt** | Domain wrapper; align tokens on touch |
| **Form wrapper** | `FormComponents.Input` (label + hint) | **5** files | **Legacy / Adapt** | → `components/ui/Input` when wrapper lands |
| **Dead wrapper** | `Field.tsx` (label/error shell) | **0** imports | **Deprecated** | Delete or ignore — not canonical |
| **Custom local styles** | Ad-hoc Tailwind on `<input>` without `.input` | subset of ~1,418 inputs | **Deprecated** | Replace with `.input` or approved wrapper |
| **Raw input without canon** | `<input>` relying only on `.app-ui` context | various | **Legacy / Adapt** | Add explicit `.input` on touch |

---

## 2) CSS Canon (Candidate Reference)

From `styles/components.css` — **already stable** (inventory verdict: low consolidation urgency).

| Class | Role | Decision |
|---|---|---|
| `.input` | Text, search, date, email, number, etc. | **Candidate** |
| `.textarea` | Multiline (`@apply input min-h-[96px]`) | **Candidate** |
| `.label` | Field label typography | **Candidate** (label only — not layout system) |
| `.input-sm` | Compact document fields | **Legacy / Adapt** | Merge into size modifier in V1 draft or keep as domain exception |
| Context: `.app-ui`, `.settings-surface`, `.modal-surface` | Reshape native inputs in shell | **Candidate** | Same token family, context-aware |

**Visual contract (locked for V1 draft):**

```
rounded-xl, border-brand-100, bg-white/90, brand focus ring
disabled/readOnly: bg-slate-100 text-slate-600 cursor-not-allowed
```

All field **roles** (text, textarea, date, search) must use this contract — not separate palettes.

---

## 3) Wrapper Analysis

| Wrapper | Purpose | Overlap | Benchmark decision |
|---|---|---|---|
| `FormComponents.Input` | label + `.input` + hint | Field-row helper, not input primitive | **Legacy / Adapt** — not promoted to `ui/Input` without wrapper trigger |
| `Field.tsx` | label + error + hint shell | 0 consumers | **Deprecated** — dead code |
| `DocumentFieldInput` | document module field types | Domain logic + `.input-sm` | **Legacy / Adapt** — stays domain, must use canon classes |
| `PhoneInput` | dial code + number | Uses `Combobox` + input | **Legacy / Adapt** — composite, not a second input style |

**Inventory verdict stands:** risk is **wrapper duplication**, not visual chaos. `INPUT_V1` documents CSS canon; **no React wrapper** unless masking/formatting/validation/async trigger (see `INPUT_V1_DRAFT` Wrapper Justification Decision).

---

## 4) Search Input — Explicit Decision

Search is **not** a separate visual variant today (embedded in filter bars and combobox filter rows).

| Pattern | Decision |
|---|---|
| Standalone filter/search field | **Candidate** — `<input type="search" className="input">` or `type="text"` + `.input` |
| Search inside `Combobox` / `MultiCombobox` | **Candidate** — filter row uses `.input` (already locked in `SELECT_V1`) |
| Custom search styling (border-gray, rounded-lg one-offs) | **Deprecated** in new code |

---

## 5) Allowed vs Legacy vs Deprecated

### Allowed (new code)

- `<input className="input" …>` for text-like, date, search, email, number
- `<textarea className="textarea" …>` for multiline
- `.label` for standalone label typography
- Domain composites (`PhoneInput`, `DocumentFieldInput`) if inner control uses canon classes

### Legacy (existing, migrate on touch)

- `FormComponents.Input` import path
- `Field.tsx` if ever referenced
- Raw `<input>` without `.input` (add class on edit)
- `.input-sm` in document/dashboard surfaces
- `DocumentFieldInput`, `PhoneInput` as domain wrappers

### Deprecated (forbidden in new code)

- Custom local input styles (one-off Tailwind field chrome)
- New masked-input libraries without governance
- New pass-through `Input.tsx` wrapper without governance trigger
- `Field.tsx` as canonical pattern
- Separate visual standards per input type (e.g. date with different border/radius than text)

---

## 6) What INPUT_V1 Is NOT (Out of Scope)

Do **not** include in `INPUT_V1` chain:

| Topic | Reason |
|---|---|
| Form System (sections, columns, field groups) | Layout layer — not primitive |
| Validation framework (schema, error aggregation) | Application concern |
| Form layout (grid, responsive field rows) | Composite / layout V1 |
| Checkbox / Radio / Toggle canon | Separate family — defer after Input lock |
| Rich text / file upload widgets | Domain components |
| Masked input / currency / phone masking lib | Not present — governance required to add |

`INPUT_V1` closes the **primitive layer** for text fields only.

---

## 7) Migration Priority

| Priority | Action | Effort |
|---|---|---|
| **P0** | `INPUT_V1_DRAFT` + Wrapper Justification Decision | Low |
| **P1** | Enforcement + `INPUT_V1` lock (CSS-only) | Low |
| **P2** | Delete or archive `Field.tsx` | Trivial |
| **P2** | Raw inputs without `.input` — fix on touch | Ongoing |
| **P3** | `.input-sm` — document as domain exception | Low |
| **—** | `Input.tsx` / `Textarea.tsx` | **Skipped** — no trigger |

No bulk migration of 708 `.input` usages — already canonical.

---

## 8) Relationship to Locked Primitives

| Need | Use | Not |
|---|---|---|
| Text / date / search field | `INPUT_V1` (`.input`) | Custom Tailwind chrome |
| Multiline | `INPUT_V1` (`.textarea`) | Raw textarea without class |
| Country / long list pick | `SELECT_V1` `Combobox` | Input styled select |
| Phone entry | `PhoneInput` composite | New phone mask primitive |
| Status / filter chip | `CHIP_V1` | Input styled as chip |

---

## 9) Chain Status

| Artifact | Status |
|---|---|
| `PRIMITIVES_AUDIT.md` §2 | ✅ (source facts) |
| `PRIMITIVES_INVENTORY.md` P2 | ✅ |
| **`INPUT_BENCHMARK.md`** | ✅ This document |
| `INPUT_V1_DRAFT.md` | ✅ Draft |
| `Input.tsx` / `Textarea.tsx` | ⬜ **Not planned** (see Wrapper Justification) |
| **`INPUT_V1.md`** | ✅ Locked |
| **`PRIMITIVES_V1.md`** | ✅ Layer 2 locked |

---

## 10) Next Steps (strict order)

1. **`INPUT_V1_DRAFT.md`** — ✅ includes Wrapper Justification Decision (no wrapper).
2. Update **`PRIMITIVES_ENFORCEMENT_AND_MIGRATION_PLAN.md`** (Input section).
3. Governance → **`INPUT_V1.md` lock**.
4. Expand **`PRIMITIVES_V1.md`** → Layer 2 primitives closed.

Only after step 4 may Layer 2 primitives be considered **closed**.
