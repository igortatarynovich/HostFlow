# INPUT_V1_DRAFT

Status: **Superseded** by `INPUT_V1.md` (locked 2026-05-31)  
Date: 2026-05-31  
Layer: 2 (Primitive)  
Input: `INPUT_BENCHMARK.md`, `FOUNDATION_V1.md`, `SELECT_V1.md`  
Purpose: define official **Input** primitive for HostFlow — **CSS-first**, wrapper optional.

## Question Answered

> Что разрешено для text fields, нужен ли React wrapper, и что запрещено?

---

## Wrapper Justification Decision

### Question

> Нужен ли `Input.tsx` / `Textarea.tsx` в `components/ui/` для `INPUT_V1` lock?

### Evidence (from audit — no new scan)

| Signal | Fact | Implication |
|---|---|---|
| Dominant pattern | `.input` — **708** uses | Standard already chosen by codebase |
| Textarea | `.textarea` extends `.input` — **83** uses | Same visual; no drift |
| Date | native `type="date"` + `.input` / context — **64** uses | No datepicker lib needed |
| Search | filter/combobox rows use `.input` — **~26** UIs | Same class, not a separate variant |
| Masking / formatting / async | **0** shared primitives | No behavior wrapper requirement |
| `FormComponents.Input` | **5** files — adds label + hint | **Field row**, not input primitive |
| `Field.tsx` | **0** imports | Dead — not a justification |

### Comparison with Button / Select (why they have components)

| Primitive | Why React component exists |
|---|---|
| `Button` | Six semantic variants + link/icon contracts; CSS string composition error-prone |
| `Combobox` | Non-native behavior: dropdown, filter, keyboard, click-outside |
| **Input** | Native `<input>` / `<textarea>` + one CSS class — **no extra behavior** |

### Decision (locked for V1 draft)

**No `Input.tsx` / `Textarea.tsx` at lock.**

| Verdict | Detail |
|---|---|
| **Canon** | CSS classes in `styles/components.css` — `.input`, `.textarea`, `.label` |
| **New code** | Native elements + approved classes |
| **Wrapper** | **Deferred** until a concrete capability requires it |

### When a wrapper becomes justified (future governance gate)

Introduce `components/ui/Input.tsx` **only** when adding one of:

| Trigger | Example |
|---|---|
| **Masking** | phone/currency/IBAN mask with shared API |
| **Formatting** | normalized display value on blur |
| **Validation integration** | shared error state contract across forms (not layout) |
| **Async behavior** | debounced search primitive distinct from `Combobox` |

Until then, wrapping native elements **only to have a component** is **forbidden**.

### Architectural note

| Primitive | V1 shape |
|---|---|
| `BUTTON_V1` | Component + CSS |
| `SELECT_V1` | Component (non-native behavior) |
| **`INPUT_V1`** | **CSS canon; no component** |

This is an intentional, valid design-system outcome for HostFlow.

---

## Governance

| Rule | Detail |
|---|---|
| Authority | `REF-UI-*` |
| New code | Native `<input>` / `<textarea>` + `.input` / `.textarea` |
| Visual source | `styles/components.css` |
| No Form System | Label/hint/error **layout** is out of scope |
| No validation framework | Out of scope |
| Wrapper | None at lock — see Wrapper Justification Decision |
| Changes | Explicit governance in `REF-UI-*` |

---

## 1) Allowed Primitives (New Code)

### Text-like

```tsx
<input className="input" type="text" … />
<input className="input" type="email" … />
<input className="input" type="number" … />
<input className="input" type="password" … />
```

### Search (same visual — not a separate variant)

```tsx
<input className="input" type="search" … />
// or type="text" with search placeholder — same .input
```

### Date (native only)

```tsx
<input className="input" type="date" … />
```

No datepicker library in V1.

### Multiline

```tsx
<textarea className="textarea" … />
```

`.textarea` = `@apply input min-h-[96px]` — preferred over bare `.input` on textarea.

### Disabled / read-only (consistent modifier)

```tsx
<input className="input bg-slate-100 text-slate-600 cursor-not-allowed" disabled … />
```

Or rely on `:disabled` styling from context when inside `.app-ui` — explicit classes also allowed.

### Label typography (optional, not a field system)

```tsx
<div className="label">Field name</div>
<input className="input" … />
```

`.label` is typography only — not a wrapper primitive.

### Context shells (existing)

Inputs inside `.app-ui`, `.settings-surface`, `.modal-surface` inherit reshaped native styling — **allowed** when combined with explicit `.input` on new code.

---

## 2) Visual Contract (Single Standard)

All allowed roles share one foundation-compatible surface:

| Token | Value |
|---|---|
| Shape | `rounded-xl` |
| Border | `border-brand-100` |
| Background | `bg-white/90` |
| Focus | `focus:border-brand-400 focus:ring-4 focus:ring-brand-100` |
| Text | `text-slate-900`, placeholder `text-slate-400` |
| Touch | `min-h-[44px] sm:min-h-0` on `.input` |

**Forbidden:** separate palettes per `type` (date vs text vs search).

Source: `.input` / `.textarea` in `components.css`.

---

## 3) Legacy (Existing — Migrate on Touch)

| Pattern | Action |
|---|---|
| `FormComponents.Input` | Legacy field-row helper (label + hint); keep until forms refactor — **not** INPUT_V1 canon |
| Raw `<input>` without `.input` | Add `.input` when editing file |
| `.input-sm` | Document module compact fields — align or document exception on touch |
| `DocumentFieldInput` | Domain composite — inner control must use canon classes |
| `PhoneInput` | Domain composite (`Combobox` + `.input`) |
| `Field.tsx` | Dead — delete in cleanup sprint |

**No requirement** to migrate 708 existing `.input` usages — already compliant.

---

## 4) Deprecated (Forbidden in New Code)

| Pattern | Reason |
|---|---|
| Custom one-off input Tailwind (border-gray, rounded-lg field chrome) | Breaks single standard |
| New `Input.tsx` pass-through wrapper without governance trigger | Abstraction without value |
| New masked-input library without REF-UI decision | Out of scope |
| Separate visual for date/search vs text | One standard only |
| `Field.tsx` as pattern for new forms | Dead + layout concern |
| Checkbox/radio styled as text inputs | Wrong family |

---

## 5) Out of Scope (Explicit)

Do not expand `INPUT_V1` to cover:

- Form layout (grid, sections, field groups)
- Validation / error aggregation
- Checkbox / Radio / Toggle (separate family, post–Layer 2)
- File upload, rich text
- Masked input (until governance trigger)

---

## 6) Relationship to Locked Primitives

| Need | Use |
|---|---|
| Text / date / search field | `.input` on native element |
| Multiline | `.textarea` |
| Long list pick | `SELECT_V1` `Combobox` |
| Phone with country code | `PhoneInput` (legacy composite) |
| Filter chip | `CHIP_V1` |

---

## 7) Implementation Status

| Item | Status |
|---|---|
| Benchmark | ✅ |
| Wrapper decision | ✅ **No wrapper at lock** |
| CSS canon (`.input`, `.textarea`) | ✅ Exists |
| `Input.tsx` / `Textarea.tsx` | ⬜ **Not planned for V1** |
| `Field.tsx` cleanup | ⬜ Optional P2 |
| Enforcement doc update | ⬜ Next |
| `INPUT_V1` lock | ⬜ After enforcement |

---

## 8) Chain Status

| Artifact | Status |
|---|---|
| `INPUT_BENCHMARK.md` | ✅ |
| **`INPUT_V1_DRAFT.md`** | ✅ Draft |
| `INPUT_V1.md` lock | ⬜ After enforcement |
| Layer 2 primitives closed | ⬜ After `INPUT_V1` lock |

---

## 9) Next Steps (strict order)

1. Update `PRIMITIVES_ENFORCEMENT_AND_MIGRATION_PLAN.md` — Input section (CSS-first, no wrapper).
2. Governance → **`INPUT_V1.md` lock** (no `Input.tsx` implementation step).
3. Expand `PRIMITIVES_V1.md` — Input family + **Layer 2 closed** note.
4. PR template — input checklist (`.input` / `.textarea`, no custom chrome).

**Skipped by design:** `components/ui/Input.tsx` — no justified trigger.
