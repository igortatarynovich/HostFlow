# ADR-044: List Workspace & Data Presentation Canon

**Status:** Accepted  
**Date:** 2026-08-13  
**Layer of change:** Experience (Design & Interaction) | Operational list pattern + one DataTable API  
**Trusted base:** `integration/release-product-a-b`  
**Related:** [`ADR-010`](ADR-010-unified-resource-list-shell.md) · [`ADR-043`](ADR-043-ui-component-composition-canon.md) · [`ADR-011`](ADR-011-hostflow-ui-platform-standard.md) · L2 [`../platform/ui-list-workspace-canon.md`](../platform/ui-list-workspace-canon.md) · epic [`../tasks/ui-platform-composition-epic.md`](../tasks/ui-platform-composition-epic.md)

**Amends (does not supersede):** ADR-010 — zone order, field kinds, rail/modal, and anti-giant-abstraction remain in force. This ADR binds them to **one product-facing pattern**: `ListWorkspace` + `DataTable`. ADR-043 — Data / list families in the closed catalog are now this pattern, not a future slot. TABLE_V1 remains the visual/behavior child (Candidates frame).

**L0 checklist:** No new L0 P-rule; no new capability Passport (UI Platform Standard #11 already owns lists via ADR-010 / #10 Resource List Shell). Applies P-01 / P-03 / INV-05 / INV-07 and AGENTS Rule 4 to **list UI**. Does not rewrite Passport/Manifest shape. List queries stay resource-owned (`/candidates`, `/vacancies`, …) — Shell does not mix modules into one endpoint (ADR-010 §7).

---

## Context

HostFlow already decided there is one list **shell** (ADR-010) and one product-facing **DataTable** (ADR-043 §7). Runtime still has four table stacks (`.table` CSS, `layout/DataTable`, `DataTableEngine`, hand-written `<table>`) plus a barely-used `EntityListShell`. Modules keep inventing Recruitment / HR / Fleet tables instead of configuring one pattern.

That is the same failure mode ADR-043 named for buttons: the page decides *how* a list works. A year later, column resize, a date filter, or sticky header cannot land once — they land N times or not at all.

`entity-table-governance.md` correctly forbids a **giant** table that owns domain cells and API. It must not be read as “every module may keep its own table.” The allowed split is: **one platform mechanism**, **module configuration and domain cells**.

---

## Decision

### 1. One ListWorkspace, one DataTable — modules supply configuration

There is no “Recruitment table”, “HR table”, or “Fleet table.” There is one platform pattern:

```text
ListWorkspace
  → Toolbar
  → Search
  → Filters
  → Saved views
  → DataTable
  → Pagination | infinite (definition mode)
  → Selection
  → Bulk actions
  → Row actions
  → Empty / loading / error
```

A product module **must not** implement a second operational list mechanism. It passes a `ListDefinition` and data.

What **differs** per resource (config / slots — not a fork of the table):

| Differs | Stays platform |
|---------|----------------|
| Column set and order | Chrome, row states, sticky header, resize, column visibility |
| Cell kinds + domain cell slots | Sort header contract, selection ≠ row click |
| Filters, sort, saved views | One search, one toolbar, active-filter chips |
| Row / bulk actions (permission-filtered) | Bulk bar only when selection is non-empty |
| Data source (module query) | Pagination / infinite as definition modes of one pattern |
| Empty copy and primary empty action | Empty / loading / error chrome |
| Insights strip (optional, filter-scoped) | Zone order (ADR-010 §2) |

The same `ListWorkspace` must be able to show candidates, vacancies, employees, documents, companies, leads, campaigns, orders, vehicles, and invoices. Appearance and interaction stay identical; only definition and data change.

Example: candidates definition asks for Name, Phone, Vacancy, Stage, Recruiter, Updated. Documents: Type, Owner, Status, Valid to, Uploaded by. The table component is the same.

### 2. Configuration, not a mega-component

`ListWorkspace` is composition + controlled state + `ListDefinition`. It is **not** a boolean explosion (`compact`, `showFilters`, `selectable`, …) and **not** a place for candidate stage rules or HR eligibility.

- Platform owns: zones, search debounce, sort, selection, bulk chrome, pagination, column layout persistence, export entry, empty/loading/error frames.
- Module owns: `ListDefinition` (columns, field kinds, filters, actions, density, data hook), domain `cell` renderers, permission filtering of actions, resource API.

Field kinds remain ADR-010 §3 (`text`, `number`, `date`, `datetime`, `boolean`, `enum`, `ref`, `user`, `tags`, `custom`). Custom cells still declare a stable `field_id`.

### 3. ListWorkspace is the first UI Pattern — not “just a table”

ADR-043 is the **control** kit. This ADR is the first **workspace pattern**: a screen-scale assembly that every operational list must use.

The same rule applies later (ADR-045, **deferred**): one `EntityListPage` template that *hosts* `ListWorkspace`. Minimal `EntityWorkspace` **chrome** (header, action bar, rail) is Platform Extraction, not ADR-045.

### 4. Analytics tables are a different family

Operational entity lists use `DataTable` inside `ListWorkspace`. Analytical totals / deltas use `AnalyticsTable` ([`ADR-046`](ADR-046-analytics-visualization-canon.md)). Do not render a dashboard as an entity list, or an entity list as a chart table.

### 5. Runtime adoption — extract once, migrate-on-touch

This ADR does **not** extract the engine in the same change set as the rule.

**Capability bar:** TABLE_V1 / Candidates is the behavioral source. The public API must express that list (pipeline cells, bulk, filters, column manager) — otherwise other modules will fork again.

**Collapse into one public API:** `EntityListShell` (zones) + Candidates table behavior + `platform/data-table` helpers. `layout/DataTable`, unused engines, and new hand-written operational `<table>` are debt.

**Page cutover (epic P1–P2):** new lists must use `ListWorkspace` from the day they ship. Existing pages migrate-on-touch: Vacancies → Leads → Employees → Companies → Admin / remaining → Candidates in-place wrap last as the richest consumer (ADR-010 risk control). The extracted API exists *before* Candidates cutover so that cutover is adoption, not invention.

### 6. Enforcement

After the public `ListWorkspace` / `DataTable` API exists: no new operational `<table>` in `pages/` / `modules/` (kit ratchet already freezes the count). New list pages without `ListWorkspace` are an architecture violation. Boolean props on the shell root remain forbidden (ADR-010 §9).

---

## Out of scope (explicit)

- Extracting / rewriting list pages in this PR
- Entity workspace / `EntityHeader` / details / timeline (ADR-045)
- Visual restyle of `.table` pixels (TABLE_V1 stays)
- `AnalyticsTable` / dashboard lists (ADR-046)
- List Metadata API (`GET /meta/list-schemas/{resource}`) — still ADR-010 v2
- Infinite loading as a second product pattern (it is a definition mode)

---

## Explicit next

1. [Platform Extraction](platform-extraction-phase.md) / Core Platform Kit: one `ListWorkspace` + `DataTable` public API; Vacancies first page cutover; Candidates = capability bar.
2. Minimal `EntityWorkspace` chrome in the same kit sprint (not Phase D; **not** ADR-045).
3. **ADR-045** only when a second real page-template consumer exists.
4. Events runtime (ADR-019 3A-1) when a consumer exists.

---

## Architecture Review Checklist (L0)

- [x] P-01…P-05 respected — composes existing UI Platform / Resource List Shell; no new Passport
- [x] INV-05 — list chrome is platform; module data/config is not a second visual language
- [x] INV-07 / two-module rule — a second list consumer uses `ListWorkspace`, it does not copy Candidates Tailwind
- [x] ADR-010 / ADR-011 / ADR-043 not superseded; product API bound
- [x] L0 freeze untouched
- [x] Area 13 list sub-gap closed as **rule**; runtime extract remains epic P1–P2

---

## Consequences

- Positive: one place to improve sort, filters, column resize, sticky header, saved views, export; Fleet / Finance lists look like Recruitment lists; modules shrink to definition + domain cells.
- Negative: until P1–P2 extract, parallel tables remain legal under migrate-on-touch; Candidates page stays large until wrap.
- Follow-on: runtime extract → ADR-045 workspace templates.

---

## Alternatives considered

1. **Keep per-module tables with a shared CSS class** — rejected; that is today’s debt; behavior still forks.
2. **Giant DataTable that imports candidate/HR cells** — rejected; ADR-010 §9; domains leak into System Layer.
3. **Candidates last for the API itself** — rejected; if the API cannot express Candidates, every rich list will fork. Candidates is last for *page* cutover, first for *capability bar*.
4. **Wait for ADR-045 page templates before the list pattern** — rejected; ListWorkspace is the first pattern; templates host it.
5. **One endpoint for all lists** — rejected; ADR-010 §7; queries stay resource-owned.

---

## Cross-references (updated in same change set)

- [`../platform/ui-list-workspace-canon.md`](../platform/ui-list-workspace-canon.md) — L2 contract
- [`ADR-010-unified-resource-list-shell.md`](ADR-010-unified-resource-list-shell.md) — zones / field kinds (amended pointer)
- [`ADR-043-ui-component-composition-canon.md`](ADR-043-ui-component-composition-canon.md) — parent composition
- [`../frontend/entity-table-governance.md`](../frontend/entity-table-governance.md) — amended: one API, still no giant domain table
- [`../frontend/TABLE_V1.md`](../frontend/TABLE_V1.md) — visual child
- [`../tasks/ui-platform-composition-epic.md`](../tasks/ui-platform-composition-epic.md) — P1–P2
- [`architecture-guide.md`](architecture-guide.md) · [`module-catalog-and-routing-map.md`](module-catalog-and-routing-map.md) · [`platform-architecture-principles.md`](platform-architecture-principles.md)
- [`ADR-038-platform-standardization-model.md`](ADR-038-platform-standardization-model.md) · [`../platform/platform-standardization-model.md`](../platform/platform-standardization-model.md)
