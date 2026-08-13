# UI Component Canon — catalog

**Hierarchy:** L2 — closed component ID catalog + consumption rules; **not** a visual restyle SoT  
**Decision record:** [`ADR-043`](../architecture/ADR-043-ui-component-composition-canon.md)  
**Parent model:** [`ADR-038`](../architecture/ADR-038-platform-standardization-model.md) · [`platform-standardization-model.md`](platform-standardization-model.md) (area `design_interaction`)  
**Visual / a11y / tokens:** [`ADR-011`](../architecture/ADR-011-hostflow-ui-platform-standard.md) (amended by ADR-043: CSS is implementation)  
**List shell (target):** [`ADR-010`](../architecture/ADR-010-unified-resource-list-shell.md) + [`ADR-044`](../architecture/ADR-044-list-workspace-data-presentation-canon.md) · [`ui-list-workspace-canon.md`](ui-list-workspace-canon.md)  
**Owner:** Frontend platform  
**Epic:** [`../tasks/ui-platform-composition-epic.md`](../tasks/ui-platform-composition-epic.md) (Core Platform Kit) · phase [`../architecture/platform-extraction-phase.md`](../architecture/platform-extraction-phase.md)

---

## 1. Purpose

Index of canonical HostFlow UI families. Product modules **compose** these IDs. Local recreation of an existing ID is an architecture violation.

This file does **not** lock pixel values or Figma. Chart palettes and analytics families live in [`ui-analytics-canon.md`](ui-analytics-canon.md) (**ADR-046**). Operational lists: [`ui-list-workspace-canon.md`](ui-list-workspace-canon.md) (**ADR-044**, rule done; runtime = Platform Extraction). Page templates remain **ADR-045** (deferred until a second template consumer).

---

## 2. Consumption contract

| Allowed in product pages (target) | Forbidden in new product-page code once the family has a kit component |
|-----------------------------------|------------------------------------------------------------------------|
| `<Button variant="primary">` | `className="btn-primary"` as the public API |
| `<PlatformIcon id="…">` | new `@tabler/icons-react` imports outside the registry |
| `<StatusBadge semantic="danger">` | ad-hoc `bg-rose-100` pills for status meaning |
| `<SemanticSurface tone="warning">` | page-local gradients / `rounded-2xl` heroes |
| `DataTable` from `components/ui` (K1) | new hand-written operational `<table>`; importing `DataTableEngine` as a product table |

CSS classes `.btn-*`, `.input`, `.table` remain **implementation** inside `hostflow-frontend/src/styles/components.css` and kit wrappers.

Import surface (target): primitives/composites from `hostflow-frontend/src/components/ui/`; Icon from `hostflow-frontend/src/platform/icons/`. Additional layout/template roots are named in ADR-045.

---

## 3. Surface profiles

| Profile | Code signal (today) | Token intent |
|---------|---------------------|--------------|
| `surface.crm` | operational SPA under `.app-ui` | dense; radius via `--radius-control` / `--radius-surface` — **not** descendant `!important` |
| `surface.public` | marketing / public / auth | more open; same Foundation color/type/spacing |

Do not mix profiles on one screen without an explicit contract (ADR-011 §2 still holds).

---

## 4. Catalog

Row contract: `component_id` · `layer` · `status` · `runtime_today` · `notes`.

`status`: `exists` (kit component usable) · `wrap` (CSS/legacy exists; React API is the P0 job) · `gap` (no canonical control yet).

P0 runtime (2026-08-13): control-layer React APIs landed. CSS remains implementation. Product pages still on className until migrate-on-touch.

### Foundation

| component_id | status | runtime_today | notes |
|--------------|--------|---------------|-------|
| `Color` | exists | `FOUNDATION_V1` + `brand.*` | Semantic UI colors only. Chart categories → [`ui-analytics-canon.md`](ui-analytics-canon.md) |
| `Type` | exists | `FOUNDATION_V1` + `.app-ui` h1–h3 | Two type scales (CRM vs pipedesign) collapse into surface profiles, not a second Foundation |
| `Spacing` | exists | `FOUNDATION_V1` 0–8 | — |
| `Radius` | exists | `--hf-radius-control` / `--hf-radius-surface`; CRM profile sets 0 | `.app-ui` descendant `!important` removed |
| `Shadow` | exists | `FOUNDATION_V1` | — |
| `Motion` | gap | ad-hoc transitions | No motion canon in this PR |

### Primitive

| component_id | status | runtime_today | notes |
|--------------|--------|---------------|-------|
| `Button` | exists | `Button.tsx` wraps `.btn-*` | Public API = React; CSS inside. Legacy `className="btn-primary"` until ratchet covers the file |
| `IconButton` | exists | `IconButton.tsx` → `variant="icon"` | Accessible name required |
| `Input` | exists | `Input.tsx` wraps `.input` | React wrapper allowed — does not reopen INPUT_V1 pixel debate |
| `Textarea` | exists | `Textarea.tsx` wraps `.textarea` | Same as Input |
| `Select` | wrap | `Combobox` / `MultiCombobox` + native `<select className="input">` | SELECT_V1 scenario tree still applies |
| `Checkbox` | exists | `Checkbox.tsx` (indeterminate supported) | — |
| `Radio` | exists | `Radio.tsx` | — |
| `Switch` | exists | `Switch.tsx` | Track/knob stay `rounded-full` |
| `Badge` | wrap | `StatusBadge` + `.badge` + inline pills | Status meaning → StatusBadge only |
| `Chip` | exists | `Chip.tsx` (3 consumers) | Promote usage; no fifth behavior without PR |
| `Icon` | wrap | `PlatformIcon` re-exported from kit barrel | Registry is the only new-import path |

### Composite

| component_id | status | runtime_today | notes |
|--------------|--------|---------------|-------|
| `SearchField` | exists | `SearchField.tsx` | ListWorkspace search zone (ADR-044) |
| `FilterBar` | gap | Candidates / dashboard / pipeline one-offs | ListWorkspace toolbar; was FILTER_BAR_V1 |
| `FormField` | exists | `FormField.tsx`; `controls/Field.tsx` is a legacy alias | Label + hint + error uses `text-rose-700` |
| `Tabs` | exists | `Tabs.tsx` wraps `.tabs` / `.tab` | — |
| `Modal` | exists | `components/Modal.tsx` close = `IconButton` | Re-exported from kit barrel |
| `Dropdown` | wrap | `.dropdown` CSS | — |
| `Pagination` | exists | `Pagination.tsx`; `EntityListPagination` wraps it | ListWorkspace mode `paged` \| `infinite` |
| `EmptyState` | exists | `EmptyState.tsx`; `EmptyStatePanel` is a legacy alias | No Tabler in the kit |
| `Toast` | wrap | `Toast.tsx` | — |
| `DateField` | wrap | native `input type=date` | INPUT_V1 native until DateField ships |
| `SemanticSurface` | exists | `SemanticSurface.tsx` tones from StatusBadge palette | HR emphasis via tone, not gradients |

### Data

| component_id | status | runtime_today | notes |
|--------------|--------|---------------|-------|
| `DataTable` | exists | `components/ui/DataTable.tsx` | Public kit API (K1). `layout/DataTable` re-exports; `DataTableEngine` is an adapter, not a second table. Candidates page not cut over. |
| `TableHeader` | wrap | kit `DataTable` header | ListWorkspace |
| `SortControl` | exists | `components/ui/SortControl.tsx` | TABLE_V1 / Candidates header pixels |
| `FacetFilter` | wrap | `FacetFilterMenu` | ListWorkspace filters |
| `BulkActionBar` | wrap | `EntityListBulkBar` | ListWorkspace; visible only with selection |

### Layout

| component_id | status | runtime_today | notes |
|--------------|--------|---------------|-------|
| `PageHeader` | exists | ~64 pages | Best-adopted layout |
| `ListWorkspace` | wrap | `EntityListShell` + parallel tables | **First workspace pattern** — ADR-044; Platform Extraction runtime |
| `EntityWorkspace` | wrap | `platform/entity-workspace` + candidate card | **Minimal chrome** this extraction sprint — not Phase D; page templates remain ADR-045 |
| `SettingsLayout` | wrap | `.settings-*` CSS | ADR-045 |
| `SplitPane` | gap | rails / inspectors | ADR-045 |

### Template

| component_id | status | runtime_today | notes |
|--------------|--------|---------------|-------|
| `EntityListPage` | gap | each list composes itself | ADR-045 template **hosts** `ListWorkspace` |
| `EntityDetailPage` | gap | candidate card is benchmark only | ADR-045 |
| `SettingsPage` | wrap | settings shells | ADR-045 |
| `OperationalQueuePage` | gap | inbox / HR queue / leads | ADR-045 |

### Analytics (ADR-046)

| component_id | status | runtime_today | notes |
|--------------|--------|---------------|-------|
| `KpiCard` | exists | `components/analytics` | Recruitment efficiency = canonical consumer |
| `TrendChart` | exists | kit | line / area |
| `FunnelChart` | exists | kit | conversion |
| `BreakdownChart` | exists | kit | composition / distribution / breakdown |
| `TargetProgress` | exists | kit | plan / capacity |
| `AnalyticsTable` | exists | kit | not ADR-044 DataTable |
| `InsightCard` | exists | kit | Insight → Action |
| `AnalyticsFilterBar` | exists | kit | date + dimensions |
| `AnalyticsEmptyState` | exists | kit | three empty kinds |
| `AnalyticsSection` | exists | kit | `density=story \| operational` |
| `AnalyticsStoryHero` | exists | kit | One headline number |
| `AnalyticsReportHeader` | exists | kit | Screenshot chrome + copy link + present |

Full families, palettes, Analytics View, and dashboard inventory: [`ui-analytics-canon.md`](ui-analytics-canon.md).

---

## 5. Child artifacts (no longer independent canons)

| Former program | Becomes |
|----------------|---------|
| `FOUNDATION_V1` | Foundation layer of this catalog |
| `PRIMITIVES_V1` / `BUTTON_V1` / `INPUT_V1` / `SELECT_V1` / `CHIP_V1` / `STATUS_BADGE_V1` | Primitive IDs |
| `TABLE_V1` | Data layer / visual child of ADR-044 `ListWorkspace` |
| `FILTER_BAR_V1` (unstarted) | `FilterBar` |
| `ENTITY_LAYOUT_V1` (draft) | `EntityWorkspace` min runtime (Platform Extraction); page templates → ADR-045 |
| REF-UI-000 roadmap | Execution notes under this tree |

Do not open a new `*_V1` as a sibling canon. Extend this catalog.

---

## 6. History

- 2026-08-13: **K1** public `DataTable` + `SortControl` in `components/ui`. `DataTableEngine` is an adapter. Candidates page not cut over.
- 2026-08-13: **Platform Extraction** — Core Platform Kit is the active stage; Vocabulary Canon closed.
- 2026-08-13: **ADR-044** `ListWorkspace` + one `DataTable` (rule). Runtime extract remains epic P1–P2. `ListLayout` renamed to `ListWorkspace`.
- 2026-08-13: **ADR-046** analytics families + presentation/share (`AnalyticsStoryHero`, `AnalyticsReportHeader`); Recruitment efficiency is the reference.
- 2026-08-13: Initial catalog under ADR-043. Runtime wrappers, DataTable extraction, layouts, visualization, and CI ratchet deferred to the epic / ADR-044…046.
- 2026-08-13: P0 control-layer React APIs + radius tokens + lower-only CI ratchet (`npm run ui:kit:check`). K1 DataTable landed; ListWorkspace / EntityWorkspace Shell remain K2–K3.
