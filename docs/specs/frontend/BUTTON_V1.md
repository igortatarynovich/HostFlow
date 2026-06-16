# BUTTON_V1

Status: **Locked**  
Draft date: 2026-05-29  
Locked date: 2026-05-31  
Governance: Approved (REF-UI-000 Primitives chain — partial)  
Input: `BUTTON_BENCHMARK.md`, `FOUNDATION_V1.md`, `PRIMITIVES_ENFORCEMENT_AND_MIGRATION_PLAN.md`  
Supersedes: `BUTTON_V1_DRAFT.md`

## Question Answered

> Какие button variants и sizes официально разрешены — и как их использовать в новом коде?

This is the canonical allow-list for HostFlow buttons. CSS canon in `components.css` is the visual source of truth; `Button.tsx` is optional thin wrapper. Enforced via PR review and migrate-on-touch.

---

## Lock Readiness (Verified)

| Gate | Requirement | Status |
|---|---|---|
| Spec | `BUTTON_V1_DRAFT` complete | ✅ |
| Component | `Button.tsx` implemented | ✅ `components/ui/Button.tsx` |
| CSS | `.btn-primary`, `.btn-secondary`, `.btn-danger`, `.btn-ghost`, `.btn-icon` | ✅ `components.css` |
| Link | `variant="link"` + `href` → `<Link>` | ✅ |
| Icon | `variant="icon"` requires `aria-label` when no visible text | ✅ PR review + HTML contract |
| Foundation | `gray-*` removed from button CSS; `slate-*` / `brand-*` used | ✅ `.btn-icon` fixed |

---

## Governance

| Rule | Detail |
|---|---|
| Authority | `REF-UI-*` only |
| New code | `.btn-*` classes **or** `<Button variant size>` |
| Visual source | `styles/components.css` — wrapper must not invent palettes |
| Max variants | **6** — no seventh without governance |
| Redesign | **Forbidden** — V1 documents existing canon |
| Changes | Explicit governance decision in `REF-UI-*` |

---

## 1) Variants (Locked)

| Variant | CSS / classes | Use |
|---|---|---|
| `primary` | `btn btn-primary` | Primary CTA, submit |
| `secondary` | `btn btn-secondary` | Default action |
| `danger` | `btn btn-danger` | Destructive confirm |
| `ghost` | `btn btn-ghost` | Tertiary / toolbar |
| `link` | brand text + underline on hover | Inline navigation action |
| `icon` | `btn-icon` | Icon-only control |

---

## 2) Sizes

| Size | CSS modifier | Applies to |
|---|---|---|
| `md` (default) | base `.btn` | primary, secondary, danger, ghost |
| `sm` | `.btn-sm` | same |
| `xs` | `.btn-xs` | same |

Sizes do **not** apply to `link` or `icon` variants.

---

## 3) Component Contract

**Path:** `components/ui/Button.tsx`

```tsx
type ButtonVariant = 'primary' | 'secondary' | 'danger' | 'ghost' | 'link' | 'icon'
type ButtonSize = 'md' | 'sm' | 'xs'

type ButtonProps = {
  variant?: ButtonVariant
  size?: ButtonSize
  type?: 'button' | 'submit' | 'reset'
  disabled?: boolean
  className?: string
  href?: string
  children: ReactNode
  onClick?: () => void
  'aria-label'?: string
}
```

**Rules (locked):**

- Default `type="button"` when not submit.
- `variant="link"` + `href` → React Router `<Link>`.
- `variant="icon"` without visible text → **`aria-label` required** (review gate).
- `className` merges last — layout/spacing escape hatch only, not new color palettes.

Direct CSS usage remains allowed:

```tsx
<button type="button" className="btn btn-primary btn-sm">Save</button>
```

---

## 4) CSS Canon

| Class | Summary |
|---|---|
| `.btn` | `inline-flex`, `rounded-xl`, `text-sm font-medium`, mobile touch min-height |
| `.btn-primary` | brand gradient, white text |
| `.btn-secondary` | white/border, slate text |
| `.btn-danger` | rose surface |
| `.btn-ghost` | transparent, slate hover |
| `.btn-sm` / `.btn-xs` | size modifiers |
| `.btn-icon` | icon-only, `slate-*` hover (no `gray-*`) |

---

## 5) Allowed vs Legacy vs Deprecated

### Allowed (new code)

- `<Button variant="…" size="…">`
- Direct `className="btn btn-*"` with allowed variants/sizes
- Explicit `type="button"` on non-submit buttons

### Legacy (existing, migrate on touch)

- Raw `<button>` with Tailwind-only styling (~57 files)
- Link-style text buttons outside `variant="link"`
- `EmptyStatePanel` local variant class strings
- Ad-hoc icon buttons (`p-2 hover:bg-slate-100`)

### Deprecated (forbidden in new code)

- Orphan `btn-ghost` without CSS definition (fixed at lock)
- New button color systems outside CSS canon
- Deprecated Foundation families in button styles (`gray-*`, `indigo-*`, etc.)

---

## 6) Implementation Status

| Item | Status |
|---|---|
| Spec locked | ✅ |
| `Button.tsx` | ✅ |
| `.btn-ghost` | ✅ |
| `.btn-icon` token fix | ✅ |
| Bulk migration of raw buttons | Legacy — on touch |
| Primitive CI | ⬜ Optional Phase 2 |

---

## 7) Chain Status

| Artifact | Status |
|---|---|
| `BUTTON_BENCHMARK.md` | ✅ |
| `BUTTON_V1_DRAFT.md` | Superseded |
| **`BUTTON_V1.md`** | ✅ **Locked** |
| `SELECT_V1.md` | ✅ Locked (companion) |
| `PRIMITIVES_V1.md` | ✅ Partial lock (expanded) |

---

## 8) Next Steps (post-lock)

1. Migrate raw `<button>` styling on touch → `Button` or `.btn-*`.
2. Optional: refactor `EmptyStatePanel` actions to `Button`.

Input family (`INPUT_V1`) opens **only after** Select + Button lock — see roadmap.
