# HostFlow RBAC Matrix & Panels

**Status:** NORMATIVE (L2) — operating matrix for trust roles  
**Parent ADR:** [`ADR-036-four-trust-roles-rbac.md`](ADR-036-four-trust-roles-rbac.md)  
**Inventory:** [`rbac-role-usage-inventory.md`](rbac-role-usage-inventory.md)

> Official matrix of **trust roles**, panels, ceilings, and module defaults. Used by backend guards, frontend conditional UI, and access tests.  
> **Do not** add a fifth canonical role without Architecture RFC. Job titles = presets.

---

## 0. Six axes (summary)

| Axis | SoT |
|------|-----|
| Role (trust) | JWT / membership — 4 values + aliases |
| Permissions | Action keys + module visible/editable matrix |
| Preset | Named starter packs (`recruiter`, `team_lead`, `hr`, `compliance`, …) |
| Org | `supervisor_id`, teams (future) |
| Scope | Company ACL / object ACL |
| access_context | `tenant` \| `portal` |

---

## 1. Canonical trust roles

| Role | Who | Notes |
|------|-----|-------|
| `superadmin` | HostFlow platform | Tenants, impersonation, platform APIs |
| `administrator` | Tenant admin / owner | Users, roles/access matrix, billing, tenant settings |
| `employee` | Operational staff | Configurable operational permissions; **no** Admin-locked capabilities |
| `viewer` | Observer or portal guest | Read-oriented; portal capabilities only when `access_context=portal` |

**Aliases (normalize → canonical):**

| Alias | Canonical | Extra |
|-------|-----------|--------|
| `owner`, `admin` | `administrator` | — |
| `recruiter`, `supervisor`, `hr_officer`, `compliance_officer`, `hr`, `manager` | `employee` | + preset id |
| `client_manager`, `client_processor`, `client`, `processor` | `viewer` | + `access_context=portal` preferred |
| `user` | `viewer` | — |

**Deprecated as security roles (do not assign to new users):** `recruiter`, `supervisor`, `hr_officer`, `compliance_officer`, `client_manager`, `client_processor`.

External: candidate / magic-link — **not** CRM trust roles.

---

## 2. Trust ceilings

| Capability | Superadmin | Admin | Employee | Viewer |
|------------|:----------:|:-----:|:--------:|:------:|
| Platform / tenants | yes | — | — | — |
| Tenant settings | yes | yes | — | — |
| Users / roles / access | yes | yes | — | — |
| Billing / subscription | yes | yes | — | — |
| Operational modules | yes | yes | configurable | configurable / read-oriented |
| Mutate business data | yes | yes | configurable | usually — |
| Portal capabilities | — | — | — | configurable |

Admin-locked rows are **not** editable for Employee/Viewer in UI or API.

---

## 3. Panels

| Panel | URI prefix | Trust roles | Notes |
|-------|------------|-------------|--------|
| Platform Control Center | `/api/v1/platform/*` | `superadmin` | — |
| Tenant Admin Console | `/api/v1/settings/*` | `administrator` (write); limited read via permissions | Not Employee/Viewer for users/roles/billing |
| Operational CRM | `/api/v1/leads/*`, `/candidates/*`, … | `administrator`, `employee` (+ permission/module) | Presets shape defaults |
| Read / portal | scoped APIs | `viewer` | `access_context` + scope |

Settings UI for matrix: **Settings → Team → Roles & access** (`/app/settings/team`).

---

## 4. Default role × module matrix

Defaults live in code: `backend/app/api/v1/tenants/service.py` (`_ROLE_MODULE_DEFAULTS`) and trust canonical keys via aliases during migration.

Target canonical keys in matrix UI: `administrator`, `employee`, `viewer` (superadmin out of tenant matrix).

Legacy matrix columns (`recruiter`, `supervisor`, …) map to **employee** presets until Phase 3 cleanup; `client_*` columns map to **viewer** (portal).

Illustrative employee/viewer defaults (visible / editable):

| Module | administrator | employee (recruiter preset) | employee (hr preset) | viewer (tenant) | viewer (portal) |
|--------|---------------|------------------------------|----------------------|-----------------|-----------------|
| candidates | V+E | V+E | — | V | V (scoped) |
| companies | V+E | V | — | V | V (scoped) |
| vacancies | V+E | V | — | V | V (scoped) |
| documents | V+E | V+E | — | — | V+E portal caps |
| leads | V+E | V | — | — | — |
| services | V+E | V+E | — | — | — |
| client_portal | V+E | — | — | — | V |
| hr | V+E | — | V+E | — | — |

(V = visible, E = editable)

---

## 5. Presets (not roles)

| Preset id | Applies to | Intent |
|-----------|------------|--------|
| `recruiter` | employee | Leads/candidates/docs ops |
| `team_lead` | employee | Ops + manager tools; org via `supervisor_id` |
| `hr` | employee | HR workspace |
| `compliance` | employee | Documents / process ops |
| `portal_guest` | viewer + portal | Scoped read + optional sign/comment |

Applying a preset copies permission/module cells; admin may tighten within ceilings.

---

## 6. access_context

| role | access_context | Typical use |
|------|----------------|-------------|
| viewer | tenant | Internal stakeholder read-only |
| viewer | portal | External client without HF license |
| employee | tenant | Staff |
| administrator | tenant | Tenant admin |

---

## 7. Middleware / enforcement

- `get_current_user` + tenant RLS (`app.tenant_id`).
- Trust normalize: `normalize_trust_role()` / aliases before ceiling checks.
- Module gate (ADR-023 Stage 2B) + role module matrix + user overrides.
- Platform routes: `superadmin`.
- Matrix PATCH: reject Admin-locked escalation for employee/viewer.
- Object scope: company ACL / entity helpers (unchanged).

---

## 8. Test checklist

- [ ] Employee cannot call users/roles/billing admin APIs.
- [ ] Viewer cannot mutate business data by default.
- [ ] Matrix PATCH rejecting Admin-locked grants for employee/viewer.
- [ ] Portal viewer ≠ treated as tenant admin; `access_context` distinct.
- [ ] Legacy alias `recruiter` still authenticates as employee trust during migration.
- [ ] Audit log on role / matrix / preset apply changes.
