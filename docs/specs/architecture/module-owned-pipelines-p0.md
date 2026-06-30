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

1. Explicit `funnel_id` on entity/profile **if** funnel belongs to `(company_id, module_key=recruitment, type=candidate)` — validate on write.
2. `company_module_settings.recruitment.settings_json.default_candidate_funnel_id` **if** set and funnel passes ownership check.
3. Company default: `funnels` where `company_id`, `module_key=recruitment`, `type=candidate`, `is_default=true`.
4. **Legacy strangler:** tenant-scoped funnel (`company_id IS NULL`) with `tenant_id` match and `is_default=true` — **log deprecation once per request path**.
5. Platform seed funnel `tenant_id='default'` — last resort for empty tenants.

**Resolution order for `lead`:** same pattern; settings field `default_lead_funnel_id` is **optional follow-up** inside P0 if not in schema yet — until then step 3 uses company default lead funnel only.

**Errors:**

- If Recruitment module not enabled for company → `403` / structured error (no silent fallback to another module).
- If no funnel resolved after step 5 → `422` with actionable message (admin must configure company funnel).

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
| Process Engine P4 mapping | Unchanged logic; funnel must belong to company when passed to mapping helpers |

### Phase M4 — API + UI

| Surface | Required change |
|---------|-----------------|
| `GET/POST/PATCH /api/v1/funnels` | Required `company_id` (query or body); filter lists by company + `module_key`; gate `company_allows_module(..., 'recruitment')` |
| `hostflow-frontend` Funnels settings | Scope to **active company**; show module badge `recruitment` |
| `FunnelSelector`, profile admin | Pass `company_id`; list company funnels only |
| Company module settings UI | Display resolved default; optional picker for `default_candidate_funnel_id` (minimal — full forms after P0) |

### Phase M5 — Analytics strangler

| Surface | Required change |
|---------|-----------------|
| `/analytics/funnel` | Accept `company_id`; optional `funnel_id`; stage order from resolved funnel labels/order when provided |
| Legacy dashboards | May continue grouping by `Candidate.stage` code; document that codes are **funnel-local**, not global semantics |

### Phase M6 — Bootstrap path

- Replace `_bootstrap_default_funnels_for_business_type` tenant seed with **per-company** seed on company create / module enable:
  - Copy tenant preset → company funnel row
  - Write `company_module_settings.recruitment.default_candidate_funnel_id` if product wants explicit pointer
- Stop creating new tenant-wide funnels except `tenant_id='default'` platform seed.

---

## 7. Acceptance criteria (gate checklist)

P0 gate is **closed** when all are true:

- [ ] Alembic migration applied; no funnel intended for operations has `company_id IS NULL` except documented platform seed / strangler rows under feature flag.
- [ ] `resolve_recruitment_funnel` covered by tests for full chain (§5).
- [ ] Candidate and lead creation use resolver; wrong-company funnel rejected on profile PATCH.
- [ ] `/meta/stages` returns stages for **company-scoped** funnel when `company_id` provided.
- [ ] Funnels API requires company context; recruitment module gate enforced.
- [ ] SPA funnels UI lists/edits company funnels only.
- [ ] No **new** runtime gate logic reads only legacy four-bucket `system_stage`.
- [ ] `RecruitmentModuleSettingsV1.default_candidate_funnel_id` read on resolver path step 2.
- [ ] Legacy tenant funnel still works for unmigrated profiles until strangler removed (logged).
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
