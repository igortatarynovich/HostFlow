# A6-S7 Operating Slots E2E Run Record

Date: `2026-03-15`  
Environment: `staging/production-like`  
Owner: `Codex/Product`  
Result: `IN_PROGRESS`  
Blocker (if any): `Manual product/QA click-path run and Stripe-side payment confirmation evidence are pending.`

Manual execution protocol: [a6-s7-manual-evidence-checklist.md](/opt/HostFlow/docs/manual-checklist/a6-s7-manual-evidence-checklist.md)

## Scope
- Validate end-to-end operating company slots flow:
  1. buy/add slot,
  2. create new operating company,
  3. downgrade/remove slot edge case without data loss.

## Step-by-step Checklist

| Step | Expected | Actual | Status (`PASS/FAIL/BLOCKED/IN_PROGRESS`) | Evidence |
|---|---|---|---|---|
| 1 | Billing shows `included + extra = effective` slots correctly. | Runtime implementation present in Billing and My Company pages; manual visual verification pending for target tenant. | `IN_PROGRESS` | Code: `BillingWorkspacePage`, `MyCompanyPage`; pending screenshot/log evidence. |
| 2 | Increase add-on slots from Billing (`- / + / Save`) succeeds. | Automated API coverage passed (`test_operating_company_slots`, `test_billing_operating_slot_sync`) + synthetic smoke flow `add-slot` step `PASS`; manual click-path evidence pending. | `IN_PROGRESS` | `pytest tests/test_operating_company_slots.py tests/api/test_billing_operating_slot_sync.py` (`PASS`, `2026-03-15`), smoke report [a6-s7-operating-slots-smoke-2026-03-15.md](/opt/HostFlow/docs/manual-checklist/a6-s7-operating-slots-smoke-2026-03-15.md). |
| 3 | New operating company can be created when slot is available. | Automated end-to-end scenario passed: first create blocked at limit, succeeds after add-on slot, then remains persisted after downgrade. | `IN_PROGRESS` | `pytest tests/test_operating_company_slots_e2e.py` (`PASS`, `2026-03-15`) + smoke report [a6-s7-operating-slots-smoke-2026-03-15.md](/opt/HostFlow/docs/manual-checklist/a6-s7-operating-slots-smoke-2026-03-15.md); manual UI proof pending. |
| 4 | At limit, creation is blocked with clear upgrade/add-slot CTA (no dead-end). | Automated guardrail/error-mapping coverage passed; manual UX screenshot evidence pending. | `IN_PROGRESS` | `pytest tests/modules/test_companies_error_mapping.py` (`PASS`, `2026-03-15`) + frontend code path (`OnboardingCompanyPage`, `MyCompanyPage`, `friendlyError`). |
| 5 | Stripe webhook sync updates `extra_operating_company_slots` from subscription item quantity. | Automated webhook/invoice sync coverage passed; live Stripe event proof pending. | `IN_PROGRESS` | `pytest tests/api/test_billing_operating_slot_sync.py` (`PASS`, `2026-03-15`), pending production webhook log snippet. |
| 6 | Downgrade/remove add-on slot does not delete companies; only creation of new ones is blocked if over limit. | Automated downgrade edge-case passed: existing operating companies preserved, new create blocked after downgrade below usage. | `IN_PROGRESS` | `pytest tests/test_operating_company_slots_e2e.py` (`PASS`, `2026-03-15`) + smoke report [a6-s7-operating-slots-smoke-2026-03-15.md](/opt/HostFlow/docs/manual-checklist/a6-s7-operating-slots-smoke-2026-03-15.md); manual billing UI proof pending. |

## Required Evidence to Close `A6-S7`
- Automated regression baseline (`2026-03-15`): `10 passed` for slot-flow suite  
  `pytest tests/test_operating_company_slots.py tests/test_operating_company_slots_e2e.py tests/api/test_billing_operating_slot_sync.py tests/modules/test_companies_error_mapping.py -q`
- Synthetic smoke artifact (`2026-03-15`): `PASS`  
  `docker compose exec -T backend python backend/scripts/a6_operating_slots_e2e_smoke.py`  
  [a6-s7-operating-slots-smoke-2026-03-15.md](/opt/HostFlow/docs/manual-checklist/a6-s7-operating-slots-smoke-2026-03-15.md), [a6-s7-operating-slots-smoke-2026-03-15.json](/opt/HostFlow/docs/manual-checklist/a6-s7-operating-slots-smoke-2026-03-15.json)
- Billing UI screenshots before/after slot change.
- API evidence for slot update (`200`) and expected payload values.
- Proof of successful operating company creation after slot increase.
- Proof of blocked creation at limit with billing recovery path.
- Webhook event log snippet (`customer.subscription.updated` / `invoice.paid`) showing entitlement sync.
- Downgrade edge-case proof: existing companies intact, new creation blocked until limits match.

## Collected Manual Baseline Artifacts

- Real-tenant baseline snapshot (`victoria-space`, before manual click-path):  
  [a6-s7-slots-snapshot-2026-03-15-victoria-space-before-manual.md](/opt/HostFlow/docs/manual-checklist/a6-s7-slots-snapshot-2026-03-15-victoria-space-before-manual.md),  
  [a6-s7-slots-snapshot-2026-03-15-victoria-space-before-manual.json](/opt/HostFlow/docs/manual-checklist/a6-s7-slots-snapshot-2026-03-15-victoria-space-before-manual.json)
- Real-tenant evidence bundle (`victoria-space`, pre-manual):  
  [a6-s7-evidence-bundle-2026-03-15-victoria-space-pre-manual.md](/opt/HostFlow/docs/manual-checklist/a6-s7-evidence-bundle-2026-03-15-victoria-space-pre-manual.md),  
  [a6-s7-evidence-bundle-2026-03-15-victoria-space-pre-manual.json](/opt/HostFlow/docs/manual-checklist/a6-s7-evidence-bundle-2026-03-15-victoria-space-pre-manual.json)  
  (`Stripe customer/subscription ids` and billing history are currently absent for this tenant, so Stripe-proof sub-step remains pending/possibly blocked until billing activation on target workspace).

## Sign-off
- Product: `PENDING`
- QA: `PENDING`
