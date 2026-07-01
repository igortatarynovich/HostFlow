# STATUS_BADGE_V1

Status: **Locked**  
Draft date: 2026-05-29  
Locked date: 2026-05-29  
Governance: Approved (REF-UI-000 Primitives chain — partial)  
Input: `PRIMITIVES_BENCHMARK.md`, `FOUNDATION_V1.md`, `PRIMITIVES_ENFORCEMENT_AND_MIGRATION_PLAN.md`  
Supersedes: `STATUS_BADGE_V1_DRAFT.md`

## Question Answered

> Как отображать статус в UI через один семантический контракт, а не через палитру?

This is the canonical allow-list for HostFlow status badges. Enforced via PR review and migrate-on-touch; primitive CI deferred to Phase 2.

---

## Governance

| Rule | Detail |
|---|---|
| Authority | `REF-UI-*`; product tasks do not change canon |
| New code | Must use `StatusBadge` semantic API |
| Color in JSX | **Forbidden** — semantics only |
| Palette mapping | Single config layer: `components/ui/statusBadgeSemantics.ts` |
| Legacy | Inline pills, raw `.badge` — migrate on touch |
| `NextActionBadge` | Separate action CTA — uses same semantic token maps |

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

### Sizes

| Size | Use | Implementation |
|---|---|---|
| `sm` | Table cells, compact inline | `text-[10px] px-1.5 py-0` |
| `md` | Default labels | `text-xs px-2 py-0.5` |

### Shapes

| Shape | Use |
|---|---|
| `default` | `rounded-md` — stage tags, general status |
| `pill` | `rounded-full` — document status |

---

## 2) Component Contract

Implementation: `hostflow-frontend/src/components/ui/StatusBadge.tsx`

```tsx
type StatusBadgeSemantic =
  | 'success' | 'warning' | 'danger' | 'info' | 'neutral' | 'brand'

type StatusBadgeProps = {
  label: string
  semantic: StatusBadgeSemantic
  size?: 'sm' | 'md'
  title?: string
  inverse?: boolean
  shape?: 'default' | 'pill'
  className?: string
}
```

Visual styling resolves internally: `semantic → statusBadgeSemantics.ts → Tailwind classes`.

---

## 3) Semantic Maps (Single Source)

File: `hostflow-frontend/src/components/ui/statusBadgeSemantics.ts`

| Helper | Purpose |
|---|---|
| `STAGE_SEMANTIC_MAP` / `stageSemanticForCode()` | Candidate + vacancy stages |
| `documentSeverityToSemantic()` | Document severity |
| `nextActionPriorityToSemantic()` | NextActionBadge priority |
| `STATUS_BADGE_SEMANTIC_CLASSES` | Light surfaces |
| `STATUS_BADGE_SEMANTIC_CLASSES_INVERSE` | Dark headers |

Stage map: 28 candidate/vacancy codes → 6 semantics. Unknown code → `neutral`.

---

## 4) Adapters (Allowed)

| Adapter | Role | Status |
|---|---|---|
| `StageTag` | Stage label via `stageSemanticForCode` | ✅ |
| `DocumentStatus` | Severity via `documentSeverityToSemantic`, `shape="pill"` | ✅ |
| `NextActionBadge` | Action CTA via `nextActionPriorityToSemantic` + inverse map | ✅ |

---

## 5) Allowed vs Legacy vs Deprecated

### Allowed (new code)

- `StatusBadge` with `semantic` prop
- Adapters listed above
- Composition in tables, headers, cards

### Legacy (existing, migrate on touch)

- Inline status pills with raw Tailwind colors
- Raw `.badge` for status meaning
- `DocumentStatus` callers passing custom classes

### Deprecated (forbidden in new code)

- Per-stage color maps (`COLORS` pattern)
- Palette props on badge components
- Deprecated Foundation families in badges (`green`, `red`, `indigo`, etc.)
- Chip used for read-only status labels

---

## 6) Visual Token Map

| Semantic | Background | Text | Border |
|---|---|---|---|
| `success` | `emerald-50` | `emerald-800` | `emerald-200` |
| `warning` | `amber-50` | `amber-800` | `amber-200` |
| `danger` | `rose-50` | `rose-800` | `rose-200` |
| `info` | `blue-50` | `blue-800` | `blue-200` |
| `neutral` | `slate-100` | `slate-800` | `slate-200` |
| `brand` | `brand-50` | `brand-800` | `brand-200` |

Inverse theme: `STATUS_BADGE_SEMANTIC_CLASSES_INVERSE` — same semantics, dark-header surfaces.

---

## 7) Implementation Status

| Item | Status |
|---|---|
| Spec locked | ✅ |
| `StatusBadge` + semantics | ✅ |
| `StageTag` refactor | ✅ |
| `DocumentStatus` adapter | ✅ |
| `NextActionBadge` token migration | ✅ |
| Inline pill backlog | Legacy — migrate on touch |
| Primitive CI enforcement | ⬜ Phase 2 |

---

## 8) Chain Status

| Artifact | Status |
|---|---|
| `PRIMITIVES_BENCHMARK.md` | ✅ |
| `STATUS_BADGE_V1_DRAFT.md` | Superseded |
| **`STATUS_BADGE_V1.md`** | ✅ **Locked** |
| `CHIP_V1.md` | ✅ Locked (companion) |
| `PRIMITIVES_V1.md` | ✅ Partial lock |
