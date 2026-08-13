# UI List Workspace Canon

**Hierarchy:** L2 — operational list pattern contract; **not** pixel SoT  
**Decision record:** [`ADR-044`](../architecture/ADR-044-list-workspace-data-presentation-canon.md)  
**Zones / field kinds:** [`ADR-010`](../architecture/ADR-010-unified-resource-list-shell.md)  
**Parent composition:** [`ADR-043`](../architecture/ADR-043-ui-component-composition-canon.md) · [`ui-component-canon.md`](ui-component-canon.md)  
**Visual child:** [`../frontend/TABLE_V1.md`](../frontend/TABLE_V1.md) (Candidates frame)  
**Owner:** Frontend platform  
**Epic:** [`../tasks/ui-platform-composition-epic.md`](../tasks/ui-platform-composition-epic.md) (Core Platform Kit / ListWorkspace stream) · [`../architecture/platform-extraction-phase.md`](../architecture/platform-extraction-phase.md)

---

## 1. Purpose

One platform `ListWorkspace` + one `DataTable` for every operational entity list. Modules pass `ListDefinition` and data. They do not fork a table.

Analytics totals tables are [`ui-analytics-canon.md`](ui-analytics-canon.md) `AnalyticsTable`, not this family.

---

## 2. Public API (target)

```tsx
<ListWorkspace definition={vacanciesList} query={query}>
  {/* domain cell slots only — no second toolbar / table */}
</ListWorkspace>
```

Forbidden in new list pages: a second operational `<table>`, a copied Candidates toolbar, a module-local pagination/bulk/search.

Runtime today: public `ListWorkspace` + `DataTable` in `hostflow-frontend/src/components/ui`. First cutover is Vacancies. Candidates page remains the capability bar and is **not** wrapped.

---

## 3. ListWorkspace assembly (closed)

| Zone / part | Catalog ID | Notes |
|-------------|------------|--------|
| Page header (host) | `PageHeader` | One primary create; template may wrap (ADR-045 `EntityListPage`) |
| Insights (optional) | — | Filter-scoped KPIs only; omit by default |
| Toolbar | `FilterBar` + `SearchField` | One toolbar; no duplicate under the table |
| Saved views | part of definition | Per `(resource_id, scope_key)` |
| Active filters | chips | Human-readable + clear all |
| Table | `DataTable` | `TableHeader`, `SortControl`, column visibility / resize / sticky |
| Selection | `Checkbox` | Checkbox ≠ row navigation |
| Bulk | `BulkActionBar` | Visible only when selection length > 0 |
| Row actions | last column `⋯` | View → edit → divider → destructive |
| Pagination / infinite | `Pagination` | Mode is definition, not a second pattern |
| Empty / loading / error | `EmptyState` | Copy and primary action from definition |

Zone **order** is ADR-010 §2. Hiding an empty zone is allowed. Reordering is not.

---

## 4. ListDefinition (what the module owns)

| Field | Role |
|-------|------|
| `resource_id` | Stable id (`candidates`, `vacancies`, …) |
| `columns[]` | `field_id`, kind, label, sortable, sticky?, cell slot |
| `filters[]` | Same `field_id` / kind; operators per ADR-010 §3 |
| `sort` | Default + allowed fields |
| `row_actions` / `bulk_actions` | Action ids; module filters by permission |
| `density` | `comfortable` \| `compact` — not a boolean on the shell |
| `pagination` | `paged` \| `infinite` + page size |
| `saved_views` | enabled? |
| `empty` | title, description, primary action |
| `data` | Module query; never a mixed-module endpoint |

Domain cells (stage pipeline, document %, HR badges) stay in the owning module as column slots. They use kit primitives (`StatusBadge`, `Chip`, `PlatformIcon`) — they do not invent hex or a second table.

---

## 5. Same pattern, many resources

Valid consumers (not an exhaustive product list): candidates, vacancies, employees, documents, companies, leads, campaigns, orders, vehicles, invoices, admin entity lists.

Invalid: “HR table v2”, a dashboard pretending to be an entity list, a new list that copies Tailwind from Candidates.

---

## 6. History

- 2026-08-13: Initial contract under ADR-044. Runtime extract = [Platform Extraction](../architecture/platform-extraction-phase.md).
- 2026-08-13: K2 public `ListWorkspace`; Vacancies is the first cutover. Candidates page not wrapped.
