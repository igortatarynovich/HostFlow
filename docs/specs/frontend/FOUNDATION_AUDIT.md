# FOUNDATION_AUDIT

Status: Complete  
Date: 2026-05-29  
Scope: `hostflow-frontend/src`  
Purpose: answer unknown question "what foundation tokens are actually used in code now?"

## Method

Static code scan of Tailwind utility usage in frontend source files.
Audit covers:

- typography tokens,
- spacing tokens,
- color tokens,
- radius tokens,
- shadow tokens,
- supporting foundation signals (z-index, breakpoints).

## 1) Typography Audit

### Font family tokens (used)

- `font-mono` (134)
- `font-sans` (1)

### Font size tokens (used, unique = 9)

- `text-xs` (2363)
- `text-sm` (2506)
- `text-base` (98)
- `text-lg` (135)
- `text-xl` (91)
- `text-2xl` (106)
- `text-3xl` (40)
- `text-4xl` (4)
- `text-6xl` (2)

### Font weight tokens (used, unique = 4)

- `font-medium` (1312)
- `font-semibold` (1504)
- `font-bold` (80)
- `font-normal` (11)

### Line-height tokens (used, unique = 7)

- `leading-relaxed` (51)
- `leading-snug` (37)
- `leading-tight` (27)
- `leading-none` (9)
- `leading-6` (2)
- `leading-5` (1)
- `leading-4` (1)

## 2) Spacing Audit

### Spacing utilities scanned

- `p-*`, `px-*`, `py-*`, `pt/pr/pb/pl-*`
- `m-*`, `mx-*`, `my-*`, `mt/mr/mb/ml-*`
- `gap-*`, `gap-x-*`, `gap-y-*`

### Unique numeric spacing values found (20)

`0, 0.5, 1, 1.5, 2, 2.5, 3, 3.5, 4, 5, 6, 7, 8, 10, 12, 16, 20, 24, 32, 96`

### High-frequency spacing tokens (top)

- `gap-2` (1068)
- `py-2` (950)
- `px-3` (820)
- `mt-1` (717)
- `px-2` (602)
- `px-4` (495)
- `mt-2` (493)
- `p-4` (432)

### Notes

- spacing variance is high (`154` unique spacing utility forms),
- outlier present: `mr-96` (single use),
- non-numeric spacing variants present: `mb-px`, `mx-px`, `gap-px`.

## 3) Color Audit

### Tailwind/palette color tokens (unique base tokens = 152)

Most used:

- `slate-500` (1541)
- `slate-200` (1245)
- `white` (1222)
- `slate-600` (1083)
- `slate-900` (967)
- `slate-700` (745)
- `slate-50` (529)
- `slate-100` (448)

### Brand semantic palette usage

`brand-*` is heavily used:

- `text-brand-700` (291)
- `text-brand-600` (103)
- `bg-brand-50` (94)
- `bg-brand-600` (86)
- plus `border-brand-*` and `ring-brand-*` variants.

### Status-family colors observed

- success-like: `emerald-*`, `green-*`
- warning-like: `amber-*`, `yellow-*`, `orange-*`
- danger-like: `red-*`, `rose-*`
- info-like: `blue-*`, `sky-*`, `indigo-*`, `cyan-*`, `teal-*`, `violet-*`, `purple-*`

### Notes

- color surface is broad (high variance),
- alpha variants are common (`/10`, `/20`, `/80`, etc.),
- mixed families are used for similar semantic intent.

## 4) Radius Audit

Used radius tokens (unique = 7):

- `rounded` (582)
- `rounded-md` (265)
- `rounded-lg` (844)
- `rounded-xl` (351)
- `rounded-2xl` (161)
- `rounded-full` (209)
- `rounded-none` (13)

## 5) Shadow Audit

Used shadow tokens (unique = 8):

- `shadow-sm` (335)
- `shadow` (92)
- `shadow-md` (24)
- `shadow-lg` (35)
- `shadow-xl` (34)
- `shadow-2xl` (14)
- `shadow-inner` (4)
- `shadow-none` (12)

## 6) Supporting Foundation Signals

### Z-index tokens (used)

- `z-10` (4)
- `z-20` (25)
- `z-30` (3)
- `z-40` (3)
- `z-50` (26)

### Breakpoint prefixes (used)

- `sm:` (479)
- `md:` (203)
- `lg:` (176)
- `xl:` (54)
- `2xl:` (2)

## Findings Summary

1. Foundation usage is not minimal yet (especially spacing and color variance).
2. Typography is relatively constrained in weight/size but still includes large-display outliers (`text-6xl`).
3. Spacing has many one-off/outlier values; canonical reduction is needed.
4. Color system is wide and mixed across many families; semantic consolidation is required.
5. Radius and shadow sets are closer to canonical candidates but still broader than target.

## Output for Next Step

This audit answers "what exists now."
Next step in roadmap remains:

1. Token Inventory (group by token family + usage count + module coverage),
2. Foundation Benchmark (candidate/legacy/deprecated per token),
3. only then `FOUNDATION_V1_DRAFT`.
