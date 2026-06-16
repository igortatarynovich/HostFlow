# Module Registry / Marketplace Installation

**Status:** P0 audit canon  
**Owner:** Platform owner + architecture canon owner  
**Scope:** Platform Core foundation layer for module registration, installation state, capabilities, dependencies, and runtime guard contracts.

## 1. Purpose / non-goals

HostFlow already has multiple places that answer “is this module available here?”:

- tenant-level JSON flags;
- company-level module overrides;
- role/user module visibility matrices;
- Process Engine handoff rules;
- Field Registry manifests;
- HR/Fleet route guards;
- tenant links and portal flags;
- marketplace/integration installation rows.

P0 exists to make that implicit surface visible before runtime code is changed.

**Purpose:**

- define one canonical language for module lifecycle and installation state;
- audit current legacy flags and guards;
- draft registry, installation, capability, dependency, and guard contracts;
- produce a P1 plan that can migrate existing behavior without changing business runtime semantics first.

**Non-goals for P0:**

- no runtime code changes;
- no new API routes;
- no data migration;
- no marketplace UI;
- no billing activation rewrite;
- no HR/Fleet/recruitment workflow changes;
- no replacement of existing guards until P1+.

## 2. Current audit map

### 2.1 Tenant settings and role matrix

| Area | Current source | Meaning today | Drift / risk |
|------|----------------|---------------|--------------|
| Tenant module flags | `Tenant.settings["modules"]`; `backend/app/api/v1/tenants/service.py::get_module_settings_snapshot` | Workspace-level module visibility/availability. Defaults are permissive. | JSON blob is acting as installation, enablement, UI visibility, and partial entitlement at once. |
| Tenant module API | `GET/PATCH /api/v1/settings/team/modules`; `backend/app/api/v1/settings/team.py` | Lets tenant admins toggle module flags. | API is settings-based, not installation-based. Unknown keys are rejected by service defaults. |
| Platform tenant admin | `GET/PATCH /api/v1/platform/tenants/{id}/modules`; `backend/app/api/v1/platform/tenants.py` | Superadmin module toggle surface. | Same backing JSON as tenant team settings. |
| Role module matrix | `Tenant.settings["modules"]["role_matrix"]`; `get_role_module_matrix_snapshot` | Role-level visible/editable matrix per module flag. | Combines permissions with module state; not a canonical installation record. |
| User module overrides | `Tenant.settings["modules"]["user_overrides"]`; `get_user_module_overrides_snapshot` | Per-user role matrix override. | Override can only speak in existing module keys and inherits tenant flag semantics. |
| Frontend permissions | `hostflow-frontend/src/hooks/usePermissions.ts` | Merges role permissions, effective role module matrix, and tenant modules. | Frontend has local module defaults and permission-to-module maps that can drift from backend. |

### 2.2 Product module keys and company scope

| Area | Current source | Meaning today | Drift / risk |
|------|----------------|---------------|--------------|
| Product module key list | `backend/app/constants/product_module_keys.py::COMPANY_MODULE_SETTING_KEYS` | Canonical keys for `company_module_settings`: `recruitment`, `hr`, `fleet`, `services`, `finance`. | Separate from tenant settings keys, which also include legacy granular flags. |
| Company module overrides | `companies.enabled_modules`; migration `202605070001_companies_enabled_modules.py`; service `company_module_access.py` | Company-level intersection with tenant modules. Missing keys default to enabled relative to tenant. | Nullable JSON is an override, not an installation row. |
| Company module settings | `company_module_settings`; migration `202605080001_company_module_settings.py`; API `company_module_settings.py` | Per-company module configuration and `is_enabled` field. | `is_enabled` overlaps semantically with `enabled_modules`; API still gates by `company_allows_module`. |
| Recruitment company enforcement | `company_module_enforcement.py` | Candidate/vacancy operations partially enforce company-level `recruitment`. | Enforcement is module-specific and incomplete across leads/listing/other modules. |
| Company onboarding defaults | `backend/app/modules/companies/crud.py::_onboarding_module_profile` | Sets tenant module presets by company/business type. | Onboarding writes availability decisions into tenant settings, not registry state. |

### 2.3 Process Engine

| Area | Current source | Meaning today | Drift / risk |
|------|----------------|---------------|--------------|
| Module manifests | `backend/app/process_engine/manifests/recruitment.py` | Process Engine registry rows are seeded per manifest module. | Module existence is implied by manifest registration, not tied to installed/enabled lifecycle. |
| Handoff enabled rules | `enabled_when.modules_installed` in PE handoff rules | Handoff rules depend on installed module names. | Uses a conceptual installed module set, but the set is derived from tenant settings. |
| Installed modules shim | `backend/app/process_engine/handoff_evaluator.py::get_installed_modules` | Always includes `recruitment`; adds `hr` and `client_portal` from tenant settings. | Hardcoded, partial, not company-scoped, not marketplace-aware. |
| HR handoff gate | `_destination_types_for_mode` and `resolve_handoff_destinations` | Internal HR destination requires `hr` installed. | Correct behavior conceptually, but source of installation is non-canonical. |

### 2.4 Field Registry

| Area | Current source | Meaning today | Drift / risk |
|------|----------------|---------------|--------------|
| Module-scoped manifests | `backend/app/field_registry/manifests/{platform,recruitment,crm,hr,fleet}.py` | Modules register canonical fields and default card layouts. | Registration does not depend on installation state; currently this is acceptable foundation behavior. |
| Registry seed | `backend/app/field_registry/seed.py` | Seeds platform and tenant field/layout artifacts for all known manifests. | Seed registration can be confused with module installation unless lifecycle terms are explicit. |
| Effective layout API | `/api/v1/platform/field-registry/effective-layout` | Resolves layouts by module/entity/layout code. | API should remain readable for registered modules; consuming UI/runtime should apply installation guards separately. |

### 2.5 Navigation and frontend visibility

| Area | Current source | Meaning today | Drift / risk |
|------|----------------|---------------|--------------|
| Sidebar module filter | `hostflow-frontend/src/components/nav/Sidebar.tsx` | Maps nav item keys to `TenantModuleSettings` keys and hides disabled modules. | Local item-to-module map; no capabilities; no company scope. |
| Frontend module types | `hostflow-frontend/src/api/types/user.ts`, legacy `src/api/types.ts` | TS shape for tenant module settings. | Type keys can drift from backend defaults and product module canon. |
| Admin module labels | `hostflow-frontend/src/modules/tenants/constants.ts` | Labels for tenant module toggles. | UI labels are keyed to TS shape; missing keys make modules invisible in admin UX. |
| Route availability | `hostflow-frontend/src/app/routeBundles/*`, `src/app/routes.tsx` | Routes are bundled regardless of installation; visibility mostly via nav/permissions. | Direct route access may rely on backend guards; not all routes have module guards. |

### 2.6 Permissions

| Area | Current source | Meaning today | Drift / risk |
|------|----------------|---------------|--------------|
| Backend roles | `backend/app/auth/deps.py` and per-route `require_roles` | Role-based access to endpoints. | Roles do not encode module installation; module guards are separate and uneven. |
| Frontend permissions | `usePermissions.ts` | Role permissions are filtered by tenant module flags and role module matrix. | Frontend can hide UI but does not guarantee backend denial. |
| Fleet roles | `backend/app/auth/fleet_access.py::_FLEET_MODULE_ROLES` | Fleet API role allowlist plus tenant fleet flag. | Dedicated guard exists for Fleet but not uniformly applied to every fleet router entry point. |
| HR roles | `backend/app/auth/hr_workforce_access.py` plus route role deps | HR workforce APIs require tenant HR flag. | Stronger than nav, but scoped to selected HR routes only. |

### 2.7 Tenant links and handoff flags

| Area | Current source | Meaning today | Drift / risk |
|------|----------------|---------------|--------------|
| Tenant links | `TenantLink.features_json` | Handoff features between agency and client/company. | Link feature flags act as channel enablement, not module installation. |
| Client portal tenant flag | `Tenant.client_portal_enabled` | Tenant-level portal availability. | Separate from `tenant.settings.modules.client_portal`; two sources can diverge. |
| Handoff service guard | `backend/app/services/handoff.py` | `internal_hr` destination requires tenant link feature `handoff_to_internal_hr`. | Does not by itself prove HR module installation; PE evaluator covers that separately. |
| Handoff routing pure logic | `candidate_handoff_routing.py` | Accepts booleans for HR module and portal/link availability. | Caller owns correctness; no canonical resolver supplies those booleans. |

### 2.8 HR/Fleet guards

| Area | Current source | Meaning today | Drift / risk |
|------|----------------|---------------|--------------|
| HR workforce gate | `backend/app/auth/hr_workforce_access.py::require_hr_workforce_module_access` | Blocks workforce API when `tenant.settings.modules.hr` is false. | Tenant-only; no company install state; no capability granularity. |
| HR APIs using gate | `backend/app/api/v1/workforce/router.py`, `hr_inbox.py`, `hr_dashboard.py` | HR endpoints guarded through dependency. | Coverage is route-by-route. |
| Fleet gate | `backend/app/auth/fleet_access.py::require_fleet_module_access` | Blocks fleet API when tenant fleet flag is false and role is not allowed. | Tenant-only; no company install state; some fleet routers/status may only use tenant access. |
| Fleet APIs | `backend/app/api/v1/fleet/*` | Fleet operational endpoints under `/api/v1/fleet`. | Need P1 coverage scan for every router include and status endpoint. |

### 2.9 Seeds and defaults

| Area | Current source | Meaning today | Drift / risk |
|------|----------------|---------------|--------------|
| Tenant creation/provisioning | `backend/app/api/v1/tenants/service.py`, platform tenant router | Creates tenant settings/license/admin data. | Module installation defaults are implicit in JSON defaults. |
| Company onboarding | `backend/app/modules/companies/crud.py::_bootstrap_tenant_settings_for_company_type` | Mutates tenant module defaults based on business type. | Preset logic should eventually emit installation defaults or recommendations, not mutate product lifecycle directly. |
| Process Engine seed | `backend/app/process_engine/seed.py` | Seeds PE manifests for recruitment. | Registered process artifacts are not installation state. |
| Field Registry seed | `backend/app/field_registry/seed.py` | Seeds canonical fields/layouts for registered modules. | Registered field artifacts are not installation state. |
| Reference/document seeds | `backend/app/reference/*`, document pack seeds | Module-specific defaults exist across reference and document layers. | Need P1 inventory of module-owned defaults versus platform defaults. |

### 2.10 API routes without uniform installation check

| Area | Current source | Current behavior | P1 question |
|------|----------------|------------------|-------------|
| Recruitment | `candidates`, `vacancies`, `leads`, `handoffs`, `recruiters`, `funnels` | Partial company-level recruitment enforcement for candidates/vacancies; no single tenant dependency. | Define whether `recruitment` product gate is triad-derived, explicit, or both during migration. |
| Services | `services`, `additional-services`, service order surfaces | Tenant `services` flag affects UI/permissions, but no single backend module gate is documented. | Decide product-level guard and capabilities. |
| Finance | `invoices`, billing/settings routes | Finance is a product module in docs, but billing settings are also platform/subscription concerns. | Separate Finance module runtime from platform billing administration. |
| Fleet | `/api/v1/fleet/*` | Dedicated fleet dependency exists, but route coverage must be verified. | P1 closure guard should assert all operational fleet routers use the canonical guard. |
| HR | `/api/v1/workforce/*`, HR inbox/dashboard | Dedicated HR dependency exists on key surfaces. | P1 closure guard should assert all HR runtime routes use the canonical guard. |
| Public portals/forms | public intake, candidate/client portal | Public access is token/link/channel based. | Do not force product module guard directly; resolve via publication/link capability. |

## 3. Canonical module lifecycle

P1 should distinguish these states explicitly:

| State | Meaning | Data owner | Runtime implication |
|-------|---------|------------|---------------------|
| `registered` | Module exists in platform catalog with manifest, capabilities, dependencies, and owned namespaces. | Platform Core | Artifacts may be seeded and resolvable. Does not grant tenant access. |
| `installed` | Tenant has the module/app installed or entitled. | Tenant installation state | Module may appear in admin/settings and can be enabled where allowed. |
| `enabled` | Installed module is active for a tenant, company, user role, or capability context. | Tenant/company settings and role policy | Runtime guards may allow access if role/company/capability checks also pass. |
| `suspended` | Installed module remains configured but is temporarily disabled by billing, admin, compliance, or support action. | Platform/admin policy | Runtime guards deny access but preserve configuration. |
| `uninstalled` | Tenant removed the installation. | Tenant installation state | Runtime guards deny access; module-owned settings may be retained for restore or archived per retention policy. |

Important distinction:

- **Registered** is platform catalog state.
- **Installed** is tenant entitlement/lifecycle state.
- **Enabled** is operational availability after tenant/company/role/capability checks.

## 4. Registry schema draft

P1 should introduce a registry without replacing all legacy flags in one step.

### `module_registry`

| Column | Draft type | Purpose |
|--------|------------|---------|
| `id` | UUID/string | Stable registry row id. |
| `module_code` | string unique | Canonical code, e.g. `recruitment`, `hr`, `fleet`, `documents`, `process_engine`, `field_registry`. |
| `kind` | enum/string | `business_module`, `platform_capability`, `core_integration`, `marketplace_app`. |
| `display_name` | string | Human label. |
| `owner` | string | Owning module/platform team. |
| `status` | enum/string | `registered`, `deprecated`, `hidden`. |
| `registry_version` | string | Manifest version. |
| `manifest` | JSON | Capabilities, dependencies, namespaces, routes, seed hooks, docs links. |
| `is_system` | bool | True for platform-shipped modules. |
| `created_at` / `updated_at` | timestamp | Audit. |

### `tenant_module_installations`

| Column | Draft type | Purpose |
|--------|------------|---------|
| `id` | UUID/string | Stable row id. |
| `tenant_id` | UUID/string | Tenant scope. |
| `module_code` | string FK/logical FK | Registry module code. |
| `state` | enum/string | `installed`, `enabled`, `suspended`, `uninstalled`. |
| `source` | enum/string | P1: `migration` or `system`; future: `plan`, `addon`, `marketplace`, `admin`. |
| `settings_json` | JSON | Tenant-level module settings that are truly lifecycle/config, not company runtime config. |
| `metadata_json` | JSON | Migration markers, billing refs, support notes. |
| `created_at` / `updated_at` | timestamp | Audit. |

### `module_capabilities`

| Column | Draft type | Purpose |
|--------|------------|---------|
| `id` | UUID/string | Stable capability row id. |
| `module_code` | string | Owning registry module code. |
| `capability_code` | string unique within module | Canonical capability, e.g. `hr.workspace.view`. |
| `kind` | enum/string | `route_access`, `write_access`, `registry_access`, `process_transition`, `runtime_evaluator`. |
| `display_name` | string | Human label. |
| `description` | string nullable | Optional documentation. |
| `default_enabled` | bool | Default capability availability under an enabled installation. |
| `config` | JSON | Future policy/dependency metadata. |
| `created_at` / `updated_at` | timestamp | Audit. |

### `module_dependencies`

| Column | Draft type | Purpose |
|--------|------------|---------|
| `id` | UUID/string | Stable dependency row id. |
| `module_code` | string | Module declaring the dependency. |
| `dependency_module_code` | string | Required or optional counterpart module. |
| `dependency_kind` | enum/string | P1 uses `optional`; future can add required/plan-gated dependency types. |
| `capability_code` | string nullable | Capability activated or constrained by the dependency. |
| `config` | JSON | Activation metadata, e.g. handoff surfaces. |
| `created_at` / `updated_at` | timestamp | Audit. |

### `company_module_installations`

| Column | Draft type | Purpose |
|--------|------------|---------|
| `id` | UUID/string | Stable row id. |
| `tenant_id` | UUID/string | Tenant scope. |
| `company_id` | UUID/string | Company scope. |
| `module_code` | string | Registry module code. |
| `state` | enum/string | `enabled`, `suspended`, `disabled`, `uninstalled`. |
| `settings_ref` | string nullable | Points to `company_module_settings` row where applicable. |
| `metadata_json` | JSON | Migration/override notes. |

P1 may implement tenant rows first and keep `companies.enabled_modules` as compatibility until company state migration is designed.

## 5. Tenant/company installation state

Canonical availability should resolve in layers:

1. **Registry:** module key exists and is `registered`.
2. **Tenant installation:** tenant has module `installed` or `enabled`; `suspended/uninstalled` deny.
3. **Tenant enabled flag:** during migration, legacy `tenant.settings.modules[key]` is read as compatibility input.
4. **Company state:** company module state or legacy `Company.enabled_modules` intersects with tenant state.
5. **Capability:** requested action is covered by module capabilities and not disabled.
6. **Role/user policy:** role matrix and user override allow visible/editable action.
7. **Runtime context:** tenant link, public token, process profile, or handoff destination can further narrow availability.

P1 compatibility rule:

- existing `tenant.settings.modules` remains readable and writable;
- resolver backfills/derives tenant installation rows from existing flags;
- existing APIs keep response shapes until clients migrate.

## 6. Capability model

A module should expose capabilities that guards can check without hardcoding every route to a product key.

Draft capability shape:

```yaml
module_key: hr
capabilities:
  - key: hr.workspace.view
    kind: route_access
    default_enabled: true
  - key: hr.employee.manage
    kind: write_access
    default_enabled: true
  - key: hr.handoff.accept
    kind: process_transition
    requires:
      modules: [recruitment, hr]
```

Initial capability groups:

| Module | Baseline capabilities |
|--------|-----------------------|
| `recruitment` | candidate view/manage, vacancy view/manage, lead intake, handoff submit, PE recruitment profiles |
| `hr` | workforce workspace view/manage, employee card layout, internal HR handoff accept, HR documents |
| `fleet` | fleet workspace view/manage, vehicle card layout, assignments, operating lines |
| `services` | service/order workspace view/manage, catalog management |
| `finance` | finance workspace view/manage, invoices, billing event consumption |
| `client_portal` | portal link access, client handoff decisions |

Capabilities are not a replacement for RBAC. They answer “is this installed/enabled surface available?” RBAC answers “may this user perform this action?”

## 7. Dependency model

Dependencies should be manifest-level data, not hardcoded service booleans.

Draft dependency shape:

```yaml
module_key: recruitment
dependencies:
  optional:
    - module_key: hr
      activates: [handoff.internal_hr]
    - module_key: client_portal
      activates: [handoff.client_portal]
  requires_platform:
    - process_engine
    - field_registry
    - document_hub
```

Rules:

- A module can be installed without every optional dependency.
- A capability can require another module/capability to be enabled.
- Process Engine `enabled_when.modules_installed` should migrate to dependency/capability checks.
- Field Registry manifests stay registered even if a tenant has not installed a module.
- Public links and tenant links are channel enablement, not product installation by themselves.

## 8. Runtime guard contract

P1 should introduce a single read-only resolver first:

```python
resolve_module_access(
    tenant_id: str,
    module_key: str,
    *,
    company_id: str | None = None,
    capability: str | None = None,
    user_id: str | None = None,
    role: str | None = None,
    context: dict | None = None,
) -> ModuleAccessDecision
```

Draft decision:

```python
{
    "allowed": bool,
    "module_key": "hr",
    "state": "enabled",
    "source": "tenant_installation|legacy_tenant_modules|company_override|role_matrix|dependency",
    "capability": "hr.workspace.view",
    "reasons": [],
}
```

Guard contract:

- Backend route dependencies call the resolver, not raw `tenant.settings.modules`.
- Process Engine handoff evaluator calls the resolver for module/capability availability.
- Frontend may consume a read API for visibility but backend remains authoritative.
- Registry seed and manifest registration do not imply access.
- Superadmin bypass must be explicit and audited.

## 9. Migration map

| Legacy surface | P1 target | Migration notes |
|----------------|-----------|-----------------|
| `tenant.settings.modules` | `tenant_module_installations` plus compatibility snapshot | Keep existing PATCH/read APIs; write-through to installation rows in P1/P2. |
| `recruitment` derived from `candidates ∧ leads ∧ vacancies` | Explicit `recruitment` product installation plus legacy triad compatibility | Define whether triad remains UI-only or becomes capabilities under recruitment. |
| `Company.enabled_modules` | `company_module_installations` or compatibility adapter | Keep nullable override behavior until company installation table exists. |
| `company_module_settings.is_enabled` | Module configuration state, not install entitlement | Clarify whether this remains “configured/enabled settings row” or migrates into company installation state. |
| HR/Fleet deps | `resolve_module_access(..., module_key, capability)` | Replace raw tenant flag reads after resolver is tested. |
| PE `get_installed_modules` | Module registry resolver adapter | Preserve current output while moving source of truth. |
| PE `enabled_when.modules_installed` | `enabled_when.capabilities` or dependency resolver | Keep manifest compatibility in P1. |
| Field Registry manifests | `platform_module_registry.manifest.field_registry` metadata | Registration remains platform-global/tenant-seeded; access applied by consuming surfaces. |
| Tenant link `features_json` | Capability/channel context | Link flags constrain handoff channel, not module installation. |
| `Tenant.client_portal_enabled` | `client_portal` installation/capability state | Reconcile with `tenant.settings.modules.client_portal`. |
| Integration installation rows | Shared installation lifecycle pattern | Reuse concepts from `tenant_integration_installations` and `company_integration_enablements` for marketplace apps. |
| Frontend local module defaults | Read API generated from registry/installations | Keep TS compatibility until backend exposes canonical DTO. |

## 10. P1 implementation plan

P1 should be a foundation slice with compatibility, not a runtime rewrite.

1. **Catalog manifest:** create canonical baseline manifest for `recruitment`, `hr`, `fleet`, `documents`, `process_engine`, and `field_registry`.
2. **Schema:** add `module_registry`, `tenant_module_installations`, `module_capabilities`, and `module_dependencies`.
3. **Seed:** idempotently seed registered modules, capabilities, dependencies, and tenant installation rows from current `tenant.settings.modules` compatibility data.
4. **Read resolver:** implement read-only `is_module_installed(tenant_id, module_code)` with canonical-row first lookup and legacy fallback.
5. **Read API:** expose installed modules plus capabilities without replacing existing tenant settings or module settings endpoints.
6. **Compatibility:** preserve current tenant settings / company module behavior; P1 does not rewrite route guards or activation flows.
7. **Closure tests:** assert registered catalog, idempotent seed, lifecycle states, capability reads, and read API payload shape.
8. **No runtime behavior change:** HR/Fleet runtime, route guards, billing, marketplace UI, and activation flow stay untouched.

P1 DoD:

- canonical registry manifest exists;
- tenant installation rows seed idempotently;
- existing tenants upgrade without losing current module flags;
- read resolver returns canonical decisions with legacy fallback for covered cases;
- installed-module read API returns capabilities and dependency metadata;
- docs and closure tests cover migration boundaries.

### P1 status

Status: **Done**.

Implemented foundation pieces:

- `module_registry` stores registered platform and business modules.
- `tenant_module_installations` stores tenant-level installation lifecycle state.
- `module_capabilities` stores capability metadata exposed by read API.
- `module_dependencies` stores optional dependency metadata for future guard migration.
- Baseline seed covers `recruitment`, `hr`, `fleet`, `documents`, `process_engine`, and `field_registry`.
- Resolver remains read-only and preserves compatibility with legacy `tenant.settings.modules`.
- Read API exposes `/api/v1/platform/module-registry/installed-modules` and `/api/v1/platform/module-registry/installed-modules/{module_code}/installed`.
- P1 intentionally does not change billing, marketplace UI, activation flow, HR/Fleet runtime, or route guards.

## 11. P2 runtime guard integration — compatibility mode

P2 makes Module Registry the first source for module availability checks without removing legacy tenant settings.

Status: **Done**.

Implemented compatibility-mode behavior:

- Process Engine `get_installed_modules()` resolves via Module Registry first and keeps legacy fallback through the resolver.
- Existing HR workforce access dependency checks `hr` through `is_module_installed()` while preserving the same denied contract.
- Existing Fleet access dependency checks `fleet` through `is_module_installed()` while preserving role checks and denied contract.
- Read helpers expose available module codes for navigation/API visibility without hard route rewrite.
- Static guard test blocks new direct module availability checks against legacy `tenant.settings.modules` outside the compatibility allowlist.

P2 intentionally does not change:

- billing;
- marketplace UI;
- install/uninstall activation flow;
- hard route blocking semantics;
- HR/Fleet business runtime;
- legacy tenant settings storage or APIs.
