# REF-UI-000 — table_vacancies_main Comparative Audit

Component ID: `table_vacancies_main` (`table_vacancies_list`)  
Page: `/app/vacancies`  
Benchmark: `table_candidates_main_v7`

## Weighted Score

- Operator Efficiency (40%): 86
- Information Density (30%): 88
- Consistency (20%): 90
- Extensibility (10%): 87
- Total: **88**
- Benchmark delta vs candidates (92): **-4**

## Strengths

- Clear list table with bulk actions, sorting, filters, saved views.
- Strong consistency with candidates visual language (table, badges, actions row).
- Explicit pagination controls reduce ambiguity for large datasets.

## Weaknesses

- Fewer inline row actions than candidates table (lower in-row execution speed).
- Less advanced filter depth compared to candidates operational filter model.
- No evidence of equivalent column DnD/resize behavior.

## Delta vs Candidates Table

- Better: explicit prev/next pagination controls.
- Worse: operator speed for communication/task actions from row.
- Net: strong candidate for reuse, but below candidates baseline.

