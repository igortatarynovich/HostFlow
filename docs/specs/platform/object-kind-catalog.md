# Object Kind Catalog — Documents / Requirements / Automation / Templates

**Status:** Accepted (L2 operating canon — platform layer)  
**Hierarchy:** L2 — indexes existing SoT; **not** itself a data SoT  
**Decision record:** [`ADR-037`](../architecture/ADR-037-platform-object-kind-catalog.md)  
**Parent model:** [`ADR-038`](../architecture/ADR-038-platform-standardization-model.md) · [`platform-standardization-model.md`](platform-standardization-model.md) (areas `object_kind` / `rules` / `libraries`)  
**Owner:** Architecture canon + platform core team  
**Slice:** Documents · Requirements · Automation · Templates (first inventory)

**Related canon:** [`ADR-009`](../architecture/ADR-009-document-hub-platform-layer.md) · [`ADR-016`](../architecture/ADR-016-requirement-evidence-document-separation.md) · [`ADR-018`](../architecture/ADR-018-requirement-policy-evaluation-model.md) · [`ADR-019`](../architecture/ADR-019-automation-capability-entitlement-control-plane.md) · [`ADR-012`](../architecture/ADR-012-activity-notification-operating-layer.md) · [`document-type-registry-v1.json`](document-type-registry-v1.json) · [`requirement-evidence-model-p0.md`](requirement-evidence-model-p0.md) · [`process-engine.md`](process-engine.md) · [`field-registry-card-configuration.md`](field-registry-card-configuration.md)

---

## 1. Purpose

This catalog answers four questions only:

1. Which architectural **object classes** exist in this slice?
2. Who **owns** each indexed object?
3. Where does the **real SoT** live?
4. What is the object **allowed to do at runtime**?

It does **not** redefine document types, requirements, or automation behavior. Zone owners stay as in the Capability Catalog.

**Row check:** *What is this architecturally, and what is it allowed to do at runtime?*

---

## 2. Vocabulary (from ADR-037)

### 2.1 ObjectKind

| Kind | Meaning |
|------|---------|
| `ReferenceObject` | Types and definitions |
| `RuntimeInstance` | Concrete persisted runtime objects |
| `RuleObject` | Decision or reaction rules |
| `LibraryObject` | Reusable definition assets |
| `EvaluationFact` | Computed fact (outcome) |

### 2.2 RuleKind (subtype of RuleObject)

| RuleKind | Meaning |
|----------|---------|
| `DomainPolicy` | Domain truth / applicability |
| `ProcessRule` | Process Engine transition / handoff |
| `AutomationReaction` | Reaction to published facts |
| `PresentationRule` | UI visibility / layout — never blockers |

### 2.3 LibraryKind (this slice)

`FormComponent` · `FieldDefinition` · `CommunicationTemplate` · `DocumentMergeTemplate` · `NotificationTemplate` · `ProcessTemplate` · `DocumentChecklistTemplate`

### 2.4 Card fields (closed)

| Field | Values |
|-------|--------|
| `kind` | ObjectKind |
| `code` | Stable id |
| `owner` | Capability + module |
| `sot` | Canonical path |
| `scope` | `platform` \| `module` \| `tenant` |
| `runtime_role` | `definition` \| `persisted_instance` \| `computed_fact` \| `executable_rule` \| `reusable_asset` |
| `status` | `canonical` \| `target` \| `bridge` \| `legacy` \| `forbidden_as_sot` |
| `integrity` | `aligned` \| `split` \| `incomplete` \| `skeleton` |
| `parameters` | Owned fields only |
| `rules` | Attached RuleKind / rule codes |
| `consumers` | See §8 Ownership & Consumption Matrix |

**Hard rules**

- `RequirementDefinition` = ReferenceObject only; `RequirementPolicy` = RuleObject / DomainPolicy only.
- `DocumentPack` = ReferenceObject (named set); applicability conditions = separate RuleObject.
- `status` and `integrity` must not mix (e.g. DocumentType: `canonical` + `split`).

---

## 3. ReferenceObject inventory

| code | owner | sot | scope | runtime_role | status | integrity | parameters (owned) | attached rules |
|------|-------|-----|-------|--------------|--------|-----------|--------------------|----------------|
| `document_type` | Document Hub / Platform Reference | [`document-type-registry-v1.json`](document-type-registry-v1.json) → `ref_document_types` | platform | definition | canonical | **split** | code, public_name, category, criticality, schema_version | — |
| `document_type_version` | Document Hub / Platform Reference | `ref_document_type_versions` | platform | definition | canonical | split | schema_json, expiry_rules, verification_profile, validity window | — |
| `requirement_definition` | Platform Requirements | `backend/app/requirement_rules/data/requirement_definitions.v1.json` | platform | definition | canonical | aligned | requirement_code, alternatives, conditions | consumed by `requirement_policy` |
| `document_pack` | Platform Reference (M1) | `ref_packs` / `ref_pack_items` | platform | definition | canonical | incomplete | pack code, item document_type_version links | applicability → separate RuleObject |
| `document_pack.module` | Documents module (bridge) | `backend/app/modules/documents/pack_definitions.py` | module | definition | bridge | incomplete | pack code, document_codes list | `document_applicability_policy` |
| `rule_pack_foundation` | Policy Reference | `backend/app/reference/reference_rule_pack_foundation.py` | platform | definition | target | skeleton | pack_code, pack_type, domain targets | — (no runtime execution) |
| `document_type.tenant_legacy` | Documents (legacy) | table `document_types` (tenant-scoped) | tenant | definition | legacy | split | tenant_id + code | **forbidden_as_sot** for evaluation |

**Notes**

- DocumentType `integrity=split`: evaluation registry uses codes such as `national_identity_card`; `document_reference_sync` / `ref_*` seed uses `id_card`; recruitment UI `definitions.py` aliases; OCR `scanner/document_types.py` has a separate keyword list (not evaluation SoT).
- `RequirementPolicy` is **not** listed here — see §5 RuleObject.

---

## 4. RuntimeInstance inventory

| code | owner | sot | scope | runtime_role | status | integrity | parameters (owned) | attached rules |
|------|-------|-----|-------|--------------|--------|-----------|--------------------|----------------|
| `document` | Document Hub | ADR-009 · `documents` | company (via owner_company_id) | persisted_instance | canonical | incomplete (links evolving) | type, file, status, expiry, review state | DomainPolicy consumers only |
| `document_link` | Document Hub | `document_entity_links` | company | persisted_instance | canonical | aligned (MVP) | linked_entity_type/id, relation_type, module_key | — |
| `document_review` | Document Hub | DocumentReview (ADR-009) | company | persisted_instance | canonical | incomplete | requirement/context review status | — |
| `candidate_evidence` | Recruitment writes; platform model ADR-016 | Candidate Evidence persistence | tenant/company | persisted_instance | target | **incomplete** (persistence not started) | requirement + variant + document instance(s) | DomainPolicy satisfaction |
| `automation_execution` | Platform Automations (ADR-019) | target AutomationExecution | platform | persisted_instance | **target** | skeleton | execution lifecycle states | AutomationReaction |
| `communication_automation_decision` | Communications C2.2 | `communication_automation_decisions` | tenant | persisted_instance | canonical | aligned (C2.2 closed) | rule version, skip/fire, Intent key | AutomationReaction (Intent-only) |

---

## 5. RuleObject inventory

| code | RuleKind | owner | sot | scope | runtime_role | status | integrity | parameters (owned) |
|------|----------|-------|-----|-------|--------------|--------|-----------|--------------------|
| `requirement_policy` | DomainPolicy | Platform Requirements | `requirement_policy.recruitment.driver_ce.pl.v1.json` (+ assignment) | platform | executable_rule | canonical | aligned (Driver CE slice) | applicability, blocks_stage, policy version pin |
| `transfer_policy` | DomainPolicy | Recruitment / Platform PE bridge | `TransferPolicyResolver` · [`transfer-policy.md`](../workflows/transfer-policy.md) | tenant | executable_rule | canonical | incomplete (aggregates legacy layers) | transfer_allowed, handoff_create_allowed, blocking_reasons |
| `document_applicability_policy` | DomainPolicy | Documents module | `document_applicability_policy.py` | module | executable_rule | canonical | aligned (module-owned by REF-4) | citizenship / role / country filters for packs |
| `process_transition_rule` | ProcessRule | Process Engine | PE registry · [`process-engine.md`](process-engine.md) P0–P6 | platform/tenant | executable_rule | canonical | aligned | pe_transition_rules, hiring pipeline gates |
| `process_handoff_rule` | ProcessRule | Process Engine | `pe_handoff_rules` | platform/tenant | executable_rule | canonical | aligned | handoff_mode, destinations |
| `automation_rule.tenant` | AutomationReaction | Automations (MVP) | table `automation_rules` · `services/automation_rules.py` | tenant | executable_rule | **legacy** (not control-plane SoT) | incomplete | trigger, conditions_json, actions_json |
| `automation_rule.comms` | AutomationReaction | Communications | `communication_automation_*` · C2.2 | tenant | executable_rule | canonical (Intent-only) | aligned | Event → Intent; never send / never Thread |
| `automation.nba` | AutomationReaction | Platform next_action | `platform/next_action` | tenant | executable_rule | legacy / absorb into `suggested` | incomplete | suggested next action |
| `automation.uos_auto_activities` | AutomationReaction | Platform | `uos_auto_activities.py` | tenant | executable_rule | legacy / absorb | incomplete | auto Activity create |
| `reaction_orchestrator` | AutomationReaction | Platform Automations ADR-019 | outbox + skeleton consumer | platform | executable_rule | **target** | **skeleton** | match fact → capability → action |
| `presentation_rule` | PresentationRule | Forms / Entity Profile P10A | `presentation_rules` / Field Registry layout | platform | executable_rule | canonical | incomplete | show/hide, required-if on form — **not blockers** |

### 5.1 Legacy / forbidden-as-SoT rule sources

| code | status | note |
|------|--------|------|
| `document_ruleset_versions` | legacy | Checklist compatibility only — **not** handoff gate |
| `sample_ruleset.json` | legacy / forbidden_as_sot for new entries | ADR-018 forbids new records |
| `requirement_slots.v1.json` | bridge | Superseded terminology by ADR-016; slot_evaluator still present |
| `candidate_profile.document_configs` | legacy | Deprecated; still seeded / Transfer Policy storage layer |

---

## 6. LibraryObject inventory

| code | LibraryKind | owner | sot | scope | runtime_role | status | integrity |
|------|-------------|-------|-----|-------|--------------|--------|-----------|
| `forms.stdlib` | FormComponent | Forms | `forms_platform/field_catalog/stdlib.py` (12 Basic) | platform | reusable_asset | canonical | aligned |
| `field_registry.field` | FieldDefinition | Platform Field Registry | Field Registry manifests / ORM | platform | reusable_asset | canonical | aligned (P1–P5); card fallback to profile JSON remains |
| `communication_template` | CommunicationTemplate | Communications C2.1 | published `CommunicationTemplateVersion` | tenant | reusable_asset | canonical | aligned |
| `merge_document_template` | DocumentMergeTemplate | Documents | `merge_document_templates` | tenant | reusable_asset | canonical | aligned |
| `notification_template` | NotificationTemplate | Notifications / reminders | `notification_templates.py` constants | platform | reusable_asset | legacy relative to C2.1 | incomplete |
| `process_template` | ProcessTemplate | Documents (legacy) / PE strategic | `process_templates` | tenant | reusable_asset | legacy | incomplete — PE is strategic owner |
| `document_checklist_template` | DocumentChecklistTemplate | Documents | `document_templates` | tenant | reusable_asset | legacy | incomplete — overlaps packs/requirements; **must not gate** |

---

## 7. EvaluationFact inventory

| code | owner | sot | scope | runtime_role | status | integrity | parameters (owned) |
|------|-------|-----|-------|--------------|--------|-----------|--------------------|
| `requirement_evaluation` | Platform Requirements | `RequirementEvaluationService` · ADR-018 | platform (computed) | **computed_fact** | canonical | aligned (Driver CE cutover 2B-3) | per-requirement status, can_transition, blockers, policy_ref, fingerprint |

**Forbidden:** treating RequirementEvaluation as Document Hub instance lifecycle or as Process Engine stage SoT. Consumers read the DTO; modules do not invent parallel blockers.

---

## 8. Ownership & Consumption Matrix

Columns: Recruitment · HR · Fleet · Finance · Services · Communications · Acquisition · Platform (Documents / Requirements / Automations / Forms / PE).

Verbs: `owns` · `writes` · `consumes` · `reacts` · `forbidden`.

| Object code | Recruitment | HR | Fleet | Finance | Services | Communications | Acquisition | Platform owner |
|-------------|-------------|----|-------|---------|----------|----------------|-------------|----------------|
| `document_type` | consumes | consumes | consumes | consumes | consumes | — | — | **owns** (Documents / Reference) |
| `document_type.tenant_legacy` | consumes (legacy) | consumes (legacy) | — | — | — | — | — | **forbidden_as_sot** for evaluation |
| `requirement_definition` | consumes | consumes | — | — | — | — | — | **owns** (Requirements) |
| `requirement_policy` | consumes | consumes | — | — | — | — | — | **owns** (Requirements) |
| `document_pack` | consumes | consumes | consumes | — | — | — | — | **owns** (`ref_packs`); module packs = bridge |
| `document` | writes · consumes | writes · consumes | writes · consumes | writes · consumes | writes · consumes | — | — | **owns** (Document Hub) |
| `document_link` | writes · consumes | writes · consumes | writes · consumes | consumes | consumes | — | — | **owns** (Document Hub) |
| `candidate_evidence` | **writes** · consumes | consumes | — | — | — | — | — | model SoT platform; Recruitment writes |
| `requirement_evaluation` | consumes · initiates | consumes | — | — | — | reacts (via events) | — | **owns** (Requirements) |
| `transfer_policy` | consumes · initiates | consumes | — | — | — | — | — | resolver in Recruitment/PE bridge |
| `process_transition_rule` | consumes | — | — | — | — | — | — | **owns** (Process Engine) |
| `process_handoff_rule` | consumes · writes requests | consumes · writes accept | — | — | — | — | — | **owns** (Process Engine) |
| `automation_rule.tenant` | reacts (call sites) | — | — | — | — | — | reacts (leads) | **owns** table (legacy control plane) |
| `automation_rule.comms` | — | — | — | — | — | **owns** | — | — |
| `reaction_orchestrator` | reacts (future) | reacts (future) | — | — | — | reacts (future) | — | **owns** (target) |
| `forms.stdlib` | consumes | consumes | — | — | consumes | — | consumes | **owns** (Forms) |
| `field_registry.field` | consumes | consumes | consumes | — | consumes | — | — | **owns** (Field Registry) |
| `communication_template` | — | — | — | — | — | **owns** | — | — |
| `document_checklist_template` | consumes | — | — | — | — | — | — | Documents owns table; **forbidden** as stage gate |
| Recruitment stage / Candidate SoT | **owns** | forbidden | forbidden | forbidden | forbidden | **forbidden** (no stage write) | forbidden | — |
| HR Employee SoT | forbidden (except handoff action) | **owns** | — | — | — | forbidden | — | — |

**Notable contracts**

- Recruitment **writes** Candidate Evidence and may **initiate** evaluation; it **consumes** `requirement_evaluation` (does not own the class).
- Communications **owns** C2.2 rules and may **react** to facts; **forbidden** to write Recruitment stage or Document Hub domain SoT.
- Document Hub **owns** Document / Link / Review; modules **write** uploads and links through Hub contracts — **forbidden** module-local file tables as SoT.
- Automations **react**; they **forbidden** to recompute requirement fulfillment or transfer readiness (ADR-019).

---

## 9. Forbidden mixing (summary)

| Mistake | Correct class |
|---------|---------------|
| Document type code as Process Engine requirement | RequirementDefinition + EvaluationFact |
| Checklist / ruleset as handoff gate | TransferPolicy / RequirementEvaluation |
| RequirementPolicy listed as ReferenceObject | RuleObject / DomainPolicy |
| DocumentPack as executable rule | ReferenceObject + separate applicability RuleObject |
| RequirementEvaluation as instance lifecycle | EvaluationFact (outcome) |
| Frontend stage doc policy as blockers | Presentation only; backend Evaluation DTO |
| C2.2 as second CRM automation engine | Intent-only AutomationReaction |
| Tenant `document_types` as evaluation SoT | platform DocumentType registry |

---

## 10. Out of scope (this document)

- Full Candidate / Lead / Employee / Vacancy / Vehicle entity cards (consumers only).
- JSON-registry, ORM, API for ObjectKind.
- Aligning DocumentType codes (`integrity=split` → `aligned`).
- Removing ruleset / `document_configs` fallbacks.
- State-dimension catalog (next: `ObjectKind → Object → State dimensions → State owner → Transition owner`).

---

## 11. History

- 2026-08-13: Parent pointer to ADR-038 Platform Standardization Model.
- 2026-08-13: Initial L2 catalog for Documents / Requirements / Automation / Templates slice; ADR-037 Accepted.
