# F3 Permission Role Matrix (Role-by-Role)

Source of truth: `docs/crm-production-readiness-ssot.md` section `9`.
Static snapshot: [f3-permission-role-matrix-static.md](/opt/HostFlow/docs/manual-checklist/f3-permission-role-matrix-static.md)

Date: `YYYY-MM-DD`  
Environment: `staging | production`  
Tenant: `<tenant-id-or-slug>`  
Owner: `<name/role>`

Legend:
- `PASS` — observed behavior matches expectation.
- `FAIL(<BUG-ID>)` — mismatch detected.
- `N/A` — route/module intentionally unavailable in current tenant profile.

## Core Role Matrix

| Route / Capability | superadmin | owner/admin (`administrator`) | supervisor | recruiter | viewer |
|---|---|---|---|---|---|
| `/app/overview` (dashboard) | `PASS/FAIL` | `PASS/FAIL` | `PASS/FAIL` | `PASS/FAIL` | `PASS/FAIL` |
| `/app/candidates` (`candidates.view`) | `PASS/FAIL` | `PASS/FAIL` | `PASS/FAIL` | `PASS/FAIL` | `PASS/FAIL` |
| `/app/clients` (`companies.view`) | `PASS/FAIL` | `PASS/FAIL` | `PASS/FAIL` | `PASS/FAIL` | `PASS/FAIL` |
| `/app/leads` (`leads.view`) | `PASS/FAIL` | `PASS/FAIL` | `PASS/FAIL` | `PASS/FAIL` | `PASS/FAIL` |
| `/app/services` (`services.view`) | `PASS/FAIL` | `PASS/FAIL` | `PASS/FAIL` | `PASS/FAIL` | `PASS/FAIL` |
| `/app/settings` (`settings.view`) | `PASS/FAIL` | `PASS/FAIL` | `PASS/FAIL` | `PASS/FAIL` | `PASS/FAIL` |
| `/app/settings/users` (`admin.users|users.manage|users.view`) | `PASS/FAIL` | `PASS/FAIL` | `PASS/FAIL` | `PASS/FAIL` | `PASS/FAIL` |
| `/app/settings/company-access` (`admin.companyAcl`) | `PASS/FAIL` | `PASS/FAIL` | `PASS/FAIL` | `PASS/FAIL` | `PASS/FAIL` |
| `/app/settings/communications` (`admin.users` + comm gate) | `PASS/FAIL` | `PASS/FAIL` | `PASS/FAIL` | `PASS/FAIL` | `PASS/FAIL` |
| `/app/settings/integrations` (`admin.metaLeads`) | `PASS/FAIL` | `PASS/FAIL` | `PASS/FAIL` | `PASS/FAIL` | `PASS/FAIL` |

## Evidence

- UI evidence: `<screens/video links or notes>`
- API/log evidence: `<if required>`
- Notes: `<role-specific observations>`

## Issues

- `<BUG-ID / N/A>`

## Sign-off

- Product: `<name>`
- QA: `<name>`
