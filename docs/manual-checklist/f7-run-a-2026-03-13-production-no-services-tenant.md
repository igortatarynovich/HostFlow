# F7 Run Record

Date: `2026-03-13`  
Scenario: `A`  
Business type: `services`  
Environment: `production`  
Tenant: `N/A (dedicated services tenant missing)`  
Owner: `Codex/Product`  
Result: `BLOCKED`  
Blocker (if any): `Production billing flow is now ready, but there is no dedicated production tenant configured as business type services for the formal Scenario A release-pass. The currently paid production tenant is 'default' with tenant type 'agency'.`

## Step-by-Step Evidence

| Step | Expected | Actual | Status (`PASS/FAIL/BLOCKED`) | Evidence |
|---|---|---|---|---|
| 1 | User registered successfully. | Existing paid production tenant verified, but no fresh services registration run was executed in this record. | `BLOCKED` | Production evidence is attached at tenant-level only; no dedicated services signup run available. |
| 2 | Payment completed. | Live Stripe payment flow and webhook sync were confirmed earlier in production. | `PASS` | SSOT `5.1.3`, live subscription `sub_1TAQFkDNUS2CNJRmeq1PmpsR`, customer `cus_U8he6GO7b06J5o`. |
| 3 | Business type `services` selected. | Production tenant inventory shows no dedicated tenant with `services` business type; current paid tenant is `default` / tenant type `agency`. | `BLOCKED` | DB inspection on `2026-03-13`: tenant `11111111-1111-1111-1111-111111111111` => `type=agency`, `slug=default`; no production services tenant found. |
| 4 | Work email connected. | Paid production tenant has active email config. | `PASS` | `tenant_email_config` active rows = `1`; active communication accounts = `78`. |
| 5 | First client created. | Paid production tenant has at least one active company record. | `PASS` | `companies` count = `1`; first company = `POLTRAKT`. |
| 6 | First message sent. | Paid production tenant has outbound delivered messages. | `PASS` | `communication_messages` outbound count = `27`; earliest outbound subject = `Hello outbound`, status = `delivered`. |
| 7 | First task created. | Paid production tenant has reminders/tasks. | `PASS` | `reminders` count = `743`; earliest reminder status = `pending`. |
| 8 | Auto-reply configured. | No verified production evidence for services auto-reply on a dedicated services tenant in this run. | `BLOCKED` | `tenant.settings.communications.auto_reply_*` not populated on the paid production tenant used for billing verification. |
| 9 | Workflow started end-to-end. | Billing is production-ready, but formal services end-to-end workflow cannot be signed off without a dedicated services tenant run. | `BLOCKED` | Missing production services tenant + missing dedicated manual run by checklist `4.2`. |

## Summary Evidence

- UI evidence: user-confirmed live production billing UX pass on `2026-03-13` (payment history, receipt access, explicit Stripe Checkout for plan change, cancel/resume flow, dates).
- API/log evidence: live Stripe subscription `sub_1TAQFkDNUS2CNJRmeq1PmpsR` now uses production starter price `price_1TAEQGDNUS2CNJRmpRJl50om` (`39 EUR`); webhook sync and tenant billing summary confirmed in production.
- Notes: commercial billing path is production-ready, but formal `Scenario A` requires a dedicated production tenant with business type `services`, plus a fresh manual run over steps `1..9`.

## Issues

- `N/A`

## Sign-off

- Product: `Codex`
- QA: `Blocked pending dedicated production services tenant`
