# SELECT_V1_DRAFT

Status: **Superseded** by `SELECT_V1.md` (locked 2026-05-31)  
Date: 2026-05-29  
Layer: 2 (Primitive)  
Input: `SELECT_BENCHMARK.md`, `FOUNDATION_V1.md`, `CHIP_V1.md`  
Purpose: define official **Select** primitives for HostFlow by scenario.

## Question Answered

> Какой select использовать в каждом сценарии — и какой API у канонических компонентов?

---

## Governance

| Rule | Detail |
|---|---|
| Authority | `REF-UI-*` |
| New code | Must match scenario → component map below |
| Scenario split | **4 scenarios**, **2–3 React primitives** + native |
| i18n | All UI strings via props or `useI18n` — no hardcoded locale in primitives |
| Multi toggle chips | `CHIP_V1` — not select |

---

## 1) Scenario Decision Tree

```
Need selection?
├─ Multiple values + chip/toggle UX on page → CHIP_V1 selectable
├─ Multiple values + dropdown checklist → MultiCombobox
├─ Single value + search/filter (>10 options or dynamic list) → Combobox
├─ Single value + remote/async fetch → AsyncCombobox (queued)
└─ Single value + small static enum (≤10, no search) → native <select className="input">
```

---

## 2) Components (Draft)

### 2.1 Native select (pattern)

No mandatory wrapper. Allowed pattern:

```tsx
<select className="input w-full" value={value} onChange={...}>
  {options.map(...)}
</select>
```

Styled by `.app-ui` / `.modal-surface` context rules in `components.css`.

Optional future: `NativeSelect` thin wrapper for label/error consistency — not required for V1 lock.

### 2.2 `Combobox` (single, sync search)

**Replaces:** `controls/Select`, `FormComponents.SearchableSelect`  
**Path (planned):** `components/ui/Combobox.tsx`

```tsx
type ComboboxOption = { value: string; label: string }

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
- a11y: listbox pattern deferred to implementation review (minimum: keyboard nav in P1 migration)

### 2.3 `MultiCombobox` (multi, sync search)

**Replaces:** `CheckboxMultiSelect`  
**Path (planned):** `components/ui/MultiCombobox.tsx`

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

**Behavior:** same panel contract as `Combobox`; checkbox rows; caption shows ≤3 labels or count summary.

### 2.4 `AsyncCombobox` (queued)

**Replaces:** dead `SelectAsync.tsx` when a consumer exists.  
Not required for partial lock. Spec deferred until first async consumer is identified.

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

Uses `FOUNDATION_V1` spacing and neutral/brand focus rings from `.input`.

---

## 4) Allowed vs Legacy vs Deprecated

### Allowed (new code)

- native `<select className="input">` for simple enum
- `Combobox` / `MultiCombobox` per scenario tree
- Domain wrappers that compose canonical primitives

### Legacy (migrate on touch)

- `controls/Select.tsx`
- `SearchableSelect`, `CheckboxMultiSelect` in `FormComponents.tsx`
- `SelectAsync.tsx`, `MultiSelect.tsx`
- Domain wrappers on raw native select

### Deprecated (new code)

- New combobox copy-paste
- `Combobox` for ≤10 static options
- Hardcoded locale strings in select primitives
- `MultiSelectChips` for new surfaces (use `CHIP_V1`)

---

## 5) Migration Map

| Current | Target | Priority |
|---|---|---|
| `SearchableSelect` (candidate card) | `Combobox` | **P1** |
| `controls/Select` | `Combobox` | **P1** |
| `CheckboxMultiSelect` | `MultiCombobox` | **P2** |
| `MultiSelect.tsx` | delete | **P2** |
| `SelectAsync.tsx` | `AsyncCombobox` or delete | **P3** |
| native selects (301) | keep; add `.input` on touch | **P3** |

---

## 6) Implementation Status

| Item | Status |
|---|---|
| Benchmark | ✅ |
| Spec defined | ✅ Draft |
| `Combobox` | ✅ Implemented |
| `MultiCombobox` | ✅ Implemented |
| `controls/Select` adapter | ✅ |
| `FormComponents` adapters | ✅ |
| Call site renames | ⬜ Optional (adapters in place) |
| CI enforcement | ⬜ Phase 2 |
| `SELECT_V1` lock | ⬜ |

---

## 7) Chain Status

| Artifact | Status |
|---|---|
| `SELECT_BENCHMARK.md` | ✅ |
| **`SELECT_V1_DRAFT.md`** | ✅ Draft |
| `SELECT_V1` lock | ⬜ After P1 implementation |

---

## 8) Next Steps

1. Implement `Combobox` in `components/ui/`.
2. Migrate candidate card `SearchableSelect` call sites.
3. Migrate `controls/Select` consumers.
4. Implement `MultiCombobox` + migrate `CheckboxMultiSelect`.
5. Governance → `SELECT_V1` lock.
