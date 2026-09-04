# Compliance obligations ops (open-queue projection)

**Status:** NORMATIVE (L2 — workflow / operating canon)  
**Date:** 2026-09-04  
**Owner:** Leads module consumes; Communication capability owns delivery  
**Parents:** [lead-lifecycle-email-policy.md](lead-lifecycle-email-policy.md) · [ADR-033](../architecture/ADR-033-lead-lifecycle-email-company-policy.md) · [lead-intake-resolution-and-activity-continuity.md](lead-intake-resolution-and-activity-continuity.md) §8.0.1

> Operational projection of **open** RODO information obligations.  
> Not a second state-machine. Does not change the six `compliance_state` values or the transition table.

---

## Freeze

| Must not change | Detail |
|-----------------|--------|
| Product invariant | Tenant configures **how** RODO is fulfilled; cannot disable fulfillment. HostFlow supplies the platform default when tenant config is absent. |
| Six states | `compliant` / `delivery_required` / `delivered` / `exempt` / `review_required` / `delivery_failed` |
| Transitions | Same table as [lead-lifecycle-email-policy.md](lead-lifecycle-email-policy.md) §4. No mark-resolved. |
| Silent close | Forbidden. Closed states still require their proof. |

This layer **sees** only `delivery_required`, `review_required`, `delivery_failed`. It does not write `compliant` / `delivered` / `exempt` itself and does not let a tenant turn execution off.

---

## What the layer does

| Slice | Does | Does not |
|-------|------|----------|
| Queue | Filter / count by open `compliance_state` + aging | Write closed states |
| Retry | Re-send on the allowed edge `delivery_failed` → `delivered` (also `delivery_required` send) | Retry `review_required` blindly; overwrite `delivery_failed` when send still fails |
| Escalation | In-app alert after tenant SMTP then platform SMTP are exhausted | Treat webhook / notify as fulfillment |
| SLA / aging | Clock from `evaluated_at` / last attempt (art.13: at collection; art.14: one month or first contact) | Change `article` or lift the gate |
| Operator | Send / covered-at-source / exempt — existing transitions with proof | Mark resolved |
| Observability | Queue, attempts, last failure, aging, audit | New `compliance_state` |

---

## SLA

- **Art.13** (`direct`): due at `evaluated_at` (notice at collection).
- **Art.14** (`indirect`): due at `evaluated_at + 30 days`, or at first CRM contact (`contacted` / `qualified` / `converted`) if that happens sooner.
- **Unknown article / `review_required`:** due at `evaluated_at` (operator must act now).
- Aging hours use last delivery attempt when present, else `evaluated_at`.
- Breach is a queue flag. It does not close the obligation and does not bypass Process / contacted gates.

---

## Retry vs operator Send

| Path | Allowed from |
|------|----------------|
| `POST /api/v1/leads/{id}/compliance/rodo/retry` and bulk retry | `delivery_failed`, `delivery_required` only |
| `POST /api/v1/leads/{id}/compliance/rodo/send` | Operator Send, including `review_required` → `delivered` with SMTP proof |
| `POST /api/v1/leads/{id}/compliance/rodo/source-provided` | Assessment proof (notice at source or operator attestation) |
| `POST /api/v1/leads/{id}/compliance/rodo/exempt` | Lawful `exemption_code` + actor |

Bulk default is canonical `delivery_failed`. Legacy `failed` / `pending_channel` / `pending_policy` / `deferred` / `undelivered` map to that open state. `review_required` as a retry filter is rejected.

---

## Escalation

After a failed send whose `delivery_evidence.attempts` show SMTP paths tried and none succeeded (or `gdpr_notice_delivery_exhausted`), the ops layer:

1. Leaves `compliance_state = delivery_failed`.
2. Stamps `normalized.rodo.ops.escalated_at` (observability only).
3. Emits audit `rodo_delivery_escalated` and in-app `lead_rodo_delivery_escalated` to tenant administrators.

Webhook success is not escalation relief and is not GDPR proof.

---

## API

- `GET /api/v1/leads/compliance/rodo/queue` — open items, counts, SLA / escalation flags.
- `POST /api/v1/leads/{id}/compliance/rodo/retry`
- `POST /api/v1/leads/{id}/compliance/rodo/exempt`
- Existing Send / source-provided / `POST /api/v1/leads/bulk/compliance/rodo/retry`

UI: Leads workspace chip / queue link `?compliance_open=1` (`LeadRodoObligationsQueue`). Intake rail Send + covered-at-source stay on the lead card.

---

## Tests

`backend/tests/services/test_lead_rodo_ops.py`, `backend/tests/services/test_lead_rodo_bulk_retry.py`. Bound-path send: `backend/tests/api/test_lead_rodo_bound_retry.py` (SalesInquiry) and `backend/tests/api/test_lead_rodo_recruitment_bound_retry.py` (Application / vacancy).
