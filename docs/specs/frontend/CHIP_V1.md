# CHIP_V1

Status: **Locked**  
Draft date: 2026-05-29  
Locked date: 2026-05-29  
Governance: Approved (REF-UI-000 Primitives chain — partial)  
Input: `PRIMITIVES_BENCHMARK.md`, `FOUNDATION_V1.md`, `STATUS_BADGE_V1.md`, `PRIMITIVES_ENFORCEMENT_AND_MIGRATION_PLAN.md`  
Supersedes: `CHIP_V1_DRAFT.md`

## Question Answered

> Какой один Chip-комponent заменяет локальные реализации filter / toggle / action chips?

This is the canonical allow-list for HostFlow chips. Enforced via PR review and migrate-on-touch; primitive CI deferred to Phase 2.

---

## Governance

| Rule | Detail |
|---|---|
| Authority | `REF-UI-*` |
| New code | Must use `Chip` with allowed `behavior` |
| Max behaviors | **4** — no fifth without governance |
| Inline custom chips | **Deprecated** in new code |
| Status labels | Use `StatusBadge` (`STATUS_BADGE_V1`) — not Chip |

---

## 1) Chip vs Badge vs Tag

| Primitive | Role | Interactive |
|---|---|---|
| **StatusBadge** | Read-only status / stage label | No |
| **Chip** | Filter, selection, action affordance | Optional |
| **Tag** (data) | Candidate tags in DB | N/A — not a UI primitive |

---

## 2) Behavior Variants (Locked Set)

| Behavior | Interactive | States | Reference |
|---|---|---|---|
| `static` | No | default | Read-only label chip |
| `dismissible` | Yes (remove) | default | `FilterBadges` |
| `selectable` | Yes (toggle) | default, selected | `CandidatesQuickViewsBar` |
| `action` | Yes (trigger/navigate) | default, hover, disabled | `NbaNextActionsChips` |

**No fifth behavior** without explicit governance decision.

---

## 3) Component Contract

Implementation: `hostflow-frontend/src/components/ui/Chip.tsx`

```tsx
type ChipBehavior = 'static' | 'dismissible' | 'selectable' | 'action'

type ChipProps = {
  label: ReactNode
  behavior: ChipBehavior
  selected?: boolean
  selectedAppearance?: 'solid' | 'soft'  // selectable only
  onDismiss?: () => void
  onClick?: () => void
  href?: string
  disabled?: boolean
  size?: 'sm' | 'md'
  title?: string
  className?: string
  dismissLabel?: string
}
```

### Rendering rules

| Behavior | Element | A11y |
|---|---|---|
| `static` | `<span>` | — |
| `dismissible` | `<span>` + dismiss button | `aria-label` on remove |
| `selectable` | `<button type="button">` | `aria-pressed={selected}` |
| `action` | `<button>` or `<Link>` if `href` | `aria-label` when icon-only |

### Selected appearance (selectable)

| Mode | Use | Visual |
|---|---|---|
| `solid` | Quick-view presets | `bg-brand-600 text-white` |
| `soft` | Shortcut filters | `bg-brand-50 text-brand-900 border-brand-400` |

---

## 4) Visual Spec (Foundation-aligned)

### Base (unselected / static / dismissible)

```
rounded-md border border-slate-200 bg-white text-slate-700
font-medium
```

### Sizes

| Size | Classes |
|---|---|
| `sm` | `text-[11px] px-2 py-0.5` (default) |
| `md` | `text-xs px-2.5 py-1` (shortcut row) |

### Dismissible

Base chip + trailing `×` with accessible dismiss control.

### Action

Default: bordered chip. Disabled: `neutral` slate surface. Locked NBA state uses `disabled` + icon — not a fifth behavior.

---

## 5) Migration Map

| Current implementation | Behavior | Status |
|---|---|---|
| `FilterBadges` chip rows | `dismissible` | ✅ |
| `CandidatesQuickViewsBar` presets | `selectable` (`solid`) | ✅ |
| `CandidatesQuickViewsBar` shortcuts | `selectable` (`soft`) | ✅ |
| `NbaNextActionsChips` | `action` | ✅ |
| `MultiSelectChips` (PublicApply) | `selectable` | ⬜ P2 |
| Ad-hoc chip markup | nearest behavior | On touch |

`FilterBadges` remains a **container** compositing multiple `Chip dismissible`.

---

## 6) Allowed vs Legacy vs Deprecated

### Allowed (new code)

- `Chip` with `behavior` ∈ `{ static, dismissible, selectable, action }`
- Composition: chip rows, scroll containers

### Legacy (existing, migrate on touch)

- `MultiSelectChips` local markup
- Ad-hoc toggle rows

### Deprecated (forbidden in new code)

- New local chip implementations without `Chip`
- Chip for **status meaning** (use `StatusBadge`)
- Fifth custom behavior pattern

---

## 7) Relationship to STATUS_BADGE_V1

| UI need | Use |
|---|---|
| Stage / severity / document status | `StatusBadge` |
| Active filter pill with remove | `Chip dismissible` |
| Quick view / saved filter toggle | `Chip selectable` |
| NBA / leads action suggestion | `Chip action` |

Do not merge StatusBadge and Chip — different semantics and a11y contracts.

---

## 8) Implementation Status

| Item | Status |
|---|---|
| Spec locked | ✅ |
| `Chip` component | ✅ |
| `FilterBadges` migration | ✅ |
| `CandidatesQuickViewsBar` migration | ✅ |
| `NbaNextActionsChips` migration | ✅ |
| Primitive CI enforcement | ⬜ Phase 2 |

---

## 9) Chain Status

| Artifact | Status |
|---|---|
| `PRIMITIVES_BENCHMARK.md` | ✅ |
| `CHIP_V1_DRAFT.md` | Superseded |
| **`CHIP_V1.md`** | ✅ **Locked** |
| `STATUS_BADGE_V1.md` | ✅ Locked (companion) |
| `PRIMITIVES_V1.md` | ✅ Partial lock |
