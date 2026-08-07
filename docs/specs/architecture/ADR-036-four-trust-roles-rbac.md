# ADR-036: Four Trust Roles RBAC (architectural invariant)

**Status:** Accepted  
**Date:** 2026-08-07  
**Trusted base:** `integration/release-product-a-b`  
**Related:** [`rbac_matrix.md`](rbac_matrix.md) · [`rbac-role-usage-inventory.md`](rbac-role-usage-inventory.md) · [`personas.md`](../personas.md) · [`platform-architecture-principles.md`](platform-architecture-principles.md) §6 (Users / Roles / Permissions) · [`ADR-003`](ADR-003-tenant-company-module-data-boundaries.md) · [`ADR-023`](ADR-023-recruitment-sales-module-separation.md) Stage 2B

**L0 checklist:** No new L0 P-rule; capability ownership remains Users / Roles / Permissions in Catalog; does not rewrite Passport/Manifest shape; security perimeter (RBAC) — see Consequences.

---

## Context

HostFlow mixed **organizational job title** with **system trust level**. That produced enum growth (`recruiter`, `supervisor`, `hr_officer`, `compliance_officer`, `client_manager`, `client_processor`, …). Each new profession threatened JWT, `require_roles`, FE pickers, seats, and tests. Org hierarchy and portal guests were incorrectly modeled as security roles.

---

## Decision

### 1. Four trust roles are an architectural invariant

Canonical CRM/platform roles (JWT / membership):

| Role | Trust meaning |
|------|----------------|
| `superadmin` | Platform |
| `administrator` | Tenant administration |
| `employee` | Operational worker (permissions via matrix + presets) |
| `viewer` | Limited consumption (read-oriented; portal capabilities when `access_context=portal`) |

**Adding a fifth canonical role requires an Architecture RFC.** In ~95% of cases a new “user type” must be a **preset**, **scope**, **capability**, or **org** element — not a new role.

Legacy job-title strings (`recruiter`, `supervisor`, `hr_officer`, `compliance_officer`, …) are **migration aliases** → `employee` + preset.  
Legacy `client_manager` / `client_processor` are **migration aliases** → `viewer` + `access_context=portal` + scope (+ portal capabilities).

Aliases: `owner` / `admin` → `administrator`; historical synonyms normalize via `ROLE_ALIASES`.

External candidate / magic-link identities remain **non-CRM** (unchanged).

### 2. Six independent axes

| Axis | Meaning |
|------|---------|
| **Role** | How much the system trusts the principal |
| **Permissions** | What actions are allowed |
| **Preset** | Starter permission pack for a profession (not a security role) |
| **Org structure** | Team / `supervisor_id` / reporting |
| **Scope** | Which companies/objects |
| **access_context** | `tenant` \| `portal` — orthogonal to role |

**Forbidden:** treating any `viewer` as “portal client”. Internal director and portal guest may both be `viewer` with different `access_context` and scope.

### 3. Trust ceilings (non-negotiable)

Administrator may configure the **allowed operational area** of Employee/Viewer but **must not** lift trust ceilings:

| Capability | Superadmin | Admin | Employee | Viewer |
|------------|:----------:|:-----:|:--------:|:------:|
| Platform / tenants | yes | — | — | — |
| Tenant settings | yes | yes | — | — |
| Users / roles / access | yes | yes | — | — |
| Billing / subscription | yes | yes | — | — |
| Operational modules | yes | yes | configurable | configurable / read-oriented |
| Mutate business data | yes | yes | configurable | usually — |
| Portal capabilities | — | — | — | configurable |

API and UI **reject / disable** attempts to grant Admin-locked capabilities to Employee/Viewer.

### 4. Portal guests and monetization

- No HostFlow license → no Employee/Admin CRM seat.
- Portal membership → `role=viewer`, `access_context=portal`, company scope; optional portal capabilities (e.g. sign/comment) — **not** a separate role.
- Paying company with its own HF tenant uses Admin/Employee in **their** tenant (`access_context=tenant`).

### 5. Migration discipline

1. **Inventory gate** — [`rbac-role-usage-inventory.md`](rbac-role-usage-inventory.md) before deleting legacy role branches.
2. Path: aliases → permission/module gates → remove dead enum usage.
3. Post-cleanup CI: ban new job-title `Role.*` outside alias allowlist; new canonical role only with RFC.

### 6. Settings surface

Canonical UI: **Settings → Team → Roles & access** (tenant admin). Platform Tenants page may reuse the same matrix for superadmin.

---

## Consequences

- Personas and UAT journeys describe **presets** for Recruiter / Team lead / HR / Compliance; portal personas use Viewer + portal context.
- `require_roles(Role.recruiter, …)` becomes technical debt classified in inventory (`JOB_PROXY`) and migrated to permissions/module gates.
- Seat / plan counters move toward Admin / Employee / Viewer (+ non-billable portal guests).
- Org promotion (recruiter → team lead) changes preset + `supervisor_id`, not trust role.

---

## Alternatives considered

1. **Keep job-title roles** — rejected; does not scale.
2. **Fifth role `portal_guest`** — rejected; duplicates Viewer trust; use `access_context` instead.
3. **Fully free-form Employee matrix including admin rights** — rejected; breaks trust ceilings.

---

## Cross-references (updated in same change set)

- [`rbac_matrix.md`](rbac_matrix.md) — operating matrix + ceilings
- [`rbac-role-usage-inventory.md`](rbac-role-usage-inventory.md) — migration inventory
- [`personas.md`](../personas.md) — trust roles + presets + portal
- [`module-catalog-and-routing-map.md`](module-catalog-and-routing-map.md) — linkage
- Runtime: `backend/app/auth/deps.py`, `backend/app/auth/trust_roles.py`, tenants role matrix ceilings, Settings Roles & access UI
