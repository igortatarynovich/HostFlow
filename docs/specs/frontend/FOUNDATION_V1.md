# FOUNDATION_V1

Status: **Locked**  
Draft date: 2026-05-29  
Locked date: 2026-05-29  
Governance: Approved (REF-UI-000 Foundation chain)  
Input: `FOUNDATION_BENCHMARK.md`, `FOUNDATION_ENFORCEMENT_AND_MIGRATION_PLAN.md`  
Supersedes: `FOUNDATION_V1_DRAFT.md`

## Question Answered

> Что официально разрешено использовать в HostFlow?

This is the canonical allow-list for HostFlow UI foundation. Derived from audit evidence. Enforced by CI on PR diffs.

## Governance

| Rule | Detail |
|---|---|
| Authority | `REF-UI-*` artifacts only; product tasks do not change canon |
| New code | Must use **Allowed** tokens only |
| Existing code | **Legacy** tokens remain valid until refactored |
| **Deprecated** | Forbidden in new code; CI blocks in diff |
| Changes | Require explicit governance decision in `REF-UI-*` |
| Enforcement | `hostflow-frontend/scripts/check-foundation-tokens.sh` (see `FOUNDATION_ENFORCEMENT_AND_MIGRATION_PLAN.md`) |

---

## 1) Typography

### Body (Allowed)

| Token | Role | Tailwind |
|---|---|---|
| `type-body-xs` | Meta, labels, table cells | `text-xs` |
| `type-body-sm` | Default UI text | `text-sm` |

### Headings (Allowed)

| Token | Role | Tailwind |
|---|---|---|
| `type-heading-sm` | Section headings | `text-lg` |
| `type-heading-md` | Page subheadings | `text-xl` |
| `type-heading-lg` | Entity titles, primary display | `text-2xl` |

### Weights (Allowed)

| Token | Tailwind |
|---|---|
| `weight-medium` | `font-medium` |
| `weight-semibold` | `font-semibold` |

### Line Height (Allowed)

| Token | Tailwind |
|---|---|
| `leading-tight` | `leading-tight` |
| `leading-relaxed` | `leading-relaxed` |

### Legacy (allowed, not default)

| Token | Tailwind | Note |
|---|---|---|
| `type-display` | `text-3xl` | Migrate to `type-heading-lg` |
| `type-prose` | `text-base` | Long-form content only |
| `weight-bold` | `font-bold` | Migrate to `weight-semibold` |
| `weight-normal` | `font-normal` | Reset only |
| `leading-none` | `leading-none` | Heading reset only |
| `font-mono` | `font-mono` | Code/IDs only |

### Deprecated (forbidden in new code)

`text-4xl`, `text-6xl`, `leading-snug`, `leading-4`, `leading-5`, `leading-6`

---

## 2) Spacing

### Allowed Scale

| Token | Value | Tailwind suffix | Typical use |
|---|---:|---|---|
| `space-0` | 0 | `0` | Reset |
| `space-xs` | 2px | `0.5` | Micro gaps |
| `space-1` | 4px | `1` | Tight inline |
| `space-2` | 8px | `2` | Default component gap |
| `space-3` | 12px | `3` | Input padding, cell padding |
| `space-4` | 16px | `4` | Card padding, section gap |
| `space-6` | 24px | `6` | Section separation |
| `space-8` | 32px | `8` | Large container padding |

**Operational rule:** tables, cards, entity layouts use `space-0` through `space-8` only.

### Legacy (allowed, not default)

| Value | Tailwind suffix | Note |
|---:|---|---|
| `space-10` | `10` | Auth/public shells only; not for tables/cards |
| `space-12` | `12` | Auth/public shells only; not for tables/cards |

### Deprecated (forbidden in new code)

Half-steps: `1.5`, `2.5`, `3.5`, `5`, `7`  
Outliers: `16`, `20`, `24`, `32`, `96`, `px`

Migration map:

| Deprecated | → Allowed |
|---|---|
| `1.5` | `2` |
| `2.5` | `2` or `3` |
| `3.5` | `3` or `4` |
| `5` | `4` or `6` |
| `7` | `6` or `8` |
| `24` | `8` or layout refactor |

---

## 3) Colors

### Storage Rule (Locked)

Colors are stored as **semantics**, not palettes.

```
✅  color-success, color-danger, color-neutral-muted
❌  emerald-500, rose-500, slate-500 (in component code)
```

Palette mapping lives in one config layer (`tailwind.config.cjs` → semantic aliases). Components reference semantics only.

### Semantic Allow-List

#### Text

| Token | Maps to |
|---|---|
| `color-text-primary` | `slate-900` |
| `color-text-secondary` | `slate-700` |
| `color-text-muted` | `slate-500` |
| `color-text-inverse` | `white` |

#### Surface

| Token | Maps to |
|---|---|
| `color-surface-primary` | `white` |
| `color-surface-secondary` | `slate-50` |
| `color-surface-elevated` | `white` + `shadow-1` |
| `color-surface-overlay` | `slate-900/80` |

#### Border

| Token | Maps to |
|---|---|
| `color-border-default` | `slate-200` |
| `color-border-subtle` | `slate-100` |
| `color-border-strong` | `slate-300` |

#### Brand

| Token | Maps to |
|---|---|
| `color-brand-subtle` | `brand-50` |
| `color-brand-default` | `brand-600` |
| `color-brand-strong` | `brand-700` |
| `color-brand-text` | `brand-700` |

#### Status

| Semantic | Palette | Allowed shade roles |
|---|---|---|
| `color-success` | `emerald` | `50`, `100`, `200`, `700`, `800`, `900` |
| `color-warning` | `amber` | `50`, `100`, `200`, `700`, `800`, `900` |
| `color-danger` | `rose` | `50`, `100`, `200`, `700`, `800`, `900` |
| `color-info` | `blue` | `50`, `100`, `200`, `700`, `800`, `900` |

### Neutral Palette (Allowed)

`slate-{50,100,200,300,400,500,600,700,800,900}`, `white`

### Brand Palette (Allowed)

`brand-{50,200,500,600,700,800}`

### Deprecated Color Families (forbidden in new code)

| Family | Migrate to |
|---|---|
| `gray` | `slate` |
| `green`, `teal` | `emerald` |
| `red` | `rose` |
| `yellow`, `orange` | `amber` |
| `sky`, `indigo`, `violet`, `purple`, `cyan` | `blue` |
| `zinc`, `neutral`, `stone` | `slate` (unused) |

---

## 4) Radius

### Allowed

| Token | Tailwind | px | Use |
|---|---|---:|---|
| `radius-sm` | `rounded` | 4px | Inputs, badges, small elements |
| `radius-md` | `rounded-lg` | 8px | Cards, panels, buttons |
| `radius-lg` | `rounded-xl` | 12px | Modals, large containers |

### Legacy

`rounded-full`, `rounded-none`

### Deprecated

`rounded-md`, `rounded-2xl`

---

## 5) Shadow

### Allowed

| Token | Tailwind | Elevation |
|---|---|---|
| `shadow-1` | `shadow-sm` | Cards, list items |
| `shadow-2` | `shadow-md` | Dropdowns, panels |
| `shadow-3` | `shadow-xl` | Modals, overlays |

### Legacy

`shadow-none`

### Deprecated

`shadow`, `shadow-lg`, `shadow-2xl`, `shadow-inner`

---

## 6) Layout Signals

**Allowed:** `z-20`, `z-50`, `sm:`, `md:`, `lg:`

**Legacy:** `z-10`, `z-30`, `z-40`, `xl:`

**Deprecated:** `2xl:`

---

## 7) Quick Reference — Allowed Set

```
Typography
  Body:     text-xs, text-sm
  Heading:  text-lg, text-xl, text-2xl
  Weight:   font-medium, font-semibold
  Leading:  leading-tight, leading-relaxed

Spacing
  0, 0.5, 1, 2, 3, 4, 6, 8

Colors (semantics)
  neutral, brand, success, warning, danger, info

Radius
  rounded, rounded-lg, rounded-xl

Shadow
  shadow-sm, shadow-md, shadow-xl
```

---

## 8) Enforcement

| Mechanism | Command / location |
|---|---|
| Change-range ratchet (blocking) | `npm run foundation:check` — comparison-base contract in `FOUNDATION_ENFORCEMENT_AND_MIGRATION_PLAN.md` §3.5 |
| Backlog scan (non-blocking) | `npm run foundation:scan` |
| CI | `.github/workflows/frontend-static-qa.yml` |
| Migration plan | `FOUNDATION_ENFORCEMENT_AND_MIGRATION_PLAN.md` |
| Allow exception | `foundation-allow: <reason, min 8 chars>` |

---

## 9) Foundation Chain (Complete)

| Artifact | Status |
|---|---|
| `FOUNDATION_AUDIT.md` | ✅ |
| `FOUNDATION_TOKEN_INVENTORY.md` | ✅ |
| `FOUNDATION_BENCHMARK.md` | ✅ |
| `FOUNDATION_V1_DRAFT.md` | ✅ Superseded by this document |
| `FOUNDATION_ENFORCEMENT_AND_MIGRATION_PLAN.md` | ✅ |
| **`FOUNDATION_V1.md`** | **✅ Locked** |

---

## 10) Next Step (Layer 2)

`PRIMITIVES_INVENTORY.md` complete. Next: `PRIMITIVES_BENCHMARK.md`.
