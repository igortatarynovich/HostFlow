# B6-B8 Governance Static Baseline

Source of truth: `docs/crm-production-readiness-ssot.md` sections `5.2`, `5.6.11`, `6`, `7`, `9`.
Checklist: [b6-b8-governance-checklist.md](/opt/HostFlow/docs/manual-checklist/b6-b8-governance-checklist.md)

Date: `2026-03-13`  
Environment: `staging`  
Tenant: `N/A` (`static audit`)  
Owner: `Codex/Product`

Итог:
- `B6`: `PASS_STATIC`
- `B7`: `PASS_STATIC`
- `B8`: `PASS_STATIC_WITH_GAP`
- Release decision: `IN_PROGRESS`

Update note:
- Этот static baseline исторически фиксирует исходный gap `B8-GAP-001`.
- После него в коде реализована explicit ownership model (`companies.owner_user_id`, `companies.manager_user_id`); для актуального статуса ориентироваться на SSOT changelog `2026-03-13`.

Причина, почему не `DONE`:
- Это статический code/doc audit без ручного tenant-level sign-off.
- На момент этого snapshot `B8` еще не имел persisted ownership fields; сейчас этот конкретный gap уже закрыт implementation-level.

## 1. B6 Role-to-Settings Matrix

### 1.1 Settings access expectations

| Route / entry point | Result | Evidence |
|---|---|---|
| `/app/settings` | `PASS` | [routes.tsx](/opt/HostFlow/hostflow-frontend/src/app/routes.tsx) uses `permission: 'settings.view'`; static matrix confirms deny for `recruiter/viewer` in [f3-permission-role-matrix-static.md](/opt/HostFlow/docs/manual-checklist/f3-permission-role-matrix-static.md) |
| `/app/settings/users` | `PASS` | [routes.tsx](/opt/HostFlow/hostflow-frontend/src/app/routes.tsx) uses `['admin.users', 'users.manage', 'users.view']`; static matrix baseline is aligned |
| `/app/settings/company-access` | `PASS` | [routes.tsx](/opt/HostFlow/hostflow-frontend/src/app/routes.tsx) uses `permission: 'admin.companyAcl'`; [CompanyAccessPage.tsx](/opt/HostFlow/hostflow-frontend/src/pages/admin/CompanyAccessPage.tsx) blocks UI when `can('admin.companyAcl') = false` |
| `/app/settings/communications` | `PASS` | [routes.tsx](/opt/HostFlow/hostflow-frontend/src/app/routes.tsx) requires `admin.users` + `withCommFeature(..., 'communicationsAdmin')` |
| `/app/settings/integrations` | `PASS` | [routes.tsx](/opt/HostFlow/hostflow-frontend/src/app/routes.tsx) uses `permission: 'admin.metaLeads'` |

### 1.2 Navigation IA anti-duplication

| Check | Result | Evidence |
|---|---|---|
| Sidebar is the canonical entry point for workspace settings | `PASS` | [Sidebar.tsx](/opt/HostFlow/hostflow-frontend/src/components/nav/Sidebar.tsx) contains dedicated `settings` section with all admin routes grouped together |
| Topbar account menu does not duplicate admin/settings shortcuts | `PASS` | [Topbar.tsx](/opt/HostFlow/hostflow-frontend/src/components/nav/Topbar.tsx) account menu contains `My account -> Profile / Logout`; admin shortcut set removed |
| Empty states and onboarding CTA do not expose hidden settings routes | `PASS_STATIC` | [AppShell.tsx](/opt/HostFlow/hostflow-frontend/src/app/AppShell.tsx) strips `/app/settings/*` for guided trial workspace except billing; onboarding path points to work routes |
| Direct URL open of forbidden settings route ends in safe deny/redirect | `PASS_STATIC` | [AppShell.tsx](/opt/HostFlow/hostflow-frontend/src/app/AppShell.tsx) redirects guided trial workspace away from hidden settings; route permissions remain enforced in router/static matrix |

## 2. B7 Self-Serve Company Bootstrap Contract

### 2.1 Field contract

| Field / artifact | Result | Evidence |
|---|---|---|
| `name` is required | `PASS` | [OnboardingCompanyPage.tsx](/opt/HostFlow/hostflow-frontend/src/pages/OnboardingCompanyPage.tsx) validates non-empty input; [schemas.py](/opt/HostFlow/backend/app/modules/companies/schemas.py) defines `name: str` |
| `company_type` is the only business-profile selector | `PASS` | [OnboardingCompanyPage.tsx](/opt/HostFlow/hostflow-frontend/src/pages/OnboardingCompanyPage.tsx) offers only `agency/employer/services`; backend schema restricts enum in [schemas.py](/opt/HostFlow/backend/app/modules/companies/schemas.py) |
| First company can be created with only `name + company_type` | `PASS_STATIC` | [OnboardingCompanyPage.tsx](/opt/HostFlow/hostflow-frontend/src/pages/OnboardingCompanyPage.tsx) submits only `{ name, company_type }`; backend create flow in [crud.py](/opt/HostFlow/backend/app/modules/companies/crud.py) accepts this minimal payload |
| First company bootstraps tenant business profile/modules | `PASS_STATIC` | [crud.py](/opt/HostFlow/backend/app/modules/companies/crud.py) updates tenant type/settings and default funnels when first company is created with `company_type` |
| Legal/billing/ops fields are deferred, not blocking first value | `PASS_STATIC` | extended company fields exist in [company.py](/opt/HostFlow/backend/app/models/company.py) and [schemas.py](/opt/HostFlow/backend/app/modules/companies/schemas.py), but are absent from first-run onboarding form |

## 3. B8 Ownership Bootstrap Of First Company

| Check | Result | Evidence |
|---|---|---|
| Bootstrap actor must be elevated role | `PASS_STATIC` | create route in [router.py](/opt/HostFlow/backend/app/modules/companies/router.py) requires elevated role; self-serve path is driven by tenant administrator in trial workspace |
| First company remains editable by elevated workspace owner/admin after create | `PASS_STATIC` | company update routes in [router.py](/opt/HostFlow/backend/app/modules/companies/router.py) are available to elevated roles |
| Delegation is explicit via company access, not hidden ownership | `PASS_STATIC` | [companies_access.py](/opt/HostFlow/backend/app/api/v1/admin/companies_access.py) and [access.py](/opt/HostFlow/backend/app/models/access.py) implement explicit `user_company_access` records |
| Historical gap at snapshot time: dedicated persisted company owner was missing | `GAP_HISTORICAL` | later closed by adding `companies.owner_user_id` / `companies.manager_user_id`; see SSOT changelog `2026-03-13` |

Accepted interpretation for this historical snapshot:
- Canonical operational owner of the first company is the bootstrap actor with elevated tenant role.
- Company-level delegation is explicit through role model and `user_company_access`.
- At snapshot time company-native ownership had not yet been introduced.

## 4. Notes

- `SettingsLandingPage` already reflects the intended IA: `Company access` is grouped under `Team`, communications setup lives in guided setup, and advanced communications controls stay separated in settings.
- `AppShell` enforces the non-blocking onboarding direction for guided trial workspace: hidden settings are removed from shell navigation and direct access redirects to safe working routes.
- `B8` should not be marked `DONE` until product explicitly accepts the current governance contract and completes manual tenant sign-off.

## 5. Issues

- `B8-GAP-001` (`historical`): at snapshot time there was no dedicated persisted `company.owner_id` / `company.manager_id` contract; later closed implementation-level by `owner_user_id` / `manager_user_id`.

## 6. Sign-off

- Product: `Static baseline accepted for documentation`
- QA: `Manual tenant run pending`
