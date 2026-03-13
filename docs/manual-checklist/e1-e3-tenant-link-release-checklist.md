# E1-E3 Tenant Link Release Checklist

Source of truth:
- `docs/crm-production-readiness-ssot.md` sections `5.5`, `10`
- `docs/specs/architecture/client_and_subscription_model.md`
- `docs/CLIENT_AND_ONBOARDING_REDESIGN_PLAN.md`

Date: `YYYY-MM-DD`  
Environment: `staging | production-safe`  
Agency tenant: `<tenant-id-or-slug>`  
Client tenant: `<tenant-id-or-slug | N/A>`  
Portal-only company: `<company-id-or-name | N/A>`  
Owner: `<name/role>`

Цель:
- `E1` подтвердить candidate visibility scope для `tenant-backed client`
- `E2` подтвердить link-based access для `portal-only client`
- `E3` формально проверить policy/ACL/audit contract вокруг `tenant_links`

Legend:
- `PASS` — observed behavior matches accepted rule.
- `FAIL(<BUG-ID>)` — mismatch detected.
- `N/A` — intentionally unavailable for this run.

## 1. E1 Tenant-Backed Client Flow

Accepted rule:
- Клиентский tenant (`Tenant.type = company`) видит своих кандидатов + кандидатов по вакансиям компаний, связанных через `tenant_links.client_tenant_id + handoff_include_company_id`.
- Для непереданных кандидатов действует reduced-profile masking.
- Для accepted/pending handoff кандидат не должен исчезать из клиентского scope.

### 1.1 Data baseline

| Check | Result | Notes |
|---|---|---|
| Client tenant exists and has active license | `PASS/FAIL` |  |
| At least one active `tenant_link` exists with `client_tenant_id` = client tenant | `PASS/FAIL` |  |
| Every agency company whose vacancies should be visible has its own `handoff_include_company_id` link | `PASS/FAIL` |  |
| Test dataset contains both handed-off and non-handed-off candidates for linked vacancies | `PASS/FAIL` |  |

### 1.2 Candidate list and masking

| Check | Result | Notes |
|---|---|---|
| Client tenant can open candidates list without manual DB fix during run | `PASS/FAIL` |  |
| Candidates from linked vacancy companies are visible in list | `PASS/FAIL` |  |
| Candidates outside linked scope are not visible | `PASS/FAIL` |  |
| Accepted handoff candidate is visible with full profile | `PASS/FAIL` |  |
| Pending handoff candidate is visible with decision-ready profile | `PASS/FAIL` |  |
| Non-handoff candidate from linked vacancy is visible in reduced form only | `PASS/FAIL` |  |
| Response includes diagnostic headers `X-Client-View` and `X-Masked-Count` when expected | `PASS/FAIL` |  |

### 1.3 Scope / RLS safety

| Check | Result | Notes |
|---|---|---|
| Request works with correct tenant scope (`X-Tenant-Id` / scope tenant) | `PASS/FAIL` |  |
| Direct tenant switch to unrelated tenant does not expose unrelated candidates | `PASS/FAIL` |  |
| Removing one `tenant_link` removes only corresponding company scope, not entire client list | `PASS/FAIL` |  |

## 2. E2 Portal-Only Client Flow

Accepted rule:
- `portal-only client` has no tenant login and no CRM shell.
- Access is only through portal token bound to `tenant_link`.
- Portal shows read-only handoff candidates for that client; visibility respects reduced-profile setting.

### 2.1 Portal link lifecycle

| Check | Result | Notes |
|---|---|---|
| Agency can create portal link for client with `client_company_id` and no `client_tenant_id` | `PASS/FAIL` |  |
| Generated link/token is returned and copyable in UI | `PASS/FAIL` |  |
| Revoked link stops working immediately or after documented grace behavior | `PASS/FAIL` |  |
| Optional expiration is respected if configured | `PASS/FAIL/N/A` |  |

### 2.2 Portal access behavior

| Check | Result | Notes |
|---|---|---|
| Token opens portal without tenant auth/login | `PASS/FAIL` |  |
| Portal does not expose CRM navigation or tenant switcher | `PASS/FAIL` |  |
| Only candidates with accepted handoff to this client are visible | `PASS/FAIL` |  |
| Candidate cards are read-only | `PASS/FAIL` |  |
| Reduced-profile mode masks PII when enabled | `PASS/FAIL` |  |
| Invalid token returns safe deny state without data leakage | `PASS/FAIL` |  |

## 3. E3 Tenant Links Policy Hardening

Accepted rule:
- `tenant_links` are created and edited only from agency side by elevated users.
- Exactly one of `client_company_id` or `client_tenant_id` is used per link.
- `handoff_include_company_id` is explicit for tenant-backed visibility scope.
- Portal-link operations and visibility-impacting changes are observable in logs/audit.

### 3.1 Creation / mutation rules

| Check | Result | Notes |
|---|---|---|
| Agency admin can create tenant-backed link with `client_tenant_id + handoff_include_company_id` | `PASS/FAIL` |  |
| Agency admin can create portal-only link with `client_company_id` only | `PASS/FAIL` |  |
| API rejects payload with both `client_company_id` and `client_tenant_id` | `PASS/FAIL` |  |
| API rejects incomplete tenant-backed payload without `handoff_include_company_id` | `PASS/FAIL` |  |
| Non-elevated user cannot manage tenant links | `PASS/FAIL` |  |

### 3.2 Visibility and auditability

| Check | Result | Notes |
|---|---|---|
| Agency sees correct link type and target in UI/API (`tenant-backed` vs `portal-only`) | `PASS/FAIL` |  |
| Client tenant cannot self-create or self-edit agency-owned tenant links | `PASS/FAIL` |  |
| Portal token rotation/revoke is reflected in API/UI state | `PASS/FAIL` |  |
| Relevant changes are traceable in logs/audit notes for release sign-off | `PASS/FAIL` |  |

## 4. Evidence

- UI evidence: `<screens/video links or notes>`
- API evidence: `<headers, payloads, endpoint notes>`
- Data evidence: `<tenant_links rows, candidate/handoff notes>`
- Notes: `<observations>`

## 5. Issues

- `<BUG-ID / N/A>`

## 6. Sign-off

- Product: `<name>`
- QA: `<name>`
