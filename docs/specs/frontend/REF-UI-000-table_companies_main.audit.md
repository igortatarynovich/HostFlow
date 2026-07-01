# REF-UI-000 — table_companies_main Comparative Audit

Component ID: `table_companies_main` (`table_companies_list`)  
Page: `/app/clients/directory`  
Benchmark: `table_candidates_main_v7`

## Weighted Score

- Operator Efficiency (40%): 68
- Information Density (30%): 80
- Consistency (20%): 74
- Extensibility (10%): 70
- Total: **74**
- Benchmark delta vs candidates (92): **-18**

## Strengths

- High business data density (commercial + recruitment metrics in one row).
- Rich filter set for ownership/stage/role and client segmentation.
- Useful cross-links to vacancies and candidates.

## Weaknesses

- No bulk action workflow in list table.
- Sorting/filter mechanics are simpler and less standardized than candidates.
- Coupling with mixed list/detail page complexity reduces reusable table contract clarity.

## Delta vs Candidates Table

- Better: commercial KPI columns for account management context.
- Worse: lower operator throughput for mass operations.
- Net: requires adaptation before any TABLE_V1 alignment.

