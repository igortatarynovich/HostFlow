# Platform Extraction — Kit Gate

**Status:** **PASS_WITH_CONSTRAINTS** (2026-08-13)  
**Decision ID:** `PLATFORM_EXTRACTION_KIT_GATE_PASS_WITH_CONSTRAINTS`  
**Type:** L2 operating gate (not an L0 P-rule; does not amend L0)  
**Parents:** [Platform Extraction](../architecture/platform-extraction-phase.md) · [Core Platform Kit](../tasks/ui-platform-composition-epic.md) · [Platform Inventory](../platform/platform-inventory.md) · [Sequential queue](../tasks/sales-to-comms-sequential-queue.md)  
**Runtime branch:** `feat/adr-035-module-pipeline-canon` (K1 `dd1ff6b4` · K2 `a1f391be` · K3 `6df2f2ff`)

> Check that a **new module can assemble a screen from the Core Platform Kit**  
> without writing its own list, workspace chrome, analytics, action bar, or filters.  
> This is **not** Phase D Universal Entity Workspace, **not** ADR-045 templates,  
> and **not** a rewrite of Candidates / Recruitment / HR workspaces.

---

## Formal decision

| Field | Value |
|-------|-------|
| **Outcome** | `PASS_WITH_CONSTRAINTS` |
| **Date** | 2026-08-13 |
| **Result** | Core Platform Kit public APIs exist. This gate closes **Platform Baseline v1**. Phase B may start **only as a consumer** of the kit |
| **Platform Baseline** | **v1** — `DataTable` · `ListWorkspace` · `EntityWorkspace` · Analytics families (`components/analytics`) |
| **Inventory** | [platform-inventory.md](../platform/platform-inventory.md) — living kit catalog |
| **Next Product Track** | Stage 3 slice 4 ([#238](https://github.com/igortatarynovich/HostFlow/pull/238)); consume Baseline v1 on touch. Meta [#222](https://github.com/igortatarynovich/HostFlow/pull/222) ✅ · slice 3 [#224](https://github.com/igortatarynovich/HostFlow/pull/224) ✅ |
| **Not outcome** | Clean `PASS` (remaining lists/dashboards migrate-on-touch; enforcement is PR checklist, not an AST scanner) · `STOP` (completion bar holds in runtime) |

**Rationale:** K1 `DataTable`, K2 `ListWorkspace` (Vacancies cutover), K3 `EntityWorkspace` Shell, and ADR-046 families in `components/analytics` are **Platform Baseline v1** — the legal imports for **new** screens. Existing Candidates list, other operational tables, and non-reference dashboards stay migrate-on-touch (Optimization). Candidate/HR/Vacancy/Recruitment Workspace were **not** extracted (two-consumer rule).

**Platform Baseline v1** is a **capability version**, not a sibling `*_V1` UI canon (does not reopen `TABLE_V1` / `FOUNDATION_V1`). A later module can require Baseline v1 (or v2 when a second consumer forces a new family). K1–K3 are the commits that produced v1; product docs should name the baseline, not the slice letters.

---

## Completion bar (evidence)

| Block | Kit API | Evidence |
|-------|---------|----------|
| List | `ListWorkspace` + `DataTable` | `hostflow-frontend/src/components/ui/{DataTable,ListWorkspace}.tsx`; Vacancies first cutover; `layout/DataTable` re-exports; `DataTableEngine` is an adapter |
| Workspace chrome | `EntityWorkspace` | `hostflow-frontend/src/components/ui/EntityWorkspace.tsx`; passport `EntityWorkspaceShell` adapts onto the kit |
| Analytics | ADR-046 families | `hostflow-frontend/src/components/analytics/` barrel (`KpiCard`, charts, `AnalyticsSection` density, `AnalyticsFilterBar`, story/report chrome). `ChartFrame` remains **implementation** inside family charts |
| Layout | kit shells / existing page inset | No ADR-045 this gate |
| Action bar | `BulkActionBar` / entity `actionBar` slot | ListWorkspace K2; EntityWorkspace optional slot |
| Filters | ListWorkspace filter zone / `AnalyticsFilterBar` | K2 + analytics kit |

Tests: `components/ui/__tests__/{dataTable,listWorkspace,entityWorkspace}.test.tsx` · `platform/entity-workspace/EntityWorkspaceShell.test.tsx`.

---

## Hard rules still in force

After this gate, every product PR:

1. **Kit Gate is law** — no new screen if a required block is missing from the kit; no local stand-in.  
2. **Two-consumer extract only** — do not lift Recruitment / HR / Vacancy / Candidate Workspace into the kit.  
3. **No second Extraction phase** — further families are small PRs when a second module needs them.  
4. **No local UI** when the kit already has the equivalent (table engine, KPI tile, entity header, filter bar, action bar).  
5. **No docs-only ADR** when Vocabulary Canon already has the rule.

Review: [architecture-review-checklist.md](../architecture/architecture-review-checklist.md) L2 Kit Gate · [`.github/pull_request_template.md`](../../../.github/pull_request_template.md).

---

## Constraints (not silent bypasses)

| ID | Constraint | Owner | Disposition |
|----|------------|-------|-------------|
| **KG-C1** | Vacancies is the only list cutover. Candidates (capability bar) and remaining operational lists stay on current chrome until migrate-on-touch | Frontend platform | **Accepted** — Optimization; gate blocks **new forks**, not a Candidates rewrite |
| **KG-C2** | Non-reference efficiency dashboards still have local KPI/chart chrome | Frontend platform | **Accepted** — ADR-046 migrate-on-touch |
| **KG-C3** | No new CI AST scanner for product-page `<table>` / KPI clones. Enforcement is PR template + L2 checklist | Frontend platform | **Accepted** — lower-only ratchet may land in Optimization; baseline tables would fail a naive ban |
| **KG-C4** | `ChartFrame` / Recharts stay implementation inside analytics family IDs (not a product import) | Frontend platform | **Accepted** — matches [`ui-analytics-canon.md`](../platform/ui-analytics-canon.md) §9 |
| **KG-C5** | Events runtime (ADR-019 3A-1) and ADR-045 page templates are **out of this gate** | Architecture | **Queued** — consumer-driven; not kit-gate blockers |

---

## What Phase B must do

New Stage 3 / Meta **product** screens compose **Platform Baseline v1**. Legal imports: [Platform Inventory](../platform/platform-inventory.md). They do not invent a fifth card shell, a sixth operational table, or a module-only KPI tile.

Existing Candidate card / list remain migrate-on-touch.

---

## History

- 2026-08-13: **PASS_WITH_CONSTRAINTS**. Names **Platform Baseline v1**. Inventory: [platform-inventory.md](../platform/platform-inventory.md). Product Track → Meta as consumer.
