# TABLE_V1

**Parent composition / list pattern:** [`ADR-043`](../architecture/ADR-043-ui-component-composition-canon.md) · [`ADR-044`](../architecture/ADR-044-list-workspace-data-presentation-canon.md) (`ListWorkspace` + `DataTable`). TABLE_V1 remains the **visual/behavior child** (Candidates frame). Public `DataTable` runtime is K1 (`components/ui/DataTable`); ListWorkspace is K2.

Status: **Locked**  
Draft date: 2026-05-29  
Locked date: 2026-05-31  
Governance: Approved (REF-UI-000 Layer 3 — Tables)  
Input: `REF-UI-000-table-benchmark-sprint1.md`, `TABLE_V1_ADAPTATION_BACKLOG.md`, `FOUNDATION_V1.md`, `PRIMITIVES_V1.md`  
Supersedes: `TABLE_V1_DRAFT.md`  
Decision mode: **Adapt** (candidates-based frame + targeted fixes — not direct Adopt)

## Question Answered

> Какой единый стандарт operational entity-list tables в HostFlow?

Reference implementation: `table_candidates_main_v7` (`/app/candidates`). Enforced via PR review and migrate-on-touch. Public runtime: `hostflow-frontend/src/components/ui/DataTable` (Platform Extraction K1). Candidates page is the capability bar and is not cut over in K1.

---

## Lock Readiness (Verified)

| Gate | Requirement | Status |
|---|---|---|
| Sprint 1 benchmark | Baseline selected | ✅ candidates (92) |
| Per-table audits | 5 P0 tables | ✅ |
| Adaptation backlog | A1–A5 triaged | ✅ Approved 2026-05-31 |
| Pagination policy | Documented | ✅ §3 |
| Mandatory vs optional | Split documented | ✅ §4 |
| Module classification | Canonical / Legacy | ✅ §8 |
| Manual validation | Checklist | ✅ Parallel — before M1 migration |
| Foundation + primitives | Badges, inputs in cells | ✅ PRIMITIVES_V1 |

---

## Governance

| Rule | Detail |
|---|---|
| Authority | `REF-UI-*` only |
| New operational list tables | Must comply with this spec |
| Legacy tables | Migrate on touch per backlog order |
| Exceptions | Documented in `REF-UI-*` (bulk-off, pagination model) |
| Frame vs domain | TABLE_V1 = frame only; column content is domain |
| Changes | Explicit governance decision |

---

## 1) Scope

Applies to operational **entity list tables**:

- candidates, vacancies, companies, employees, leads,
- HR operational lists (adapt on touch),
- future entity-list modules.

Out of scope: kanban boards, detail-page subtables, admin diagnostic tables (legacy until touched).

---

## 2) Visual and Density (Mandatory)

| Token | Value |
|---|---|
| Typography | `text-sm` (`FOUNDATION_V1` body-sm) |
| Header height | `h-11` (44px) |
| Cell padding vertical | `py-2.5` |
| Cell padding horizontal | `px-4` standard; `px-3` compact operational columns |
| Header | **Sticky** on desktop workspace tables |
| Row separation | `border-t border-slate-200/90` or `.table` equivalent |
| CSS | Prefer `.table` from `components.css` where applicable |

---

## 3) Pagination Policy (Mandatory Declaration)

Every TABLE_V1 table must declare **one** approved model:

| Model | Description | Example |
|---|---|---|
| **A — Explicit pager** | Prev/next or page control visible | vacancies, leads |
| **B — Fixed batch limit** | Load cap with documented limit; operator informed | candidates (limit 200) |
| **C — Infinite scroll** | **Deprecated** without governance |

Rules:

- Model must be documented in module spec or UI copy when using batch limit.
- Switching models on migration requires no regression in operator clarity.

---

## 4) Mandatory vs Optional Features

### Mandatory (frame)

| Feature | Rule |
|---|---|
| Sticky header | Desktop operational tables |
| Filter/search bar | **Above** table — always |
| Column sort | Sort controls in header for sortable columns |
| Selection column | Required for **bulk-capable** tables |
| Bulk action zone | Visible iff selection non-empty; top canonical zone |
| Loading / empty / error | Shared pattern per module family |
| Pagination | Declared model (§3) |
| Status in cells | `STATUS_BADGE_V1` / adapters — not ad-hoc pills |

### Optional (advanced tier)

| Feature | Notes |
|---|---|
| Column drag reorder | candidates-style customization |
| Column resize | persisted layout |
| Saved views / layout persistence | candidates, vacancies |
| Inline row actions | domain-specific (e.g. Call/Email) — **not required** on all entities |
| Work-panel integration | candidates-specific |

**Locked:** Do not require candidates name-cell inline actions on vacancies, companies, leads, employees.

---

## 5) Placement Rules

1. Filters and search **above** table.
2. Bulk actions in top action zone when rows selected.
3. Sort controls in headers only (not floating toolbars).
4. Row actions in row action slot or bulk zone — no ad-hoc placements.

---

## 6) Bulk Actions — Exceptions

Default: bulk-capable operational tables have selection + bulk zone.

| Module | Exception | Reason |
|---|---|---|
| HR employees | Bulk optional — document if omitted | Single-row HR ops dominant |
| Companies | Bulk optional — document if omitted | Account-management KPI model |

New tables without bulk require **REF-UI exception** note in spec.

---

## 7) Allowed vs Legacy vs Deprecated

### Allowed (new code)

- TABLE_V1 density + placement rules
- `.table` CSS or equivalent tokens
- Domain-specific columns and cell content
- Approved pagination model A or B

### Legacy (migrate on touch — see backlog order)

| Module | Table ID | Priority |
|---|---|---|
| Vacancies | `table_vacancies_main` | **M1** |
| Leads | `table_leads_main` | M2 |
| Employees | `table_employees_main` | M3 |
| Companies | `table_companies_main` | M4 |
| HR/admin bespoke tables | various | on touch |

Candidates: **reference** — refactor when extracting shared utilities.

### Deprecated (forbidden in new tables)

1. Sortable columns without header sort controls.
2. Filters bypassing top filter bar placement.
3. Bulk-capable table without selection + bulk zone (unless governed exception).
4. Non-sticky header on desktop operational workspace.
5. Typography/spacing outside §2 contract.
6. Module-unique row action layout without governance.
7. Hidden/inconsistent bulk placement.
8. Infinite scroll (model C) without governance.
9. Ad-hoc status pills in cells (use `STATUS_BADGE_V1`).

---

## 8) Module Classification (Locked)

| Module | Score | Decision |
|---|---:|---|
| Candidates | 92 | **Reference (frame source)** |
| Vacancies | 88 | Legacy / Adapt |
| Leads | 82 | Legacy / Adapt |
| Employees | 81 | Legacy / Adapt |
| Companies | 74 | Legacy / Adapt |

---

## 9) Governance Triage Record (A1–A5)

Approved 2026-05-31:

| ID | Decision |
|---|---|
| **A1** | Frame contract locked in this spec (sticky header, selection, sort header, bulk zone, states) |
| **A2** | Pagination policy §3 locked |
| **A3** | Filter bar above table — mandatory |
| **A4** | Density contract §2 locked |
| **A5** | Bulk zone contract §5 + exceptions §6 |

P1 items (A6–A10): migration guidance — do not block lock.

---

## 10) Implementation Status

| Item | Status |
|---|---|
| Spec locked | ✅ |
| Shared `TableFrame` component | ⬜ Not required at lock |
| Vacancies migration (M1) | ⬜ Post-lock |
| Manual validation before M1 | ⬜ See checklist |
| TABLE CI enforcement | ⬜ Phase 2 |

---

## 11) Chain Status

| Artifact | Status |
|---|---|
| Table audits + Sprint 1 | ✅ |
| `TABLE_V1_ADAPTATION_BACKLOG.md` | ✅ Triage complete |
| `TABLE_V1_MANUAL_VALIDATION_CHECKLIST.md` | ✅ |
| `TABLE_V1_DRAFT.md` | Superseded |
| **`TABLE_V1.md`** | ✅ **Locked** |
| `TABLE_V1_ENFORCEMENT_AND_MIGRATION_PLAN.md` | ✅ |

---

## 12) Next Steps

1. Complete manual validation checklist before **M1** (vacancies).
2. Migrate vacancies toward TABLE_V1 frame alignment.
3. Layer 3 next composite: `FILTER_BAR_V1` (must not redefine table frame).
