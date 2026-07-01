# FOUNDATION_TOKEN_INVENTORY

Status: Complete  
Date: 2026-05-29  
Input: `FOUNDATION_AUDIT.md`  
Purpose: normalize audit output — identify unique tokens vs duplicates/overlaps, and define canonical candidate ranges.

## Question Answered

> Какие из найденных токенов являются уникальными, а какие фактически дублируют друг друга?

This document answers that question per token family. It does not lock canon yet — that is `FOUNDATION_BENCHMARK.md`.

---

## Consolidation Summary

| Category | Used Now | Likely Unique | Duplicate / Overlap | Canonical Target | Priority |
|---|---:|---:|---:|---:|---|
| Font Size | 9 | 5 | 2 display + 2 outliers | 5–6 | Medium |
| Spacing Values | 20 | 9 core | 6 merge-candidates + 5 outliers | 8–10 | **Critical** |
| Color Tokens (base) | 154 | ~25 semantic roles | ~129 shade variants + cross-family overlap | 20–30 semantic | **Critical** |
| Radius | 7 | 4 | 3 overlapping steps | 3–4 | Low |
| Shadow | 8 | 4 | 4 merge/alternate pairs | 3–4 | Medium |
| Line Height | 7 | 2 | 5 merge/legacy | 2–3 | Low |

---

## 1) Typography Inventory

### Font Size — Used vs Canon

| Token | Uses | Tier | Verdict |
|---|---:|---|---|
| `text-xs` | 2363 | XS | **Canon** — dominant body/meta size |
| `text-sm` | 2506 | SM | **Canon** — dominant UI size |
| `text-base` | 98 | MD | **Canon** — default prose, low volume |
| `text-lg` | 135 | LG | **Canon** — section headings |
| `text-xl` | 91 | XL | **Canon** — page subheadings |
| `text-2xl` | 106 | Display-1 | **Overlap** — competes with `text-xl`/`text-3xl` for headings |
| `text-3xl` | 40 | Display-2 | **Overlap** — second display tier, low reuse |
| `text-4xl` | 4 | — | **Outlier** — remove or scope to marketing only |
| `text-6xl` | 2 | — | **Outlier** — remove or scope to marketing only |

**Duplicate signal:** operational UI effectively runs on `text-xs` + `text-sm` (4870 of 5345 uses = 91%). The upper half of the scale (`text-lg` through `text-3xl`) splits 472 uses across 4 tokens — heading hierarchy is not consolidated.

**Canon candidate:** `XS / SM / MD / LG / XL` (+ optional single `Display` tier replacing both `text-2xl` and `text-3xl`).

### Font Weight — Used vs Canon

| Token | Uses | Verdict |
|---|---:|---|
| `font-semibold` | 1504 | **Canon** — primary emphasis |
| `font-medium` | 1312 | **Canon** — secondary emphasis |
| `font-bold` | 80 | **Overlap** — near-duplicate of semibold in operational UI |
| `font-normal` | 11 | **Canon** — reset/base, rare |

**Duplicate signal:** `font-bold` vs `font-semibold` — same intent, different weight. Benchmark should pick one.

### Line Height — Used vs Canon

| Token | Uses | Verdict |
|---|---:|---|
| `leading-relaxed` | 51 | **Canon** |
| `leading-tight` | 27 | **Canon** |
| `leading-snug` | 37 | **Duplicate** — sits between tight/relaxed, no distinct role |
| `leading-none` | 9 | **Legacy** — heading reset only |
| `leading-4/5/6` | 4 | **Duplicate** — numeric aliases of tight/relaxed |

**Canon candidate:** `leading-tight`, `leading-normal` (currently unused), `leading-relaxed`.

---

## 2) Spacing Inventory

### Value Set — Used vs Canon

| Value | Uses | Canon Bucket | Verdict |
|---:|---:|---|---|
| 2 | 3543 | `space-2` (SM) | **Canon** |
| 3 | 2409 | `space-3` (MD) | **Canon** |
| 1 | 1729 | `space-1` (XS) | **Canon** |
| 4 | 1533 | `space-4` (MD) | **Canon** |
| 1.5 | 472 | → merge to 2 | **Duplicate** |
| 0.5 | 438 | `space-0.5` (XS) | **Canon** (micro-spacing) |
| 6 | 382 | `space-6` (LG) | **Canon** |
| 2.5 | 189 | → merge to 2 or 3 | **Duplicate** |
| 5 | 126 | → merge to 4 or 6 | **Duplicate** |
| 8 | 119 | `space-8` (LG) | **Canon** |
| 0 | 99 | `space-0` | **Canon** (reset) |
| 10 | 26 | `space-10` (XL) | **Canon** |
| 24 | 20 | — | **Outlier** |
| 3.5 | 16 | → merge to 3 or 4 | **Duplicate** |
| 12 | 10 | `space-12` (XL) | **Canon** |
| 7 | 6 | → merge to 6 or 8 | **Duplicate** |
| 16 | 2 | — | **Outlier** |
| 96 | 1 | — | **Outlier** — `mr-96`, remove |
| 32 | 1 | — | **Outlier** |
| 20 | 1 | — | **Outlier** |

### Volume Split

| Bucket | Values | Uses | Share |
|---|---|---:|---:|
| Canon core | 0, 0.5, 1, 2, 3, 4, 6, 8, 10, 12 | 9850 | 87.5% |
| Merge candidates | 1.5, 2.5, 3.5, 5, 7 | 1247 | 11.1% |
| Outliers | 16, 20, 24, 32, 96 | 25 | 0.2% |
| Non-numeric (`px`) | — | 4 | negligible |

**Duplicate signal:** spacing is not random — 87.5% of usage already clusters on 10 values. The problem is the remaining 11.1% spread across 6 "in-between" half-steps (`1.5`, `2.5`, `3.5`, `5`, `7`) that duplicate adjacent canon steps.

**Canon candidate:** `0, 0.5, 1, 2, 3, 4, 6, 8, 10, 12` (10 values).

**Structural drift:** 154 unique spacing utility *forms* (`px-3`, `mt-2`, `gap-2`, etc.) vs 20 numeric values — high form variance, moderate value variance. Normalization is primarily a value merge, not a full redesign.

---

## 3) Color Inventory

### Scale

| Metric | Count |
|---|---:|
| Base color tokens (no alpha) | 154 |
| Tokens with alpha variants | 313 |
| Color families in use | 22 |
| Dominant neutral family | `slate` (7459 uses, 97% of neutrals) |

### Neutral Layer — Mostly Unique

| Family | Uses | Verdict |
|---|---:|---|
| `slate` | 7459 | **Canon** — de facto neutral system |
| `gray` | 18 | **Duplicate** — merge to slate |
| `zinc`, `neutral`, `stone` | 0 | unused |

**Duplicate signal:** neutral layer is already decided in practice. `gray-*` is residual noise.

### Brand Layer — Unique, Keep

| Token cluster | Uses | Verdict |
|---|---:|---|
| `brand-*` (50–900) | 1268 | **Canon** — defined in `tailwind.config.cjs`, aligned to pipedesign |
| Top: `brand-700`, `brand-600`, `brand-50` | 778 | primary brand ramp |

### Status Semantics — Highest Duplicate Risk

Each semantic intent is served by multiple color families:

| Semantic | Families Used | Total Uses | Dominant | Duplicates to Merge |
|---|---|---:|---|---|
| Success | emerald, green, teal | 511 | emerald (388) | green (101), teal (22) |
| Warning | amber, yellow, orange | 827 | amber (803) | yellow (8), orange (16) |
| Danger | rose, red | 714 | rose (512) | red (202) |
| Info | blue, sky, indigo, violet, purple, cyan | 476 | blue (188) | sky (102), indigo (122), violet (38), purple (19), cyan (7) |

**Duplicate signal:** status colors are not token-rich — they are *family-rich*. The same semantic shade role (e.g. `*-50` background, `*-700` text) is repeated across 14–17 families at shade level 50–900. This is palette duplication, not semantic diversity.

### Cross-Family Shade Pattern (structural duplicate)

The same shade number appears across many families for the same UI role:

| Shade | Families | Example |
|---|---|---|
| `*-50` | 17 | bg tint: `slate-50`, `amber-50`, `rose-50`, `emerald-50`… |
| `*-100` | 17 | light bg/border |
| `*-200` | 16 | border/subtle bg |
| `*-500` | 12 | icon/mid accent |
| `*-600` | 13 | button/bg accent |
| `*-700` | 14 | text emphasis |
| `*-800` | 15 | dark text |
| `*-900` | 14 | darkest text |

These are not 154 unique design decisions — they are ~8 shade roles × ~17 families. The canonical model should be **semantic role tokens**, not per-family shade grids.

### Canon Candidate — Semantic Layer

| Role | Target Tokens | Source |
|---|---|---|
| Text | `primary`, `secondary`, `muted`, `inverse` | slate ramp |
| Surface | `primary`, `secondary`, `elevated`, `overlay` | slate + white |
| Border | `default`, `subtle`, `strong` | slate ramp |
| Brand | `brand-subtle`, `brand-default`, `brand-strong` | brand ramp (existing) |
| Status | `success`, `warning`, `danger`, `info` × (`bg`, `text`, `border`) | one family each |

**Target:** 20–30 semantic tokens. Current 154 base tokens collapse to ~24 semantic roles with ~6× family duplication.

---

## 4) Radius Inventory

| Token | Uses | px equiv | Verdict |
|---|---:|---|---|
| `rounded-lg` | 844 | 8px | **Canon** → `radius-md` |
| `rounded` | 582 | 4px | **Canon** → `radius-sm` |
| `rounded-xl` | 351 | 12px | **Canon** → `radius-lg` |
| `rounded-md` | 265 | 6px | **Duplicate** — between sm and md, no distinct role |
| `rounded-full` | 209 | 50% | **Shape** — keep for avatars/pills only |
| `rounded-2xl` | 161 | 16px | **Duplicate** — competes with xl |
| `rounded-none` | 13 | 0 | **Reset** — keep |

**Duplicate signal:** 3-step scale (`rounded` / `rounded-lg` / `rounded-xl`) carries 1577 uses (72%). `rounded-md` and `rounded-2xl` add two extra steps for 426 uses — likely historical, not intentional hierarchy.

**Canon candidate:** `radius-sm` (4px), `radius-md` (8px), `radius-lg` (12px) + `full` + `none`.

---

## 5) Shadow Inventory

| Token | Uses | Verdict | Canon Map |
|---|---:|---|---|
| `shadow-sm` | 335 | **Canon** | `shadow-1` (card) |
| `shadow` | 70 | **Duplicate** of sm | merge → `shadow-1` |
| `shadow-md` | 24 | **Canon** | `shadow-2` (panel/dropdown) |
| `shadow-lg` | 35 | **Duplicate** of md | merge → `shadow-2` |
| `shadow-xl` | 34 | **Canon** | `shadow-3` (modal/overlay) |
| `shadow-2xl` | 14 | **Duplicate** of xl | merge → `shadow-3` |
| `shadow-none` | 12 | **Reset** | keep |
| `shadow-inner` | 4 | **Legacy** | deprecate |

**Duplicate signal:** shadow usage forms 3 natural pairs (default/sm, md/lg, xl/2xl). Canon needs 3 elevation levels, not 6.

**Canon candidate:** `shadow-1`, `shadow-2`, `shadow-3`, `shadow-none`.

---

## 6) Duplicate / Overlap Priority Matrix

| Rank | Family | Duplicate Type | Impact | Action in Benchmark |
|---|---|---|---|---|
| 1 | Colors | cross-family semantic duplication | visual inconsistency in status/neutral | pick one family per semantic, deprecate rest |
| 2 | Spacing | half-step values (1.5, 2.5, 3.5, 5, 7) | micro misalignment across components | merge to nearest canon step |
| 3 | Typography | display tier split (2xl/3xl/4xl/6xl) | heading hierarchy drift | collapse to optional single Display |
| 4 | Shadows | paired duplicates (shadow/shadow-sm, etc.) | elevation inconsistency | collapse pairs |
| 5 | Radius | md and 2xl as extra steps | subtle shape drift | collapse to 3-step scale |
| 6 | Line height | snug + numeric aliases | low impact | merge to tight/relaxed |

---

## 7) What Is Actually Unique (Foundation Core)

If duplicates are removed today, the operational UI already revolves around this core:

```
Typography:  text-xs, text-sm, text-lg, font-medium, font-semibold
Spacing:     0, 0.5, 1, 2, 3, 4, 6, 8
Colors:      slate-{50..900}, white, brand-{50,200,500,600,700,800},
             amber-* (warning), rose-* (danger), emerald-* (success), blue-* (info)
Radius:      rounded, rounded-lg, rounded-xl, rounded-full
Shadow:      shadow-sm, shadow-md, shadow-xl
```

Everything outside this core is either a merge candidate or an outlier. That is the factual basis for `FOUNDATION_V1`.

---

## Output to Next Step

This inventory answers:

- which token groups are oversized (colors, spacing forms),
- which tokens duplicate each other (with usage evidence),
- what target ranges should guide canon.

Next artifact:

**`FOUNDATION_BENCHMARK.md`** — per-token classification: `Candidate` / `Legacy` / `Deprecated`, with migration notes per family.
