# TABLE_V1_DRAFT

Status: **Superseded** by `TABLE_V1.md` (locked 2026-05-31)  
Date: 2026-05-29  
Source benchmark: `table_candidates_main_v7` (`/app/candidates`)  
Decision mode: `Adapt` (not direct `Adopt`)

## Purpose

Define one canonical table standard for all HostFlow operational entity lists.

Applies to:

- candidates,
- vacancies,
- companies,
- employees,
- leads,
- other entity-list modules that use operational tables.

## Canonical Table Contract

## 1) Visual and Density Baseline

1. Base typography: `text-sm` (14px).
2. Header height: `44px` baseline (`h-11` equivalent).
3. Cell vertical padding baseline: `py-2.5`.
4. Cell horizontal padding baseline:
- standard cells: `px-4`,
- compact operational cells: `px-3`.
5. Sticky header is mandatory.
6. Density target: operational compact mode, with no decorative spacing inflation.

## 2) Interaction Baseline

1. Sorting: mandatory at column level for sortable data columns.
2. Filtering:
- global filter/search bar above table,
- column-level filters supported for relevant columns.
3. Search: mandatory and always visible in table filter bar.
4. Bulk actions:
- shown only when selection is non-empty,
- located in canonical bulk action area,
- role-aware visibility.
5. Row actions: allowed in canonical row action slot; must not break row scanability.
6. Status badges: use canonical status badge style and semantic mapping.

## 3) Structure Baseline

1. Selection checkbox column is mandatory for bulk-capable tables.
2. Loading/empty/error states must follow a single shared pattern.
3. Pagination contract is mandatory:
- either visible pagination control, or approved fixed-limit model with documented reason.
4. Column model:
- default canonical order,
- optional user customization (order/width) only through approved table capabilities.

## 4) Placement Rules

1. Filters/search are always above table.
2. Bulk actions appear in canonical top action zone when rows are selected.
3. Sort controls are in headers only.
4. Table-specific actions must stay inside row action area or bulk action area (no ad-hoc placements).

## Forbidden (Hard Rules)

1. Tables without sorting for sortable columns.
2. Module-unique custom filter UI that bypasses canonical filter bar.
3. One-off row action layouts unique to one module without governance approval.
4. New visual table styles outside TABLE_V1 contract.
5. Arbitrary spacing/typography values that violate canonical baseline.
6. Hidden or inconsistent bulk action placement.
7. Non-sticky operational headers in desktop workspace tables.

## Adaptation Notes From Benchmark

Before final lock, TABLE_V1 must include:

1. Domain-agnostic frame extraction from candidates table — see `TABLE_V1_ADAPTATION_BACKLOG.md` **A1**.
2. Explicit pagination policy (and exception policy) — **A2**, **A8**.
3. Minimal column visibility rules for smaller desktop widths — **A6**.
4. Clear separation between mandatory and optional advanced features — **A6**, §5 Frame vs Domain.

Adaptation backlog: `TABLE_V1_ADAPTATION_BACKLOG.md` (governance triage pending).

## Compliance Policy

1. New tables must declare TABLE_V1 compliance in spec/review.
2. Non-compliant legacy tables are tagged `Legacy` with migration plan.
3. Any exception requires governance decision in `REF-UI-*`.

## Output of Tables Phase

Tables phase is complete when:

1. `TABLE_V1_DRAFT` is approved,
2. table modules are mapped to `Canonical / Legacy / Deprecated`,
3. deviation backlog is created per module.
