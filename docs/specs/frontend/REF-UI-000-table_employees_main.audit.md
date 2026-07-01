# REF-UI-000 — table_employees_main Comparative Audit

Component ID: `table_employees_main` (`table_hr_employees`)  
Page: `/app/hr/employees`  
Benchmark: `table_candidates_main_v7`

## Weighted Score

- Operator Efficiency (40%): 79
- Information Density (30%): 83
- Consistency (20%): 80
- Extensibility (10%): 81
- Total: **81**
- Benchmark delta vs candidates (92): **-11**

## Strengths

- Good HR-specific filter bar and status/compliance visibility.
- Dense operational rows for missing/expiring documents and next action.
- Clear detail/handoff navigation from row.

## Weaknesses

- No bulk action framework comparable to candidates table.
- More static column model; less adaptable list interaction pattern.
- Pagination contract not explicit in UI despite backend limit usage.

## Delta vs Candidates Table

- Better: HR compliance signal density for workforce tasks.
- Worse: mass-operation speed and reusable interaction sophistication.
- Net: suitable domain table, below TABLE_V1 candidate baseline.

