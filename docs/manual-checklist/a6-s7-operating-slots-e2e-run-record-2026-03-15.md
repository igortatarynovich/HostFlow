# A6-S7 Operating Slots E2E Run Record

Date: `2026-03-15`  
Environment: `staging/production-like`  
Owner: `Codex/Product`  
Result: `IN_PROGRESS`  
Blocker (if any): `Manual product/QA click-path run and Stripe-side payment confirmation evidence are pending.`

## Scope
- Validate end-to-end operating company slots flow:
  1. buy/add slot,
  2. create new operating company,
  3. downgrade/remove slot edge case without data loss.

## Step-by-step Checklist

| Step | Expected | Actual | Status (`PASS/FAIL/BLOCKED/IN_PROGRESS`) | Evidence |
|---|---|---|---|---|
| 1 | Billing shows `included + extra = effective` slots correctly. | Runtime implementation present in Billing and My Company pages; manual visual verification pending for target tenant. | `IN_PROGRESS` | Code: `BillingWorkspacePage`, `MyCompanyPage`; pending screenshot/log evidence. |
| 2 | Increase add-on slots from Billing (`- / + / Save`) succeeds. | API/UI path implemented (`POST /settings/billing/company-slots`), live click-path evidence pending. | `IN_PROGRESS` | Backend route + frontend controls; pending API log/screenshot. |
| 3 | New operating company can be created when slot is available. | Guardrails implemented; positive path manual run pending. | `IN_PROGRESS` | Pending onboarding/my-company create proof. |
| 4 | At limit, creation is blocked with clear upgrade/add-slot CTA (no dead-end). | Guardrails implemented (`OPERATING-COMPANY-LIMIT` handling and billing CTA). | `IN_PROGRESS` | Code in Onboarding/MyCompany/FriendlyError; pending UX evidence. |
| 5 | Stripe webhook sync updates `extra_operating_company_slots` from subscription item quantity. | Webhook mapping implemented; live Stripe event proof pending. | `IN_PROGRESS` | `_handle_subscription_event` slot quantity sync; pending webhook log snippet. |
| 6 | Downgrade/remove add-on slot does not delete companies; only creation of new ones is blocked if over limit. | Enforcement model implemented; explicit downgrade edge-case manual pass pending. | `IN_PROGRESS` | Pending controlled downgrade run evidence. |

## Required Evidence to Close `A6-S7`
- Billing UI screenshots before/after slot change.
- API evidence for slot update (`200`) and expected payload values.
- Proof of successful operating company creation after slot increase.
- Proof of blocked creation at limit with billing recovery path.
- Webhook event log snippet (`customer.subscription.updated` / `invoice.paid`) showing entitlement sync.
- Downgrade edge-case proof: existing companies intact, new creation blocked until limits match.

## Sign-off
- Product: `PENDING`
- QA: `PENDING`
