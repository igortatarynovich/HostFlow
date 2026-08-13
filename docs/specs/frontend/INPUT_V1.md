# INPUT_V1

Status: **Locked**  
Draft date: 2026-05-31  
Locked date: 2026-05-31  
Governance: Approved (REF-UI-000 Primitives chain — Layer 2 complete)  
Input: `INPUT_BENCHMARK.md`, `FOUNDATION_V1.md`, `PRIMITIVES_ENFORCEMENT_AND_MIGRATION_PLAN.md`  
Supersedes: `INPUT_V1_DRAFT.md`

## Question Answered

> Что разрешено для text fields, нужен ли React wrapper, и что запрещено?

This is the canonical allow-list for HostFlow inputs. **Visual source remains CSS** (`.input` / `.textarea`). After ADR-043 the **public API** may be a thin React wrapper. Enforced via PR review and migrate-on-touch. Foundation CI (`npm run foundation:check`) blocks deprecated tokens in diffs.

---

## Lock Readiness (Verified)

| Gate | Requirement | Status |
|---|---|---|
| Spec | `INPUT_V1_DRAFT` + Wrapper Justification | ✅ |
| CSS canon | `.input`, `.textarea`, `.label` in `components.css` | ✅ |
| Wrapper decision | Justified trigger required for `Input.tsx` | ✅ **No wrapper at lock**; ADR-043 allows thin kit API |
| New code | Native elements + approved classes only | ✅ See §1 |
| Foundation | Single standard uses `brand-*`, `slate-*` | ✅ |
| Component | `Input.tsx` not required | ✅ By design |

---

**Amended by:** [`ADR-043`](../architecture/ADR-043-ui-component-composition-canon.md) — a thin React `Input` / `Textarea` is now **allowed as kit public API** wrapping existing `.input` / `.textarea` CSS. This is a composition-contract trigger, not a visual redesign. Masking / validation / async remain out of scope until a dedicated PR.

## Wrapper Justification Decision (Locked)

**At INPUT_V1 lock:** no wrapper (CSS-only).

**After ADR-043:** kit public API may wrap the same CSS. Product pages target `<Input>` / `<Textarea>`; they do not restyle the field.

| Primitive | V1 visual source | Public API after ADR-043 |
|---|---|---|
| `BUTTON_V1` | CSS `.btn-*` | `<Button>` |
| `SELECT_V1` | Combobox components | `<Combobox>` / `<MultiCombobox>` |
| **`INPUT_V1`** | CSS `.input` / `.textarea` | thin `<Input>` / `<Textarea>` wrapping the same CSS |

Do **not** invent a second visual language for inputs. Masking / formatting / async still need a dedicated PR.

---

## Governance

| Rule | Detail |
|---|---|
| Authority | `REF-UI-*` + ADR-043 composition canon |
| New code | After Input kit exists: `<Input>` / `<Textarea>`. Until then: native + `.input` / `.textarea` (migrate-on-touch) |
| Visual source | `styles/components.css` |
| No Form System | Label/hint/error layout → `FormField` (ADR-043 catalog), not a second input visual |
| No validation framework | Out of scope |
| Wrapper | Thin kit API allowed (ADR-043). No second visual language |
| Changes | Explicit governance decision in `REF-UI-*` or ADR-043 tree |

---

## 1) Allowed Primitives (New Code)

### Text-like

```tsx
<input className="input" type="text" … />
<input className="input" type="email" … />
<input className="input" type="number" … />
<input className="input" type="password" … />
```

### Search (same visual)

```tsx
<input className="input" type="search" … />
```

### Date (native only)

```tsx
<input className="input" type="date" … />
```

### Multiline

```tsx
<textarea className="textarea" … />
```

`.textarea` = `@apply input min-h-[96px]`.

### Label typography (optional)

```tsx
<div className="label">Field name</div>
<input className="input" … />
```

### Disabled / read-only

```tsx
<input className="input bg-slate-100 text-slate-600 cursor-not-allowed" disabled … />
```

### Context shells

`.app-ui`, `.settings-surface`, `.modal-surface` — allowed; new code still adds explicit `.input`.

---

## 2) Visual Contract (Single Standard)

| Token | Value |
|---|---|
| Shape | `rounded-xl` |
| Border | `border-brand-100` |
| Background | `bg-white/90` |
| Focus | `focus:border-brand-400 focus:ring-4 focus:ring-brand-100` |
| Text | `text-slate-900`, placeholder `text-slate-400` |
| Touch | `min-h-[44px] sm:min-h-0` |

Text, textarea, date, and search share this contract — no per-type palettes.

---

## 3) Allowed vs Legacy vs Deprecated

### Allowed (new code)

- Native `<input className="input">` / `<textarea className="textarea">`
- `.label` for field title typography
- Domain composites if inner control uses canon classes

### Legacy (migrate on touch)

- `FormComponents.Input` — field-row helper (label + hint), not INPUT_V1 canon
- Raw `<input>` without `.input`
- `.input-sm` in documents/dashboard
- `DocumentFieldInput`, `PhoneInput` composites
- `Field.tsx` (0 imports — delete in cleanup)

### Deprecated (forbidden in new code)

- Custom one-off input Tailwind field chrome
- Pass-through `Input.tsx` without governance trigger
- Masked-input libraries without REF-UI decision
- Separate visual per input type
- Checkbox/radio as text-input substitutes

---

## 4) Out of Scope

Form layout, validation framework, checkbox/radio/toggle canon, file upload, rich text, masked input (until governance).

---

## 5) Relationship to Locked Primitives

| Need | Use |
|---|---|
| Text / date / search | `.input` |
| Multiline | `.textarea` |
| Long list | `SELECT_V1` `Combobox` |
| Phone | `PhoneInput` (legacy composite) |
| Filter chip | `CHIP_V1` |

---

## 6) Implementation Status

| Item | Status |
|---|---|
| Spec locked | ✅ |
| CSS canon | ✅ |
| Wrapper | ⬜ Not planned (by decision) |
| `Field.tsx` cleanup | ⬜ Optional P2 |
| Primitive CI | ⬜ Phase 2 |

---

## 7) Chain Status

| Artifact | Status |
|---|---|
| `INPUT_BENCHMARK.md` | ✅ |
| `INPUT_V1_DRAFT.md` | Superseded |
| **`INPUT_V1.md`** | ✅ **Locked** |
| **`PRIMITIVES_V1.md`** | ✅ Layer 2 complete |
| Layer 3 composites | ← Next program stream |

---

## 8) Wrapper Triggers (Future Only)

| Trigger | Action |
|---|---|
| Masking | Governance → `Input.tsx` spec |
| Formatting | Governance → shared API |
| Validation integration | Governance → error contract (not layout) |
| Async debounced search | Governance → distinct from `Combobox` |

Until then: **forbidden** to add wrapper “for consistency with Button/Select”.
