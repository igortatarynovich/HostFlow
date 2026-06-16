# BUTTON_BENCHMARK

Status: Complete  
Date: 2026-05-29  
Input: `PRIMITIVES_INVENTORY.md`, `FOUNDATION_V1.md`  
Scope: **Buttons only** — Input queued.  
Purpose: classify button implementations as **Candidate**, **Legacy**, or **Deprecated** for `BUTTON_V1`.

## Question Answered

> Нужен ли новый button system или достаточно задокументировать существующий CSS canon?

## Governing Rules

| Status | Meaning | New code | Existing code |
|---|---|---|---|
| **Candidate** | Default for new work | Required | Keep |
| **Legacy / Adapt** | Allowed; migrate on touch | Discouraged | Keep until refactored |
| **Deprecated** | Forbidden pattern | Forbidden | Migrate with backlog |

**Locked decisions (this benchmark):**

1. **CSS canon is real** — `.btn-primary`, `.btn-secondary`, `.btn-danger` are the visual source of truth (~75% of button files).
2. `BUTTON_V1` = **document + thin React wrapper** — not a redesign.
3. Edge roles (ghost, link, icon-only) get **named variants** — no new orphan classes.
4. Raw Tailwind action buttons in forms/toolbars → migrate to `.btn-*` or `Button` on touch.

---

## 1) Classification

| Implementation | Uses | Decision | Maps to `BUTTON_V1` |
|---|---:|---|---|
| `.btn-primary` | **269** | **Candidate** | `variant="primary"` |
| `.btn-secondary` | **731** | **Candidate** | `variant="secondary"` |
| `.btn-danger` | **57** | **Candidate** | `variant="danger"` |
| `.btn-sm` / `.btn-xs` | 370 / 224 | **Candidate** | `size="sm"` / `size="xs"` |
| Base `.btn` | combined | **Candidate** | shared layout (touch target, rounded-xl) |
| `.btn-icon` | **0** | **Legacy / Adapt** | `variant="icon"` — fix `gray-*` → `slate-*` first |
| `btn-ghost` (orphan) | **1** | **Deprecated** | `variant="ghost"` in V1 |
| Raw `<button>` without `.btn-*` | **57 files** | **Legacy / Adapt** | migrate on touch |
| Link-style (`text-brand-700 underline`) | **~55** | **Legacy / Adapt** | `variant="link"` |
| `EmptyStatePanel` internal variants | few | **Legacy / Adapt** | compose `Button` |
| `HrDocumentOpenButton` link/button | 1 component | **Legacy / Adapt** | domain wrapper |
| Icon-only ad-hoc (`p-2 hover:bg-slate-100`) | scattered | **Legacy / Adapt** | `variant="icon"` |

---

## 2) Variant Model (pre-V1)

### Semantic variants (locked set)

| Variant | CSS | Use |
|---|---|---|
| `primary` | `.btn-primary` | Main CTA, submit, confirm |
| `secondary` | `.btn-secondary` | Default actions, cancel-adjacent |
| `danger` | `.btn-danger` | Destructive confirm |
| `ghost` | new: borderless slate hover | Tertiary toolbar actions |
| `link` | text brand + underline on hover | Inline navigation actions |
| `icon` | `.btn-icon` (fixed tokens) | Icon-only controls |

**No seventh variant** without governance.

### Sizes (modifiers, not variants)

| Size | CSS | Note |
|---|---|---|
| `default` | base `.btn` | `min-h-[44px]` mobile touch |
| `sm` | `.btn-sm` | dense toolbars |
| `xs` | `.btn-xs` | table/card micro actions |

---

## 3) CSS Fixes Required Before Lock

| Issue | Location | Fix |
|---|---|---|
| `.btn-icon` uses `gray-*` | `components.css` | → `slate-*` per `FOUNDATION_V1` |
| `.btn-ghost` undefined | 1 orphan usage | define in CSS or remove orphan |
| Gradient primary | `.btn-primary` | **Candidate** — keep; document as canon |

---

## 4) Allowed vs Legacy vs Deprecated

### Allowed (new code)

- `.btn-*` classes directly **or** `<Button variant=… size=…>`
- `type="button"` explicit on non-submit buttons

### Legacy (migrate on touch)

- Raw `<button className="rounded-lg border…">` in app surfaces
- Link-style text buttons outside `variant="link"`
- Component-local variant string maps duplicating CSS

### Deprecated (new code)

- Orphan `btn-ghost` without CSS definition
- New deprecated color families in button styles (`gray-*`, `indigo-*`)
- One-off gradient buttons outside `.btn-primary`

---

## 5) Migration Priority

| Priority | Action | Effort |
|---|---|---|
| **P0** | `BUTTON_V1_DRAFT` + `Button.tsx` wrapper | Low |
| **P1** | Fix `.btn-icon` tokens | Trivial |
| **P2** | Define `.btn-ghost` in CSS | Trivial |
| **P2** | Migrate 57 unstyled button files (on touch) | Ongoing |
| **P3** | Consolidate `EmptyStatePanel` actions | Low |

**Low consolidation urgency** — opposite of Badge/Chip/Select.

---

## 6) Chain Status

| Artifact | Status |
|---|---|
| `PRIMITIVES_AUDIT.md` | ✅ |
| `PRIMITIVES_INVENTORY.md` | ✅ |
| **`BUTTON_BENCHMARK.md`** | ✅ This document |
| `BUTTON_V1_DRAFT.md` | ← Next |
| `BUTTON_V1` lock | ⬜ After wrapper + CSS fixes |

---

## 7) Next Steps

1. `BUTTON_V1_DRAFT.md` — React API over CSS canon.
2. Implement `components/ui/Button.tsx`.
3. CSS: fix `.btn-icon`, add `.btn-ghost`.
4. Governance → `BUTTON_V1` lock.
