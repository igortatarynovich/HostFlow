# UI List Workspace Canon

**Hierarchy:** L2 — operational list pattern contract; **not** pixel SoT  
**Decision record:** [`ADR-044`](../architecture/ADR-044-list-workspace-data-presentation-canon.md)  
**Zones / field kinds:** [`ADR-010`](../architecture/ADR-010-unified-resource-list-shell.md)  
**Parent composition:** [`ADR-043`](../architecture/ADR-043-ui-component-composition-canon.md) · [`ui-component-canon.md`](ui-component-canon.md)  
**Visual child:** [`../frontend/TABLE_V1.md`](../frontend/TABLE_V1.md) (Candidates frame)  
**Owner:** Frontend platform  
**Epic:** [`../tasks/ui-platform-composition-epic.md`](../tasks/ui-platform-composition-epic.md) (Core Platform Kit / ListWorkspace stream) · [`../architecture/platform-extraction-phase.md`](../architecture/platform-extraction-phase.md)  
**What to import:** [`platform-inventory.md`](platform-inventory.md)

---

## 1. Purpose

`ListWorkspace` is the **collection orchestration** layer: search, filter, sort, saved view, pagination, selection, bulk binding, URL sync, and representation.

It is **not** a list-page around `DataTable`. `DataTable` / `TABLE_V1` is one registered representation renderer.

```text
Collection Workspace / collection consumer
  → collection_orchestration (ListWorkspace)
    → representation
      → DataTable / TABLE_V1
        → fields / cells
```

Kit-layer id: **`collection_orchestration`**. Implementation: `ListWorkspace`. This id is a platform capability, not a widget.

Modules pass `ListDefinition` + resource data. They do not own query/filter/sort/pagination/selection/saved-view wiring.

Analytics totals tables are [`ui-analytics-canon.md`](ui-analytics-canon.md) `AnalyticsTable`, not this family.

---

## 2. Public API

```tsx
const list = useListWorkspace(definition)
<ListWorkspace controller={list} rows={rows} total={total} loading={loading} />
```

Forbidden in a **primary collection screen**:

- a second operational `<table>`
- a copied Candidates toolbar
- module-local search / filter / sort / pagination / selection / saved-view orchestration
- importing `DataTable` as the page’s list surface (`DataTable` is legal only as the table representation inside ListWorkspace, or on migrate-on-touch pages not yet cut over)

Proof (Vacancies): the collection screen supplies definition + domain cells/actions + fetch. It does not call `useSearchParams` or keep local selection/page/sort/filter state.

---

## 3. ListWorkspace assembly (closed)

| Zone / part | Catalog ID | Notes |
|-------------|------------|--------|
| Page header (host) | `PageHeader` | One primary create; template may wrap (ADR-045 `EntityListPage`) |
| Insights (optional) | — | Filter-scoped KPIs only; omit by default |
| Toolbar | ListWorkspace search + filter zone | `filter_bar` is **this zone**, not a separate widget |
| Saved views | part of definition + platform runtime | Per `(resource_id, scope_key)`; apply writes query + URL |
| Active filters | chips | Human-readable + clear all |
| Representation | `table` today | Registry; DataTable is the table renderer, not the workspace |
| Selection | `Checkbox` | Checkbox ≠ row navigation; platform-owned |
| Bulk | `BulkActionBar` | Visible only when selection length > 0; actions bound from definition |
| Row actions | last column `⋯` | View → edit → divider → destructive |
| Pagination / infinite | `Pagination` | Mode is definition, not a second pattern |
| Empty / loading / error | `EmptyState` | Copy and primary action from the consumer |

Zone **order** is ADR-010 §2. Hiding an empty zone is allowed. Reordering is not.

---

## 4. ListDefinition (what the module owns)

| Field | Role |
|-------|------|
| `resource_id` | Stable id (`candidates`, `vacancies`, …) |
| `columns[]` | `field_id`, kind, label, sortable, sticky?, cell slot |
| `filters[]` | Same `field_id` / kind; widget `chips` \| `text`; URL key |
| `sort` | Default column + direction |
| `row_actions` / `bulk_actions` | Action ids; module implements domain `onAction(ids)` |
| `density` | `comfortable` \| `compact` — not a boolean on the shell |
| `pagination` | `paged` \| `infinite` + page size |
| `saved_views` | views + persist callbacks; apply/save/remove runtime is platform |
| `representations` | Registered ids; default `table` |
| `empty` | title, description, primary action (consumer slot today) |
| data fetch | Module query from `list.query`; never a mixed-module endpoint |

Domain cells (stage pipeline, document %, HR badges) stay in the owning module as column slots. They use kit primitives (`StatusBadge`, `Chip`, `PlatformIcon`) — they do not invent hex or a second table.

Platform owns: query state, filter model, sort, pagination, selection, bulk chrome binding, saved-view apply/save/remove, URL synchronization, representation dispatch.

---

## 5. Same pattern, many resources

Valid consumers (not an exhaustive product list): candidates, vacancies, employees, documents, companies, leads, campaigns, orders, vehicles, invoices, admin entity lists.

Invalid: “HR table v2”, a dashboard pretending to be an entity list, a new list that copies Tailwind from Candidates, a primary collection screen that imports `DataTable` directly.

---

## 6. Acceptance (orchestration proof)

K2 shipped zone chrome. That is **not** sufficient.

A collection screen is assembled from the platform when:

1. It uses `useListWorkspace` + `ListWorkspace`.
2. It does not locally wire search, filters, sort, pagination, selection, or saved views.
3. `DataTable` is reached only through the representation registry.

Vacancies is the proof consumer. Remaining lists stay migrate-on-touch.

---

## 7. History

- 2026-08-13: Initial contract under ADR-044. Runtime extract = [Platform Extraction](../architecture/platform-extraction-phase.md).
- 2026-08-13: K2 public `ListWorkspace`; Vacancies is the first cutover. Candidates page not wrapped.
- 2026-08-21: **ListWorkspace Orchestration Completion** — canonical `ListDefinition`, platform-owned query/filter/sort/pagination/selection/saved-view/URL, representation registry (`table` → DataTable). Vacancies collapsed to definition + domain cells/actions/fetch. Kit-layer id `collection_orchestration`.
