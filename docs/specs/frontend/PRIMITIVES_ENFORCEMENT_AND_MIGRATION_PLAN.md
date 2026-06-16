# PRIMITIVES_ENFORCEMENT_AND_MIGRATION_PLAN

Status: Complete (Layer 2 — Badge, Chip, Select, Button, Input)  
Date: 2026-05-29  
Updated: 2026-05-31 (Input lock — Layer 2 closed)  
Input: `STATUS_BADGE_V1.md`, `CHIP_V1.md`, `SELECT_V1.md`, `BUTTON_V1.md`, `INPUT_V1.md`, `FOUNDATION_ENFORCEMENT_AND_MIGRATION_PLAN.md`  
Purpose: define how all Layer 2 locked primitives become real.

## Question Answered

> Как locked primitives (Badge, Chip, Select, Button, Input) станут реальным стандартом, а не только документом?

---

## 1) Scope (This Plan)

| Family | Artifact | Enforcement |
|---|---|---|
| Status badges | `STATUS_BADGE_V1.md` | PR review + migrate on touch |
| Chips | `CHIP_V1.md` | PR review + migrate on touch |
| Selects | `SELECT_V1.md` | PR review + migrate on touch |
| Buttons | `BUTTON_V1.md` | PR review + migrate on touch |
| Input | `INPUT_V1.md` | PR review + migrate on touch (CSS-first) |

Full primitive CI grep checks are **Phase 2** (after remaining P0 migrations and backlog scan).

---

## 2) Current State (Baseline)

Scan date: 2026-05-29. Scope: `hostflow-frontend/src`.

### StatusBadge — migrated adapters

| Component | Status |
|---|---|
| `StatusBadge` + `statusBadgeSemantics.ts` | ✅ Canonical |
| `StageTag` → `StatusBadge` adapter | ✅ |
| `DocumentStatus` → `StatusBadge` adapter | ✅ |
| `NextActionBadge` → semantic inverse map | ✅ |

### Chip — migrated surfaces

| Surface | Status |
|---|---|
| `Chip` component (4 behaviors) | ✅ Canonical |
| `FilterBadges` → `Chip dismissible` | ✅ |
| `CandidatesQuickViewsBar` → `Chip selectable` | ✅ |

### Chip — remaining legacy (migrate on touch)

| Pattern | Location | Priority |
|---|---|---|
| `MultiSelectChips` (PublicApply) | public intake | P2 |
| Ad-hoc chip toggle rows | on touch | P3 |

### Select — canonical

| Component | Status |
|---|---|
| `Combobox` + `MultiCombobox` | ✅ Canonical |
| `controls/Select` / `SearchableSelect` / `CheckboxMultiSelect` | Legacy adapters |

### Select — remaining legacy (migrate on touch)

| Pattern | Location | Priority |
|---|---|---|
| Deprecated alias imports | `FormComponents` consumers | P2 |
| Dead `SelectAsync` / `MultiSelect` | `components/controls/` | P3 delete |
| Native selects without `.input` | various | P3 on touch |

### Button — canonical

| Component | Status |
|---|---|
| `Button.tsx` + `.btn-*` CSS | ✅ Canonical |
| `.btn-ghost`, `.btn-icon` (slate tokens) | ✅ |

### Button — remaining legacy (migrate on touch)

| Pattern | Location | Priority |
|---|---|---|
| Raw Tailwind `<button>` | ~57 files | on touch |
| `EmptyStatePanel` local classes | `EmptyStatePanel.tsx` | P3 |

### Input — canonical (CSS-only)

| Artifact | Status |
|---|---|
| `.input` / `.textarea` / `.label` in `components.css` | ✅ Canonical |
| `Input.tsx` wrapper | ❌ Not planned (Wrapper Justification) |

### Input — remaining legacy (migrate on touch)

| Pattern | Location | Priority |
|---|---|---|
| `FormComponents.Input` (label+hint row) | candidate forms | P2 |
| Raw `<input>` without `.input` | various | on touch |
| `.input-sm` | documents/dashboard | P3 |
| `DocumentFieldInput`, `PhoneInput` | domain composites | on touch |
| `Field.tsx` | dead file | P3 delete |

### Badge — remaining legacy (migrate on touch)

| Pattern | Location | Priority |
|---|---|---|
| Inline status pills (raw Tailwind) | tables, public pages, HR surfaces | P1 |
| Raw `.badge` CSS for status meaning | various | P1 |

**Rule:** legacy may remain in untouched files. Any edit must not add new deprecated patterns.

---

## 3) Enforcement Plan

### 3.1 Status Rules

Same model as Foundation (see `FOUNDATION_ENFORCEMENT_AND_MIGRATION_PLAN.md` §3.1):

| Status | Existing code | New code | New usages in edited files |
|---|---|---|---|
| **Allowed** | Keep | Required | Required |
| **Legacy** | Keep | **Forbidden** | **Forbidden** |
| **Deprecated** | Keep until migrated | **Forbidden** | **Forbidden** |

### 3.2 Mechanisms at Lock

| Mechanism | What it blocks | When | Status |
|---|---|---|---|
| **PR review checklist** | Primitive anti-patterns in new code | At lock | ✅ PR template |
| **Code review convention** | Palette props, per-stage color maps | At lock | ✅ |
| **Migrate on touch** | Legacy in files being edited | Ongoing | ✅ |
| **CI grep (primitives)** | Deprecated badge/chip patterns in diff | Phase 2 | ⬜ Deferred |
| **Full scan (non-blocking)** | Backlog report | Phase 2 | ⬜ Deferred |

Foundation CI (`npm run foundation:check`) already blocks deprecated **color families** in diffs — this covers many badge palette violations indirectly.

### 3.3 Forbidden in New Code (from lock)

**Status badges:**

- Per-stage Tailwind color maps (`COLORS`, inline `bg-emerald-100` for stage meaning)
- `variant="green"` / palette props on badge components
- Raw `.badge` for **status meaning** (stage, severity, document status)
- Chip used for read-only status labels

**Chips:**

- New local chip implementations (`rounded-md px-2` toggle rows without `Chip`)
- Fifth behavior variant without governance
- Chip for status meaning (use `StatusBadge`)

**Selects:**

- New combobox copy-paste
- `SelectAsync` / `MultiSelect` in new code
- `Combobox` for ≤10 static options
- Hardcoded locale in `Combobox` / `MultiCombobox`

**Buttons:**

- New button color systems outside `.btn-*` canon
- Deprecated Foundation families in button styles
- `variant="icon"` without `aria-label` (no visible text)

**Inputs:**

- Custom one-off input Tailwind field chrome
- Pass-through `Input.tsx` without governance trigger
- Separate visual per input type (date vs text vs search)
- Masked-input libraries without REF-UI decision

### 3.4 Allowed in New Code

- `StatusBadge` with `semantic` prop (+ `size`, `shape`, `inverse`)
- Adapters: `StageTag`, `DocumentStatus`, `NextActionBadge` (shared semantic map)
- `Chip` with `behavior` ∈ `{ static, dismissible, selectable, action }`
- Composition containers (`FilterBadges`, quick-view rows) wrapping canonical chips
- `Combobox` / `MultiCombobox` / native `<select className="input">` per `SELECT_V1` scenario tree
- `Button` or `.btn-*` with allowed variants
- Native `<input className="input">` / `<textarea className="textarea">` per `INPUT_V1`
- `.label` for field title typography only

---

## 4) Migration Phases

| Phase | Target | Status |
|---|---|---|
| **P0** | Badge + Chip core + candidates migrations | ✅ |
| **P0** | Select (`Combobox` / `MultiCombobox`) + Button lock | ✅ |
| **P0** | Input lock (CSS-only, no wrapper) | ✅ |
| **P1** | Inline status pills; deprecated select alias cleanup | Ongoing |
| **P2** | `MultiSelectChips`, dead select file deletion | Queued |
| **P3** | Raw button migration on touch | Ongoing |
| **Phase 2 CI** | Diff grep for primitive anti-patterns | Deferred |

---

## 5) Success Metrics

| Metric | Baseline | Target | Done when |
|---|---|---|---|
| Canonical badge API in new code | partial | **100%** | No new inline status pills |
| Canonical chip API in new code | partial | **100%** | No new ad-hoc chip markup |
| Canonical select API in new code | partial | **100%** | Per `SELECT_V1` scenario tree |
| Canonical button API in new code | partial | **100%** | `Button` or `.btn-*` |
| Canonical input API in new code | partial | **100%** | `.input` / `.textarea` on native elements |
| P0 migrations complete | — | ✅ | All 5 Layer 2 families |
| `NbaNextActionsChips` migrated | — | ✅ | Uses `Chip action` |
| Primitive CI check | ⬜ | Active | Optional Phase 2 |

---

## 6) Governance Sequence

| Step | Artifact / Action | Status |
|---|---|---|
| 1 | `PRIMITIVES_AUDIT.md` | ✅ |
| 2 | `PRIMITIVES_INVENTORY.md` | ✅ |
| 3 | `PRIMITIVES_BENCHMARK.md` | ✅ |
| 4 | `STATUS_BADGE_V1_DRAFT` / `CHIP_V1_DRAFT` | ✅ |
| 5 | `PRIMITIVES_V1_DRAFT` (partial) | ✅ |
| 6 | **This document** | ✅ |
| 7 | Governance approval | ✅ 2026-05-29 |
| 8 | `STATUS_BADGE_V1` lock | ✅ |
| 9 | `CHIP_V1` lock | ✅ |
| 10 | `PRIMITIVES_V1` partial lock (Badge + Chip) | ✅ |
| 11 | `NbaNextActionsChips` migration | ✅ |
| 12 | `SELECT_V1` / `BUTTON_V1` lock | ✅ 2026-05-31 |
| 13 | `INPUT_V1` benchmark | ✅ |
| 14 | `INPUT_V1_DRAFT` + Wrapper Justification (no component) | ✅ |
| 15 | Input enforcement + `INPUT_V1` lock | ✅ 2026-05-31 |
| 16 | **`PRIMITIVES_V1` Layer 2 closed** | ✅ |
| 17 | Layer 3 composites | ← Next (roadmap) |

---

## 7) Lock Readiness Checklist

| Check | Status | Detail |
|---|---|---|
| Core components / canon | ✅ | Badge, Chip, Select, Button components; Input CSS |
| P0 migrations complete | ✅ | All Layer 2 families locked |
| Input wrapper | ✅ | None by design |
| Enforcement model documented | ✅ | PR review + migrate on touch |
| Foundation CI covers color drift | ✅ | `foundation:check` active |
| Primitive CI | ⬜ | Phase 2 — not a lock blocker |

**Lock status:** Layer 2 primitives (Badge, Chip, Select, Button, Input) are locked and enforceable via review. Legacy backlog does not block features. Layer 3+ follows `REF-UI-000` roadmap.
