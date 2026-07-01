# STATUS_BADGE_V1_DRAFT

Status: **Superseded** by `STATUS_BADGE_V1.md` (locked 2026-05-29)  
Date: 2026-05-29  
Layer: 3 (Composite) — derived from Layer 2 Badge primitive  
Input: `PRIMITIVES_BENCHMARK.md`, `FOUNDATION_V1.md`  
Purpose: define the official **semantic-first** status badge for HostFlow.

## Question Answered

> Как отображать статус в UI через один семантический контракт, а не через палитру?

---

## Governance

| Rule | Detail |
|---|---|
| Authority | `REF-UI-*`; product tasks do not change canon |
| New code | Must use `StatusBadge` semantic API |
| Color in JSX | **Forbidden** — semantics only |
| Palette mapping | Single config layer (`statusBadgeSemantics.ts` or Tailwind semantic aliases) |
| Legacy | `StageTag`, `DocumentStatus`, inline pills — migrate on touch |
| `NextActionBadge` | Stays separate (action CTA, not status label) — uses same semantic tokens |

---

## 1) Core Model — Semantic First

### Allowed semantics

| Semantic | Meaning | Foundation |
|---|---|---|
| `success` | Complete, positive, employed, open | `color-success` |
| `warning` | Attention, pending, paused, at-risk | `color-warning` |
| `danger` | Rejected, blocked, error, returned | `color-danger` |
| `info` | In progress, waiting, informational | `color-info` |
| `neutral` | Default, unknown, closed, idle | `color-neutral` |
| `brand` | Active pipeline, contacted, engaged | `color-brand` |

**Forbidden as public API:** `variant="green"`, `className="bg-red-100"`, per-stage hex/Tailwind palette props.

### Sizes (from audit)

| Size | Use | Tailwind scale |
|---|---|---|
| `sm` | Table cells, compact inline | `text-[10px] px-1.5 py-0` |
| `md` | Default labels | `text-xs px-2 py-0.5` |

---

## 2) Component Contract (Draft)

```tsx
type StatusBadgeSemantic =
  | 'success'
  | 'warning'
  | 'danger'
  | 'info'
  | 'neutral'
  | 'brand'

type StatusBadgeProps = {
  label: string
  semantic: StatusBadgeSemantic
  size?: 'sm' | 'md'
  title?: string
}
```

Visual styling resolves internally:

```
semantic → FOUNDATION_V1 color tokens → Tailwind classes (one map)
```

No consumer passes `bg-*` / `text-*` for status meaning.

---

## 3) Stage → Semantic Map (Candidate + Vacancy)

Replaces `StageTag` `COLORS` map (30 palette entries → 6 semantics).

### Candidate pipeline stages

| Stage code | Label source | Semantic | Rationale |
|---|---|---|---|
| `new` | i18n | `neutral` | Entry/default |
| `no_answer` | i18n | `warning` | Needs follow-up |
| `contacted` | i18n | `brand` | Active outreach |
| `interview` | i18n | `brand` | Active pipeline |
| `questionnaire_submitted` | i18n | `brand` | Engaged |
| `docs_wait` | i18n | `info` | Waiting on docs |
| `docs_got` | i18n | `success` | Milestone reached |
| `permit_ordered` | i18n | `warning` | Pending external |
| `permit_received` | i18n | `success` | Milestone reached |
| `visa` | i18n | `info` | In progress |
| `red_paper` | i18n | `danger` | Blocked / problem |
| `trip_plan` | i18n | `info` | Planning phase |
| `at_client` | i18n | `neutral` | Stable state |
| `employment_pending` | i18n | `info` | Awaiting decision |
| `on_trip` | i18n | `success` | Active positive |
| `hiring` | i18n | `warning` | Decision pending |
| `employed` | i18n | `success` | Terminal positive |
| `probation` | i18n | `info` | Monitoring |
| `probation_ok` | i18n | `success` | Cleared |
| `rejected` | i18n | `danger` | Terminal negative |
| `declined` | i18n | `danger` | Terminal negative |
| `ready_for_handoff` | i18n | `info` | Handoff queue |
| `processing_by_client` | i18n | `info` | External processing |
| `docs_submitted_permit` | i18n | `warning` | Awaiting review |
| `handoff_returned` | i18n | `danger` | Returned / rework |

### Vacancy stages

| Stage code | Semantic | Rationale |
|---|---|---|
| `open` | `success` | Active recruiting |
| `paused` | `warning` | Temporarily inactive |
| `closed` | `neutral` | Closed |

**Fallback:** unknown stage code → `neutral`.

### `StageTag` migration

| Today | V1 |
|---|---|
| `StageTag` + `COLORS` map | `StageTag` wraps `StatusBadge` + `stageSemanticMap[code]` |
| 30 Tailwind palette strings | **0** in component code |

---

## 4) Other Badge Adapters

### DocumentStatus → StatusBadge

| `severity` (current) | Semantic |
|---|---|
| `ok` | `success` |
| `warn` | `warning` |
| `bad` | `danger` |
| default / `info` | `info` |

`DocumentStatus` becomes thin wrapper or alias — not a second badge system.

### NextActionBadge — separate role, shared tokens

`NextActionBadge` is an **action CTA badge**, not a status label. It stays a distinct component but must use the same semantic palette map:

| Priority | Semantic | Notes |
|---|---|---|
| `critical` | `danger` | Replace `rose-500` / `rose-100` with semantic map |
| `high` | `warning` | Replace `amber-*`, `sky-*` → use warning |
| `normal` | `info` | Replace `sky-*` |
| `idle` | `neutral` | Replace slate/white variants |

Loading/error meta-states: `neutral` / `danger` respectively.

### Static `.badge` CSS

| Use | Semantic default |
|---|---|
| Generic label chip | `neutral` |
| Filter context | see `CHIP_V1` (dismissible chip, not status badge) |

---

## 5) Allowed vs Legacy vs Deprecated

### Allowed (new code)

- `StatusBadge` with `semantic` prop
- `StageTag` after semantic refactor (adapter only)
- `NextActionBadge` after semantic token migration

### Legacy (existing, migrate on touch)

- `DocumentStatus` direct severity classes
- Inline status pills (`rounded-md px-2`, `rounded-full border px-2`)
- Raw `.badge` without semantic wrapper

### Deprecated (forbidden in new code)

- Per-stage color maps (`COLORS` in `StageTag`)
- Palette props on badge components
- Deprecated Foundation families in badges (`green`, `red`, `indigo`, etc.)

---

## 6) Visual Token Map (single source)

Draft mapping — implementation lives in one file:

| Semantic | Background | Text | Border |
|---|---|---|---|
| `success` | `emerald-50` | `emerald-800` | `emerald-200` |
| `warning` | `amber-50` | `amber-800` | `amber-200` |
| `danger` | `rose-50` | `rose-800` | `rose-200` |
| `info` | `blue-50` | `blue-800` | `blue-200` |
| `neutral` | `slate-100` | `slate-800` | `slate-200` |
| `brand` | `brand-50` | `brand-800` | `brand-200` |

Inverse theme (dark headers): separate `inverse` map keyed by same semantics — used by `NextActionBadge`.

---

## 7) Implementation Status

| Item | Status |
|---|---|
| Spec defined | ✅ |
| `StatusBadge` + semantics | ✅ Implemented |
| `StageTag` refactor | ✅ |
| `DocumentStatus` adapter | ✅ |
| `NextActionBadge` token migration | ✅ |
| CI enforcement | ⬜ |

---

## 8) Chain Status

| Artifact | Status |
|---|---|
| `PRIMITIVES_BENCHMARK.md` | ✅ |
| `STATUS_BADGE_V1_DRAFT.md` | ✅ Draft |
| `STATUS_BADGE_V1` (lock) | ⬜ After implementation + governance |
| `CHIP_V1_DRAFT` | ✅ See companion doc |

---

## 9) Next Steps

1. Implement `StatusBadge` + `stageSemanticMap`.
2. Refactor `StageTag` as adapter (smallest high-impact migration).
3. Governance review → `STATUS_BADGE_V1` lock.
4. Add badge palette check to foundation/primitives enforcement (optional Phase 2).
