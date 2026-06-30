# Module-owned pipelines P0 — Recruitment / company-scoped funnels

**Status:** Architecture gate before migration (L2 operating canon). **No migration PR merges without this gate marked satisfied in the PR checklist.**

**Owner:** Architecture canon + platform core team.

**Related (must stay consistent):**

- [`ADR-004-five-product-modules-and-billing-events.md`](ADR-004-five-product-modules-and-billing-events.md) — module independence, recruitment-only / HR-only tenants
- [`ADR-005-three-level-settings-hierarchy.md`](ADR-005-three-level-settings-hierarchy.md) — Company Module Settings
- [`process-engine.md`](../platform/process-engine.md) — shared evaluator; per-module system stages
- [`module-catalog-and-routing-map.md`](module-catalog-and-routing-map.md) — product keys, settings hierarchy
- [`invariants-recruitment-hr-document-hub.md`](invariants-recruitment-hr-document-hub.md) — HR never owns recruitment pipeline
- [`recruitment-domain-model.md`](recruitment-domain-model.md) — candidate / lead / vacancy ownership

---

## 1. Problem

HostFlow split **product modules** (Recruitment, HR, Fleet, …) in code and ADRs, but **process ownership** still lives in tenant-scoped CRM artifacts:

| Artifact | Current scope | Effect |
|----------|---------------|--------|
| `funnels` / `funnel_stages` | `tenant_id` only | One pipeline set for whole workspace |
| Legacy `system_stage` on stages | Four buckets shared by all funnel types | Implies one cross-module skeleton |
| `/meta/stages`, analytics, UI funnels | Tenant default funnel | Ignores `company_id` and `company_module_settings` |
| `RecruitmentModuleSettingsV1.default_candidate_funnel_id` | Stored, **not read** at runtime | Module settings hang in the air |

Until funnels are **company-scoped** and **module-owned**, HostFlow remains a **CRM with separated screens**, not a modular platform. **Module independence starts with process ownership**, not UI.

**P0 scope:** Recruitment pipelines only (`module_key=recruitment`, funnel `type` ∈ `candidate` | `lead`). HR employee pipeline, Fleet operational statuses, and module-settings UI forms are **explicitly after P0** (§9).

---

## 2. Canon (non-negotiable)

### 2.1 No universal skeleton for all modules

The legacy four values on `funnel_stages.system_stage` — `new`, `in_progress`, `hired`, `declined_rejected` — are **Recruitment-era analytics buckets**. They **must not** be treated as the platform-wide semantic model for HR, Fleet, Finance, or future modules.

**Semantic stages** live in **Process Engine per module namespace** (`recruitment.ready_for_handoff`, `hr.verification`, `fleet.assigned`, …). See [`process-engine.md`](../platform/process-engine.md) §3.1.

### 2.2 Process Engine = mechanism only

Platform Core provides:

- registries (`pe_system_stages`, profiles, pipelines, transition/handoff rules)
- runtime evaluator (`evaluate_transition`, `evaluate_handoff`)

Business modules **register** their stages and rules. Core **must not** encode Recruitment-, HR-, or Fleet-specific semantics except via **module manifests** and tenant/company seeds.

### 2.3 Pipelines belong to a module

| Owns | Does not own |
|------|----------------|
| Module: funnel definitions, stage labels, ordering, PE mapping, transition rules for its entities | Platform: evaluator, shared field/document registries |
| Company: which funnel is default, enabled module, process profile bindings | Tenant: license ceiling, default **presets** (copied into company on bootstrap) |

**Rule:** every funnel row carries **`module_key`** (ADR-004 product key). Recruitment P0 uses `module_key=recruitment`. `funnel.type` remains the **entity pipeline kind** inside the module (`candidate` | `lead`; `deal` is legacy — out of P0).

### 2.4 Funnels are company-scoped

Every operational funnel **must** have:

- `tenant_id` — RLS
- `company_id` — operational owner (FK → `companies.id`)
- `module_key` — ADR-004 key (`recruitment` in P0)

Uniqueness (target invariant after migration):

- At most one `is_default=true` per `(tenant_id, company_id, module_key, type)`.

API list/create/update **must** filter by company context. Tenant-wide funnels without `company_id` are **legacy only** during strangler period.

### 2.5 Legacy `system_stage` = strangler / analytics fallback only

During migration:

- **`pe_maps_to_module` + `pe_maps_to_code`** on `funnel_stages` are the **source of truth** for gate logic (already enforced for candidate funnels — Process Engine P4).
- Legacy `system_stage` may be **derived or preserved** for backward-compatible dashboards and external exports.
- **New code** must not implement business gates using the four-bucket `system_stage` alone.
- Removal of the column is a **later** migration; P0 **freezes** new dependence on it.

### 2.6 Module independence

A tenant with **Recruitment only** must function without HR manifests, HR funnels, or HR stages seeded. Resolver and UI **must not** assume another module is installed. Handoff rules stay inactive when target module is off ([`process-engine.md`](../platform/process-engine.md) P5).

---

## 3. Current state (as-is inventory)

| Location | Behaviour today |
|----------|-----------------|
| `backend/app/models/funnel.py` | `tenant_id`, `type`, `is_default`; no `company_id`, no `module_key` |
| `backend/app/modules/companies/crud.py` | `_ensure_default_funnel_if_missing` seeds **tenant** funnels on onboarding |
| `backend/app/api/v1/funnels.py` | CRUD scoped to `tenant_id`; legacy `SYSTEM_STAGES` four buckets |
| `backend/app/api/v1/meta.py` `/meta/stages` | Default **tenant** candidate funnel |
| `backend/app/schemas/company_module_settings_json.py` | `RecruitmentModuleSettingsV1.default_candidate_funnel_id` — unused at runtime |
| `backend/app/process_engine/manifests/recruitment.py` | Only recruitment manifest registered |
| `hostflow-frontend/.../FunnelsPage.tsx` | Tenant-wide settings UI |
| `backend/app/api/v1/analytics.py` `/analytics/funnel` | Aggregates `Candidate.stage` codes tenant-wide; not funnel-definition-aware |

---

## 4. Target data model (P0)

### 4.1 `funnels` table changes

| Column | Type | Notes |
|--------|------|-------|
| `company_id` | `String(36)` FK → `companies.id`, nullable → **NOT NULL** after backfill | Operational owner |
| `module_key` | `String(32)` NOT NULL default `'recruitment'` for backfill | Canonical ADR-004 key |

Indexes (recommended):

- `(tenant_id, company_id, module_key, type, is_default)`
- `(company_id, module_key)`

### 4.2 `funnel_stages` (no schema change required for P0)

Continue using:

- `pe_maps_to_module`, `pe_maps_to_code` — gate / evaluator truth
- `system_stage` — legacy analytics only (§2.5)
- `code`, `label`, `order`, `is_terminal`, `stage_contract_v1`, `conversion_root_v1` (lead)

### 4.3 Company Module Settings linkage

`RecruitmentModuleSettingsV1` (existing fields, now **wired**):

```yaml
default_candidate_funnel_id: uuid | null   # optional explicit default for candidate pipelines
# future P1+: default_lead_funnel_id
```

PATCH validates that referenced funnel belongs to **same company** and `module_key=recruitment`.

---

## 5. Funnel resolution (canonical)

Single service: **`resolve_recruitment_funnel`** (name illustrative) used by all runtime call sites.

**Inputs:** `tenant_id`, `company_id`, pipeline kind (`candidate` | `lead`), optional hints (`profile.funnel_id`, `vacancy` context).

**Resolution order for `candidate`:**

1. **`explicit_funnel_id`** (when passed to resolver): load by id; **Forbidden** if `funnel.company_id` ≠ request company; **NotFound** if missing — **never fallback**.
2. `company_module_settings.recruitment.settings_json.default_candidate_funnel_id` **if** set and funnel passes ownership check.
3. Company default: `funnels` where `(company_id, module_key, type, is_default=true)` — **at most one** per scope (partial unique index).
4. **Legacy strangler:** tenant-scoped funnel (`company_id IS NULL`) — log once per path.
5. Platform seed funnel `tenant_id='default'`.

**Funnel identity (canon):** `(company_id, module_key, type)` + display `name`. No «company default» without `module_key`.

**Errors:**

- Recruitment disabled → `403`
- No funnel after step 5 → `422`
- Explicit funnel wrong company → `403` (`RecruitmentFunnelForbiddenError`) — **no fallback**

---

## 5.1 Database invariants (M1/M2 gate)

| Invariant | Enforcement |
|-----------|-------------|
| One default per company scope | PostgreSQL partial unique index `uq_funnels_company_default_scope` on `(company_id, module_key, type) WHERE is_default` |
| One legacy default per tenant scope | `uq_funnels_tenant_legacy_default_scope` on `(tenant_id, module_key, type) WHERE company_id IS NULL AND is_default` |
| Clone preserves stage metadata | Backfill copies **all** `funnel_stages` columns except `id`, `funnel_id` (PE mapping, `system_stage`, `stage_contract_v1`, `conversion_root_v1`, order, terminal) |
| Profile funnel binding | `CandidateProfile` create/patch validates `funnel_id` vs `company_id` / `client_id`; cross-company → `403` |

Migration: `202606300002_funnels_default_uniqueness_p0` dedupes duplicate defaults before creating indexes.

---

## 6. Migration plan (Recruitment P0)

Work proceeds in **ordered PRs**; each PR references this gate.

### Phase M1 — Schema + backfill (Alembic)

1. Add nullable `company_id`, `module_key` to `funnels`.
2. Backfill script (same migration or data migration step):
   - Set `module_key='recruitment'` for all rows where `type IN ('candidate','lead','deal')`.
   - For each tenant with existing default funnels:
     - For each **operating company** with recruitment enabled (or all companies if `enabled_modules` null — product: treat as all tenant modules):
       - **Clone** tenant default funnel + stages into `(tenant_id, company_id, module_key, type)` OR **reassign** if single-company tenant.
     - Preserve stage ids **only** if reassignment; on clone, update `CandidateProfile.funnel_id`, `Lead.funnel_id`, and CMS references via mapping table **or** leave profiles pointing at legacy tenant funnel until M3 (document chosen strategy in PR — **prefer clone + CMS update** for multi-company tenants).
3. Set `company_id` NOT NULL for new writes; keep nullable read path until M4 removes strangler.

### Phase M2 — Resolver service + tests

- Implement `resolve_recruitment_funnel` (§5).
- Unit tests: CMS override, company default, legacy tenant fallback, module disabled, wrong-company funnel rejected.

### Phase M3 — Wire runtime

| Call site | Required change |
|-----------|-----------------|
| Candidate create / stage defaults | Resolve funnel; initial `Candidate.stage` = first stage of resolved funnel |
| Lead create / intake (`intake_decision`, conversion) | Resolve lead funnel; set `lead.funnel_id` |
| `GET /meta/stages` | Query param or header **`company_id`** (and optional `type=candidate|lead`); resolve funnel; return its stages |
| `CandidateProfile` / vacancy profile binding | Validate `funnel_id` company scope |
| Process Engine P4 mapping | Resolve via `resolve_candidate_funnel_id_for_runtime` (assignment helper → resolver) |

**M3 hardening (pre-M4 gate):**

| Concern | Canon |
|---------|-------|
| Single entry point | Runtime consumers call `recruitment_funnel_assignment` helpers; only `resolve_recruitment_funnel` performs resolution logic |
| Company change | `reconcile_candidate_funnel_on_company_change` / `reconcile_lead_funnel_on_company_change` rebind funnel via resolver — no stale cross-company `funnel_id` |
| Legacy fallback telemetry | `record_recruitment_funnel_resolve` on every resolve; `GET /meta/recruitment-funnel-metrics` (admin) exposes counters by source + `legacy_strangler_hits` |
| Direct `funnel_id` assignment | Legacy at seeds/migrations only; runtime paths listed below must use assignment helpers |

**Runtime entry-point audit (M3):**

| Path | Status | Notes |
|------|--------|-------|
| Candidate create | ✅ resolver via assignment | `resolve_recruitment_funnel_for_candidate` |
| Candidate update (company/vacancy) | ✅ reconcile | `reconcile_candidate_funnel_on_company_change` |
| Lead create (`leads/crud`) | ✅ assignment | `assign_recruitment_funnel_to_lead` |
| Lead intake POOL | ✅ assignment | explicit funnel validated via resolver |
| Lead re-route (`_processing`) | ✅ reconcile | on company change |
| `GET /meta/stages?company_id=` | ✅ resolver | direct call (read path) |
| `CandidateProfile` create/patch | ✅ validate | `validate_recruitment_funnel_id_for_company` |
| Process Engine stage mapping | ✅ assignment | `resolve_candidate_funnel_id_for_runtime` |
| `/analytics/funnel` | ✅ M5 | `company_id` + `pipeline_type`; funnel-bound stages; legacy explicit |
| Lead stage contracts | ✅ display resolve | per-lead when `company_id` set |
| Seeds / Alembic / demo bootstrap | ✅ M6 | company-scoped bootstrap; legacy read-only strangler |
| `_bootstrap_default_funnels_for_business_type` | ✅ M6 | per-company seed on operating company create/update |

### Phase M4 — API + UI

| Surface | Required change | Status |
|---------|-----------------|--------|
| `GET/POST/PATCH /api/v1/funnels` | Required `company_id` (query or body); filter lists by company + `module_key`; gate `company_allows_module(..., 'recruitment')` | ✅ |
| `hostflow-frontend` Funnels settings | Scope to **active company**; show module badge `recruitment` | ✅ |
| `FunnelSelector`, profile admin | Pass `company_id`; list company funnels only | ✅ |
| Company module settings UI | Display resolved default; picker for `default_candidate_funnel_id` on recruitment tab | ✅ |
| Legacy tenant funnels | Read-only via GET by id (strangler); excluded from list/create | ✅ |

### Phase M5 — Analytics strangler

| Surface | Required change | Status |
|---------|-----------------|--------|
| `/analytics/funnel` | `company_id` + `pipeline_type` (`candidate` \| `lead`, never mixed); optional `funnel_id`; stage order from resolved funnel | ✅ |
| Legacy dashboards | `legacy_tenant=true` explicit mode when `company_id` omitted; counts only stages in active funnel; `excluded_unbound` telemetry | ✅ |
| Metrics | `analytics_by_pipeline` counters (`candidate:recruitment_company`, `lead:legacy_tenant`, …) on `GET /meta/recruitment-funnel-metrics` | ✅ |
| Legacy dashboards | May continue grouping by funnel-local stage codes during strangler | documented |

### Phase M6 — Bootstrap path ✅

| Surface | Required change | Status |
|---------|-----------------|--------|
| `_bootstrap_default_funnels_for_business_type` | Per-company seed via `bootstrap_recruitment_funnels_for_company`; sets `company_id`, `module_key=recruitment` | ✅ |
| Own-company onboarding | Tenant settings only; **no** tenant-wide funnel creation | ✅ |
| Operating company create/update | Bootstrap candidate/lead funnels gated by recruitment module flags | ✅ |
| CMS pointer | Write `default_candidate_funnel_id` on bootstrap when unset; company module settings picker (M6+) | ✅ |
| Demo seed | Company-scoped funnel resolution; services demo bootstraps lead funnel on demo client company | ✅ |
| Legacy tenant funnels | Read-only strangler for demo/resolver; **no new** tenant-wide operational rows | ✅ |
| PE mapping | Candidate funnel stages mapped on first bootstrap | ✅ |

- Stop creating new tenant-wide funnels except `tenant_id='default'` platform seed and explicit legacy fallback paths (e.g. `driver_ce_default` when no operating company).

---

## 7. Acceptance criteria (gate checklist)

P0 gate is **closed** when all are true:

- [ ] Alembic migration applied; no funnel intended for operations has `company_id IS NULL` except documented platform seed / strangler rows under feature flag.
- [ ] `resolve_recruitment_funnel` covered by tests for full chain (§5).
- [ ] Candidate and lead creation use resolver; wrong-company funnel rejected on profile PATCH.
- [ ] `/meta/stages` returns stages for **company-scoped** funnel when `company_id` provided.
- [x] Funnels API requires company context; recruitment module gate enforced.
- [x] SPA funnels UI lists/edits company funnels only (`FunnelsPage`, `FunnelSelector`).
- [x] `/analytics/funnel` company-scoped with explicit legacy mode; pipeline types not mixed (M5).
- [ ] No **new** runtime gate logic reads only legacy four-bucket `system_stage`.
- [x] `RecruitmentModuleSettingsV1.default_candidate_funnel_id` read on resolver path step 2.
- [x] Partial unique indexes for default funnel per `(company_id, module_key, type)` — migration `202606300002`.
- [x] `CandidateProfile` funnel_id validated vs company on create/patch.
- [x] M3 wired: candidate create, lead create, `GET /meta/stages?company_id=` (resolver).
- [x] M3 hardening: assignment helpers, company-change reconcile, resolver metrics, runtime entry-point audit (§6 M3).
- [ ] Legacy tenant funnel still works for unmigrated profiles until strangler removed (logged + metrics).
- [ ] Documentation: [`recruitment/module-scope.md`](../../recruitment/module-scope.md) updated with company-scoped funnel ownership.

---

## 8. Explicitly out of scope (P0)

Do **not** start these until §7 gate is closed:

| Item | Reason |
|------|--------|
| HR Process Engine manifest + employee pipeline | Depends on company-scoped funnel pattern |
| HR module settings UI forms | Depends on HR pipeline + CMS |
| Fleet / Services / Finance pipelines | Separate module keys |
| Removing `system_stage` column | Strangler period |
| Removing tenant-wide funnels entirely | After profile/backfill migration complete |
| Full Process Profile UI on vacancy | Orthogonal; keep PE P3 binding |
| `deal` funnel type | Legacy; not recruitment P0 |

---

## 9. Follow-on (after P0)

Ordered product/tech sequence:

1. **HR manifest** — register `hr.*` system stages in Process Engine.
2. **HR employee pipeline** — company-scoped funnels with `module_key=hr`, resolver `resolve_hr_funnel`.
3. **Module settings UI** — typed forms for `RecruitmentModuleSettingsV1` / `HrModuleSettingsV1` (replace JSON editor).
4. **Strangler removal** — drop tenant-scoped operational funnels; remove legacy `system_stage` dependence from analytics.

---

## 10. Enforcement notes for PR authors

- Funnel queries without `company_id` filter → **reject in review** unless strangler fallback module with `# TODO(strangler)` and test.
- New funnel seeds at tenant scope → **reject**; use company bootstrap.
- Cross-module funnel reuse → **reject**; handoff uses PE handoff rules, not shared funnel rows.
- Reference this document in migration PR title/body: `Gate: module-owned-pipelines-p0`.

---

## History

- 2026-06: P0 architecture gate — Recruitment company-scoped funnels, resolver canon, migration phases, explicit deferral of HR pipeline and module-settings UI.
- 2026-06: M1/M2 hardening — default funnel partial unique indexes, full stage clone on backfill, explicit funnel Forbidden (no fallback), profile funnel gate, M3 resolver wiring (candidate/lead create, `/meta/stages`).
