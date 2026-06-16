# REF-3 Implementation Gate Plan

Status: approved to start (based on REF-2 = PASS_WITH_CONSTRAINTS)  
Depends on: `docs/specs/gates/ref2_gate_record_2026-05-27.md`  
Purpose: implement `ReferenceServiceFacade` as mandatory boundary layer.

## 1. REF-3 Scope

REF-3 is an access-boundary stage, not catalog expansion.

In scope:
1. introduce backend `ReferenceServiceFacade` as single read boundary;
2. define stable facade response shape for current phase;
3. migrate first runtime consumer to facade;
4. add conformance tests for canonical/stable response;
5. enforce forbidden direct access patterns for migrated scope.

Out of scope:
1. broad catalog enrichment (REF-4);
2. new runtime engines/contracts/consumers;
3. UI expansion;
4. OCR/automation extensions.

## 2. Hard Constraints from REF-2

While REF-3 is in progress:
1. M5 remains frozen as `consumer-preview`;
2. runtime expansion is prohibited;
3. onboarding new consumers is prohibited (except explicitly chosen pilot consumer);
4. creating new contracts is prohibited;
5. any layer above facade is `STOP`.

## 3. Facade Target

`ReferenceServiceFacade` must be the only allowed module entry point for reference read-paths in migrated scope.

Initial facade capabilities:
1. countries;
2. citizenship groups;
3. document types;
4. document type versions;
5. document field schemas;
6. applicability (packs + rules);
7. tenant overrides;
8. labels/localization projection;
9. validation metadata.

## 4. Facade API Surface (v1)

## 4.1 Input

`ReferenceContext` (as defined in REF-2), minimally:
- tenant/module/entity_type/entity_id
- work_country/citizenship/residence_status
- position_category/stage/employment_type
- client_id/vacancy_id
- locale/as_of

## 4.2 Operations

1. `get_reference_bundle(context)`
- returns canonical response for module consumption.

2. `get_document_applicability(context)`
- returns expected docs + reasons + source + criticality + due points + validation.

3. `get_document_type_profile(code|id, locale)`
- returns canonical type metadata, active version, fields schema, expiry/verification metadata.

4. `get_country_profile(country_code, locale)`
- returns country/citizenship metadata and applicable packs/rules references.

## 4.3 Output (stable canonical response)

Must follow REF-2 response model and include:
1. `version`
2. `reference_version`
3. `context_echo`
4. `items[]`
5. `applicability`
6. `errors[]`

## 5. Allowed Consumers in REF-3

Only one pilot consumer is allowed for cutover in this stage:
1. HR expected document read-path (or equivalent single path selected at implementation start).

No other new consumers during REF-3.

## 6. Forbidden Access (effective during REF-3)

For migrated scope, modules are forbidden to:
1. read reference tables directly;
2. build local applicability rules;
3. map legacy `doc_type` outside resolver/fallback/sync;
4. consume document metadata outside facade;
5. create module-local rule engines.

## 7. Migration Strategy (REF-3)

1. Introduce facade in parallel with existing resolvers.
2. Wire facade to existing canonical resolvers internally:
- `DocumentTypeRuntimeResolver`
- `DocumentApplicabilityResolver`
- reference registry/foundation modules
3. Pilot consumer switches to facade response.
4. Keep compatibility projection only at facade edge.
5. Mark old direct path deprecated with owner + removal milestone (REF-5 target).

## 8. Compatibility Boundaries

Allowed temporary compatibility zones:
1. resolver fallback paths;
2. sync/backfill services;
3. compatibility tests.

Forbidden compatibility sprawl:
1. adding new module-local compatibility logic in runtime paths;
2. adding new direct reference access in modules.

## 9. Testing Gates (must pass)

## 9.1 Conformance tests

1. facade returns stable canonical response shape;
2. locale/labels fields are present and deterministic;
3. version + reference_version always present;
4. context echo integrity.

## 9.2 Integration tests

1. pilot consumer reads only facade output;
2. no behavior regression versus previous canonical output;
3. fallback behavior remains safe when legacy data present.

## 9.3 Guard tests / scan gate

1. no new direct reference-table reads in migrated module path;
2. no new local applicability if/else in migrated path;
3. no new blocker generation outside designated resolver/facade boundaries.

## 10. Delivery Gates for REF-3 PASS

REF-3 is `PASS` only if all are true:
1. facade exists and is callable in backend services;
2. one pilot consumer is migrated to facade-only read-path;
3. conformance tests are green;
4. guard checks for forbidden patterns are green for migrated scope;
5. compatibility path has owner + removal milestone;
6. UI remains unchanged.

If any is false -> REF-3 remains `PASS_WITH_CONSTRAINTS` or `STOP`.

## 11. Ownership Model

1. Platform/Reference team owns facade contract and rule delivery.
2. Module teams own rendering/use of facade response only.
3. Module teams do not own reference rule computation.

## 12. Execution Sequence

1. Create facade service skeleton + DTOs.
2. Implement `get_reference_bundle` using existing canonical resolvers.
3. Implement pilot consumer cutover.
4. Add conformance + integration + guard tests.
5. Run REF-3 gate evaluation.
6. If PASS -> proceed to REF-4 catalog completion.
