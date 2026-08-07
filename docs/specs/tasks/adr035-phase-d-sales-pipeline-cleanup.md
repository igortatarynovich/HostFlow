# ADR-035 Phase D — Sales pipeline ownership (implementation note)

**Status:** implementation context (L3) under Accepted [ADR-035](../architecture/ADR-035-module-object-pipeline-settings.md) + [ADR-023](../architecture/ADR-023-recruitment-sales-module-separation.md).

## Rule

Sales **never** operates on `Candidate`.

```text
SalesInquiry → Opportunity → Client
```

Recruitment may later create Candidates against that **Client** demand — a separate process and object.

## What this slice does

- Marks legacy `Service Sales Pipeline` under `module_key=recruitment` / `type=lead` as **legacy** in [`funnel_presets.py`](../../../backend/app/modules/companies/funnel_presets.py) (`legacy_sales_under_recruitment: true`).
- Product UI for Sales pipelines must live under the Sales host; do not add new recruitment lead funnels named as Sales.
- System transitions for Sales catalog source are `close_*` and client conversion — not Candidate handoffs.

## Forbidden

- Moving a Candidate from a Sales screen.
- Encoding Sales Inquiry stages as `Candidate.stage`.
- Creating company “Sales” funnels with `module_key=recruitment` for new tenants (strangler only for existing rows).
