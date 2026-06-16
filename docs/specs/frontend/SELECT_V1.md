# SELECT_V1

Status: **Locked**  
Draft date: 2026-05-29  
Locked date: 2026-05-31  
Governance: Approved (REF-UI-000 Primitives chain — partial)  
Input: `SELECT_BENCHMARK.md`, `FOUNDATION_V1.md`, `CHIP_V1.md`, `PRIMITIVES_ENFORCEMENT_AND_MIGRATION_PLAN.md`  
Supersedes: `SELECT_V1_DRAFT.md`

## Question Answered

> Какой select использовать в каждом сценарии — и какой API у канонических компонентов?

This is the canonical allow-list for HostFlow selects. Enforced via PR review and migrate-on-touch; primitive CI deferred to Phase 2. Foundation CI (`npm run foundation:check`) blocks deprecated tokens in diffs.

---

## Lock Readiness (Verified)

| Gate | Requirement | Status |
|---|---|---|
| Spec | `SELECT_V1_DRAFT` complete | ✅ |
| Component | `Combobox` implemented | ✅ `components/ui/Combobox.tsx` |
| Multi | `MultiCombobox` implemented | ✅ `components/ui/MultiCombobox.tsx` |
| Deprecated | `SelectAsync`, duplicate combobox copies forbidden in new code | ✅ No external imports of `SelectAsync` / `MultiSelect` |
| New code | Approved select primitives only | ✅ See §4 |
| Foundation | No deprecated tokens in new primitive code | ✅ Uses `.input`, `slate-*`, `brand-*` |

---

## Governance

| Rule | Detail |
|---|---|
| Authority | `REF-UI-*` only |
| New code | Must match scenario → component map (§1) |
| Scenario split | **4 scenarios**, **2 React primitives** + native — no mega-select |
| i18n | UI strings via props or `useI18n` — no hardcoded locale in `Combobox` / `MultiCombobox` |
| Multi toggle chips | `CHIP_V1` selectable — not select |
| Legacy adapters | `controls/Select`, `SearchableSelect`, `CheckboxMultiSelect` — migrate on touch |
| Changes | Explicit governance decision in `REF-UI-*` |

---

## 1) Scenario Decision Tree

```
Need selection?
├─ Multiple values + chip/toggle UX on page → CHIP_V1 selectable
├─ Multiple values + dropdown checklist → MultiCombobox
├─ Single value + search/filter (>10 options or dynamic list) → Combobox
├─ Single value + remote/async fetch → AsyncCombobox (queued — not in V1 lock)
└─ Single value + small static enum (≤10, no search) → native <select className="input">
```

---

## 2) Components

### 2.1 Native select (pattern)

Allowed without React wrapper:

```tsx
<select className="input w-full" value={value} onChange={...}>
  {options.map(...)}
</select>
```

Styled by `.app-ui` / `.modal-surface` context rules in `components.css`.

### 2.2 `Combobox` (single, sync search)

**Path:** `components/ui/Combobox.tsx`  
**Types:** `components/ui/comboboxShared.ts` (`ComboboxOption`)

```tsx
type ComboboxProps = {
  options: ComboboxOption[]
  value: string
  onChange: (value: string) => void
  disabled?: boolean
  placeholder?: string
  searchPlaceholder?: string
  noResultsLabel?: string
  className?: string
}
```

**Behavior (locked):**

- Trigger: `<button type="button" className="input w-full text-left">`
- Panel: `absolute z-50 mt-2 w-full rounded-xl border bg-white shadow-xl`
- Filter: `.input` with autofocus; filters label + value (case-insensitive)
- Close: click outside + Escape

### 2.3 `MultiCombobox` (multi, sync search)

**Path:** `components/ui/MultiCombobox.tsx`

```tsx
type MultiComboboxProps = {
  options: ComboboxOption[]
  values: string[]
  onChange: (values: string[]) => void
  disabled?: boolean
  placeholder?: string
  searchPlaceholder?: string
  noResultsLabel?: string
  multiSelectedLabel?: (count: number) => string
  className?: string
}
```

Same panel contract as `Combobox`; checkbox rows; caption shows ≤3 labels or count summary.

### 2.4 Legacy adapters (allowed until migrated)

| Adapter | Wraps | Note |
|---|---|---|
| `controls/Select.tsx` | `Combobox` | RU defaults for public intake only |
| `FormComponents.SearchableSelect` | `Combobox` | Deprecated alias |
| `FormComponents.CheckboxMultiSelect` | `MultiCombobox` | Deprecated alias |

### 2.5 Queued (not in this lock)

`AsyncCombobox` — replaces `SelectAsync.tsx` when first async consumer exists.

---

## 3) Visual Contract

| Part | Classes |
|---|---|
| Trigger | `.input`, disabled: `bg-slate-100 text-slate-600 cursor-not-allowed` |
| Panel | `rounded-xl border bg-white shadow-xl` |
| Filter | `.input` in `p-2` |
| Option | `w-full px-3 py-2 text-left hover:bg-slate-50` |
| Selected option | `bg-slate-50` |
| Empty | `px-3 py-2 text-slate-500 text-sm` |

---

## 4) Allowed vs Legacy vs Deprecated

### Allowed (new code)

| Scenario | Use |
|---|---|
| Simple enum (≤10, no search) | native `<select className="input">` |
| Searchable single | `Combobox` |
| Multi dropdown | `MultiCombobox` |
| Domain feature | Wrapper composing canonical primitive |

### Legacy (existing, migrate on touch)

- `controls/Select.tsx` direct import (prefer `Combobox`)
- `SearchableSelect` / `CheckboxMultiSelect` in `FormComponents.tsx`
- `SelectAsync.tsx`, `MultiSelect.tsx` (dead files)
- Domain wrappers on raw native select

### Deprecated (forbidden in new code)

- New combobox copy-paste (third implementation)
- `Combobox` for ≤10 static options
- Hardcoded locale strings in `Combobox` / `MultiCombobox`
- `SelectAsync` / `MultiSelect` in new code
- `MultiSelectChips` for new surfaces (use `CHIP_V1`)

---

## 5) Implementation Status

| Item | Status |
|---|---|
| Spec locked | ✅ |
| `Combobox` | ✅ |
| `MultiCombobox` | ✅ |
| Legacy adapters | ✅ |
| Call site renames | Optional — adapters sufficient |
| `AsyncCombobox` | ⬜ Queued |
| Primitive CI | ⬜ Phase 2 |

---

## 6) Chain Status

| Artifact | Status |
|---|---|
| `SELECT_BENCHMARK.md` | ✅ |
| `SELECT_V1_DRAFT.md` | Superseded |
| **`SELECT_V1.md`** | ✅ **Locked** |
| `BUTTON_V1.md` | ✅ Locked (companion) |
| `PRIMITIVES_V1.md` | ✅ Partial lock (expanded) |

---

## 7) Next Steps (post-lock)

1. Optional: rename call sites from deprecated aliases → direct `Combobox` / `MultiCombobox` imports.
2. Delete `SelectAsync.tsx` / `MultiSelect.tsx` in cleanup sprint (0 consumers).
3. Implement `AsyncCombobox` when async consumer identified.

Input family (`INPUT_V1`) opens **only after** this lock — see roadmap.
