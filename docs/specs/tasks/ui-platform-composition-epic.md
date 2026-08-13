# UI Platform composition epic

**Status:** Active (runtime follow-on to ADR-043)  
**Canon:** [`ADR-043`](../architecture/ADR-043-ui-component-composition-canon.md) · L2 [`../platform/ui-component-canon.md`](../platform/ui-component-canon.md)  
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

## P1 — One DataTable

Blocked on **ADR-044**. Product-facing API: one. Candidates is the canonical implementation. Migration: Vacancies → Leads → Employees → Companies → Admin lists.

---

## P2 — List contract

Search + Filters + Sort + Pagination + Bulk + persisted view state — one contract, different columns. Same ADR-044.

---

## P3 — Layouts / templates

Blocked on **ADR-045**. New modules pick `EntityListPage` / `EntityWorkspace` / `OperationalQueuePage` / `SettingsPage`. They do not design a page type.

---

## P4 — Analytics kit (parallel to P0)

Canon: [`ADR-046`](../architecture/ADR-046-analytics-visualization-canon.md) · L2 [`../platform/ui-analytics-canon.md`](../platform/ui-analytics-canon.md).

Not a recolor. Dashboards assemble `KpiCard` / `TrendChart` / `FunnelChart` / `BreakdownChart` / `TargetProgress` / `AnalyticsTable` / `InsightCard` / `AnalyticsFilterBar`.

**Reference (done):** Recruitment efficiency dashboard. **Migrate-on-touch:** Sales, HR, Finance, Fleet, Marketing, Overview widgets, lead conversion funnel.

## Parallel (not this epic’s first slice)

- Marketing `surface.public` tokenisation of `#0B0E14` / pipedesign radii — after CRM P0.  
- ADR-038 Actions / Events — different standardization group; may proceed in parallel.

---

## Success bar

A second module that needs a control **adds a catalog ID or reuses one**. It does not copy Tailwind from Candidates or HR.
