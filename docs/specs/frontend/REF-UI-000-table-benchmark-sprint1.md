# REF-UI-000 — Table Benchmark Sprint 1

Goal: determine whether `table_candidates_main_v7` is the best table baseline in HostFlow.

Scoring model:

- Operator Efficiency: 40%
- Information Density: 30%
- Consistency: 20%
- Extensibility: 10%

## Results

| Table | Operator Efficiency (40%) | Information Density (30%) | Consistency (20%) | Extensibility (10%) | Total Score | Benchmark Delta vs Candidates |
|---|---:|---:|---:|---:|---:|---:|
| table_candidates_main_v7 | 94 | 91 | 92 | 90 | **92** | 0 |
| table_vacancies_main | 86 | 88 | 90 | 87 | **88** | -4 |
| table_leads_main | 82 | 84 | 82 | 80 | **82** | -10 |
| table_employees_main | 79 | 83 | 80 | 81 | **81** | -11 |
| table_companies_main | 68 | 80 | 74 | 70 | **74** | -18 |

## Decision (Sprint 1)

- Provisional best candidate: `table_candidates_main_v7`.
- Canonical decision mode: **Adapt**, not direct **Adopt**.
- Current recommendation: `TABLE_V1 = candidates-based frame + targeted fixes` after delta backlog capture.

## Required next step before TABLE_V1 lock

- ~~Convert score deltas into adaptation backlog (top 5-10 issues).~~ ✅ `TABLE_V1_ADAPTATION_BACKLOG.md`
- Validate scores with manual UI walkthrough and representative user flows.
- Governance triage of backlog items A1–A5.
- Keep final `TABLE_V1` lock blocked until backlog triage is approved.

## Priority Shift

Sprint 1 produced sufficient evidence to proceed.
Layer 3 current stream: **TABLE_V1** (adaptation backlog → governance → lock).
Entity layout (`REF-UI-000-entity-benchmark-sprint2.md`) remains parallel track for Layer 4.
