# PRIMITIVES_AUDIT

Status: Complete  
Date: 2026-05-29  
Scope: `hostflow-frontend/src`  
Input: `FOUNDATION_V1.md` (locked)  
Purpose: answer unknown question **"what primitive components actually exist in the codebase now?"**

## Method

Static scan of `hostflow-frontend/src` (`.ts`, `.tsx`):

- component definitions and CSS primitives,
- usage counts (ripgrep),
- implementation variants per family.

This audit records facts only. No canon decisions.

## Layer 2 Chain (Locked Discipline)

Same sequence as Foundation:

```
AUDIT → INVENTORY → BENCHMARK → V1_DRAFT → ENFORCEMENT → LOCK
```

This document is step 1 for Layer 2 (Primitives).

---

## Executive Summary

| Finding | Detail |
|---|---|
| Shared primitive kit | **Does not exist** — no `Button.tsx`, `Input.tsx`, `Badge.tsx` in `components/ui/` |
| CSS layer | `styles/components.css` defines `.btn-*`, `.input`, `.badge`, `.label` |
| Dominant pattern | Raw HTML (`<button>`, `<input>`, `<select>`) + utility/CSS classes |
| Highest duplication | Selects (3 combobox stacks), Badges (4+ subsystems) |
| Dead code | `Field.tsx`, `SelectAsync.tsx`, `MultiSelect.tsx` — 0 external imports |
| Roadmap link | `STATUS_BADGE_V1` (Layer 3) depends on badge facts captured here |

---

## 1) Buttons

### Question

How many button variants really exist: primary, secondary, ghost, danger, icon, link — or more?

### CSS-defined variants (`components.css`)

| Class | Defined | TSX usage |
|---|---:|---:|
| `.btn` | ✅ base | (combined with variants) |
| `.btn-primary` | ✅ | **269** |
| `.btn-secondary` | ✅ | **731** |
| `.btn-danger` | ✅ | **57** |
| `.btn-sm` | ✅ size | **370** |
| `.btn-xs` | ✅ size | **224** |
| `.btn-icon` | ✅ | **0** |
| `.btn-ghost` | ❌ not in CSS | **1** (orphan class) |
| `.btn-link` | ❌ not in CSS | **0** |

### React button components

| Component | Path | Variants |
|---|---|---|
| — | No shared `Button.tsx` | — |
| `EmptyStatePanel` | `components/EmptyStatePanel.tsx` | `primary` \| `secondary` (internal) |
| `HrDocumentOpenButton` | `components/hr/HrDocumentOpenButton.tsx` | `link` \| `button` |

### Raw usage

| Pattern | Count | Files |
|---|---:|---:|
| `<button` | **1,418** | ~200+ |
| Link-style (`text-brand-700` + `hover:underline`) | **~55** | ~50 |

### Answer

**6 semantic roles observed**, but only **3 are CSS-canonical** (primary, secondary, danger):

| Role | How implemented | Canonical? |
|---|---|---|
| Primary | `.btn-primary` | ✅ CSS |
| Secondary | `.btn-secondary` | ✅ CSS |
| Danger | `.btn-danger` | ✅ CSS |
| Ghost | `btn-ghost` (1×, no CSS) + ad-hoc Tailwind | ❌ fragmented |
| Icon | `.btn-icon` defined, unused | ❌ dead CSS |
| Link | underline text pattern, `HrDocumentOpenButton` | ❌ outside `.btn-*` |

Sizes (`btn-sm`, `btn-xs`) are modifiers, not semantic variants.

---

## 2) Inputs

### Question

How many input types exist: text, textarea, search, masked, date — and what styles?

### CSS primitives

| Class | Role |
|---|---|
| `.input` | Text-like inputs (rounded-xl, brand focus ring) |
| `.textarea` | Multiline |
| `.label` | Field label |
| `.input-sm` | Document fields variant |

Context overrides: `.app-ui`, `.settings-surface`, `.modal-surface` reshape same classes.

### React wrappers

| Component | Path | Imports |
|---|---|---:|
| `Input` | `candidate/shared/FormComponents.tsx` | **5 files** |
| `Field` | `components/controls/Field.tsx` | **0** (dead) |
| `PhoneInput` | `components/controls/PhoneInput.tsx` | **2 files** |
| `DocumentFieldInput` | `modules/documents/components/DocumentFieldInput.tsx` | documents module |

### Usage by type

| Type | Implementation | Count |
|---|---|---:|
| Text-like | `.input` class | **708** |
| Textarea | `<textarea>` / `.textarea` | **83** |
| Search | placeholder/filter inside selects, not a shared Input variant | **~26** search UIs |
| Masked | No shared mask primitive | **0** |
| Date | native `<input type="date">` | **64** (`type="date"`) |
| Phone | `PhoneInput` (select + input) | **2** consumers |

### Answer

**5 input roles** in practice; **1 CSS style** (`.input`) dominates. No masked-input library. Date = native only. Search is embedded in combobox/filter UIs, not a standalone primitive.

---

## 3) Selects

### Question

How many implementations: native select, custom select, combobox, async select?

### Implementations

| Type | Location | Usage | Status |
|---|---|---:|---|
| **Native `<select>`** | Inline across app | **301** / **101 files** | Dominant |
| **`Select`** (searchable combobox) | `components/controls/Select.tsx` | **3** import paths | Active (public intake, phone) |
| **`SearchableSelect`** | `FormComponents.tsx` | **8** JSX / **5 files** | Active (candidate card) |
| **`CheckboxMultiSelect`** | `FormComponents.tsx` | **4** JSX / **3 files** | Active |
| **`SelectAsync`** | `controls/SelectAsync.tsx` | **0** imports | **Dead** |
| **`MultiSelect`** | `controls/MultiSelect.tsx` | **0** imports | **Dead** |
| **`MultiSelectChips`** | local in `PublicApplyPage.tsx` | **4** JSX | Public intake only |
| Domain wrappers | `FunnelSelector`, `RecruiterAvailabilitySelect`, `LeadTemplateSelectField` | native or local | Feature-specific |

### Combobox pattern comparison

All custom selects share: button trigger → dropdown → filter input → click-outside close.

| | `controls/Select` | `SearchableSelect` | `SelectAsync` |
|---|---|---|---|
| Search | ✅ | ✅ | ✅ |
| Async fetch | ❌ | ❌ | ✅ (unused) |
| Dropdown style | `rounded-2xl shadow-xl` | `rounded-xl shadow-xl` | `rounded-lg` |

### Answer

**4 live select patterns** (native, `Select`, `SearchableSelect`, `CheckboxMultiSelect`) + **2 dead** (`SelectAsync`, `MultiSelect`). Native select is ~93% of select usage by count. Async select exists in code but is not wired.

---

## 4) Badges

### Question

How many badge variants exist? Are the same statuses rendered consistently?

### Subsystems (no unified `Badge.tsx`)

| System | Path / source | Distinct variants |
|---|---|---:|
| `.badge` CSS | `components.css` | **1** base style |
| `StageTag` | `components/StageTag.tsx` | **30** stage color keys + `sm`/`md` |
| `NextActionBadge` | `components/candidate/NextActionBadge.tsx` | **4** priorities × **2** themes + loading/error |
| `DocumentStatus` | `components/surfaces/DocumentStatus.tsx` | **4** severities |
| `FilterBadges` | `modules/candidates/components/FilterBadges.tsx` | dismissible `.badge` chips |
| Inline pills | HR/admin tables | **~15+** ad-hoc Tailwind combos |

### Usage counts

| Component / pattern | Count |
|---|---:|
| `className="badge"` | **28** |
| `<StageTag` | **10** |
| `NextActionBadge` refs | **18** |
| `DocumentStatus` (tsx) | **42** |
| `FilterBadges` | **19** refs |
| `rounded-full border px-2` pills | **18** |
| `inline-flex rounded-md px-2` pills | **~55** |

### Status consistency signal

`StageTag` alone uses **deprecated color families** from Foundation (`green`, `red`, `indigo`, `yellow`, `orange`, `purple`, `sky`, `teal`) — same semantic stage intent, different palettes across the map. This directly conflicts with `FOUNDATION_V1` status semantics and foreshadows `STATUS_BADGE_V1` work.

### Answer

**4+ badge subsystems**, **50+ visual variants** when counting `StageTag` keys and inline pills. Status rendering is **not consistent** across modules.

---

## 5) Chips / Tags

### Question

Is there one component or several implementations?

### Findings

| Name | Path | Role |
|---|---|---|
| `Chip.tsx` / `Tag.tsx` | — | **Do not exist** |
| `NbaNextActionsChips` | `components/nba/NbaNextActionsChips.tsx` | NBA action chips |
| `MultiSelectChips` | local in `PublicApplyPage.tsx` | toggle multiselect |
| `FilterBadges` | candidates module | dismissible filter chips |
| `CandidatesQuickViewsBar` | candidates module | saved-view chips |
| `BulkTagsModal` | candidates module | tag assignment (modal, not chip primitive) |

`chip` string appears in **~70** refs across **24** files — mostly local patterns, not a shared API.

### Answer

**No shared Chip/Tag primitive.** At least **4 parallel implementations** for the same visual role (filter chip, toggle chip, action chip, quick-view chip).

---

## 6) Checkboxes / Radios / Toggles

### Question

How many visual variants?

| Control | Implementation | Count |
|---|---|---:|
| Checkbox (native) | `<input type="checkbox">` | **186** |
| Checkbox (component) | `FormComponents.Checkbox` | **4** usages |
| Checkbox in dropdown | `CheckboxMultiSelect`, filter menus | duplicated pattern |
| Radio (native) | `<input type="radio">` | **7** / **4 files** |
| Switch / toggle | `role="switch"` | **0** |
| Segmented toggle | `aria-pressed` button groups | **2** files |
| View-mode toggles | button groups (`btn-secondary`) | several pages |

Global styling: `accent-color: brand.500` on all native checkboxes/radios in `components.css`.

### Answer

**1 visual variant** for checkbox/radio (browser native + brand accent). **No Switch primitive.** Boolean UX split between raw checkboxes and button-group toggles.

---

## 7) Primitive Definition Index

```
hostflow-frontend/src/styles/components.css          # CSS primitives
hostflow-frontend/src/components/controls/Field.tsx           # dead
hostflow-frontend/src/components/controls/Select.tsx
hostflow-frontend/src/components/controls/SelectAsync.tsx     # dead
hostflow-frontend/src/components/controls/MultiSelect.tsx     # dead
hostflow-frontend/src/components/controls/PhoneInput.tsx
hostflow-frontend/src/components/candidate/shared/FormComponents.tsx
hostflow-frontend/src/components/EmptyStatePanel.tsx
hostflow-frontend/src/components/hr/HrDocumentOpenButton.tsx
hostflow-frontend/src/components/StageTag.tsx
hostflow-frontend/src/components/candidate/NextActionBadge.tsx
hostflow-frontend/src/components/surfaces/DocumentStatus.tsx
hostflow-frontend/src/modules/candidates/components/FilterBadges.tsx
hostflow-frontend/src/components/nba/NbaNextActionsChips.tsx
hostflow-frontend/src/modules/documents/components/DocumentFieldInput.tsx
hostflow-frontend/src/components/ui/SectionCard.tsx           # layout only
hostflow-frontend/src/components/ui/FieldGrid.tsx             # layout only
```

`components/ui/` is **not** a primitive kit — 2 layout helpers only.

---

## 8) Duplication Priority (for Inventory step)

| Rank | Family | Issue | Severity |
|---|---|---|---|
| 1 | Badges | 4+ subsystems; `StageTag` uses deprecated colors | **Critical** |
| 2 | Selects | 3 live combobox stacks + 2 dead; 301 native selects | **High** |
| 3 | Buttons | 1,418 raw `<button>`; ghost/link outside CSS | **High** |
| 4 | Chips/Tags | No shared primitive; 4+ patterns | **Medium** |
| 5 | Inputs | 708 raw `.input`; 2 wrappers (1 dead) | **Medium** |
| 6 | Checkbox/Toggle | Native only; no Switch | **Low** |

---

## 9) Findings Summary

1. Primitives are **CSS-first**, not **component-first**.
2. Button canon in CSS (primary/secondary/danger) is real but **incomplete** — ghost, icon, link live outside it.
3. Native `<select>` dominates; custom combobox logic is **triplicated**.
4. Badges are the **most fragmented** family — critical for `STATUS_BADGE_V1`.
5. Dead controls (`Field`, `SelectAsync`, `MultiSelect`) add noise without usage.
6. `StageTag` is a canary for Foundation color migration — uses many deprecated families.

---

## Output for Next Step

This audit answers **what exists now.**

Next artifact:

**`PRIMITIVES_INVENTORY.md`** — variant grouping, owners, overlap, consolidation priority.

Chain:

| Artifact | Status |
|---|---|
| `PRIMITIVES_AUDIT.md` | ✅ |
| `PRIMITIVES_INVENTORY.md` | ✅ |
| `PRIMITIVES_BENCHMARK.md` | ← Next |
