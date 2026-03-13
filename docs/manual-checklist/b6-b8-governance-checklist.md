# B6-B8 Governance Checklist

Source of truth: `docs/crm-production-readiness-ssot.md` sections `5.2`, `5.6.11`, `6`, `7`, `9`.

Date: `YYYY-MM-DD`  
Environment: `staging | production`  
Tenant: `<tenant-id-or-slug>`  
Owner: `<name/role>`

Цель: формально закрывать governance-блок self-serve CRM без двусмысленности:
- `B6` role-to-settings matrix
- `B7` self-serve company bootstrap contract
- `B8` ownership bootstrap первой компании

Legend:
- `PASS` — observed behavior matches accepted rule.
- `FAIL(<BUG-ID>)` — mismatch detected.
- `N/A` — intentionally unavailable in current tenant/profile.

## 1. B6 Role-to-Settings Matrix

Baseline reference:
- [f3-permission-role-matrix-static.md](/opt/HostFlow/docs/manual-checklist/f3-permission-role-matrix-static.md)

### 1.1 Settings access expectations

| Route / entry point | superadmin | administrator | supervisor | recruiter | viewer | Expected notes |
|---|---|---|---|---|---|---|
| `/app/settings` | `PASS/FAIL` | `PASS/FAIL` | `PASS/FAIL` | `PASS/FAIL` | `PASS/FAIL` | `recruiter/viewer` must not enter settings shell |
| `/app/settings/users` | `PASS/FAIL` | `PASS/FAIL` | `PASS/FAIL` | `PASS/FAIL` | `PASS/FAIL` | user-management only for elevated roles |
| `/app/settings/company-access` | `PASS/FAIL` | `PASS/FAIL` | `PASS/FAIL` | `PASS/FAIL` | `PASS/FAIL` | no access leakage to non-admin roles |
| `/app/settings/communications` | `PASS/FAIL` | `PASS/FAIL` | `PASS/FAIL` | `PASS/FAIL` | `PASS/FAIL` | advanced comms diagnostics remain admin-only |
| `/app/settings/integrations` | `PASS/FAIL` | `PASS/FAIL` | `PASS/FAIL` | `PASS/FAIL` | `PASS/FAIL` | integrations are not exposed to low-permission roles |

### 1.2 Navigation IA anti-duplication

| Check | Result |
|---|---|
| Sidebar is the canonical entry point for workspace settings | `PASS/FAIL` |
| Topbar account menu does not duplicate admin/settings shortcuts | `PASS/FAIL` |
| Empty states and onboarding CTA do not expose hidden settings routes | `PASS/FAIL` |
| Direct URL open of forbidden settings route ends in safe deny/redirect | `PASS/FAIL` |

## 2. B7 Self-Serve Company Bootstrap Contract

Accepted bootstrap rule:
- First-run company creation must collect only fields required for immediate CRM activation.
- Additional legal/billing/ops fields must be deferred until they have a clear use and a non-blocking place in the flow.

### 2.1 Field contract

| Field / artifact | Current state | Required now | Purpose | Validation |
|---|---|---|---|---|
| `name` | Bootstrap form | `YES` | create first company record and identify workspace entity | non-empty |
| `company_type` (`agency/employer/services`) | Bootstrap form | `YES` | select business profile, module baseline, terminology, onboarding path | enum only |
| `legal_name` | Deferred | `NO` | legal/billing profile later | must not block first value |
| `tax_id` | Deferred | `NO` | legal/billing later | must not block first value |
| `email` | Deferred | `NO` | company contact later | must not block first value |
| `phone` | Deferred | `NO` | company contact later | must not block first value |
| `website` | Deferred | `NO` | company profile later | must not block first value |
| `address/country/city` | Deferred | `NO` | legal/ops later | must not block first value |
| `contacts/extra` | Deferred | `NO` | expanded profile later | must not block first value |

### 2.2 Bootstrap acceptance

| Check | Result |
|---|---|
| Company can be created with only `name + company_type` | `PASS/FAIL` |
| First company updates tenant business profile/modules | `PASS/FAIL` |
| Bootstrap does not require legal/billing fields before first value | `PASS/FAIL` |
| Post-bootstrap user can continue work immediately without forced settings detour | `PASS/FAIL` |

## 3. B8 Ownership Bootstrap Of First Company

Accepted governance rule for current launch:
- First self-serve company must receive explicit persisted ownership via `companies.owner_user_id`.
- `companies.manager_user_id` is also persisted; by default it inherits the bootstrap owner unless explicitly reassigned.
- Canonical bootstrap actor is the current elevated tenant user who created the company.
- If company-level delegation is needed later, it is expressed explicitly through `owner_user_id`, `manager_user_id`, and `user_company_access`, not by guessing hidden ownership.

### 3.1 Ownership expectations

| Check | Result |
|---|---|
| Bootstrap actor is tenant administrator or equivalent elevated role | `PASS/FAIL` |
| First company stores explicit `owner_user_id` and `manager_user_id` after create | `PASS/FAIL` |
| First company remains editable by elevated workspace owner/admin after create | `PASS/FAIL` |
| Ownership is not silently assigned to unrelated user | `PASS/FAIL` |
| Manager defaults to owner unless explicitly reassigned | `PASS/FAIL` |
| If company access is granted later, it is explicit via `user_company_access` / company access UI | `PASS/FAIL` |
| UI/API expose real editable owner/manager controls consistent with persisted model | `PASS/FAIL` |

### 3.2 Follow-up product gap

Заполнить при ревью:
- Достаточно ли current placement в company profile для ежедневной операционной модели?
- Какие workflow реально зависят от `owner_user_id` / `manager_user_id` (`documents`, `approvals`, `communications`, `client handoff`)?
- Нужны ли дополнительные safeguards для backfill/legacy компаний с `NULL` ownership?

## 4. Evidence

- UI evidence: `<screens/video links or notes>`
- API/log evidence: `<if required>`
- Notes: `<observations>`

## 5. Issues

- `<BUG-ID / N/A>`

## 6. Sign-off

- Product: `<name>`
- QA: `<name>`
