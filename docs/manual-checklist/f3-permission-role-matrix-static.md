# F3 Permission Matrix Static Snapshot

Date: `2026-03-12`
Source: `npm --prefix hostflow-frontend run permissions:report`

Этот файл сгенерирован автоматически из `scripts/check-permission-matrix.mjs`.

## default-tenant

| Route | superadmin | owner/admin | supervisor | recruiter | viewer |
| --- | --- | --- | --- | --- | --- |
| overview | ALLOW | ALLOW | ALLOW | ALLOW | ALLOW |
| candidates [candidates.view] | ALLOW | ALLOW | ALLOW | ALLOW | ALLOW |
| clients [companies.view] | ALLOW | ALLOW | ALLOW | ALLOW | ALLOW |
| leads [leads.view] | ALLOW | ALLOW | ALLOW | ALLOW | ALLOW |
| services [services.view] | ALLOW | ALLOW | ALLOW | ALLOW | ALLOW |
| settings [settings.view] | ALLOW | ALLOW | ALLOW | DENY | DENY |
| settings/users [admin.users|users.manage|users.view] | ALLOW | ALLOW | ALLOW | DENY | DENY |
| settings/company-access [admin.companyAcl] | ALLOW | ALLOW | ALLOW | DENY | DENY |
| settings/communications [admin.users] | ALLOW | ALLOW | DENY | DENY | DENY |
| settings/integrations [admin.metaLeads] | ALLOW | ALLOW | ALLOW | DENY | DENY |

Mismatches: `0`

## client-tenant

| Route | superadmin | owner/admin | supervisor | recruiter | viewer |
| --- | --- | --- | --- | --- | --- |
| overview | ALLOW | ALLOW | ALLOW | ALLOW | ALLOW |
| candidates [candidates.view] | ALLOW | ALLOW | ALLOW | ALLOW | ALLOW |
| clients [companies.view] | ALLOW | ALLOW | ALLOW | ALLOW | ALLOW |
| leads [leads.view] | ALLOW | ALLOW | ALLOW | DENY | ALLOW |
| services [services.view] | ALLOW | ALLOW | ALLOW | DENY | ALLOW |
| settings [settings.view] | ALLOW | ALLOW | ALLOW | DENY | DENY |
| settings/users [admin.users|users.manage|users.view] | ALLOW | ALLOW | ALLOW | DENY | DENY |
| settings/company-access [admin.companyAcl] | ALLOW | ALLOW | ALLOW | DENY | DENY |
| settings/communications [admin.users] | ALLOW | ALLOW | DENY | DENY | DENY |
| settings/integrations [admin.metaLeads] | ALLOW | ALLOW | ALLOW | DENY | DENY |

Mismatches: `0`

