# REF-UI-000 — table_leads_main Comparative Audit

Component ID: `table_leads_main` (`table_leads_workspace`)  
Page: `/app/leads` (table mode)  
Benchmark: `table_candidates_main_v7`

## Weighted Score

- Operator Efficiency (40%): 82
- Information Density (30%): 84
- Consistency (20%): 82
- Extensibility (10%): 80
- Total: **82**
- Benchmark delta vs candidates (92): **-10**

## Strengths

- Strong operational feature set: bulk updates, advanced filters, table/kanban switch.
- Explicit pagination and selection model.
- Rich action cells for routing/process workflows.

## Weaknesses

- Higher complexity from dual-mode behavior (recruitment/services variants).
- Table behavior diverges by tenant/context, reducing predictability.
- Consistency gaps vs candidates table header/cell interaction patterns.

## Delta vs Candidates Table

- Better: explicit mode switching and footer pagination.
- Worse: consistency and cognitive load due to conditional behaviors.
- Net: good operational table, but not best benchmark candidate.

