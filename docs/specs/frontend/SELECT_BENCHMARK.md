# SELECT_BENCHMARK

Status: Complete  
Date: 2026-05-29  
Input: `PRIMITIVES_INVENTORY.md`, `FOUNDATION_V1.md`  
Scope: **Selects only** — Button / Input queued.  
Purpose: classify select implementations as **Candidate**, **Legacy**, or **Deprecated** for `SELECT_V1`.

## Question Answered

> Какие Select-реализации становятся Candidate / Legacy / Deprecated — и сколько канонических компонентов нужно?

## Governing Rules

| Status | Meaning | New code | Existing code |
|---|---|---|---|
| **Candidate** | Default for new work in scenario | Required | Keep |
| **Legacy / Adapt** | Allowed; migrate on touch | Discouraged | Keep until refactored |
| **Deprecated** | Forbidden pattern | Forbidden | Remove or migrate |

**Locked decisions (this benchmark):**

1. Select canon is **scenario-first** — do not merge native `<select>` and combobox into one mega-component.
2. **Two canonical React primitives** after consolidation: `Combobox` (single) + `MultiCombobox` (multi).
3. Native `<select>` remains valid for **simple enum** — optional thin wrapper, not mandatory React component.
4. Dropdown panel uses **one visual contract** (`rounded-xl`, `shadow-xl`, `.input` trigger) aligned with `FOUNDATION_V1`.

---

## 1) Scenario Classification

| Scenario | When | Current implementation | Uses | Decision | Maps to `SELECT_V1` |
|---|---|---|---:|---|---|
| **Simple enum** | ≤10 static options, no search | native `<select>` | **~301** / 101 files | **Candidate** | Native pattern + `.input` styling via `.app-ui` |
| **Searchable list (sync)** | Long list, local filter | `controls/Select` + `SearchableSelect` | 3 + 13 refs | **Candidate** (merge) | `Combobox` |
| **Multi with checkboxes** | Multiple values, dropdown | `CheckboxMultiSelect` | 8 refs | **Candidate** (rename) | `MultiCombobox` |
| **Async / remote options** | Fetch on open/search | `SelectAsync` | **0** imports | **Legacy / Adapt** | `AsyncCombobox` (queued) |
| **Multi toggle chips** | Public intake UX | `MultiSelectChips` local | 5 JSX | **Legacy / Adapt** | `CHIP_V1` selectable — not select |
| **Domain wrappers** | Feature-specific | `FunnelSelector`, `RecruiterAvailabilitySelect`, etc. | few | **Legacy / Adapt** | Wrap canonical primitive internally |
| **Dead duplicates** | Unused code | `MultiSelect.tsx` | **0** | **Deprecated** | Delete after `MultiCombobox` |
| **Dead async** | Unused code | `SelectAsync.tsx` | **0** | **Legacy / Adapt** | Revive as `AsyncCombobox` or delete in cleanup sprint |

---

## 2) Duplicate Analysis

### `Select` ↔ `SearchableSelect` (~90% overlap)

| Feature | `controls/Select` | `SearchableSelect` |
|---|---|---|
| Trigger | `.input` button | `.input` button |
| Filter input | ✅ hardcoded RU | ✅ i18n props |
| Click outside | ✅ mousedown only | ✅ mousedown + Escape |
| Panel radius | `rounded-2xl` | `rounded-xl` |
| z-index | `z-50` | `z-20` |
| Value filter | label only | label + value |

**Benchmark decision:** merge into **`Combobox`** — take `SearchableSelect` as base (Escape, i18n props, value+label filter). Unify panel to `rounded-xl shadow-xl z-50`.

### `CheckboxMultiSelect` ↔ dead `MultiSelect`

Same UX pattern (dropdown + checkboxes). **Candidate:** `MultiCombobox` from `CheckboxMultiSelect` implementation. **Deprecated:** `MultiSelect.tsx`.

### Native vs combobox

**Do not replace** 301 native selects with combobox. Different a11y/UX contracts. Native stays for filters, settings, bulk modals, admin forms.

---

## 3) Visual Contract (pre-V1)

| Element | Allowed | Deprecated in new combobox |
|---|---|---|
| Trigger | `.input` class, full width in forms | Ad-hoc `border rounded-lg` triggers |
| Panel | `rounded-xl border bg-white shadow-xl` | Mixed `rounded-2xl` / `rounded-lg` |
| Filter row | `.input` inside panel padding `p-2` | — |
| Option row | `px-3 py-2 hover:bg-slate-50`, selected `bg-slate-50` | Custom per-file colors |
| Empty state | `text-slate-500 text-sm` | Hardcoded locale strings in component |

**i18n rule:** no hardcoded UI strings in primitive (`Select.tsx` RU placeholders → forbidden in new code).

---

## 4) Allowed vs Legacy vs Deprecated

### Allowed (new code)

| Scenario | Use |
|---|---|
| Simple enum | native `<select className="input">` or `NativeSelect` wrapper |
| Searchable single | `Combobox` |
| Multi dropdown | `MultiCombobox` |
| Remote options | `AsyncCombobox` when implemented |

### Legacy (migrate on touch)

| Pattern | Action |
|---|---|
| `controls/Select` | → `Combobox` |
| `SearchableSelect` in `FormComponents` | → `Combobox` |
| `CheckboxMultiSelect` | → `MultiCombobox` |
| Domain wrappers on native select | keep until feature refactor |
| `MultiSelectChips` | → `CHIP_V1` selectable |

### Deprecated (forbidden in new code)

| Pattern | Reason |
|---|---|
| New third combobox copy | Duplicates `Combobox` |
| `MultiSelect.tsx` | Dead duplicate |
| Hardcoded-locale select primitive | i18n violation |
| Combobox for ≤10 static options | Wrong scenario — use native |

---

## 5) Migration Priority

| Priority | Action | Effort | Impact |
|---|---|---|---|
| **P0** | Implement `Combobox` in `components/ui/` | Medium | Removes dual combobox |
| **P1** | Migrate `SearchableSelect` call sites (candidate card) | Medium | Highest custom usage |
| **P1** | Migrate `controls/Select` (public intake, phone) | Low | 3 paths |
| **P2** | Implement `MultiCombobox`, migrate `CheckboxMultiSelect` | Medium | 8 refs |
| **P2** | Delete `MultiSelect.tsx` | Trivial | Dead code |
| **P3** | `AsyncCombobox` — revive or delete `SelectAsync` | Medium | 0 current consumers |
| **P3** | Native select audit — ensure `.input` on forms | Low | Consistency |

**Do not migrate** native selects to combobox in bulk — scenario mismatch.

---

## 6) Chain Status

| Artifact | Status |
|---|---|
| `PRIMITIVES_AUDIT.md` | ✅ |
| `PRIMITIVES_INVENTORY.md` | ✅ |
| **`SELECT_BENCHMARK.md`** | ✅ This document |
| `SELECT_V1_DRAFT.md` | ← Next |
| `SELECT_V1` lock | ⬜ After implementation + governance |

---

## 7) Next Steps

1. `SELECT_V1_DRAFT.md` — component API + scenario decision tree.
2. Implement `Combobox` + migrate `SearchableSelect` / `Select`.
3. Implement `MultiCombobox` + migrate `CheckboxMultiSelect`.
4. Governance → `SELECT_V1` lock.
