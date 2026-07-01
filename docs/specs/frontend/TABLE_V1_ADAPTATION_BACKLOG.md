# TABLE_V1_ADAPTATION_BACKLOG

Status: Complete (governance triage approved 2026-05-31)  
Date: 2026-05-31  
Input: `REF-UI-000-table-benchmark-sprint1.md`, per-table audits, `TABLE_V1_DRAFT.md`, `FOUNDATION_V1.md`, `PRIMITIVES_V1.md`  
Purpose: convert benchmark score deltas into **actionable adaptation items** required before `TABLE_V1` lock.

## Question Answered

> Какие targeted fixes и module mappings обязательны перед lock `TABLE_V1`?

Sprint 1 decision stands: **Adapt** candidates frame — not direct Adopt. **Triage approved** — see `TABLE_V1.md` §9.

---

## 1) Benchmark Summary (Sprint 1 — no rescan)

| Table ID | Page | Total | Δ vs candidates (92) |
|---|---|---:|---:|
| `table_candidates_main_v7` | `/app/candidates` | **92** | 0 |
| `table_vacancies_main` | `/app/vacancies` | **88** | -4 |
| `table_leads_main` | `/app/leads` | **82** | -10 |
| `table_employees_main` | `/app/hr/employees` | **81** | -11 |
| `table_companies_main` | `/app/clients/directory` | **74** | -18 |

Baseline frame source: **`table_candidates_main_v7`**.

---

## 2) Module Classification (TABLE_V1)

| Module | Table ID | Decision | Rationale |
|---|---|---|---|
| Candidates | `table_candidates_main_v7` | **Candidate (frame source)** | Highest score; defines Adapt base |
| Vacancies | `table_vacancies_main` | **Legacy / Adapt** | -4; strong reuse, add row-action parity |
| Leads | `table_leads_main` | **Legacy / Adapt** | -10; dual-mode complexity |
| Employees | `table_employees_main` | **Legacy / Adapt** | -11; HR domain, no bulk framework |
| Companies | `table_companies_main` | **Legacy / Adapt** | -18; KPI-rich but lowest operator throughput |
| HR tasks/docs tables | `table` CSS, partial patterns | **Legacy** | Migrate on touch |
| Admin bespoke tables | inline `<th>` styles | **Legacy / Adapt** | Migrate on touch |
| New entity list tables | — | **Must comply** with `TABLE_V1` after lock |

### Deprecated (forbidden in new tables post-lock)

From `TABLE_V1_DRAFT` + benchmark evidence:

1. Sortable columns without sort controls in header.
2. Filter/search UI that bypasses canonical filter bar placement (above table).
3. Bulk-capable tables without selection column + canonical bulk zone.
4. Non-sticky header on desktop operational workspace tables.
5. One-off table typography/spacing outside TABLE_V1 density contract.
6. Module-unique row action layout without governance exception.
7. Hidden or inconsistent bulk action placement.

---

## 3) Adaptation Backlog (Top 10 — Domain-Agnostic Frame)

Items apply to **TABLE_V1 canon**, not product features. Ordered by lock dependency.

| # | Item | Source | Priority | Blocks lock? |
|---|---|---|---|---|
| **A1** | **Extract domain-agnostic table frame contract** from candidates: sticky header, selection column, sortable header slot, bulk action zone, loading/empty/error | candidates audit §5.2 | **P0** | ✅ Yes |
| **A2** | **Pagination policy** — document allowed models: (a) explicit pager, (b) fixed batch limit with documented cap, (c) infinite scroll forbidden without governance | candidates gap + vacancies strength | **P0** | ✅ Yes |
| **A3** | **Filter bar placement** — search + filters always above table; column filters in header only | TABLE_V1_DRAFT §4 | **P0** | ✅ Yes |
| **A4** | **Density contract** — lock `text-sm`, header `h-11`, cell `py-2.5`, `px-4` / compact `px-3` | candidates audit §2 | **P0** | ✅ Yes |
| **A5** | **Bulk action contract** — visible iff selection non-empty; role-aware; canonical top zone | candidates audit §1.5 | **P0** | ✅ Yes |
| **A6** | **Optional vs mandatory features** — column DnD/resize, saved layouts, work-panel = optional advanced tier | candidates audit §5.2 | **P1** | No |
| **A7** | **Row inline actions** — optional per domain; TABLE_V1 must not require candidate-style name-cell actions on all entities | leads/employees delta | **P1** | No |
| **A8** | **Pagination parity** — vacancies/leads explicit pager documented as allowed pattern; candidates batch-200 documented as allowed with cap disclosure | sprint1 deltas | **P1** | No |
| **A9** | **CSS alignment** — operational tables use `.table` from `components.css` or TABLE_V1 equivalent tokens | code scan (~11 explicit `.table` uses + candidates native table) | **P1** | No |
| **A10** | **Status badges in cells** — use `STATUS_BADGE_V1` / `StageTag` adapters, not ad-hoc pills | PRIMITIVES_V1 | **P1** | No |

---

## 4) Per-Module Adaptation Notes

### Vacancies (-4)

| Adapt | Detail |
|---|---|
| Keep | Explicit pagination controls |
| Add | Row-level operator actions parity where business-critical |
| Align | Header stickiness, filter bar placement, bulk zone layout |

### Leads (-10)

| Adapt | Detail |
|---|---|
| Keep | Bulk updates, footer pagination, mode switch (outside TABLE_V1) |
| Reduce | Conditional table behaviors that break predictability |
| Align | Header/cell interaction patterns to candidates frame |

### Employees (-11)

| Adapt | Detail |
|---|---|
| Keep | HR compliance column density |
| Add | Bulk framework **or** documented exception (HR may be single-row ops) |
| Align | Pagination contract visibility; filter bar standard |

### Companies (-18)

| Adapt | Detail |
|---|---|
| Keep | Commercial KPI columns (domain-specific) |
| Add | Bulk workflow **or** documented exception for account-management model |
| Align | Sort/filter mechanics to TABLE_V1 header contract |

---

## 5) Frame vs Domain Boundary (Locked for Draft)

`TABLE_V1` specifies **frame only**:

| In frame (mandatory) | Domain (optional / module-specific) |
|---|---|
| Sticky header, density, selection column | Column definitions |
| Filter bar placement | Filter types |
| Bulk action zone existence | Which bulk ops |
| Sort in header | Sort keys |
| Empty/loading/error pattern | Cell content, inline actions |
| Pagination policy choice | Page size defaults |

Do **not** force candidates inline Call/Email/Tasks on vacancies/companies/leads.

---

## 6) Manual Validation Gate

Sprint 1 required manual walkthrough before lock.

| Check | Status |
|---|---|
| Visible row count on 1080p (candidates) | ⬜ Pending manual measure |
| Sort/filter/bulk happy path | ⬜ Pending UX walkthrough |
| Cross-table visual consistency spot-check | ⬜ Pending |

**Lock may proceed** with backlog governance approval; manual validation can run in parallel but must complete before first migration sprint.

---

## 7) Migration Order (Post-Lock)

| Phase | Target | Effort |
|---|---|---|
| **M0** | Document frame in `TABLE_V1.md` (no code extraction required at lock) | Low |
| **M1** | Vacancies — closest delta (-4) | Medium |
| **M2** | Leads table mode (-10) | Medium |
| **M3** | Employees (-11) | Medium |
| **M4** | Companies (-18) | High |

Candidates table: **reference implementation** — refactor only when extracting shared frame utilities.

---

## 8) Chain Status (Layer 3 — Tables)

| Artifact | Status |
|---|---|
| Per-table audits (5) | ✅ |
| `REF-UI-000-table-benchmark-sprint1.md` | ✅ |
| `TABLE_V1_DRAFT.md` | ✅ Draft |
| **`TABLE_V1_ADAPTATION_BACKLOG.md`** | ✅ This document |
| Governance triage of backlog | ✅ 2026-05-31 |
| Manual validation gate | ⬜ Before M1 — see checklist |
| `TABLE_V1.md` lock | ✅ |
| `TABLE_V1_ENFORCEMENT` | ✅ |

---

## 9) Next Steps

1. ~~Governance triage — approve/adjust items A1–A5~~ ✅
2. ~~Update draft → `TABLE_V1.md` lock~~ ✅
3. Complete `TABLE_V1_MANUAL_VALIDATION_CHECKLIST.md` before M1.
4. First migration: vacancies (M1).

Other Layer 3 composites (`FILTER_BAR_V1`, `MODAL_V1`, …) start **after** TABLE_V1 lock or in parallel only if they do not redefine table frame.
