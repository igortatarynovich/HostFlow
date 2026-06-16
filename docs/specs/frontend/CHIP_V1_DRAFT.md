# CHIP_V1_DRAFT

Status: **Superseded** by `CHIP_V1.md` (locked 2026-05-29)  
Date: 2026-05-29  
Layer: 2 (Primitive)  
Input: `PRIMITIVES_BENCHMARK.md`, `FOUNDATION_V1.md`  
Purpose: define the official **Chip** primitive with a limited behavior variant set.

## Question Answered

> Какой один Chip-компонент заменяет локальные реализации filter / toggle / action chips?

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

"Tag" in bulk-tagging modals is **data**, not UI. UI chip covers filter/selection surfaces.

---

## 2) Behavior Variants (Locked Set)

| Behavior | Interactive | States | Reference |
|---|---|---|---|
| `static` | No | default | Read-only label chip |
| `dismissible` | Yes (remove) | default | `FilterBadges` |
| `selectable` | Yes (toggle) | default, selected | `CandidatesQuickViewsBar` |
| `action` | Yes (trigger/navigate) | default, hover, disabled | `NbaNextActionsChips` |

**No fifth behavior** without explicit governance decision.

### Action chip decision

Benchmark left `action` as Candidate with optional split. **V1 Draft decision:** keep as `behavior="action"` on same `Chip` component. Same a11y base as `selectable` + optional `href` / `onClick`. Split to `ActionChip` only if keyboard contract diverges in implementation review.

---

## 3) Component Contract (Draft)

```tsx
type ChipBehavior = 'static' | 'dismissible' | 'selectable' | 'action'

type ChipProps = {
  label: string
  behavior: ChipBehavior
  selected?: boolean          // selectable
  onDismiss?: () => void      // dismissible
  onClick?: () => void        // selectable | action
  href?: string               // action (Link)
  disabled?: boolean
  size?: 'sm' | 'md'
  title?: string
}
```

### Rendering rules

| Behavior | Element | A11y |
|---|---|---|
| `static` | `<span>` | — |
| `dismissible` | `<span>` + dismiss button | `aria-label` on remove |
| `selectable` | `<button type="button">` | `aria-pressed={selected}` |
| `action` | `<button>` or `<Link>` if `href` | `aria-label` when icon-only |

---

## 4) Visual Spec (Foundation-aligned)

### Base (unselected / static / dismissible default)

```
rounded-md border border-slate-200 bg-white text-slate-700
text-[11px] font-medium px-2 py-0.5
```

Uses `FOUNDATION_V1` spacing (`space-2`, `space-3` equivalents) and neutral tokens.

### Selected (selectable)

```
bg-brand-600 text-white border-brand-600 shadow-sm
hover:bg-brand-700
```

Matches `CandidatesQuickViewsBar` active preset pattern.

### Dismissible

Base chip + trailing `×` control with `min-h-[44px]` touch target on mobile for dismiss hit area (or padded dismiss zone).

### Action

Default: bordered chip. Hover: `hover:bg-slate-50`. Locked state (NBA): `bg-slate-100 text-slate-600` + lock icon — semantic `neutral`, not new behavior.

### Sizes

| Size | Classes |
|---|---|
| `sm` | `text-[11px] px-2 py-0.5` (default, matches audit) |
| `md` | `text-xs px-2.5 py-1` (shortcut row) |

---

## 5) Migration Map

| Current implementation | Behavior | Priority |
|---|---|---|
| `FilterBadges` chip rows | `dismissible` | **P1** |
| `CandidatesQuickViewsBar` presets | `selectable` | **P1** |
| `CandidatesQuickViewsBar` doc shortcuts | `selectable` | P2 |
| `MultiSelectChips` (PublicApply) | `selectable` | P2 |
| `NbaNextActionsChips` | `action` | P3 |
| Ad-hoc `chip` markup | → nearest behavior | On touch |

`FilterBadges` remains a **container** compositing multiple `Chip dismissible` — not replaced wholesale.

---

## 6) Allowed vs Legacy vs Deprecated

### Allowed (new code)

- `Chip` with `behavior` ∈ `{ static, dismissible, selectable, action }`
- Composition: chip rows, scroll containers (existing layout patterns)

### Legacy (existing, migrate on touch)

- `FilterBadges` internal markup
- `CandidatesQuickViewsBar` `presetBtn` / `shortcutBtn` local classes
- `NbaNextActionsChips` inline classes

### Deprecated (forbidden in new code)

- New local chip implementations (`rounded-md px-2` toggle rows without `Chip`)
- Chip used for **status meaning** (use `StatusBadge` instead)
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
| Spec defined | ✅ |
| `Chip` component | ✅ Implemented |
| `FilterBadges` migration | ✅ |
| `CandidatesQuickViewsBar` migration | ✅ |
| CI enforcement | ⬜ |

---

## 9) Chain Status

| Artifact | Status |
|---|---|
| `PRIMITIVES_BENCHMARK.md` | ✅ |
| `CHIP_V1_DRAFT.md` | ✅ Draft |
| `STATUS_BADGE_V1_DRAFT.md` | ✅ Draft |
| `CHIP_V1` (lock) | ⬜ After implementation + governance |
| `PRIMITIVES_V1_DRAFT` (partial) | ⬜ Badge + Chip sections |

---

## 10) Next Steps

1. Implement `Chip` with 4 behaviors.
2. Migrate `FilterBadges` + `CandidatesQuickViewsBar` (same owner: candidates).
3. Governance review → `CHIP_V1` lock.
4. Partial `PRIMITIVES_V1_DRAFT` (Badge + Chip allow-list).
