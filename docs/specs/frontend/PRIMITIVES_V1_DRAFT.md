# PRIMITIVES_V1_DRAFT

Status: **Superseded** by `PRIMITIVES_V1.md` (partial lock 2026-05-29)  
Date: 2026-05-29  
Input: `STATUS_BADGE_V1_DRAFT.md`, `CHIP_V1_DRAFT.md`, `FOUNDATION_V1.md`  
Purpose: official allow-list for implemented Badge + Chip primitives.

## Scope

This partial draft covers **P0 families only**. Queued: Select, Button, Input.

## Implemented Components

| Component | Path | Status |
|---|---|---|
| `StatusBadge` | `components/ui/StatusBadge.tsx` | ✅ |
| `stageSemanticForCode` | `components/ui/statusBadgeSemantics.ts` | ✅ |
| `Chip` | `components/ui/Chip.tsx` | ✅ |
| `StageTag` | adapter → `StatusBadge` | ✅ |
| `DocumentStatus` | adapter → `StatusBadge` | ✅ |

---

## 1) StatusBadge — Allowed

### Semantics

`success`, `warning`, `danger`, `info`, `neutral`, `brand`

### Sizes

`sm`, `md`

### Shapes

`default` (rounded-md), `pill` (rounded-full)

### Adapters (allowed)

- `StageTag` — stage label via `stageSemanticForCode`
- `DocumentStatus` — severity via `documentSeverityToSemantic`

### Legacy (migrate on touch)

- Inline status pills with raw Tailwind colors
- Raw `.badge` for status meaning
- `NextActionBadge` palette strings (→ semantic inverse map)

### Deprecated (new code)

- Per-stage color maps
- Palette props / `bg-green-100` for status

---

## 2) Chip — Allowed

### Behaviors

`static`, `dismissible`, `selectable`, `action`

### Sizes

`sm`, `md`

### Legacy (migrate on touch)

- `FilterBadges` internal markup
- `CandidatesQuickViewsBar` preset/shortcut buttons
- `NbaNextActionsChips` inline classes

### Deprecated (new code)

- Ad-hoc chip markup without `Chip`
- Chip for status labels (use `StatusBadge`)

---

## 3) Queued (not in this draft)

| Family | Artifact |
|---|---|
| Selects | `SELECT_V1` |
| Buttons | `BUTTON_V1` |
| Inputs | `INPUT_V1` |

---

## 4) Next Steps

1. ~~Migrate `FilterBadges` → `Chip dismissible`~~ ✅
2. ~~Migrate `CandidatesQuickViewsBar` → `Chip selectable`~~ ✅
3. ~~Migrate `NextActionBadge` → semantic inverse tokens~~ ✅
4. Governance → partial lock / full `PRIMITIVES_V1` after remaining families
