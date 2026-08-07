# Threat Model — RBAC Trust Roles (ADR-036)

**Surface:** authentication / authorization — trust roles, role×module matrix, Settings Roles & access, `require_roles` bridge.  
**Parent ADR:** [`docs/specs/architecture/ADR-036-four-trust-roles-rbac.md`](../../specs/architecture/ADR-036-four-trust-roles-rbac.md) · matrix [`rbac_matrix.md`](../../specs/architecture/rbac_matrix.md) · inventory [`rbac-role-usage-inventory.md`](../../specs/architecture/rbac-role-usage-inventory.md)

## Assets

- Tenant membership role strings (JWT / DB)
- Role × module matrix (`tenant.settings.modules.role_matrix`) and user overrides
- Admin-locked capabilities (users/roles/billing/platform)
- Portal vs tenant `access_context` (orthogonal to trust role)

## Trust boundaries

- Platform (`superadmin`) ↔ Tenant admin (`administrator`) ↔ Operational staff (`employee`) ↔ Observer/guest (`viewer`)
- `access_context=tenant` vs `access_context=portal` (same `viewer` trust ≠ same data)

## Threats

| ID | Threat | Vector |
|----|--------|--------|
| RBAC-1 | Privilege escalation via matrix | Tenant admin grants Employee Admin-locked capabilities through module matrix / overrides |
| RBAC-2 | Role confusion | Treating job-title aliases (`recruiter`, `hr_officer`) as distinct trust levels forever; or treating every `viewer` as portal client |
| RBAC-3 | Portal over-privilege | Legacy `client_manager` / `client_processor` used as CRM seats without license; write beyond portal capabilities |
| RBAC-4 | UI-only deny | FE hides Settings but API still accepts mutations for Employee/Viewer |
| RBAC-5 | Inventory drift | New `require_roles(Role.recruiter, …)` without permission gate / inventory update |

## Controls

- **Trust ceilings:** API rejects matrix edits that violate ADR-036 ceilings (`assert_matrix_role_editable`, viewer mutate limits); Administrator column locked for tenant admins in UI.
- **Four-role invariant:** new canonical trust role requires Architecture RFC; presets/scope/org/`access_context` for new user types.
- **Normalize helpers:** `normalize_trust_role`, `infer_access_context` in `backend/app/auth/trust_roles.py`.
- **Bridge (migration):** `expand_allowed_roles_for_trust` so `employee` satisfies legacy job-proxy `require_roles` during inventory close-out — not a permanent dual model.
- **Discoverable admin surface:** Settings → Team → Roles & access; platform Tenants matrix for superadmin.
- **Gate:** `scripts/rbac/scan_role_usage.py` + `make rbac-role-lint` (no *new* job-title `Role.*` outside inventory/shim).

## Residual / follow-up

- Bulk migration of inventory H-risk `JOB_PROXY` / `PORTAL_LEGACY` call sites to permission/module gates (separate PR).
- Persist `access_context` explicitly on membership/JWT for portal guests (not only inferred from legacy role).
- Seat counters: stop billing portal guests as CRM seats.

## Related checklist

- [`../security-review-checklist.md`](../security-review-checklist.md) §2 RBAC
- SSOT: [`../security-ssot.md`](../security-ssot.md)
