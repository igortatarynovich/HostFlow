# REF-4 Core Catalog Completion Gate Plan

Status: draft-for-gate
Target decision: PASS / PASS_WITH_CONSTRAINTS / STOP
Depends on:
1. REF-3 PASS WITH ENFORCEMENT (`docs/specs/gates/ref3_4_facade_rollout_closure_report_2026-05-28.md`)
2. REF-3.1 guard-scan enforcement baseline (`docs/specs/gates/ref3_1_enforcement_baseline_2026-05-27.md`)
3. Reference Delivery Contract (`docs/specs/reference_delivery_contract_standard.md`)
4. Architecture Gate Checklist (`docs/specs/architecture_gate_checklist_standard.md`)

Purpose: define REF-4 as an architecture gate for core catalog completion with stable facade delivery and strict boundary discipline.

## 1) Gate Intent (Architecture, not task checklist)

REF-4 is a foundation/catalog stage.

Allowed in REF-4:
1. canonical catalog/domain completion;
2. facade delivery expansion for catalog/reference data;
3. schema/version/deprecation formalization;
4. deterministic seed/migration for reference domains.

Forbidden in REF-4:
1. new eligibility/compliance runtime behavior;
2. new module-local rule engines;
3. direct consumer access to reference tables/resolvers;
4. UI behavior changes that depend on new runtime logic;
5. M5 scope expansion.

## 2) Scope and Boundaries

In scope:
1. countries + ISO + lifecycle state;
2. country grouping model (EU/EEA/Schengen/work/legal groups);
3. citizenship grouping model;
4. document type catalog completion;
5. document field schema standardization;
6. applicability/rules/packs catalog hardening;
7. tenant override boundaries (catalog-level);
8. stable facade delivery shape for these domains.

Out of scope:
1. workflow/automation orchestration;
2. new verification UX;
3. OCR runtime pipeline (only extractability metadata is allowed);
4. operation decision logic redesign.

## 3) Catalog Ownership Model (Mandatory)

For each domain REF-4 must define:
1. source of truth;
2. owner;
3. immutable/mutable split;
4. tenant override policy;
5. deprecation + version policy.

Ownership matrix baseline:

| Domain | Source of truth | Owner | Immutable | Mutable | Tenant override | Deprecation/version |
|---|---|---|---|---|---|---|
| countries | reference catalog | platform-reference | canonical code, ISO codes | display metadata, active flag lifecycle | labels only | versioned membership + deprecate window |
| country_groups | reference catalog | platform-reference | group code/semantics | membership version rows | none (read-only) | valid_from/valid_to required |
| citizenship_groups | reference catalog | platform-reference | group code/semantics | membership mapping | none (read-only) | versioned mapping required |
| document_types | canonical catalog | platform-reference | canonical code/category/business purpose | display labels, lifecycle status | enable/disable where allowed | replacement type + deprecate reason |
| document_type_versions | canonical rules profile | platform-reference | semantics + required field keys | status/validity windows | none | valid_from/valid_to required |
| document_field_schemas | canonical schema registry | platform-reference | field identifiers/types/normalization meaning | locale labels/help text | label/help text only | schema version lineage required |
| applicability_packs/rules | canonical applicability layer | platform-reference | rule code/condition semantics | activation windows/ordering | tenant enablement only | rule version + precedence policy |
| tenant_overrides | tenant config layer | tenant + platform guard | canonical IDs/semantics | allowed policy knobs only | bounded | override audit + rollback required |

## 4) Facade Delivery Shape Stability (Mandatory)

REF-4 must publish a field-level stability contract for facade DTOs.

Stability classes:
1. `stable`: safe for consumer dependency;
2. `experimental`: opt-in and version-tagged;
3. `deprecated`: removal milestone declared.

Nullability classes:
1. `required`
2. `nullable`
3. `conditional` (with explicit condition)

Required artifact:
1. DTO stability matrix attached to REF-4 gate record.

Minimum facade response sections (stable):
1. `contract_version`;
2. `reference_version`;
3. `context_echo`;
4. `countries`;
5. `country_groups`;
6. `citizenship_groups`;
7. `document_types`;
8. `document_type_profiles`;
9. `document_field_schemas`;
10. `applicability`;
11. `tenant_overrides_projection`;
12. `errors`.

Hard rule:
- no consumer may bind to undocumented/unstable fields.

## 5) Country and Group Model (Mandatory)

Country entity minimum:
1. `country_code_alpha2`;
2. `country_code_alpha3`;
3. `country_code_numeric`;
4. canonical display name;
5. lifecycle status (`active|deprecated`).

Group model minimum:
1. EU;
2. EEA;
3. Schengen;
4. work-zone groups;
5. legal/compliance applicability groups.

Membership model minimum:
1. code-based deterministic lookup;
2. `valid_from` / `valid_to`;
3. membership source;
4. deprecation strategy.

Gate fail condition:
- REF-4 cannot pass with "countries table only" and no group model.

## 6) Document Field Schema Model (Mandatory)

Each canonical field definition must contain:
1. canonical field identifier;
2. typed value class (`string|date|enum|number|boolean|object|list`);
3. normalization rules;
4. verification relevance;
5. expiry relevance;
6. OCR extractability marker;
7. locale/display metadata separate from canonical semantics.

Hard rules:
1. no module-local ad-hoc field keys;
2. no locale text as canonical ID;
3. no mixed storage/display semantics;
4. no schema writes from modules.

## 7) Tenant Override Boundaries (Mandatory)

Tenant MAY (policy-bound):
1. rename display labels;
2. reorder presentation;
3. enable/disable allowed applicability items;
4. set allowed reminders/instructions/owner routing;
5. add bounded custom metadata extension points.

Tenant MAY NOT:
1. change canonical identifiers;
2. redefine compliance meaning/criticality semantics;
3. remap system document meaning;
4. bypass versioned system schema;
5. convert custom types into protected system-compliance types.

Enforcement requirement:
- facade must project overrides only after policy validation.

## 8) Rule and Version Governance

REF-4 must define:
1. rule precedence order (system > pack > tenant-override within allowed policy);
2. version lifecycle (`draft|active|deprecated` where applicable);
3. replacement strategy (`replacement_code` + reason);
4. backward compatibility window for deprecated versions.

## 9) Migration and Seeding Gate Requirements

Must be approved before implementation starts:
1. deterministic idempotent seed strategy;
2. migration ordering by domain dependencies;
3. unknown/legacy fallback behavior;
4. rollback plan;
5. migration observability events;
6. compatibility path owner + removal milestone.

## 10) Consumer Usage Rules (Post REF-4)

Modules (Recruitment, HR, Documents, others) must use:
1. `module -> ReferenceServiceFacade -> canonical response`.

Forbidden patterns:
1. direct reference table reads;
2. direct resolver coupling bypassing facade;
3. module-local applicability if/else;
4. module-local document schema forks.

## 11) Test and Enforcement Gates

Required checks:
1. seed idempotency tests;
2. facade DTO shape/stability regression tests;
3. country/group consistency tests;
4. document field schema validation tests;
5. override boundary enforcement tests;
6. migration fallback tests;
7. REF-3.1 guard-scan pass with no new violations.

Required CI artifacts:
1. latest guard-scan report;
2. REF-4 catalog conformance report;
3. compatibility path registry update.

## 12) STOP Conditions (Hard Blockers)

REF-4 implementation is blocked if any condition is true:
1. facade contract unstable or missing freeze plan;
2. catalog ownership undefined for any in-scope domain;
3. document field schema model unresolved;
4. tenant override boundaries unclear or unenforced;
5. country grouping model incomplete;
6. migration strategy missing;
7. DTO stability matrix absent;
8. multiple sources of truth active for same domain;
9. unresolved direct-access violations from guard-scan;
10. REF-4 work includes runtime behavior expansion.

## 13) PASS Criteria (Gate to Start REF-4 Implementation)

REF-4 can start only when all are true:
1. ownership cards/matrix approved for all in-scope domains;
2. facade DTO stability matrix approved;
3. country/group model approved;
4. document field schema model approved;
5. override boundary policy approved and testable;
6. migration/seeding strategy approved;
7. guard-scan baseline clean for targeted scope;
8. STOP conditions all clear.

Decision output must be recorded as:
1. `PASS`, or
2. `PASS_WITH_CONSTRAINTS` (with explicit constraints), or
3. `STOP`.

## 14) Execution Sequence (After Gate PASS Only)

1. finalize domain schemas and version policies;
2. implement deterministic seeds/migrations;
3. expand facade delivery (catalog-only);
4. migrate allowed consumers through facade only;
5. run full REF-4 gate test pack and publish gate record.

Runtime behavior must remain unchanged during REF-4.

## 15) Architecture Gate Controls (Non-Negotiable)

This plan is an architecture gate, not a task checklist.

Execution control rules:
1. no catalog implementation may proceed without approved ownership card for that domain;
2. no consumer rollout may proceed without stable facade DTO contract classification (`stable/experimental/deprecated`);
3. no country-domain completion is valid without group model (`EU/EEA/Schengen/work/legal groups`);
4. no document-domain completion is valid without canonical field schema model controls;
5. no tenant override implementation is valid without explicit allowed/forbidden boundary policy;
6. any unresolved hard STOP condition blocks progression immediately.

Gate promotion rule:
1. gate state changes only by explicit decision record (`PASS`, `PASS_WITH_CONSTRAINTS`, `STOP`) with dated evidence links.
