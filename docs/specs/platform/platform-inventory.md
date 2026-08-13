# Core Platform Kit — Inventory

**Status:** **LIVING CATALOG** (L2 operating index — **not** a canon, **not** an ADR)  
**Date:** 2026-08-13  
**Baseline:** **Platform Baseline v1** — [Kit Gate](../gates/platform-extraction-kit-gate.md) `PASS_WITH_CONSTRAINTS`  
**Contracts (SoT):** [`ADR-043`](../architecture/ADR-043-ui-component-composition-canon.md) · [`ui-component-canon.md`](ui-component-canon.md) · [`ADR-044`](../architecture/ADR-044-list-workspace-data-presentation-canon.md) · [`ui-list-workspace-canon.md`](ui-list-workspace-canon.md) · [`ADR-046`](../architecture/ADR-046-analytics-visualization-canon.md) · [`ui-analytics-canon.md`](ui-analytics-canon.md)  
**Does not amend L0.** Does not replace those canons. Pixels stay [`ADR-011`](../architecture/ADR-011-hostflow-ui-platform-standard.md).

> One page of **what a module is allowed to import**.  
> If it is not on this list as `exists` / `slot`, do not invent a local stand-in — extend the kit (two-consumer rule) or stop.

---

## How to use this file

| Question | Answer |
|----------|--------|
| What may I import? | Rows with **legal import** below |
| What is the contract? | Linked canon — this file does not restyle or redefine APIs |
| What does a new module need? | **Platform Baseline v1** |
| What is still missing? | `gap` / `wrap` rows — Optimization or a two-consumer extract, not a product fork |

**Legal barrels**

- UI kit: `hostflow-frontend/src/components/ui`
- Analytics kit: `hostflow-frontend/src/components/analytics`

**Forbidden as product APIs:** `DataTableEngine`, `layout/DataTable` (re-export only), `platform/entity-workspace` Shell as the *public* chrome (passport **adapter** only), Recruitment / HR / Vacancy / Candidate Workspace.

`status`: `exists` (import it) · `slot` (compose via a kit prop, not a second component) · `wrap` (legacy CSS/screen; React API incomplete) · `gap` (no kit block yet — do not ship a local clone if Baseline v1 already covers the need).

---

## Platform Baseline v1

The Kit Gate bar. A new product screen that needs these blocks **must** compose them:

| ID | Legal import |
|----|----------------|
| `DataTable` | `components/ui` |
| `ListWorkspace` | `components/ui` |
| `EntityWorkspace` | `components/ui` |
| Analytics families | `components/analytics` (`KpiCard`, chart family, `AnalyticsSection`, `AnalyticsFilterBar`, story/report chrome) |

Later: “Module X requires Platform Baseline v1” or “this feature requires Baseline v2” when a **second** module forces a new family. Do not mint Baseline v2 as a docs-only label.

---

## Workspace

| ID | Status | Legal import / slot | Notes |
|----|--------|---------------------|-------|
| `ListWorkspace` | exists | `components/ui` | Search, filters slot, sort, pagination, bulk, saved views, view switcher. Hosts one `DataTable`. Vacancies = first cutover |
| `EntityWorkspace` | exists | `components/ui` | Header, optional action bar, summary, nav, content, rail. Timeline = **content slot** |
| `EntityWorkspaceHeader` / `Summary` / `Rail` | exists | `components/ui` | Helpers for **new** chrome. Candidate header stays module-owned |
| `EntityWorkspaceShell` | adapter | `platform/entity-workspace` | Passport adapter **onto** kit chrome — not a second shell |
| `PageHeader` | exists | widely used layout | Not Baseline v1; keep using; ADR-045 templates still deferred |
| `SettingsLayout` | wrap | `.settings-*` | ADR-045 |
| `SplitPane` | gap | — | ADR-045 |

**Not platform:** Recruitment / HR / Vacancy / Candidate Workspace.

---

## Data

| ID | Status | Legal import | Notes |
|----|--------|--------------|-------|
| `DataTable` | exists | `components/ui` | One operational table API |
| `SortControl` | exists | `components/ui` | TABLE_V1 / Candidates header pixels |
| `TableHeader` | wrap | inside `DataTable` | Do not fork |
| `Pagination` | exists | `components/ui` | ListWorkspace `paged` \| `infinite` |
| `AnalyticsTable` | exists | `components/analytics` | Totals / story table — **not** ADR-044 `DataTable` |

---

## Analytics

| ID | Status | Legal import | Notes |
|----|--------|--------------|-------|
| `KpiCard` / `KpiCardGrid` | exists | `components/analytics` | No module-local KPI tile |
| `AnalyticsSection` | exists | `components/analytics` | `density=story \| operational` |
| Chart family | exists | `TrendChart` · `FunnelChart` · `BreakdownChart` · `TargetProgress` | Meaning → family in analytics canon |
| `AnalyticsFilterBar` | exists | `components/analytics` | Date + dimensions |
| `AnalyticsStoryHero` | exists | `components/analytics` | One headline number |
| `AnalyticsReportHeader` | exists | `components/analytics` | Copy-link / `present=1` |
| `InsightCard` | exists | `components/analytics` | Insight → Action |
| `AnalyticsEmptyState` | exists | `components/analytics` | Three empty kinds |
| `ChartFrame` | implementation | **not** a product import | Inside family charts (KG-C4) |

Remaining efficiency dashboards = migrate-on-touch.

---

## Navigation

| ID | Status | Legal import | Notes |
|----|--------|--------------|-------|
| `Tabs` | exists | `components/ui` | EntityWorkspace may pass a custom `navigation` slot (Candidates pills stay module-owned until touch) |
| `Chip` | exists | `components/ui` | Filters / saved views / toggles |
| `SavedViewChips` | exists | `components/ui` | ListWorkspace saved views |

---

## Feedback

| ID | Status | Legal import | Notes |
|----|--------|--------------|-------|
| `EmptyState` | exists | `components/ui` | Lists / pages |
| `SemanticSurface` | exists | `components/ui` | Tone, not a local gradient hero |
| `StatusBadge` | exists | `components/ui` | Status meaning |
| Loading (table) | slot | `DataTable` `loading` / `loadingOverlay` | No separate `LoadingState` component |
| `LoadingState` | gap | — | Do not invent a second spinner kit in a product page; use table/page slot or extract when a second module needs it |
| `ErrorState` | gap | field errors via `FormField` | No page-level ErrorState yet |

---

## Actions

| ID | Status | Legal import / slot | Notes |
|----|--------|---------------------|-------|
| `Button` / `IconButton` | exists | `components/ui` | Public API = React |
| `BulkActionBar` | exists | `components/ui` | Visible with selection |
| Entity action bar | slot | `EntityWorkspace` `actionBar` | Compose `Button`s; not a second ActionBar product |
| `ActionBar` (standalone) | gap | — | Covered by Bulk + entity slot for Baseline v1 |

---

## Inputs

| ID | Status | Legal import / slot | Notes |
|----|--------|---------------------|-------|
| `SearchField` | exists | `components/ui` | ListWorkspace search |
| `Input` / `Textarea` | exists | `components/ui` | Wrappers over `.input` / `.textarea` |
| `FormField` | exists | `components/ui` | Label + hint + error |
| `Combobox` / `MultiCombobox` | exists | `components/ui` | SELECT_V1 tree |
| List filters | slot | `ListWorkspace` `filters` | Module owns filter widgets; kit owns the zone |
| `FilterBar` | gap | — | Canon ID; do not ship a fourth filter chrome |
| `FacetFilter` | wrap | `FacetFilterMenu` | ListWorkspace |
| `DateField` | wrap | native `input type=date` | Until DateField ships |

---

## Selection

| ID | Status | Legal import | Notes |
|----|--------|--------------|-------|
| `Checkbox` | exists | `components/ui` | DataTable selection; click ≠ row nav |
| `Radio` | exists | `components/ui` | — |
| `Switch` | exists | `components/ui` | — |

---

## Also in the UI barrel (not Baseline v1, still legal)

`PlatformIcon` (only new icon path) · `Modal` · `FieldGrid` · `SectionCard`.

`Dropdown` / `Toast` / `Avatar` remain wrap — not Kit Gate blockers.

---

## Adoption checklist (new product screen)

- [ ] Operational list → `ListWorkspace` + `DataTable` (not a handwritten `<table>`, not `DataTableEngine`)
- [ ] Entity chrome → `EntityWorkspace` (not a fifth card shell)
- [ ] Analytics → `components/analytics` (not a local KPI/chart)
- [ ] Bulk / row actions → `BulkActionBar` or entity `actionBar` slot + `Button`
- [ ] Search / filters → kit search + ListWorkspace filter slot / `AnalyticsFilterBar`
- [ ] Empty → `EmptyState` or `AnalyticsEmptyState`
- [ ] No promotion of Candidate/HR/Vacancy/Recruitment Workspace into the kit

PR: [`.github/pull_request_template.md`](../../../.github/pull_request_template.md) · [architecture-review-checklist.md](../architecture/architecture-review-checklist.md) L2 Kit Gate.

This checklist is the intended seed for a later AST / ratchet scanner (KG-C3).

---

## History

- 2026-08-13: Opened after Kit Gate. Index of Baseline v1 + full kit; contracts stay in existing canons.
