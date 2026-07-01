# PRIMITIVES_INVENTORY

Status: Complete  
Date: 2026-05-29  
Input: `PRIMITIVES_AUDIT.md`  
Purpose: normalize audit output — per family: usage, variants, owners, overlap, consolidation priority.

## Question Answered

> Какие варианты примитивов уникальны, кто их владеет, и что консолидировать в первую очередь?

This document does not lock canon. It ranks families for Benchmark and future `*_V1` work.

---

## Consolidation Priority Matrix

| Priority | Family | Overlap | Future V1 | Rationale |
|---|---|---|---|---|
| **P0** | Badges | **Critical** | `STATUS_BADGE_V1` | 4+ subsystems; `StageTag` conflicts with `FOUNDATION_V1`; blocks Layer 3 |
| **P0** | Chips / Tags | **High** | `CHIP_V1` | No shared component; 4+ implementations of same visual role |
| **P1** | Selects | **High** | `SELECT_V1` | 4 live patterns — consolidate API only after scenario mapping |
| **P1** | Buttons | **Medium** | `BUTTON_V1` | CSS canon mostly works; 57 files outside `.btn-*` |
| **P2** | Inputs | **Low** | `INPUT_V1` | Single `.input` style; role split is thin |
| **P2** | Checkbox / Radio / Toggle | **Low** | (defer) | Native + accent; no Switch primitive |

### Proposed Layer 2 → Layer 3 work order

```
1. STATUS_BADGE_V1   (from Badges P0)
2. CHIP_V1           (from Chips P0)
3. SELECT_V1         (from Selects P1)
4. BUTTON_V1         (from Buttons P1)
5. INPUT_V1          (from Inputs P2)
```

Not all primitive families are equally problematic. Badges and Chips are the primary UI-debt source.

---

## P0 — Badges

### Inventory

| System | Variants | Usage | Top owners | Overlap |
|---|---|---:|---|---|
| `StageTag` | **30** stage color keys × `sm`/`md` | 10 JSX | candidates, vacancies, pipeline | Uses **14 color families**; many deprecated in `FOUNDATION_V1` |
| `NextActionBadge` | 4 priorities × 2 themes + meta | 7 JSX | communications, candidate, documents | Structured DTO-driven; best candidate API |
| `DocumentStatus` | 4 severities | 6 JSX | documents, hr, surfaces | Overlaps with status badge semantics |
| `.badge` CSS | 1 base | **75** class uses | **candidates**, hr, calendar | Shared class, no semantics |
| Inline `rounded-md px-2` pills | **~15+** ad-hoc colors | **70** | **admin**, candidate, invoices | Duplicate of badge role |
| Inline `rounded-full border px-2` pills | **~10+** ad-hoc | **49** | **hr**, candidate, services | Duplicate of status pill role |
| `FilterBadges` | dismissible filter chips | 2 JSX | candidates | Overlaps with Chip family |

### `StageTag` — Foundation conflict detail

| Color family in `StageTag` | Keys | FOUNDATION_V1 status |
|---|---:|---|
| `slate`, `brand`, `emerald`, `amber`, `rose` | 14 | Allowed |
| `green`, `red`, `indigo`, `yellow`, `orange`, `purple`, `sky`, `teal`, `violet` | 16 | **Deprecated** |

Same stage semantics rendered with incompatible palettes.

### Duplicate signal

Not 4 components — **4 semantic models** for one UI role (status/label pill):

1. **Pipeline stage** (`StageTag`) — 30 arbitrary colors  
2. **Next action priority** (`NextActionBadge`) — structured  
3. **Document severity** (`DocumentStatus`) — 4-level  
4. **Ad-hoc admin/HR pills** — no shared API  

### Consolidation hypothesis (for Benchmark)

- One **status badge** semantic layer (`success`, `warning`, `danger`, `info`, `neutral`, `brand`) aligned with `FOUNDATION_V1`.
- `StageTag` colors collapse to semantic roles, not per-stage palette grid.
- `NextActionBadge` priority map becomes reference implementation.
- Inline pills migrate to shared badge primitive.

**Target variant count:** ~6 semantic variants + 2 sizes (not 50+).

---

## P0 — Chips / Tags

### Inventory

| Implementation | Role | Usage | Owner | Overlap |
|---|---|---:|---|---|
| `FilterBadges` | Dismissible active-filter chip | 21 refs | **candidates** | Badge + chip hybrid |
| `CandidatesQuickViewsBar` | Selectable saved-view chip | 10 refs | **candidates** | Toggle/selection UX |
| `MultiSelectChips` (PublicApply) | Toggle multiselect chip | 5 JSX | public intake | Selection UX |
| `NbaNextActionsChips` | Action suggestion chip | 3 refs | nba | Action/navigation UX |
| `chip` string refs | Ad-hoc local patterns | 11 refs | scattered | Unowned |

**No `Chip.tsx` or `Tag.tsx` exists.**

### One component or different entities?

| UX behavior | Examples | Same primitive? |
|---|---|---|
| **Static label** | stage label, read-only tag | Base chip |
| **Dismissible** | `FilterBadges` | Variant: `dismissible` |
| **Selectable / toggle** | QuickViews, MultiSelectChips | Variant: `selected` |
| **Action** | `NbaNextActionsChips` | Variant: `action` (or separate `ActionChip`) |

**Inventory verdict:** **one logical component** (`Chip`) with **3–4 behavior variants**, not 4 separate primitives.  
`Tag` is not a separate entity in code today — "tags" appear as candidate bulk-tagging (data) and filter chips (UI). UI chip covers both.

### Consolidation hypothesis (for Benchmark)

- `CHIP_V1` = base + `dismissible` + `selectable` (+ optional `action`).
- `FilterBadges` and `CandidatesQuickViewsBar` are first migration targets (same owner: candidates module).

---

## P1 — Selects

### Inventory by scenario (not by component count)

| Scenario | Implementation | Usage | Top owners | Notes |
|---|---|---:|---|---|
| **Simple enum** | native `<select>` | **301** | admin (45), hr (29), calendar (24), fleet (21) | Default for settings, filters, forms |
| **Searchable list (sync)** | `controls/Select` | 3 import paths | public intake, phone | Combobox with local filter |
| **Searchable list (form)** | `SearchableSelect` | 13 refs | **candidate card** | Near-duplicate of `Select` |
| **Multi with checkboxes** | `CheckboxMultiSelect` | 8 refs | candidate sections | Dropdown multiselect |
| **Async load** | `SelectAsync` | **0** imports | — | **Dead** |
| **Multi chips** | `MultiSelect` | **0** imports | — | **Dead** |
| **Domain wrappers** | `FunnelSelector`, etc. | few | profile, leads | Native or thin wrapper |

### Overlap

| Pair | Relationship |
|---|---|
| `Select` ↔ `SearchableSelect` | **~90% duplicate logic** (trigger, dropdown, filter) |
| `CheckboxMultiSelect` ↔ `MultiSelect` (dead) | Same UX, different codepath |
| native `<select>` ↔ combobox | Different scenarios — **do not merge blindly** |

### Scenario map (for Benchmark — do not collapse yet)

| When to use | Candidate canon |
|---|---|
| &lt;10 static options, no search | native `Select` or thin styled wrapper |
| Long list, local search | `Combobox` (merge `Select` + `SearchableSelect`) |
| Multiple values | `MultiSelect` / `CheckboxMultiSelect` |
| Remote/async options | `AsyncSelect` (revive `SelectAsync` or replace) |

**Inventory verdict:** **4 scenarios, 1–2 canonical components** after Benchmark — not one mega-select.

---

## P1 — Buttons

### Inventory

| Layer | Variants | Usage | Overlap |
|---|---|---:|---|
| CSS `.btn-primary` | 1 | **269** | Canon |
| CSS `.btn-secondary` | 1 | **731** | Canon |
| CSS `.btn-danger` | 1 | **57** | Canon |
| Size modifiers `btn-sm`, `btn-xs` | 2 | 370 / 224 | Modifiers, not variants |
| CSS `.btn-icon` | 1 | **0** | Dead definition |
| `btn-ghost` | — | **1** | Orphan |
| Raw `<button>` total | — | **1,418** | — |
| Files using `.btn-*` | — | **~143 files** | — |
| Files with `<button>` **without** `.btn-*` | — | **57 files** | Drift zone |
| Link-style (`underline`) | — | **~55** | Outside `.btn-*` system |

### Top owners (CSS buttons)

| Owner | Files with btn-* |
|---|---:|
| `pages/admin` | 26 |
| `components/candidate` | 19 |
| `components/hr` | 16 |
| `modules/candidates` | 14 |
| `components/leads` | 12 |

### Duplicate signal

**Opposite of badges:** CSS system is real and heavily adopted (~75% of button files use `.btn-*`).  
Gap is **edge variants** (ghost, link, icon) and **57 unstyled button files** — not a missing primary system.

**Inventory verdict:** **low consolidation urgency.** `BUTTON_V1` likely documents + thin React wrapper over existing CSS, not redesign.

---

## P2 — Inputs

### Inventory

| Role | Implementation | Usage | Top owners | Overlap |
|---|---|---:|---|---|
| Text-like | `.input` class | **708** | admin (239), calendar (71), vacancies (49) | Single style |
| Textarea | `.textarea` | **83** | scattered | Same design language |
| Date | `type="date"` native | **64** | filters, HR | No calendar component |
| Phone | `PhoneInput` | 2 files | candidate | Composite |
| Form wrapper | `FormComponents.Input` | 5 files | candidate | Thin wrapper |
| Dead wrapper | `Field.tsx` | **0** | — | Remove candidate |
| Document fields | `DocumentFieldInput` | documents module | documents | Domain-specific |

### Duplicate signal

**Minimal.** One visual style (`.input`), multiple roles. Risk is **wrapper duplication** (`Field` dead, `FormComponents.Input` marginal), not visual chaos.

**Inventory verdict:** **`INPUT_V1` = document roles + `.input` contract.** Low priority.

---

## P2 — Checkbox / Radio / Toggle

| Control | Usage | Variants | Notes |
|---|---:|---|---|
| Checkbox native | **186** | 1 (brand accent) | `FormComponents.Checkbox` in 4 places only |
| Radio native | **7** | 1 | 4 files (onboarding, leads) |
| Switch | **0** | — | No primitive |
| Button-group toggle | few | ad hoc | `aria-pressed` / `btn-secondary` groups |

Defer until after Chip/Badge/Select. No inventory action required now beyond audit facts.

---

## Dead Code (cross-family)

| File | Family | External imports |
|---|---|---:|
| `controls/Field.tsx` | Input | **0** |
| `controls/SelectAsync.tsx` | Select | **0** |
| `controls/MultiSelect.tsx` | Select | **0** |

Candidate for removal or revival in Benchmark (async select scenario).

---

## Per-Family Summary Table

| Family | Implementations | Variant count | Usage (core) | Overlap | Priority | Future V1 |
|---|---|---:|---|---|---|---|
| Badges | 4+ systems | **50+** | 75–210+ | Critical | **P0** | `STATUS_BADGE_V1` |
| Chips/Tags | 4+ local | **4 behaviors** | ~50 refs | High | **P0** | `CHIP_V1` |
| Selects | 4 live + 2 dead | 4 scenarios | 301 native + ~20 custom | High | **P1** | `SELECT_V1` |
| Buttons | CSS + raw HTML | 3 canon + 3 edge | 1,418 `<button>` | Medium | **P1** | `BUTTON_V1` |
| Inputs | CSS + wrappers | 1 style, 5 roles | 708 `.input` | Low | **P2** | `INPUT_V1` |
| Checkbox/Toggle | native only | 1 | 186 / 7 | Low | **P2** | defer |

---

## Output to Next Step

This inventory answers:

- which families matter most (Badges, Chips),
- which are scenario-split not count-split (Selects),
- which are already stable (Buttons, Inputs),
- proposed `*_V1` sequencing.

Next artifact:

**`PRIMITIVES_BENCHMARK.md`** — Badge/Chip classification complete.

Chain:

| Artifact | Status |
|---|---|
| `PRIMITIVES_AUDIT.md` | ✅ |
| `PRIMITIVES_INVENTORY.md` | ✅ |
| `PRIMITIVES_BENCHMARK.md` | ✅ |
| `STATUS_BADGE_V1_DRAFT` | ✅ Draft |
| `CHIP_V1_DRAFT` | ✅ Draft |
| Implementation + lock | ← Next |
