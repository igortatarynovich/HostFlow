# F7 Run Record Template

Use this template for each manual run of scenarios `A/B/C`.

Naming convention:
- `docs/manual-checklist/f7-run-<scenario>-YYYY-MM-DD-<env>-<tenant>.md`
- Example: `f7-run-b-2026-03-12-staging-tenant-demo.md`

## Header

Date: `YYYY-MM-DD`  
Scenario: `A | B | C`  
Business type: `services | agency | employer`  
Environment: `staging | production`  
Tenant: `<tenant-id-or-slug>`  
Owner: `<name/role>`  
Result: `PASS | FAIL | BLOCKED`  
Blocker (if any): `<text or N/A>`

## Step-by-Step Evidence

| Step | Expected | Actual | Status (`PASS/FAIL/BLOCKED`) | Evidence |
|---|---|---|---|---|
| 1 | `<from run-sheet>` | `<observed behavior>` | `PASS/FAIL/BLOCKED` | `<screenshot/video/log link>` |
| 2 | `<...>` | `<...>` | `PASS/FAIL/BLOCKED` | `<...>` |

## Summary Evidence

- UI evidence: `<links/notes>`
- API/log evidence: `<links/snippets>`
- Notes: `<key observations>`

## Issues

- `<BUG-ID / N/A>`

## Sign-off

- Product: `<name>`
- QA: `<name>`
