# FOUNDATION_BENCHMARK

Status: Complete  
Date: 2026-05-29  
Input: `FOUNDATION_TOKEN_INVENTORY.md`  
Purpose: classify every foundation token family as **Candidate**, **Legacy**, or **Deprecated** — the decision layer before `FOUNDATION_V1_DRAFT`.

## Question Answered

> Что мы сохраняем, что переводим в Legacy, что запрещаем?

## Governing Principle

**Канон обнаруживается, а не придумывается.**

Classification rules:

| Status | Meaning | New code | Existing code |
|---|---|---|---|
| **Candidate** | Discovered standard; default for new work | Required | Keep |
| **Legacy** | Allowed but not default; migrate on touch | Discouraged | Keep until refactored |
| **Deprecated** | Duplicate, outlier, or semantic conflict | Forbidden | Migrate with backlog |

---

## Classification Summary

| Family | Candidate | Legacy | Deprecated | Migration Priority |
|---|---:|---:|---:|---|
| Font Size (body) | 2 | 0 | 0 | Low |
| Font Size (heading) | 3 | 2 | 2 | Low |
| Font Weight | 2 | 2 | 0 | Low |
| Line Height | 2 | 1 | 4 | Low |
| Spacing | 8 | 2 | 10 | Medium |
| Colors (families) | 6 | 1 | 15 | **High** |
| Radius | 3 | 2 | 2 | Low |
| Shadow | 3 | 1 | 4 | Low |

---

## 1) Typography

### Principle

91% of operational UI runs on `text-xs` + `text-sm` (4870 of 5345 uses). Body typography is discovered in code. Heading typography is a separate required layer — headings are not Legacy, they are part of the system.

### Body Typography

| Token | Uses | Status | Rationale |
|---|---:|---|---|
| `text-xs` | 2363 | **Candidate** | Primary meta/body size |
| `text-sm` | 2506 | **Candidate** | Primary UI size |

### Heading Typography

| Token | Uses | Status | Rationale |
|---|---:|---|---|
| `text-lg` | 135 | **Candidate** | Section headings |
| `text-xl` | 91 | **Candidate** | Page subheadings |
| `text-2xl` | 106 | **Candidate** | Primary display / entity titles |
| `text-3xl` | 40 | **Legacy** | Oversized display; migrate to `text-2xl` on touch |
| `text-base` | 98 | **Legacy** | Prose default; long-form content only |
| `text-4xl` | 4 | **Deprecated** | Outlier; marketing-only if ever needed |
| `text-6xl` | 2 | **Deprecated** | Outlier; marketing-only if ever needed |

**Canon for new work:** body = `text-xs`, `text-sm`; headings = `text-lg`, `text-xl`, `text-2xl`.

### Font Weight

| Token | Uses | Status | Rationale |
|---|---:|---|---|
| `font-semibold` | 1504 | **Candidate** | Primary emphasis |
| `font-medium` | 1312 | **Candidate** | Secondary emphasis |
| `font-bold` | 80 | **Legacy** | Near-duplicate of semibold; migrate on touch |
| `font-normal` | 11 | **Legacy** | Reset weight |

### Line Height

| Token | Uses | Status | Migration |
|---|---:|---|---|
| `leading-tight` | 27 | **Candidate** | — |
| `leading-relaxed` | 51 | **Candidate** | — |
| `leading-snug` | 37 | **Deprecated** | → `leading-tight` |
| `leading-none` | 9 | **Legacy** | Heading reset only |
| `leading-4/5/6` | 4 | **Deprecated** | → `leading-tight` or `leading-relaxed` |

### Font Family

| Token | Uses | Status |
|---|---:|---|
| `font-sans` | 1 | **Candidate** (implicit default) |
| `font-mono` | 134 | **Legacy** | Code/IDs only |

---

## 2) Spacing

### Principle

87.5% of spacing usage already sits on a natural 10-value core. Benchmark ratifies an 8-value operational scale and pushes edge values to Legacy or Deprecated.

### Classification

| Value | Uses | Status | Migration Target | Cost |
|---:|---:|---|---|---|
| `0` | 99 | **Candidate** | — | — |
| `0.5` | 438 | **Candidate** | — | — |
| `1` | 1729 | **Candidate** | — | — |
| `2` | 3543 | **Candidate** | — | — |
| `3` | 2409 | **Candidate** | — | — |
| `4` | 1533 | **Candidate** | — | — |
| `6` | 382 | **Candidate** | — | — |
| `8` | 119 | **Candidate** | — | — |
| `10` | 26 | **Legacy** | prefer `8` in operational UI | Low |
| `12` | 10 | **Legacy** | prefer `8` in operational UI | Low |
| `1.5` | 472 | **Deprecated** | → `2` | **High** |
| `2.5` | 189 | **Deprecated** | → `2` or `3` | Medium |
| `3.5` | 16 | **Deprecated** | → `3` or `4` | Low |
| `5` | 126 | **Deprecated** | → `4` or `6` | Medium |
| `7` | 6 | **Deprecated** | → `6` or `8` | Low |
| `16` | 2 | **Deprecated** | → `12` or layout refactor | Low |
| `20` | 1 | **Deprecated** | → nearest canon | Low |
| `24` | 20 | **Deprecated** | → `12` or component refactor | Low |
| `32` | 1 | **Deprecated** | → nearest canon | Low |
| `96` | 1 | **Deprecated** | remove (`mr-96`) | Low |
| `px` | 4 | **Deprecated** | → `0.5` or `1` | Low |

**Operational canon:** `0, 0.5, 1, 2, 3, 4, 6, 8`.

### Spacing 10/12 Verification (tables + cards)

Checked before canonization:

| Context | `10` uses | `12` uses | Verdict |
|---|---:|---:|---|
| Table files (11) | 0 | 0 | Not systematic |
| Card files (17) | 0 | 1 (`mt-12`) | Not systematic |
| Entity detail (13) | 1 (`gap-10`) | 1 (`pb-12`) | Isolated |
| Auth / public / onboarding | 22 | 7 | Marketing & shell layouts |

`10` and `12` appear in auth pages, public landing, modals, and onboarding — not in operational tables or cards. **Status confirmed: Legacy**, not Candidate. Large-container spacing in operational UI should use `8`; `10`/`12` remain allowed in marketing/auth shells until migrated.

**Migration backlog estimate:** ~809 deprecated half-step uses. Highest item: `1.5` (472). Not blocking `FOUNDATION_V1_DRAFT` — deprecation is forward-looking.

---

## 3) Colors

### Principle

The problem is **semantic**, not quantitative. One meaning is expressed by multiple color families. Benchmark picks one family per semantic role and deprecates the rest.

### Neutral

| Family | Uses | Status | Rationale |
|---|---:|---|---|
| `slate` | 7441 | **Candidate** | De facto neutral system (97% of neutrals) |
| `white` | 1256 | **Candidate** | Surface inverse |
| `black` | 31 | **Legacy** | Rare; prefer `slate-900` |
| `gray` | 18 | **Deprecated** | → `slate` equivalent |
| `zinc`, `neutral`, `stone` | 0 | **Deprecated** | Unused |

**Neutral canon:** `slate-{50,100,200,300,400,500,600,700,800,900}`, `white`.

### Brand

| Family | Uses | Status | Rationale |
|---|---:|---|---|
| `brand` | 1261 | **Candidate** | Defined in `tailwind.config.cjs`, aligned to pipedesign |

**Brand canon:** `brand-{50,200,500,600,700,800}` (top-used shades). Full ramp stays available but new work should prefer the 6-shade subset.

### Status — Semantic Consolidation (Critical)

| Semantic Role | Candidate Family | Uses | Deprecated Families | Uses to Migrate |
|---|---|---:|---|---:|
| Success | `emerald` | 388 | `green`, `teal` | 123 |
| Warning | `amber` | 803 | `yellow`, `orange` | 24 |
| Danger | `rose` | 512 | `red` | 202 |
| Info | `blue` | 188 | `sky`, `indigo`, `violet`, `purple`, `cyan` | 288 |

**Status shade roles (per family):** only these shade numbers are Candidate:

| Role | Shades | Example |
|---|---|---|
| Subtle bg | `50`, `100` | `bg-emerald-50` |
| Border / light | `200` | `border-amber-200` |
| Mid accent | `500`, `600` | `bg-brand-600` |
| Text emphasis | `700`, `800` | `text-rose-700` |
| Dark text | `900` | `text-amber-900` |

Shades outside active use in a family (e.g. `emerald-300`, `rose-400`) are **Legacy** — allowed in existing code, not for new status UI.

### Color Storage Rule (for FOUNDATION_V1)

Colors must be stored as **semantics**, not palettes.

Forbidden as canon:

```
emerald-500, rose-500, amber-500
```

Required model:

```
success, danger, warning, info, neutral, brand
```

Palette mapping (`emerald`, `rose`, `amber`, `blue`, `slate`, `brand`) lives in one config layer — components reference semantics only.

### Semantic Token Model (for FOUNDATION_V1)

Benchmark pre-decides the semantic layer that `FOUNDATION_V1_DRAFT` will formalize:

```
text-primary      → slate-900
text-secondary    → slate-700
text-muted        → slate-500
text-inverse      → white

surface-primary   → white
surface-secondary → slate-50
surface-elevated  → white + shadow-1
surface-overlay   → slate-900/80

border-default    → slate-200
border-subtle     → slate-100
border-strong     → slate-300

brand-subtle      → brand-50
brand-default     → brand-600
brand-strong      → brand-700

status-success    → emerald
status-warning    → amber
status-danger     → rose
status-info       → blue
```

Each status semantic maps to 5 shade roles above — yields ~24 semantic tokens, replacing 154 ad-hoc base tokens.

### Color Migration Priority

| Priority | Action | Effort |
|---|---|---|
| P0 | Stop new usage of deprecated families | Policy only |
| P1 | Merge `red-*` → `rose-*` (202 uses) | Medium |
| P2 | Merge `green-*` + `teal-*` → `emerald-*` (123 uses) | Low |
| P3 | Merge info families → `blue-*` (288 uses) | Medium |
| P4 | Merge `gray-*` → `slate-*` (18 uses) | Trivial |

---

## 4) Radius

### Principle

Data confirms a 3-step scale. Close quickly — low migration cost, low visual risk.

| Token | Uses | px | Status | Canon Name |
|---|---:|---:|---|---|
| `rounded` | 582 | 4px | **Candidate** | `radius-sm` |
| `rounded-lg` | 844 | 8px | **Candidate** | `radius-md` |
| `rounded-xl` | 351 | 12px | **Candidate** | `radius-lg` |
| `rounded-full` | 209 | 50% | **Legacy** | Shape only (avatars, pills, badges) |
| `rounded-none` | 13 | 0 | **Legacy** | Reset |
| `rounded-md` | 265 | 6px | **Deprecated** | → `rounded` or `rounded-lg` |
| `rounded-2xl` | 161 | 16px | **Deprecated** | → `rounded-xl` |

**Migration backlog:** 426 uses (`rounded-md` + `rounded-2xl`). Merge rule: `rounded-md` → nearer neighbor by context; `rounded-2xl` → `rounded-xl`.

---

## 5) Shadow

### Principle

Three elevation levels already dominate. Pairs are duplicates, not design intent.

| Token | Uses | Status | Canon Name | Migration |
|---|---:|---|---|---|
| `shadow-sm` | 335 | **Candidate** | `shadow-1` (card) | — |
| `shadow-md` | 24 | **Candidate** | `shadow-2` (panel/dropdown) | — |
| `shadow-xl` | 34 | **Candidate** | `shadow-3` (modal/overlay) | — |
| `shadow-none` | 12 | **Legacy** | Reset | — |
| `shadow` | 70 | **Deprecated** | → `shadow-sm` | Low |
| `shadow-lg` | 35 | **Deprecated** | → `shadow-md` | Low |
| `shadow-2xl` | 14 | **Deprecated** | → `shadow-xl` | Low |
| `shadow-inner` | 4 | **Deprecated** | Remove or special-case | Trivial |

**Migration backlog:** 123 uses across 4 deprecated tokens. Low priority.

---

## 6) Supporting Signals (Pre-classified)

### Z-index

| Token | Uses | Status |
|---|---:|---|
| `z-20`, `z-50` | 51 | **Candidate** (operational layers) |
| `z-10`, `z-30`, `z-40` | 10 | **Legacy** |
| Custom values | — | **Deprecated** |

### Breakpoints

| Prefix | Uses | Status |
|---|---:|---|
| `sm:` | 479 | **Candidate** |
| `md:` | 203 | **Candidate** |
| `lg:` | 176 | **Candidate** |
| `xl:` | 54 | **Legacy** |
| `2xl:` | 2 | **Deprecated** |

---

## 7) Decision Log

| # | Decision | Evidence | Reversible? |
|---|---|---|---|
| D1 | Body typography = `text-xs` + `text-sm` | 91% usage | No — observed fact |
| D1b | Heading typography = `text-lg` / `text-xl` / `text-2xl` | Required system layer | No |
| D2 | Spacing canon = 8 values (`0`–`8`) | 87.5% on core; `10`/`12` not systematic in tables/cards | Yes — low cost |
| D8 | Colors stored as semantics, not palettes | Prevents re-duplication | No |
| D3 | Neutral = `slate` only | 97% neutral share | No |
| D4 | Status = one family per semantic | Cross-family duplication | No — core architecture |
| D5 | Radius = 3 steps | 72% on `rounded`/`lg`/`xl` | Yes — 426 migrations |
| D6 | Shadow = 3 elevations | Natural pairs in data | Yes — 123 migrations |
| D7 | `FOUNDATION_V1` not before this doc | Governance chain | — |

---

## 8) What This Benchmark Does NOT Do

- Does not execute migrations — creates the classification for them.
- Does not redefine brand colors — ratifies existing `brand` ramp.
- Does not block product work — Legacy tokens remain valid until touched.

---

## Output to Next Step

This benchmark answers:

- what is **Candidate** (default for new code),
- what is **Legacy** (allowed, migrate on touch),
- what is **Deprecated** (forbidden in new code),
- where migration cost is high vs trivial.

Next artifact:

**`FOUNDATION_V1.md`** — locked canonical allow-list.

Chain status:

| Artifact | Status |
|---|---|
| `FOUNDATION_AUDIT.md` | ✅ Complete |
| `FOUNDATION_TOKEN_INVENTORY.md` | ✅ Complete |
| `FOUNDATION_BENCHMARK.md` | ✅ Complete |
| `FOUNDATION_V1.md` | ✅ Locked |
| `PRIMITIVES_V1_DRAFT` | ← Next (Layer 2) |
