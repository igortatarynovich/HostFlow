# State / Lifecycle Inventory — Object Kind slice

**Status:** Accepted (L2 operating canon — platform layer)  
**Hierarchy:** L2 — descriptive inventory of state dimensions; **not** a shared status SoT  
**Decision record:** [`ADR-039`](../architecture/ADR-039-state-lifecycle-inventory.md)  
**Parent model:** [`ADR-038`](../architecture/ADR-038-platform-standardization-model.md) area `states_transitions`  
**Object index:** [`object-kind-catalog.md`](object-kind-catalog.md)  
**Owner:** Architecture canon + platform core team  
**Slice:** Documents · Requirements · Automation · Templates (same as ADR-037 inventory)

**Related:** [`document-runtime-engine-p0.md`](document-runtime-engine-p0.md) · [`ADR-018`](../architecture/ADR-018-requirement-policy-evaluation-model.md) · [`ADR-019`](../architecture/ADR-019-automation-capability-entitlement-control-plane.md)

---

## 1. Purpose

For each object in the Object Kind Catalog slice, record:

```text
ObjectKind → Object → State dimension → State owner → Transition owner
```

**Observed values are descriptive** (current code/docs). They are **not** a platform-wide canonical enum.

**Forbidden:** using one vocabulary for publication + instance lifecycle + execution + evaluation outcome.

---

## 2. Dimension kinds (from ADR-039)

`publication` · `configuration` · `instance_lifecycle` · `review` · `validity_expiry` · `execution` · `outcome` · `decision` · `enablement` · `none`

---

## 3. Inventory rows

| object_code | object_kind | dimension | dimension_purpose | observed_values (descriptive) | state_owner | transition_owner | sot_refs | notes |
|-------------|-------------|-----------|-------------------|-------------------------------|-------------|------------------|----------|-------|
| `document_type` | ReferenceObject | publication | Is the type draft/active/deprecated in the reference registry? | `draft` \| `active` \| `deprecated` (ref model / `ref_document_types.status`) | Document Hub / Platform Reference | Platform admin / reference sync | [`document-type-registry-v1.json`](document-type-registry-v1.json), `ref_document_types`, ADR-009 | Not file lifecycle. `integrity=split` on codes is Naming gap, not a state dimension. |
| `document_type_version` | ReferenceObject | publication | Version validity / deprecation of a type schema snapshot | `valid_from` / `valid_to`; replacement_document_type_id; version_code | Document Hub / Platform Reference | Platform reference publishers | `ref_document_type_versions` | Orthogonal to instance workflow. |
| `document_type.tenant_legacy` | ReferenceObject | publication | Tenant-local type row active? | per-tenant `document_types` rows | Documents (legacy) | Tenant admin | table `document_types` | **forbidden_as_sot** for evaluation; do not invent parallel lifecycle. |
| `document_pack` | ReferenceObject | publication | Pack draft/published in `ref_packs` | `ref_packs.status` (`draft` / …) | Platform Reference | Platform pack publishers | `ref_packs` | Named set — not a rule. |
| `document_pack` | ReferenceObject | enablement | Which packs are enabled for a tenant | `tenant_document_pack_enablements.enabled` + effective window | Platform Reference + tenant config | Tenant admin | `tenant_document_pack_enablements` | Separate from pack publication. |
| `document_pack.module` | ReferenceObject | none | Bridge pack definitions are code constants | — | Documents module (bridge) | — | `pack_definitions.py` | Applicability is a **RuleObject**, not pack state. |
| `rule_pack_foundation` | ReferenceObject | none | Skeleton metadata only | `lifecycle_state=draft` in foundation tuples (non-runtime) | Policy Reference | — | `reference_rule_pack_foundation.py` | `integrity=skeleton`; no runtime state machine. |
| `requirement_definition` | ReferenceObject | configuration | Which registry version of definitions is loaded | `registry_version` in JSON seed | Platform Requirements | Platform seed/registry owners | `requirement_definitions.v1.json` | Seed/registry — not readiness. No per-row publish workflow yet. |
| `requirement_policy` | RuleObject | configuration | Which policy applies / is pinned for evaluation | policy_ref / `requirement_policy_version` pin on evaluation | Platform Requirements | Platform policy authors; assignment services | `requirement_policy.recruitment.driver_ce.pl.v1.json`, ADR-018 | **Not** readiness or blocker outcome. |
| `document` | RuntimeInstance | instance_lifecycle | Workflow path of the file instance | Document Runtime: `missing` \| `uploaded` \| `pending_review` \| `approved` \| `rejected` \| `replaced` \| `superseded` | Document Hub / Document Runtime | Upload/review APIs; replacement flows | [`document-runtime-engine-p0.md`](document-runtime-engine-p0.md), Hub | Do not merge with expiry. |
| `document` | RuntimeInstance | review | Verification decision in Hub/review context | review/approve/reject paths; DocumentReview linkage | Document Hub | Reviewers via Hub | ADR-009; DocumentReview | May align with workflow `approved`/`rejected`; keep as dimension for multi-context review. |
| `document` | RuntimeInstance | validity_expiry | Time validity of the instance | `valid` \| `expiring_soon` \| `expired` \| `missing_expiry` | Document Hub / Document Runtime | Expiry engine + data edits | document-runtime-engine §4.2; expiry engine | Orthogonal to workflow_status. |
| `document_link` | RuntimeInstance | none | Link record MVP (no lifecycle) | — | Document Hub | Link create/delete | `document_entity_links` | Completeness row. |
| `document_review` | RuntimeInstance | review | Review status in a requirement/module context | reviewed status / comment / reviewed_at (ADR-009 model) | Document Hub | Reviewers | ADR-009 Document Review | One file → many reviews. |
| `candidate_evidence` | RuntimeInstance | outcome | Chosen evidence fulfillment fact (target persistence) | target: requirement + variant + document instance(s); persistence **incomplete** | Platform model; Recruitment writes | Recruitment writers | ADR-016; object-kind-catalog | Not EvaluationFact; not started as table SoT. |
| `requirement_evaluation` | EvaluationFact | outcome | Computed per-requirement / overall evaluation result | Per-req: `fulfilled` \| `missing` \| `pending_review` \| `invalid` \| `expired` \| `not_applicable` \| `not_required_yet` \| `not_selected` \| `process_pending` \| `waived` \| `unresolved`; overall: `ready` \| `blocked` \| `pending` \| `unresolved` | Platform Requirements | `RequirementEvaluationService` (recompute); waivers via override paths | `result_contract.py`, ADR-018 | **Never** instance_lifecycle. Modules consume DTO. |
| `automation_execution` | RuntimeInstance | execution | Reaction Orchestrator run lifecycle | ADR-019: `detected` → `suggested` \| `awaiting_approval` \| `queued` → `running` → `succeeded` \| `failed` \| `cancelled` \| `skipped` \| `superseded` | Platform Automations (target) | Reaction Orchestrator (target); skeleton today | ADR-019 §4; object-kind `status=target` | Not domain truth. |
| `communication_automation_decision` | RuntimeInstance | decision | Whether a C2.2 rule fired Intent | `fire` \| `skip` (`DECISION_OUTCOME_*`) | Communications | C2.2 evaluator / emitter | `communication_automation.py`, C2.2 | Intent-only; not send status. |
| `automation_rule.tenant` | RuleObject | enablement | Tenant CRM rule on/off | `automation_rules.enabled` | Automations (MVP/legacy control plane) | Tenant automation admin | `automation_rules` | Legacy as control-plane SoT. |
| `automation_rule.comms` | RuleObject | publication | Draft vs published rule version | version `draft` \| `published`; rule `active` \| `archived` | Communications | Comms automation API | `communication_automation_*` | Separate from decision dimension. |
| `automation.nba` | RuleObject | none | Suggestion surface — absorb into execution `suggested` | — | Platform next_action | — | `platform/next_action` | Not a separate status SoT. |
| `automation.uos_auto_activities` | RuleObject | none | Absorb into Action Registry | — | Platform | — | `uos_auto_activities.py` | — |
| `reaction_orchestrator` | RuleObject | none | Mechanism; executions carry state | — | Platform Automations | — | ADR-019 skeleton | State lives on `automation_execution`. |
| `presentation_rule` | RuleObject | none | UI show/hide — not blockers | — | Forms / Entity Profile | Form/presentation editors | P10A / layouts | Must not become readiness dimension. |
| `transfer_policy` | RuleObject | outcome | Aggregated readiness report (computed) | `transfer_allowed`, `handoff_create_allowed`, blocking_reasons | Recruitment / PE bridge (resolver) | Resolver recompute on inputs | TransferPolicyResolver; transfer-policy.md | Computed report — not Document status. Legacy ruleset **forbidden** as gate SoT. |
| `process_transition_rule` | RuleObject | configuration | Which PE transition/gate rules are bound | PE rule registry on process profile | Process Engine | PE admin / seed | process-engine.md | Stage movement owned by PE + consumers; values are rule config. |
| `process_handoff_rule` | RuleObject | configuration | Handoff mode / destination rules | `pe_handoff_rules`, handoff_mode | Process Engine | PE admin / seed | process-engine.md | — |
| `document_applicability_policy` | RuleObject | none | Pure function / policy module | — | Documents module | — | `document_applicability_policy.py` | Not a persisted state machine. |
| `forms.stdlib` | LibraryObject | none | Component catalog entries | — | Forms | Catalog registration | `forms_platform/field_catalog/stdlib.py` | — |
| `field_registry.field` | LibraryObject | none | Field definitions (registry versioning separate) | registry_version / status on FR rows if present | Field Registry | FR seed/manifest upsert | field-registry-card-configuration.md | Card layout fallback ≠ field lifecycle. |
| `communication_template` | LibraryObject | publication | Template / version publish state | template + version draft/published/active patterns (C2.1) | Communications | Template Platform API | C2.1 templates | Not delivery attempt status. |
| `merge_document_template` | LibraryObject | enablement | Template active for merge | `is_active` | Documents | Template admins | `merge_document_templates` | — |
| `process_template` | LibraryObject | publication | Process template availability | tenant template rows / active flags | Documents (legacy); PE strategic | Template admins | `process_templates` | Strategic owner = PE long-term. |
| `notification_template` | LibraryObject | none | Code constants | — | Notifications | — | `notification_templates.py` | Not C2.1. |
| `document_checklist_template` | LibraryObject | enablement | Checklist template active | `document_templates.is_active` | Documents | Tenant admin | `document_templates` | **Forbidden** as stage/readiness dimension. |

### 3.1 Legacy / forbidden readiness sources

| object_code | note |
|-------------|------|
| `document_ruleset_versions` | Checklist compatibility only — **not** a handoff/readiness state dimension |
| `sample_ruleset.json` | Forbidden for new entries as SoT (ADR-018) |
| `requirement_slots.v1.json` | Bridge; do not extend as lifecycle SoT |
| `candidate_profile.document_configs` | Legacy storage; not a state dimension owner |

---

## 4. Collisions called out

| Collision | Resolution in this inventory |
|-----------|------------------------------|
| Document `approved` vs RequirementEvaluation `fulfilled` | Different dimensions (`instance_lifecycle`/`review` vs `outcome`) |
| `pending_review` on Document Runtime vs Evaluation | Same string, different owners — do not unify yet |
| `published` on templates vs `active` on packs/rules | Stay under `publication` / `enablement` per object |
| TransferPolicy `transfer_allowed` vs Evaluation `ready` | Both computed outcomes; separate objects/owners |
| Automation `skipped`/`superseded` vs Document `superseded` | `execution` vs `instance_lifecycle` — different kinds |

---

## 5. How to extend

1. Add or update the object in [`object-kind-catalog.md`](object-kind-catalog.md) first (ADR-037/038 Platform-first).  
2. Add dimension rows here with owners and observed values.  
3. Do **not** add a cross-object status enum in the same change.  
4. Candidate/Lead/Vacancy/Employee/Campaign = **new slice** later.

---

## 6. History

- 2026-08-13: Initial inventory for Object Kind Documents / Requirements / Automation / Templates slice; ADR-039 Accepted. Shared value vocabulary deferred.
