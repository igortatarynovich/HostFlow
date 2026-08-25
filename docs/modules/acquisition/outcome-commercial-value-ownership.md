# Outcome Commercial Value — Ownership Card

Status: accepted  
Date: 2026-08-03

## Domain

Name: `Acquisition Outcome Commercial Value`  
Owner: **Sales** declares commercial value facts; **Acquisition** owns ROI compose (Stage 6)

## Source of truth

- **V1 (`declared_v1`):** delivery snapshot on completed `CampaignOutcome`
  (`commercial_value_amount`, `commercial_value_currency`, `commercial_value_source`,
  `commercial_value_set_at`)
- Written **only** via
  `backend/app/acquisition/contracts/outcome_commercial_value.py`
- Not inventable inside analytics compose; not auto-joined from `SalesOrder`
  (inquiry→order path does not exist yet)

## Consumers

1. Stage 6 ROI read compose (KPI / flight-compare / cohorts / portfolio) — PR-6b
2. Marketing UI declaration of value on completed Outcomes

## Delivery contract

Path: `backend/app/acquisition/contracts/outcome_commercial_value.py`

- DTO: `OutcomeCommercialValueRead`
- Writers: `set_outcome_commercial_value`
- Readers: `get_outcome_commercial_value`, `list_outcome_commercial_values`

HTTP: `PUT|GET /api/v1/platform/campaigns/{campaign_id}/outcomes/{outcome_id}/commercial-value`

## Versioning strategy

| Version | Meaning |
|---------|---------|
| `declared_v1` | Operator/Sales-declared amount + ISO currency on Outcome |
| `sales_order_v2` *(later)* | Opaque link to Sales commercial objects via contract — no Acquisition FK |

## Override policy

None. Replacing a value overwrites the snapshot through the same contract (same source code unless version bump).

## Explicit non-ownership

Acquisition does **not** own:

1. SalesOrder / invoice / billable amount SoT
2. Recruitment hire commercial valuation
3. A second KPI / metrics ledger table
4. Runtime pause/launch from ROI

## Critical invariants

1. Only completed Outcomes may carry commercial value
2. Amount must be `> 0`; currency is ISO-4217 alpha-3 (same normalization as Flight spend)
3. Analytics must not invent amounts when snapshot is null → ROI stays null
4. Mixed value currencies within a Flight/Campaign raise the same class of error as mixed spend

## Enforcement

1. Contract module is the only writer of `commercial_value_*` columns
2. API tests: non-completed → 422; bad currency / non-positive → 422; company scope
3. Threat model: [`docs/security/threat-models/acquisition-stage-6-analytics.md`](../../security/threat-models/acquisition-stage-6-analytics.md)

## Current boundary state

1. PR-6a+PR-6b shipped: ownership + contract + write/read HTTP + ROI compose/UI
2. Stage 6 Analytics sealed as DONE; `sales_order_v2` remains backlog
