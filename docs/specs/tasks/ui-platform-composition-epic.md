# UI Platform composition epic

**Status:** Active (runtime follow-on to ADR-043)  
**Canon:** [`ADR-043`](../architecture/ADR-043-ui-component-composition-canon.md) · L2 [`../platform/ui-component-canon.md`](../platform/ui-component-canon.md) · list [`ADR-044`](../architecture/ADR-044-list-workspace-data-presentation-canon.md) · analytics [`ADR-046`](../architecture/ADR-046-analytics-visualization-canon.md)  
**Does not amend L0.** Visual tokens remain [`ADR-011`](../architecture/ADR-011-hostflow-ui-platform-standard.md).

This is an **implementation epic**, not a new design-spec program. Do not start with marketing. Do not restyle `.btn-*` as a prerequisite.

---

## P0 — Control layer (CRM first)

Wrap current CSS where it exists. Product pages gain a React API; pixels stay.

- [x] Button  
- [x] IconButton  
- [x] Checkbox  
- [x] Radio  
- [x] Switch  
- [x] SearchField  
- [x] Tabs  
- [x] StatusBadge  
- [x] Chip  
- [x] PlatformIcon (only legal new icon import path — re-exported from the kit barrel)  
- [x] Modal  
- [x] EmptyState  
- [x] Pagination  
- [x] FormField  
- [x] SemanticSurface (`success` / `warning` / `danger` / `info` / `neutral` / `brand`)

- [x] Baseline CI ratchets (hex, Tabler, intrinsic button, gradients, rounded) — **lower-only** (`npm run ui:kit:check`).  
- [x] Remove `.app-ui` descendant `border-radius: 0 !important` in favor of `--hf-radius-control` / `--hf-radius-surface`.

Public import: `hostflow-frontend/src/components/ui`. CSS className in product modules remains legal until migrate-on-touch.

---

## P1 — One DataTable (inside ListWorkspace)

Canon: [`ADR-044`](../architecture/ADR-044-list-workspace-data-presentation-canon.md) · L2 [`../platform/ui-list-workspace-canon.md`](../platform/ui-list-workspace-canon.md). **Rule: done.** Runtime extract: next.

Product-facing API: one `ListWorkspace` hosting one `DataTable`. Modules pass `ListDefinition` (columns, cell kinds, filters, sort, actions, bulk, data source, saved views, permissions, empty). They do not fork a table.

**Capability bar:** Candidates / TABLE_V1 (the API must express that list). **Page cutover:** Vacancies → Leads → Employees → Companies → Admin / remaining → Candidates in-place wrap last.

---

## P2 — List contract (same pattern, not a second ADR)

Search + Filters + Sort + Pagination / infinite + Bulk + persisted views — zones of `ListWorkspace`. Not a second table.

---

## P3 — Layouts / templates

Blocked on **ADR-045**. New modules pick `EntityListPage` / `EntityWorkspace` / `OperationalQueuePage` / `SettingsPage`. They do not design a page type.

---

## P4 — Analytics kit (parallel to P0)

Canon: [`ADR-046`](../architecture/ADR-046-analytics-visualization-canon.md) · L2 [`../platform/ui-analytics-canon.md`](../platform/ui-analytics-canon.md).

Not a recolor. Four layers: metrics semantics → visualization grammar → analytics composition → presentation & sharing.

Dashboards assemble `AnalyticsReportHeader` / `AnalyticsStoryHero` / `KpiCard` / `TrendChart` / `FunnelChart` / `BreakdownChart` / `TargetProgress` / `AnalyticsTable` / `InsightCard` / `AnalyticsFilterBar`. URL Analytics View + `present=1`. No second reporting product.

**Reference (done):** Recruitment efficiency (story composition, copy-link, presentation mode). **Migrate-on-touch:** Sales, HR, Finance, Fleet, Marketing, Overview widgets, lead conversion funnel. Named save / PDF / schedule = same Analytics View later.

## Parallel (not this epic’s first slice)

- Marketing `surface.public` tokenisation of `#0B0E14` / pipedesign radii — after CRM P0.  
- ADR-038 Actions / Events — different standardization group; may proceed in parallel.

---

## Success bar

A second module that needs a control **adds a catalog ID or reuses one**. It does not copy Tailwind from Candidates or HR.
