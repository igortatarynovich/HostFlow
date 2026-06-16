# Process Engine — platform capability canon

**Status:** Accepted (architecture canon). **Implementation: P0–P6 complete** (registry → evaluator → profile binding → pipeline mapping → handoff rules → profile-scoped gates). **Closure gate:** `test_process_engine_closure.py`.  
**Hierarchy:** L2 operating canon — platform layer. Supersedes ad-hoc «recruitment pipeline gate» framing as the **strategic** source of truth for process rules.  
**Owner:** Architecture canon + platform core team.

### P1 implementation status (2026-08-14)

| Deliverable | Status | Location |
|-------------|--------|----------|
| Registry ORM models | Done | `backend/app/models/process_engine.py` |
| Alembic migration | Done | `backend/alembic/versions/202608140001_process_engine_registry_p1.py` |
| Recruitment module manifest | Done | `backend/app/process_engine/manifests/recruitment.py` |
| Registry upsert service | Done | `backend/app/process_engine/registry.py` |
| Tenant seed (default profile) | Done | `backend/app/process_engine/seed.py` → wired in `backend/app/seed.py` |
| Legacy mapping columns | Done | `candidate_profiles.pe_process_profile_id`, `funnel_stages.pe_maps_to_*` |
| Transition evaluator adapter | Done | `backend/app/process_engine/evaluator_adapter.py` → delegates to `TransferPolicyResolver` |
| P2 facade wiring (API/service → adapter) | Done | `candidates/service.py`, `candidates/router.py`, `recruitment_package_readiness.py` |
| P3 vacancy profile binding | Done | `vacancies.pe_process_profile_id`, `process_engine/profile_resolver.py` |
| P4 pipeline mapping | Done | `FunnelStage.pe_maps_to_*`, `process_engine/pipeline_mapping.py` |
| P5 handoff rule activation | Done | `process_engine/handoff_evaluator.py`, `TransitionEvaluatorAdapter.evaluate_handoff` |
| P6 profile-scoped stage gates | Done | `process_engine/transition_rules_adapter.py`, `TransitionEvaluatorAdapter.resolve_hiring_pipeline_gates` |
| Tests | Done | `test_process_engine_p1.py` … `test_process_engine_p6.py`, `test_process_engine_closure.py` |

**Not changed in P1–P6 (compat):** `TransferPolicyResolver` document/package layers, `CandidateProfile` config, legacy funnel `code` / `system_stage`, `tenant_links` storage. **`hiring_stage_gates_v1` tenant settings blob** remains as legacy fallback and Settings editor storage (deprecated for runtime).

### P3 migration notes (2026-08-16)

| Change | Detail |
|--------|--------|
| Alembic | `202608160001_vacancy_process_profile_binding_p3` — adds `vacancies.pe_process_profile_id` FK → `pe_process_profiles` |
| Resolver | `resolve_effective_process_profile(vacancy, tenant)` — order: vacancy → legacy `candidate_profile_id` bridge → tenant default → system `recruitment_default` |
| Candidate | `TransitionEvaluatorAdapter.resolve_effective_process_profile_for_candidate_id` — stage logic entry (via vacancy) |
| Seed | `ensure_recruitment_process_engine_defaults` asserts `recruitment_default`; backfills vacancy PE profile where null |
| Not in P3 | Vacancy UI profile picker, pipeline UI, HR, handoff registry activation, `CandidateProfile` removal |

### P4 migration notes (2026-08-17)

| Change | Detail |
|--------|--------|
| Mapping module | `process_engine/pipeline_mapping.py` — sync, validate, runtime qualified stage resolution |
| FunnelStage | `pe_maps_to_module='recruitment'`, `pe_maps_to_code=<system stage>` enforced on candidate funnel writes |
| Sync | `sync_funnel_stages_from_pipeline_config` + `ensure_recruitment_funnel_stages_mapped` in tenant seed |
| Runtime | `TransitionEvaluatorAdapter` resolves legacy funnel code → PE system stage before Transfer Policy |
| Legacy compat | `docs_wait`→`waiting_documents`, `docs_got`→`documents_received`; funnel `code` unchanged on candidates |
| Validation | Candidate funnel stage create/update rejects codes with no registered PE system stage mapping |

### P5 migration notes (2026-08-17)

| Change | Detail |
|--------|--------|
| Handoff evaluator | `process_engine/handoff_evaluator.py` — `evaluate_handoff_destinations()` |
| Routing | Process profile `handoff_mode` → active `pe_handoff_rules` → tenant_link destination flags |
| Modes | `none`, `client_portal`, `internal_hr`, `both` (manifest + profile config) |
| Module gate | `internal_hr` requires tenant module `hr`; `client_portal` works recruitment-only |
| Transfer policy | `handoff_create_allowed` / `destinations_allowed` via PE evaluator (tenant_link = compat config) |
| Adapter | `TransitionEvaluatorAdapter.evaluate_handoff()` |
| Legacy | Empty `pe_handoff_rules` → tenant_link-only fallback (`routing_source=tenant_link_legacy`) |
| Not in P5 | HR runtime, client portal UI, magic link rewrite, tenant_links removal, billing/modules UI |

### P6 migration notes (2026-08-17)

| Change | Detail |
|--------|--------|
| Transition rules adapter | `process_engine/transition_rules_adapter.py` — `resolve_hiring_pipeline_gates_for_candidate()` |
| Registry rule | `recruitment_pipeline_gates_default` on default process profile (`rule_kind=hiring_pipeline_gates`) |
| Resolution chain | Vacancy → Process Profile → `pe_transition_rules` → tenant `hiring_stage_gates_v1` fallback |
| Stage PATCH / bulk | `resolve_hiring_pipeline_gates(db, tenant_id, candidate_id=…)` — PE first |
| Legacy editor | Settings → Hiring Pipeline Gates dual-writes tenant blob + default profile PE rule |
| Seed migration | `sync_tenant_hiring_gates_to_default_profile_rule()` on tenant PE seed |
| Deprecation | `Tenant.settings["hiring_stage_gates_v1"]` — legacy fallback / editor only; not removed in P6 |
| Adapter | `TransitionEvaluatorAdapter.resolve_hiring_pipeline_gates()` |
| Not in P6 | New transition-rules UI, tenant settings removal, HR, custom pipeline editor |

### Closure gate (P0–P6 stabilization)

| Check | Detail |
|-------|--------|
| Migrations | Single Alembic head; P1 registry + P3 vacancy profile migrations present |
| Seed | `ensure_recruitment_process_engine_defaults` idempotent (handoff + transition rule counts stable) |
| Tenant upgrade | Existing tenant with legacy `hiring_stage_gates_v1` → default profile, handoff rules, mapped funnel stages, migrated PE gates rule |
| Runtime path | `Vacancy → Process Profile → pe_transition_rules / pe_handoff_rules → evaluator` |
| Regression | `test_process_engine_p6.py`, `test_transfer_policy_regression*.py`, `test_recruitment_lock_bulk_guard.py`, `test_hiring_pipeline_gates.py` |
| Deprecation guard | No new direct `hiring_gates_from_tenant_settings` / `hiring_stage_gates_v1` reads outside legacy editor + adapter fallback |
| Tests | `backend/tests/process_engine/test_process_engine_closure.py` |

**Next layer (post-closure):** [`field-registry-card-configuration.md`](field-registry-card-configuration.md) — Field Registry & Card Configuration (P0 canon accepted).

**Related (must stay consistent):**

- [`platform-architecture-principles.md`](../architecture/platform-architecture-principles.md) — Tenant / Company / Module model
- [`module-catalog-and-routing-map.md`](../architecture/module-catalog-and-routing-map.md) §0 — Core vs business modules
- [`ADR-004`](../architecture/ADR-004-five-product-modules-and-billing-events.md) — independent product modules
- [`ADR-009`](../architecture/ADR-009-document-hub-platform-layer.md) — Document Hub (sibling capability)
- [`handoff-contract.md`](../architecture/handoff-contract.md) — cross-module handoff product contract
- [`transfer-policy.md`](../workflows/transfer-policy.md) — **tactical slice** (Recruitment transition evaluator; migrates here)

---

## Decision (canon)

**Process Engine lives in Platform Core.**

It is **not** a business module (Recruitment, HR, Fleet, …).  
It is **not** sold as a separate product line.  
It is a **shared platform capability** — same class as Auth, RBAC, Tenant, Audit, **Document Hub**, **Canonical Field Registry**.

Business modules **register** their system stages, process profiles, pipeline templates, and rules. They **consume** the runtime evaluator. They **must not** implement parallel process engines.

**Module independence rule:**

| Wrong | Right |
|-------|-------|
| Recruitment → depends on HR | Recruitment → Core |
| HR → depends on Recruitment | HR → Core |
| Fleet → depends on Recruitment | Fleet → Core |

Cross-module behaviour uses **only**: published **contracts**, **events**, **handoff rules**, and **module installation checks**. No direct imports between business modules.

---

## 1. Purpose

### 1.1 What Process Engine solves

HostFlow needs **one** mechanism for:

- defining **what a process stage means** (system semantics, not user labels);
- declaring **when a transition is allowed** (fields, documents, confirmations, overrides);
- declaring **when a handoff between modules/processes is allowed**;
- evaluating rules at runtime with a **single truth** for UI, API gates, and automation;
- supporting **marketplace-installable modules** that share the engine but own their domain data.

Without Process Engine, each module reinvents pipelines, gates, and handoff checks — as happened with Recruitment (`stages.py`, `hiring_pipeline_gates`, `TransferPolicyResolver`, `CandidateProfile` config fragments).

### 1.2 Goals

- **One runtime evaluator** for transition and handoff decisions.
- **Registries** as declarative storage (versioned, auditable, module-scoped).
- **System stages** as immutable platform codes; user labels are presentation only.
- **Process profiles** bound to operational context (e.g. vacancy, fleet assignment template) — owned by **module configuration**, stored via platform registries.
- **Graceful degradation** when a target module is not installed (handoff rules inactive, not hard failure).
- **Alignment with Document Hub and Field Registry** — requirements reference canonical codes, not ad-hoc strings.

### 1.3 Non-goals

Process Engine **must not**:

- contain **Recruitment**, **HR**, or **Fleet** business logic;
- encode **CE-driver**, **warehouse**, or any vertical-specific rules in core;
- assume **Candidate** as the only process entity;
- replace **Document Hub** (file storage, verification workflow shell) or **Field Registry** (field taxonomy);
- replace **RBAC** (who may attempt an action — authorization stays separate from rule evaluation);
- be a **user-facing CRM stage designer** that invents arbitrary semantic codes;
- be licensed as a sixth product module in ADR-004.

Tactical implementations (e.g. current `TransferPolicyResolver` for Recruitment `ready_for_handoff`) remain valid **until migrated**; new work must target Process Engine contracts.

---

## 2. Platform Core boundaries

### 2.1 Architecture stack

```
┌─────────────────────────────────────────────────────────────┐
│ Platform Core                                                │
│  Tenant · Auth · RBAC · Audit                               │
│  Canonical Field Registry                                    │
│  Document Hub                                                │
│  Process Engine  ← this document                             │
└─────────────────────────────────────────────────────────────┘
                              ▲
                              │ depends on Core only
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
   Recruitment              HR                  Fleet
   (registers               (registers          (registers
    recruitment/*            hr/*                fleet/*
    stages, profiles)        stages, profiles)   stages, profiles)
        │                     │                     │
        └─────────── contracts / events / handoff rules ───────┘
                    (only when both sides installed)
```

### 2.2 What lives in Core (Process Engine)

| Component | Role |
|-----------|------|
| **System Stage Registry** | Canonical stage codes per module namespace |
| **Process Profile Registry** | Named bundles of pipeline + rules + requirements |
| **Pipeline Template Registry** | Ordered user-visible stages mapped to system stages |
| **Transition Rule Registry** | Requirements to enter / leave a system stage within one process instance |
| **Handoff Rule Registry** | Cross-module / cross-process transfer contracts |
| **Field Requirement Registry** | Required / visible field rules (references Field Registry codes) |
| **Document Requirement Registry** | Required / verified document rules (references Document Hub types) |
| **Override Rule Registry** | Approved exceptions to transition requirements |
| **Runtime Evaluator** | `evaluate_transition`, `evaluate_handoff`, structured blocking reasons |

### 2.3 What lives in business modules

Each module **owns**:

- its **entities** (e.g. Recruitment Candidate, HR Case, Fleet Assignment);
- **registration** of its system stages and stage templates (behaviour hooks);
- **process profiles** content (which pipeline, which rules for which context);
- **side effects** on successful transition (create HR case, emit billing event — via module handlers, not core).

Each module **does not own**:

- a separate pipeline engine;
- duplicate document/field taxonomies.

### 2.4 Comparison to sibling capabilities

| Capability | Process Engine | Document Hub | Field Registry |
|------------|----------------|--------------|----------------|
| **Question answered** | May this stage change / handoff proceed? | What document exists, verified, linked? | What is field `phone`, valid values? |
| **Storage** | Rules + profiles + pipelines | Documents, types, links | Field schemas per entity |
| **Module provides** | Stage codes, profiles, handlers | Document types in context | Entity field extensions |
| **Runtime output** | `allowed`, `blocking_reasons[]` | `status`, `missing`, `expired` | `value`, `validation` |

---

## 3. Registry schemas

All registries share common metadata:

```yaml
registry_item:
  id: uuid
  registry_version: string          # e.g. process_engine_v1
  tenant_id: uuid | null            # null = platform seed / module defaults
  owner_company_id: uuid | null     # company-scoped profile when applicable
  module: string                    # recruitment | hr | fleet | ...
  code: string                      # stable key within module namespace
  status: active | draft | archived
  created_at / updated_at
  audit_ref: optional
```

### 3.1 System Stage Registry

**Purpose:** Immutable semantic stage codes. User never deletes or renames these; they only map display labels to them.

```yaml
system_stage:
  module: recruitment
  code: ready_for_handoff           # unique with module
  template_id: ready_for_handoff_v1 # built-in behaviour template
  terminal: false
  labels:
    en: "Ready for handoff"
    ru: "Готов к передаче"
  metadata:
    owner_lane: agency | client | hr | shared
    analytics_bucket: in_progress   # optional coarse grouping
```

**Platform seeds** per module. Modules may **register additional** stages via module manifest; they may not override core seed semantics without ADR.

**Examples (illustrative, not exhaustive):**

| module | code | template_id |
|--------|------|-------------|
| recruitment | new | generic_progress_v1 |
| recruitment | contacted | generic_progress_v1 |
| recruitment | waiting_documents | documents_gate_v1 |
| recruitment | documents_received | documents_received_v1 |
| recruitment | ready_for_handoff | ready_for_handoff_v1 |
| recruitment | rejected | rejected_v1 |
| hr | received_from_recruitment | hr_intake_v1 |
| hr | verification | hr_verification_v1 |
| hr | contract | hr_contract_v1 |
| hr | active | hr_active_v1 |
| fleet | assigned | fleet_assignment_v1 |

### 3.2 Process Profile Registry

**Purpose:** Named configuration bundle selected at entity creation (e.g. vacancy profile, fleet template).

```yaml
process_profile:
  module: recruitment
  code: driver_ce_eu
  name: "CE Driver (EU)"
  pipeline_template_id: recruitment_agency_default_v2
  default: false                    # tenant/company default when unset
  bindings:
    entity_types: [vacancy, candidate_process]
  stage_overrides:                  # optional per-stage config
    - system_stage: ready_for_handoff
      config:
        handoff_mode: both          # none | internal_hr | client_portal | both
        destination_required: true
        recruiter_confirmation_required: true
  rule_set_ids: [transition_ruleset_uuid, ...]
  field_requirement_set_id: uuid
  document_requirement_set_id: uuid
```

**Effective profile resolution** (runtime, module-specific context keys):

1. explicit on entity (e.g. `vacancy.process_profile_id`)
2. company module settings
3. tenant module default
4. platform module default seed

### 3.3 Pipeline Template Registry

**Purpose:** User-visible funnel — **display only** + ordering. Logic comes from mapped system stages.

```yaml
pipeline_template:
  module: recruitment
  code: agency_driver_default
  name: "Agency driver pipeline"
  stages:
    - order: 10
      user_label: "Новый"
      maps_to: recruitment.new
    - order: 40
      user_label: "Проверяем документы"
      maps_to: recruitment.documents_received
    - order: 50
      user_label: "Готов к передаче"
      maps_to: recruitment.ready_for_handoff
  allowed_transitions:              # optional graph constraint
    - from: recruitment.documents_received
      to: [recruitment.ready_for_handoff, recruitment.rejected]
```

**Invariant:** every pipeline stage **must** `maps_to` exactly one `module.code` system stage. Arbitrary user `code` must not drive gate logic.

### 3.4 Transition Rule Registry

**Purpose:** Requirements to perform a transition **within** one process instance.

```yaml
transition_rule:
  id: uuid
  module: recruitment
  profile_id: optional              # scope: profile-specific or module-wide
  trigger:
    type: enter_stage | leave_stage | attempt_transition
    system_stage: recruitment.ready_for_handoff
  requirements:
    field_requirements: [field_req_id, ...]
    document_requirements: [doc_req_id, ...]
    confirmation_requirements: [...]
    custom_evaluators:              # module-registered hooks only
      - hook: recruitment.package_ready
  blocking_message_templates: {...}
  severity: blocking | warning
  priority: int
```

### 3.5 Handoff Rule Registry

**Purpose:** Transfer between **process instances** and/or **modules**. Implements product contracts (e.g. [`handoff-contract.md`](../architecture/handoff-contract.md)).

```yaml
handoff_rule:
  id: uuid
  code: recruitment_to_hr_internal
  source:
    module: recruitment
    entity_type: candidate
    system_stage: recruitment.ready_for_handoff
  target:
    module: hr
    entity_type: hr_case
    system_stage: hr.received_from_recruitment
  enabled_when:
    modules_installed: [recruitment, hr]
  destination_impl:
    type: internal_hr | client_portal | api | magic_link
    config_ref: tenant_link | portal_config | ...
  idempotency_key: template
  payload_contract: handoff_contract_v1
  events_emitted: [workforce.handoff_from_candidate, ...]
```

**Recruitment-only tenant:** rules with `modules_installed: [hr]` are **inactive** (not errors). Client portal handoff remains available via `destination_impl: client_portal` without HR module.

### 3.6 Field Requirement Registry

**Purpose:** Declarative field gates referencing **Canonical Field Registry** codes.

```yaml
field_requirement:
  id: uuid
  module: recruitment
  entity_type: candidate
  fields:
    - field_code: phone              # canonical, immutable
      requirement: required | visible | hidden
      scope: transition | card_save | handoff
  source_layer: process_engine
```

User/tenant may toggle **visibility** and **required**; may not invent alternate system codes.

### 3.7 Document Requirement Registry

**Purpose:** Declarative document gates referencing **Document Hub** type codes and packs.

```yaml
document_requirement:
  id: uuid
  module: recruitment
  entity_type: candidate
  documents:
    - document_type_code: passport
      level: blocking | warning
      verification: required | optional
    - pack_code: pl_transport_driver
      level: blocking
  relaxed_by_override: true
```

Document Hub evaluates presence/verification; Process Engine aggregates into transition result.

### 3.8 Override Rule Registry

**Purpose:** Approved exceptions (supervisor/admin) to specific requirement classes.

```yaml
override_rule:
  id: uuid
  module: recruitment
  scope: transition | handoff | both
  relaxes:
    document_type_codes: [work_permit]
  approval:
    roles: [supervisor, administrator]
  storage_entity: candidate_pipeline_override   # legacy; migrates to generic override table
```

---

## 4. Module registration contract

Each marketplace / business module **must** ship a **Process Module Manifest** (JSON/YAML, loaded at install/enable):

```yaml
process_module_manifest:
  module_key: recruitment                 # ADR-004 key
  registry_version: process_engine_v1
  system_stages: [...]                    # seeds merged into System Stage Registry
  stage_templates:                        # behaviour templates (ids + handler refs)
    - id: ready_for_handoff_v1
      hooks:
        on_enter: optional
        evaluate_transition: recruitment.handlers.ready_for_handoff
  default_pipeline_templates: [...]
  default_process_profiles: [...]
  transition_rules: [...]                 # or references to platform seeds
  handoff_rules: [...]                    # only rules this module originates
  entity_types:
    - type: candidate
      process_instance_field: stage       # legacy; evolves to process_instance_id
      profile_binding: vacancy.process_profile_id
  dependencies:
    platform: [document_hub, field_registry, process_engine]
    modules: []                           # MUST be empty — no module→module deps
```

### 4.1 Registration API (platform, conceptual)

| Operation | Caller | Effect |
|-----------|--------|--------|
| `register_module(manifest)` | module bootstrap | Merge stages, templates, default rules |
| `unregister_module(module_key)` | tenant uninstall | Disable rules; preserve historical data |
| `resolve_effective_profile(context)` | module runtime | Profile + pipeline for entity |
| `evaluate_transition(context)` | module API on PATCH stage | Blocking reasons or allow |
| `evaluate_handoff(context)` | handoff create / auto-handoff | Cross-module allow + payload |

Modules call Core APIs; Core **never** imports module business packages directly — only registered **hook references** (same pattern as Document Hub policy resolvers).

### 4.2 Forbidden patterns

- `from backend.app.modules.hr import ...` inside Recruitment service.
- Duplicate stage gate in module without registry entry.
- Hardcoded stage string checks in UI as **source of truth** (UI may read evaluator result only).
- Tenant-global gate tables that bypass profile binding (legacy `hiring_stage_gates` — migrate).

---

## 5. Transition Rules vs Handoff Rules

| Dimension | Transition Rule | Handoff Rule |
|-----------|-----------------|--------------|
| **Scope** | Single process instance | Source instance → target instance/module |
| **Question** | Can we move to stage X? | Can we create/link cross-module handoff? |
| **Examples** | Missing passport blocks `ready_for_handoff` | Recruitment candidate → HR case |
| **Module install** | Needs source module only | Needs source + target modules (configurable) |
| **Destination** | N/A | `internal_hr`, `client_portal`, `magic_link`, `api` |
| **Evaluator** | `evaluate_transition` | `evaluate_handoff` (may call transition on source) |
| **User visibility** | Transfer readiness report | Handoff wizard + portal link |

**Layering:** `ready_for_handoff` **transition** must pass before **handoff create** is attempted. Handoff rule may add destination-specific requirements (`require_destination: true` — current Transfer Policy flag).

**Events:** successful handoff emits **operational events** ([`operational-event-boundaries.md`](../architecture/operational-event-boundaries.md)); stage change alone does not bypass handoff contract.

---

## 6. System Stage namespace

### 6.1 Qualified stage reference

Canonical form:

```
{module}.{code}
```

Examples: `recruitment.ready_for_handoff`, `hr.verification`, `fleet.assigned`.

Stored in registries as separate `module` + `code` fields; serialized as qualified string in APIs and evaluator context.

### 6.2 Stage templates (Level 2 in product model)

Templates attach **behaviour** to system stages without duplicating codes:

| template_id | Behaviour (Core orchestrates, module implements hooks) |
|-------------|----------------------------------------------------------|
| `generic_progress_v1` | SLA, owner_role |
| `documents_received_v1` | Document requirement evaluation |
| `ready_for_handoff_v1` | Transition + optional handoff_mode config |
| `rejected_v1` | Reason required, terminal |
| `hr_verification_v1` | HR case document plan |

### 6.3 User stages (Level 3)

User-facing pipeline rows:

- `user_label` — any language, any marketing name;
- `maps_to` — **required** qualified system stage;
- `user_code` — optional slug for UI only; **must not** be used in gate logic.

This replaces free-form `FunnelStage.code` as semantic authority.

### 6.4 Coarse analytics buckets (legacy compat)

Current `FunnelStage.system_stage` values (`new`, `in_progress`, `hired`, `declined_rejected`) become **analytics_bucket** on system stage metadata — not replacement for granular system codes.

---

## 7. Runtime evaluator contract

### 7.1 Input context

```yaml
evaluation_context:
  tenant_id: uuid
  owner_company_id: uuid
  module: recruitment
  entity_type: candidate
  entity_id: uuid
  process_instance_id: uuid | null      # future: explicit instance row
  current_qualified_stage: recruitment.documents_received
  target_qualified_stage: recruitment.ready_for_handoff
  evaluation_kind: transition | handoff
  handoff_target:                       # when kind=handoff
    rule_id: uuid
    destination_impl: client_portal
  effective_profile_id: uuid
  actor: user_ctx
  require_destination: bool             # handoff-only flag; migrates to rule config
```

### 7.2 Output contract

```yaml
evaluation_result:
  allowed: bool
  policy_version: process_engine_v1
  evaluation_kind: transition | handoff
  # Transition-specific
  transition_allowed: bool              # alias when kind=transition
  handoff_create_allowed: bool          # when kind=handoff or combined template
  destinations_allowed: [internal_hr, client_portal]
  blocking_reasons:
    - code: missing_required_document
      message: "Required document 'work_permit' is missing."
      source_layer: document_requirements | field_requirements | override | tenant_link
      document_code: work_permit
  warnings: [...]
  required_documents: [...]
  missing_documents: [...]
  pending_verification_documents: [...]
  missing_data_fields: [...]
  required_confirmations: [...]
  approved_overrides: [...]
  source_layers: [...]
  effective_profile: { id, code, module }
```

**Invariant:** UI, API 409 gates, and automation **must** consume this contract — no local recomputation.

### 7.3 Evaluator pipeline (Core)

1. Resolve **effective process profile** and pipeline.
2. Load **transition rules** for target stage (+ template defaults).
3. Evaluate **field requirements** (Field Registry).
4. Evaluate **document requirements** (Document Hub + packs).
5. Apply **override rules** (approved relaxations).
6. Run **module hook** (if registered for template).
7. For handoff: evaluate **handoff rule** + **module installation** + destination impl.
8. Return unified result.

Current `TransferPolicyResolver.resolve()` is **step 3–6 hardwired for Recruitment** — tactical; rename/migrate to `ProcessEngine.evaluate_transition()` with `module=recruitment` plugin.

### 7.4 Authorization vs evaluation

| Concern | Layer |
|---------|-------|
| May user attempt action? | RBAC / module gates |
| Is process state valid for transition? | Process Engine |
| Audit log | Audit service |

Both must pass; order: auth first, then evaluator.

---

## 8. Module installation logic

### 8.1 Installation states

| State | Meaning |
|-------|---------|
| Platform Core always on | Process Engine available |
| Module licensed on tenant | Module manifest registered |
| Module enabled on company | Company uses module profiles |
| Handoff rule active | All `enabled_when.modules_installed` satisfied |

### 8.2 Rule activation matrix

```yaml
# Example: recruitment → HR internal handoff
enabled_when:
  modules_installed: [recruitment, hr]
  company_flags:
    recruitment: true
    hr: true
```

If `hr` not installed: rule **skipped**; evaluator returns `handoff_create_allowed: false` with warning `handoff_target_module_not_installed` — not 500.

### 8.3 Product scenarios (canon)

| Purchased | Transition on recruitment stages | Handoff |
|-----------|-----------------------------------|---------|
| Recruitment only | Yes | `client_portal` / `magic_link` only |
| HR only | N/A (HR profiles) | Import/API/manual case creation |
| Recruitment + HR | Yes | Internal HR + optional client portal |
| Fleet only | N/A | Fleet assignments via fleet profiles |

### 8.4 Marketplace plugins

Plugins **extend** a business module manifest or register a new `module_key` — they still use Process Engine registries. Plugins **must not** patch another module's Python internals; only add registry rows and hooks via Core APIs ([`ADR-006`](../architecture/ADR-006-marketplace-and-integration-platform.md)).

---

## 9. Relation to Document Hub and Field Registry

### 9.1 Document Hub (ADR-009)

- **Document Requirement Registry** stores *what* is required for a transition.
- **Document Hub** stores *instances*, verification state, links to entities.
- Evaluator queries Hub adapters; Hub does not decide stage transitions.
- Handoff **reuses documents via links**, not copies ([`ADR-009`](../architecture/ADR-009-document-hub-platform-layer.md), [`invariants-recruitment-hr-document-hub.md`](../architecture/invariants-recruitment-hr-document-hub.md)).

### 9.2 Canonical Field Registry

**Canon:** [`field-registry-card-configuration.md`](field-registry-card-configuration.md) (P0 accepted).

- Platform registry of **entity field codes** (`recruitment.candidate.contacts.phone`, `recruitment.vacancy.work_country`, …).
- **Field Requirement Registry** references qualified codes; card layout toggles visibility/required.
- Evaluator validates populated values via Field Registry schema — not free-text field names in rules.

Current partial implementation: `reference_field_schema_registry.py` (reference/legal domains) — **expand** to entity card fields; Process Engine consumes unified registry.

### 9.3 Single blocking_reason model

All three layers report into **`blocking_reasons[]`** with `source_layer`:

| source_layer | Origin |
|--------------|--------|
| `field_requirements` | Field Requirement Registry |
| `document_requirements` | Document Requirement Registry / Hub |
| `transition_rules` | Transition Rule Registry |
| `handoff_rules` | Handoff Rule Registry |
| `override` | Override Rule Registry |
| `tenant_link` | Destination impl config (until fully modeled as handoff impl) |
| `module_hook` | Module-registered evaluator |

Aligns with existing Transfer Readiness UI ([`transfer-policy.md`](../workflows/transfer-policy.md)).

---

## 10. Migration map (current code → Process Engine)

**Strategy:** strangler fig — introduce registries and evaluator API; shim legacy paths; no big-bang rewrite.

### 10.1 Summary table

| Legacy artifact | Location | Role today | Target in Process Engine |
|-----------------|----------|------------|---------------------------|
| **`CandidateProfile`** | `backend/app/models/candidate_profile.py`, API | Recruitment-specific profile: funnel, fields, docs, gates in `config` JSON | **Process Profile Registry** (`module=recruitment`); `Vacancy.candidate_profile_id` → `process_profile_id`; config split into registry rows |
| **`TransferPolicyResolver`** | `backend/app/services/transfer_policy_resolver.py` | Tactical runtime aggregator for Recruitment handoff transition | **Runtime Evaluator** — `evaluate_transition(module=recruitment, template=ready_for_handoff_v1)`; keep API `/transfer-readiness` as compatibility facade |
| **`hiring_pipeline_gates`** | `backend/app/services/hiring_pipeline_gates.py`, tenant settings | Tenant-global stage lists for doc verify / vacancy gates | **Transition Rule Registry** + profile-scoped overrides; deprecate `hiring_stage_gates_v1` tenant blob |
| **`stages.py`** | `backend/app/constants/stages.py` | Flat recruitment stage enum + `STAGE_META` | **System Stage Registry** seeds for `module=recruitment`; constants file becomes re-export/shim for compat |
| **`FunnelStage`** | `backend/app/models/funnel.py` | User pipeline stages; coarse `system_stage`; optional `stage_contract_v1` | **Pipeline Template Registry** user rows with `maps_to` qualified system stage; `stage_contract_v1` → transition rule fragments |
| **`tenant_links`** | `backend/app/models/tenant.py`, features_json | Handoff routing flags (`handoff_enabled`, destinations) | **Handoff Rule Registry** `destination_impl` config; tenant link = impl backend, not semantic source of truth |
| **`transfer-policy.md` workflow** | `docs/specs/workflows/transfer-policy.md` | Tactical Recruitment slice docs | L2 workflow; points here for strategy; regression tests remain valid during migration |
| **`recruitment_package_readiness`** | PR16 services | Dossier blocks + contact fields | Module hook `recruitment.package_ready` + Field/Document Requirement Registry |
| **`document_packs` / eligibility** | M5 workforce eligibility | Required docs | **Document Requirement Registry** + Hub |
| **`candidate_pipeline_overrides`** | pipeline overrides service | Approved relaxations | **Override Rule Registry** |
| **`FunnelsPage` UI** | frontend admin | Free-form stage codes | Pipeline editor: pick system stage template, label only |
| **`candidateStageDocPolicy.ts`** | frontend | Duplicated hiring gate defaults | Read effective profile / evaluator only |

### 10.2 Phased migration (recommended)

| Phase | Deliverable | Legacy shim | Status |
|-------|-------------|-------------|--------|
| **P0 — Canon** | This document + ADR reference | None | Done |
| **P1 — Registry schema** | DB/API for System Stage + Process Profile (read) | `stages.py`, `CandidateProfile` unchanged at runtime | **Done** |
| **P2 — Evaluator facade** | `TransitionEvaluatorAdapter` wraps `TransferPolicyResolver` | API/service → adapter only; resolver is compatibility impl | **Done** |
| **P3 — Profile binding** | Vacancy → process profile; effective resolution | `CandidateProfile.pe_process_profile_id` bridge; legacy `candidate_profile_id` bridge on vacancy | **Done** |
| **P4 — Pipeline mapping** | `FunnelStage.pe_maps_to_*` qualified system stage | Legacy funnel `code` + `system_stage` columns kept | **Done** |
| **P5 — Handoff rules** | Handoff Rule Registry activation; tenant_link as impl config | `handoff-contract.md` unchanged semantically | **Done** |
| **P6 — Stage gates** | Profile-scoped hiring pipeline gates via `pe_transition_rules` | Tenant `hiring_stage_gates_v1` blob = legacy fallback + Settings editor | **Done** |

### 10.3 API compatibility

Until clients migrate:

- `GET /api/v1/candidates/:id/transfer-readiness` — remains; backed by Process Engine evaluator.
- `GET /api/v1/candidates/:id/recruitment-package` — remains; embeds evaluator summary.
- New canonical: `GET /api/v1/process/evaluate` (or module-scoped variant) — TBD in implementation ADR.

### 10.4 Tests

Regression suite in [`transfer-policy.md`](../workflows/transfer-policy.md) § Regression scenarios remains **valid** for Recruitment transition behaviour; re-home tests under `process_engine` package as evaluator is extracted.

---

## 11. Implementation notes for agents

When changing stage or handoff behaviour:

1. Read **this document** (strategy) and **handoff-contract.md** (cross-module product rules).
2. Do **not** add new hardcoded gates outside Process Engine registries / evaluator.
3. Do **not** couple Recruitment services to HR modules — use handoff rules + events.
4. Prefer extending **registries** over new tenant settings blobs.
5. UI shows evaluator output only ([`TransferReadinessReport`](../../hostflow-frontend/src/components/candidate/TransferReadinessReport.tsx) pattern).

**Next implementation work (after canon):** P1 registry schema + module manifest for `recruitment` — not UI packs, not new settings screens.

---

## 12. References

- [`hostflow-core-domain-map-v1.md`](../architecture/hostflow-core-domain-map-v1.md)
- [`ADR-002`](../architecture/ADR-002-modular-recruitment-hr-boundary.md)
- [`ADR-003`](../architecture/ADR-003-tenant-company-module-data-boundaries.md)
- [`ADR-004`](../architecture/ADR-004-five-product-modules-and-billing-events.md)
- [`ADR-006`](../architecture/ADR-006-marketplace-and-integration-platform.md)
- [`ADR-009`](../architecture/ADR-009-document-hub-platform-layer.md)
- [`handoff-contract.md`](../architecture/handoff-contract.md)
- [`operational-event-boundaries.md`](../architecture/operational-event-boundaries.md)
- [`transfer-policy.md`](../workflows/transfer-policy.md) — tactical Recruitment evaluator + regression gate

**Planned follow-up ADR:** `ADR-015-process-engine-platform-layer` (status: to be drafted from this canon).
