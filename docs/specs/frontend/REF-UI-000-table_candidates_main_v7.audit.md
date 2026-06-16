# REF-UI-000 — table_candidates_main_v7 Audit

Component ID: `table_candidates_main_v7`  
Page: `/app/candidates`  
Source: `src/pages/Candidates.tsx`, `src/modules/candidates/components/*`  
Audit date: 2026-05-29  
Status: `Candidate`  
Audit State: `Audited`  
Decision: `Candidate for TABLE_V1` (no final canon lock until cross-table comparison)

## 1. Structural Audit (Baseline)

### 1.1 Table shell

- Render mode: native HTML table (`<table>`, `<thead>`, `<tbody>`), not third-party grid.
- Header: sticky (`top-0`, `z-10`) with inset separator shadow.
- First column: checkbox column, fixed width `56px`, sticky behavior in header.
- Column system:
  - default visible columns from `DEFAULT_VISIBLE_COLS`;
  - default order from `DEFAULT_COLUMN_ORDER`;
  - user-customizable order + width persisted to local storage.
- Data loading:
  - hook: `useCandidatesTableData`;
  - fetch limit: `200` (`const [limit] = useState(200)`);
  - no UI pagination control in table footer/header.

### 1.2 Columns (default order seed)

From `DEFAULT_COLUMN_ORDER`:

1. `name`
2. `stage`
3. `docsStatus`
4. `reasons`
5. `intakeKind`
6. `vacancy`
7. `manager`
8. `risk`
9. `docsOrdered`
10. `docsValid`
11. `docsFiles`

### 1.3 Filters

- Global/top filters: `CandidatesFiltersToolbar` (search + multi-filter controls + saved views).
- Per-column filters: `CandidatesTableColumnHeaderContent` + `ColumnFilterMenu`.
- Filter classes present:
  - text filters,
  - multi-select filters,
  - date ranges,
  - docs-related filters,
  - stage/manager/vacancy/reason filters,
  - quick views and queue-specific filters.
- Filter persistence:
  - URL sync (`useCandidatesUrlSync`),
  - local persistence (`useCandidatesFiltersPersistence`),
  - saved views support (with optional table layout save).

### 1.4 Sorting

- Multi-column sorting support by active `sortKey` + `sortDir`.
- Sort trigger in header cells (`renderSortButton`).
- Sort indicators: active direction arrow + passive hover indicator.

### 1.5 Bulk actions

Visible only when selection is non-empty and role allows management.

Available actions from bulk toolbar:

- stage update,
- manager assign,
- vacancy assign,
- handoff,
- tags update,
- activities create,
- delete,
- clear selection.

### 1.6 Pagination

- Explicit pagination component: not present.
- Current behavior: batch loading with limit 200 + filter/sort on loaded set.
- Audit note: pagination pattern must be compared with other P0 tables before TABLE_V1 lock.

## 2. Visual Density (Required)

### 2.1 Measured UI parameters from code

- Base table typography: `text-sm` (14px nominal Tailwind size).
- Header row height: `h-11` (44px).
- Header cell padding:
  - checkbox header: `px-4`,
  - other headers: `px-4` or `pl-2 pr-4` (customize mode),
  - vertical: `py-2.5` via shared header class.
- Body cell padding:
  - compact columns (`stage`, `docsStatus`, `vacancy`, `manager`): `px-3 py-2.5`,
  - other columns: `px-4 py-2.5`.
- Body row separation: top border per row (`border-t border-slate-200/90`).
- Whitespace usage:
  - compact mode on key operational columns,
  - high-content `name` cell includes inline actions and secondary metadata.

### 2.2 Visible rows on standard desktop

- Formula baseline:
  - row visual block is driven by `py-2.5` plus content-dependent height;
  - with one-line content rows approach compact density;
  - with name-cell action row, effective row height increases.
- Initial audit estimate:
  - medium laptop viewport (1080p, browser full height): ~12-18 rows visible depending on toolbar/banner presence and row content wrapping.
- Validation state:
  - needs manual screenshot measurement for `Validated` state.

### 2.3 Density conclusion

- Information density: high for operational CRM usage.
- Density tradeoff: row-level inline actions increase height but reduce navigation overhead.

## 3. Operator Efficiency (Required)

### 3.1 Actions available without opening detail card

Directly from list row / list shell:

- call,
- email,
- open card,
- open tasks modal,
- favorite toggle,
- row selection,
- bulk operations.

### 3.2 Inline actions

- Present in `name` cell (`Call`, `Email`, `Open`, `Tasks`).
- Stage and docs status visible inline in table row.

### 3.3 Click path to key operations (current)

- Open candidate card: 1 click.
- Select candidate for bulk: 1 click on checkbox.
- Bulk stage/manager/vacancy/handoff/tags/activities/delete: 2-3 clicks after selection.
- Quick communication:
  - call/email: 1 click from row action.

### 3.4 Status visibility without deep navigation

- Stage, reasons, docs readiness shown in table row.
- Supports queue triage without opening entity card.
- Horizontal scroll may be needed when many columns are enabled.

### 3.5 Find speed

- Search in toolbar + structured filters + saved views + quick queues.
- URL + local persistence reduces repeated setup cost.

### 3.6 Efficiency conclusion

- Operator efficiency is strong and aligned with high-throughput recruiter workflows.
- Main risk: complexity of filter surface can increase cognitive load for new users.

## 4. Deviations / Risks

### 4.1 Deviations to track against future TABLE_V1

- No explicit pagination component pattern.
- High feature density tightly coupled to candidates domain behavior.
- Column customization + persisted layout adds implementation complexity.

### 4.2 Technical risks for reuse

- Coupling to candidate-specific data model and helper maps.
- Rich row cell composition (actions + previews + badges) may be hard to generalize naively.

## 5. Reuse Decision (Required)

### 5.1 Can it be TABLE_V1 base?

- Yes, as primary candidate base for entity list table.

### 5.2 What must be adapted before canon lock

1. Extract domain-agnostic table frame contract:
   - sticky header,
   - selection model,
   - sortable/filterable header,
   - bulk action slot,
   - empty/loading/error states.
2. Standardize pagination behavior contract (even if "no visible pager" remains valid pattern).
3. Define minimal required column set for small/medium screens.
4. Separate optional advanced features:
   - column DnD/resize,
   - saved layout in views,
   - work-panel integration.

### 5.3 Constraints

- Must preserve operator speed and density.
- Must not force all entities to adopt candidate-specific inline actions.
- Must keep predictable filter and bulk action placements.

### 5.4 First migration targets after provisional TABLE_V1

1. `/app/vacancies` (`table_vacancies_list`)
2. `/app/clients/directory` (`table_companies_list`)
3. `/app/leads` (`table_leads_workspace` table mode)
4. `/app/hr/employees` (`table_hr_employees`)

Rationale: same operational entity-list family and closest business usage.

## 6. Final Audit Output

- Current decision: `Candidate for TABLE_V1`.
- Canonical lock: `Blocked` until comparative audit of other P0/P1 tables is complete.
- Next required audits by same template:
  - `table_vacancies_list`,
  - `table_companies_list`,
  - `table_leads_workspace`,
  - `table_hr_employees`.
