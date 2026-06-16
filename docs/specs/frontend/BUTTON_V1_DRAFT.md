# BUTTON_V1_DRAFT

Status: **Superseded** by `BUTTON_V1.md` (locked 2026-05-31)  
Date: 2026-05-29  
Layer: 2 (Primitive)  
Input: `BUTTON_BENCHMARK.md`, `FOUNDATION_V1.md`  
Purpose: document official **Button** primitive — CSS-first, React wrapper second.

## Question Answered

> Какие button variants и sizes официально разрешены — и как их использовать в новом коде?

---

## Governance

| Rule | Detail |
|---|---|
| Authority | `REF-UI-*` |
| New code | `.btn-*` classes **or** `<Button>` with allowed `variant` / `size` |
| Visual source | `styles/components.css` — wrapper must not invent new palettes |
| Max variants | **6** — primary, secondary, danger, ghost, link, icon |
| Redesign | **Forbidden** — V1 documents existing canon |

---

## 1) Variants (Locked)

| Variant | CSS mapping | Use |
|---|---|---|
| `primary` | `btn btn-primary` | Primary CTA |
| `secondary` | `btn btn-secondary` | Default action |
| `danger` | `btn btn-danger` | Destructive |
| `ghost` | `btn btn-ghost` (to add) | Tertiary / toolbar |
| `link` | link classes (no `.btn` padding) | Inline text action |
| `icon` | `btn-icon` | Icon-only |

---

## 2) Sizes

| Size | CSS | Classes applied |
|---|---|---|
| `md` (default) | base `.btn` | — |
| `sm` | `.btn-sm` | appended |
| `xs` | `.btn-xs` | appended |

---

## 3) Component Contract (Draft)

**Path (planned):** `components/ui/Button.tsx`

```tsx
type ButtonVariant = 'primary' | 'secondary' | 'danger' | 'ghost' | 'link' | 'icon'
type ButtonSize = 'md' | 'sm' | 'xs'

type ButtonProps = {
  variant?: ButtonVariant
  size?: ButtonSize
  type?: 'button' | 'submit' | 'reset'
  disabled?: boolean
  className?: string
  href?: string          // link variant → <Link> or <a>
  children: ReactNode
  onClick?: () => void
}
```

**Rules:**

- Default `type="button"` when not submit.
- `variant="link"` renders `<Link>` if `href` internal, else `<button>` with link styling.
- `variant="icon"` requires `aria-label` when no visible text.
- `className` merges last — escape hatch only, not for new palettes.

---

## 4) CSS Canon (from `components.css`)

Existing definitions remain authoritative:

| Class | Summary |
|---|---|
| `.btn` | `inline-flex`, `rounded-xl`, `text-sm font-medium`, touch min-height |
| `.btn-primary` | brand gradient, white text |
| `.btn-secondary` | white/border, slate text |
| `.btn-danger` | rose surface |
| `.btn-sm` / `.btn-xs` | smaller padding/text |

### To add before lock

```css
.btn-ghost {
  @apply btn border-transparent bg-transparent text-slate-700
         hover:bg-slate-100 active:bg-slate-200;
}
```

### To fix before lock

`.btn-icon`: replace `gray-*` with `slate-*`.

---

## 5) Allowed vs Legacy vs Deprecated

### Allowed (new code)

- `<Button variant="…">` or direct `className="btn btn-primary"`
- Size modifiers on any variant except `link`

### Legacy (migrate on touch)

- Raw `<button>` with Tailwind-only styling
- `EmptyStatePanel` local variant strings
- Ad-hoc icon buttons

### Deprecated (new code)

- Undefined `btn-ghost` orphan
- New button color systems outside CSS canon
- Deprecated foundation color families in button styles

---

## 6) Implementation Status

| Item | Status |
|---|---|
| Benchmark | ✅ |
| Spec defined | ✅ Draft |
| `Button.tsx` | ✅ Implemented |
| `.btn-ghost` CSS | ✅ |
| `.btn-icon` token fix | ✅ |
| CI enforcement | ⬜ Optional — foundation colors cover partial drift |
| `BUTTON_V1` lock | ⬜ |

---

## 7) Chain Status

| Artifact | Status |
|---|---|
| `BUTTON_BENCHMARK.md` | ✅ |
| **`BUTTON_V1_DRAFT.md`** | ✅ Draft |
| `BUTTON_V1` lock | ⬜ After wrapper |

---

## 8) Next Steps

1. Add `.btn-ghost` + fix `.btn-icon` in `components.css`.
2. Implement `Button.tsx`.
3. Migrate high-traffic orphan buttons on touch (optional before lock).
4. Governance → `BUTTON_V1` lock.
