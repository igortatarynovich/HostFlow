# F11 Mobile Run Record Template

Use this template for each manual run of `F11` mobile adaptation pass.

Naming convention:
- `docs/manual-checklist/f11-mobile-run-YYYY-MM-DD-<env>-<tenant>.md`
- Example: `f11-mobile-run-2026-03-12-staging-tenant-demo.md`

## Header

Date: `YYYY-MM-DD`  
Environment: `staging | production`  
Tenant: `<tenant-id-or-slug>`  
Owner: `<name/role>`  
Result: `PASS | FAIL`  
Decision: `GO | NO-GO`  
Blockers: `<text or N/A>`

## Device Matrix

- iOS Safari: `<device/os/version>`
- Android Chrome: `<device/os/version>`
- Desktop emulation: `<browser/version>`

## Route/Breakpoint Results

| Route | 320 | 375 | 390 | 768 | Notes | Evidence |
|---|---|---|---|---|---|---|
| `/` | `PASS/FAIL` | `PASS/FAIL` | `PASS/FAIL` | `PASS/FAIL` | `<observation>` | `<link>` |
| `/signup` | `PASS/FAIL` | `PASS/FAIL` | `PASS/FAIL` | `PASS/FAIL` | `<observation>` | `<link>` |
| `/app/onboarding/company` | `PASS/FAIL` | `PASS/FAIL` | `PASS/FAIL` | `PASS/FAIL` | `<observation>` | `<link>` |
| `/app/onboarding/getting-started` | `PASS/FAIL` | `PASS/FAIL` | `PASS/FAIL` | `PASS/FAIL` | `<observation>` | `<link>` |
| `/app/overview` | `PASS/FAIL` | `PASS/FAIL` | `PASS/FAIL` | `PASS/FAIL` | `<observation>` | `<link>` |
| `/app/clients` | `PASS/FAIL` | `PASS/FAIL` | `PASS/FAIL` | `PASS/FAIL` | `<observation>` | `<link>` |
| `/app/leads` | `PASS/FAIL` | `PASS/FAIL` | `PASS/FAIL` | `PASS/FAIL` | `<observation>` | `<link>` |
| `/app/messages` | `PASS/FAIL` | `PASS/FAIL` | `PASS/FAIL` | `PASS/FAIL` | `<observation>` | `<link>` |
| `/app/reminders` | `PASS/FAIL` | `PASS/FAIL` | `PASS/FAIL` | `PASS/FAIL` | `<observation>` | `<link>` |
| `/public/scan` | `PASS/FAIL` | `PASS/FAIL` | `PASS/FAIL` | `PASS/FAIL` | `<observation>` | `<link>` |
| `/app/settings` | `PASS/FAIL` | `PASS/FAIL` | `PASS/FAIL` | `PASS/FAIL` | `<observation>` | `<link>` |

## Touch/Keyboard/Modal Audit

- Touch target baseline (`>=44px`): `<PASS/FAIL + notes>`
- Soft keyboard overlap (`iOS/Android`): `<PASS/FAIL + notes>`
- Modal scroll and sticky actions: `<PASS/FAIL + notes>`
- Horizontal overflow check: `<PASS/FAIL + notes>`

## Summary Evidence

- Screenshots: `<links>`
- Videos: `<links>`
- Notes: `<key observations>`

## Issues

- `<BUG-ID / N/A>`

## Sign-off

- Product: `<name>`
- QA: `<name>`
