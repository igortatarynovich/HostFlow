# ADR-043: Profile-Owned Module Requirements

**Status:** Accepted  
**Date:** 2026-10-07

**Related:** ADR-002 · ADR-016 · ADR-018 · ADR-026 (P-02) · ADR-028 · requirement-policy-authority.md · requirement-resolution-contract.md · ready-for-employment-contract.md · recruitment-employment-boundary-ownership.md · entity-profile-vacancy-overlay-contract.md

## 1. Decision

Module requirement configuration is moved from the global RPM/R5 policy writer to versioned profiles configured by the bounded context that consumes the requirement.

**Platform Requirements remains the owner of the requirement capability**: requirement/evaluation contracts, shared semantics, versioning rules and evaluator behavior.

The canonical module configuration authorities are:

- **Recruitment Profile Version** for Recruitment candidate field and document requirement configuration.
- **HR Employment Profile Version** for Employment/HR field and document requirement configuration, including legalization, medical/BHP, contract and ZUS concerns.

The profiles are configuration SoTs under P-04; they do not create Recruitment- or HR-local requirement engines.

For P-04 purposes:

- Recruitment configures Recruitment Profile requirement membership and requiredness;
- HR configures HR Employment Profile requirement membership and requiredness;
- Platform Requirements owns the shared requirement/evaluation semantics and evaluator.

The corresponding Recruitment and HR Capability Passports MUST be updated in the same architecture cutover to record these configuration classes explicitly.

A profile requirement references canonical platform definitions. It does not create a second Field Registry or Document Type Registry.

The platform registries continue to answer:

- what a canonical field means;
- what a canonical document type means;
- its schema and metadata.

A module profile answers:

- whether that canonical item participates in this module process;
- whether it is hidden, preferred/optional, or required.

There MUST be one configuration authority for one bounded-context requirement question, while the Platform Requirements capability remains the single owner of requirement/evaluation semantics.

## 2. Why

The current implementation has multiple layers capable of contributing answers to candidate requirements:

- CandidateProfile `field_configs` / `document_configs`;
- Entity Profile membership and refs;
- Document Packs;
- Process Profile transition requirements;
- RPM/R5 `merge(pack, tenant_delta)`;
- vacancy-specific overlays;
- package/readiness consumers.

This makes requirement provenance difficult to reason about and allows the same business question to be answered by several independently evolving mechanisms.

Recruitment and HR also have different responsibilities.

A document may be irrelevant to Recruitment but required by HR. Conversely, Recruitment may require evidence for candidate qualification that is not an HR start requirement.

A global document-policy configuration writer therefore does not represent bounded-context configuration ownership correctly.

## 3. Platform invariants retained

This ADR does NOT change the following principles:

1. P-02: Platform Requirements remains the single owner of the requirement/evaluation capability.
2. Requirement, Evidence and Document remain separate concepts.
3. Field Registry remains the canonical field definition authority.
4. Document Type Registry remains the canonical document-type definition authority.
5. Evidence is shared by reference; modules do not create duplicate copies.
6. Recruitment and Employment remain separate bounded contexts.
7. Recruitment emits the handoff; Employment owns employability and employment.
8. Handoff does not create a second source of person facts or documents.
9. Evaluation is derived from policy + facts + evidence. Evaluation is not policy authority.
10. A read model, projection or compatibility adapter MUST NOT become a second policy writer.

## 4. Recruitment Profile

A versioned Recruitment Profile defines the Recruitment information contract for candidates using canonical references.

It contains at least:

### Fields

Each field membership has module requirement semantics such as:

- hidden;
- optional;
- required.

### Documents

Each document membership has module requirement semantics such as:

- hidden;
- preferred;
- required.

Document membership references a canonical Document Type Registry identity.

The profile does not duplicate document schemas or metadata.

A vacancy selects and pins a Recruitment Profile Version.

A Profile Version is an immutable decision-basis identity. Once referenced by a vacancy, candidate decision, handoff or Employment decision, its requirement configuration MUST NOT change in place.

`profile_code` is the stable logical profile identity. A concrete immutable revision has its own persistent identity and monotonically ordered version/revision number.

The existing mutable `EpEntityProfile.version` field does NOT satisfy this contract by itself: the current registry updates one `(tenant_id, profile_code)` row in place and replaces its field rows. The migration MUST introduce or prove an immutable revision identity before runtime pinning is cut over.

Editing a profile after an immutable revision has been published MUST create a new revision rather than mutate the published revision.

A vacancy MUST NOT independently add, remove, tighten or relax Recruitment document requirements.

If different requirements are needed, a different profile version is required.

## 5. Candidate requirement state

Candidate-specific state is separate from profile policy.

For a document requirement the operator-facing declaration state supports:

- unknown;
- does_not_have;
- has_document;
- upload_requested.

`has_document` is a declaration only.

It MAY expose/create an upload slot for the canonical document type.

It MUST NOT satisfy a required requirement by itself.

Evidence lifecycle remains independently owned by the evidence/document capabilities, including uploaded, verification and rejection state.

## 6. Requirement satisfaction

A required Recruitment document requirement is satisfied only when acceptable evidence satisfies the requirement according to the canonical evidence/verification contract.

A required requirement may alternatively be waived by an authorized manager override.

A manager override MUST be:

- scoped to the candidate requirement;
- scoped to the pinned profile version;
- actor-attributed;
- reasoned;
- timestamped;
- auditable;
- version-safe.

Absence of evidence without an applicable approved override remains blocking.

Preferred/optional requirements do not block Ready for handoff.

## 7. Vacancy ownership

Vacancy owns the hiring opportunity and its binding to a Recruitment Profile Version.

Vacancy does not own Recruitment requirement policy.

The existing Vacancy Overlay contract is amended:

- vacancy-specific screening/value criteria MAY remain where separately owned;
- vacancy overlay MUST NOT add/remove/tighten/relax document requiredness;
- vacancy overlay MUST NOT create field presence requirements that redefine Recruitment Profile requiredness.

The existing `KIND_DOCUMENT` requirement mutation is deprecated and must be removed during cutover.

Requirement-affecting `KIND_PRESENCE` mutation is likewise deprecated.

## 8. Ready for handoff

Ready for handoff evaluates the pinned Recruitment Profile Version against live canonical candidate facts, evidence and applicable overrides.

A candidate MUST NOT become ready for handoff while a required Recruitment requirement remains unsatisfied and unwaived.

Ready for handoff MUST NOT obtain additional Recruitment requirements from:

- vacancy document overlays;
- Process Profile document requirements;
- Document Pack requiredness;
- RPM/R5 tenant document policy;
- legacy CandidateProfile JSON;
- package-specific independent requirement writers.

During migration these systems MAY act as compatibility adapters only where explicitly documented.

They MUST NOT remain independent policy authorities after parity.

## 9. Handoff

Handoff transfers authority/access/provenance, not duplicated facts or document payloads.

The handoff pins or references sufficient provenance to reproduce the Recruitment decision, including:

- Recruitment Profile Version;
- relevant fact/evidence references and versions;
- applicable manager overrides;
- decision provenance.

`ready_for_employment.v1` remains a boundary artifact and MUST NOT become the live source of person facts, evidence or HR requirements.

Employment consumes the same canonical facts/evidence through its own authority and access rules.

## 10. HR Employment Profile

Employment/HR has an independent versioned HR Employment Profile.

It may define requirements for:

- employee facts;
- legalization;
- employment documents;
- medical/BHP;
- contract/formalization;
- ZUS;
- other Employment-owned pre-start obligations.

The HR profile references the same canonical Field Registry and Document Type Registry.

A document already supplied during Recruitment is reused as evidence when acceptable.

HR MUST NOT require a duplicate upload solely because the requirement originates from a different bounded context.

Recruitment requirements do not automatically become HR requirements.

HR requirements do not move upstream into Recruitment merely because HR will need them later.

## 11. HR instance state

`hr_employment_requirements` remains the materialized requirement state for one Employment.

It is not replaced by the HR Profile.

The target relationship is:

HR Employment Profile Version
→ materialize Employment requirements
→ `hr_employment_requirements`
→ resolve against canonical facts/evidence
→ Legal Eligibility / Ready to Start consumers.

The current R5-derived `hr_required_set` is a migration dependency and not the target policy authority.

## 12. Legacy CandidateProfile

Legacy CandidateProfile `field_configs` / `document_configs` already provide useful operator/editor behavior.

They MUST NOT be revived as a new independent source of truth.

Their editor capabilities are to be migrated onto the versioned profile requirement contract.

After cutover, legacy JSON may remain temporarily as compatibility storage/projection only if explicitly marked derived.

## 13. Entity Profile evolution

Entity Profile is extended from role membership/refs into a versioned module-profile configuration contract capable of binding canonical fields and document types with module requirement semantics.

The stable Entity Profile identity and its immutable Profile Versions are distinct concepts. Existing storage MAY be evolved or normalized during migration, but consumers that require reproducibility MUST pin the immutable version identity, not merely `profile_code` and not a mutable row whose contents can later be replaced.

This is a P-04 configuration surface consumed by the Platform Requirements capability. It is not a second implementation or owner of Requirement Evaluation.

This extension MUST reuse existing registries and profile/version infrastructure.

It MUST NOT mint:

- a second Field Registry;
- a second Document Type Registry;
- a second Evidence store;
- a second Requirement Evaluation engine;
- module-local document type definitions.

Recruitment Profile and HR Employment Profile are distinct bounded-context policies even when they reference the same canonical definitions.

## 14. RPM/R5 migration

`r5_merge_pack_tenant_delta` is superseded as the target module requirement configuration write authority.

This does not transfer ownership of the Platform Requirements capability or Requirement Evaluation into Recruitment or HR.

RPM/R5 remains temporarily available only to preserve existing consumers during staged cutover.

No new consumer may be introduced against R5 for module requirement ownership after acceptance of this ADR.

Migration adapters must have a named deletion condition.

Target flow for Recruitment:

Recruitment Profile Version
→ Recruitment requirement evaluation
→ Ready for handoff.

Target flow for HR:

HR Employment Profile Version
→ materialized `hr_employment_requirements`
→ HR requirement resolution
→ Employment gates.

R5 MUST NOT remain between Profile and evaluator in the final architecture.

## 15. Process Profile and Document Pack

Process Profile may continue to describe process/stage behavior and determine when a requirement evaluation is consulted.

It MUST NOT independently define module field/document requiredness once the corresponding module is cut over.

For example, a Process Profile MAY gate `ready_for_handoff` on the result of Recruitment requirement evaluation. It MUST NOT independently declare that `medical_certificate`, address, or another field/document becomes required at that transition.

Document Packs may remain as presentation/grouping/catalog conveniences where useful.

They MUST NOT independently answer whether a candidate or employee must provide canonical document type X after profile cutover.

This explicitly supersedes the CL0 rule that transition/handoff requiredness belongs to Process Profile / Transfer Policy **for module field/document requiredness**. Process Engine retains ownership of process behavior and transition timing; module Profile configuration owns which module facts/documents are required.

It also supersedes the Requirement Rules Engine v1 source rule where Entity Profile + Document Pack independently contribute the module required set. Platform Requirements remains the evaluator, but after module cutover the applicable immutable Profile Version is the module requirement configuration input.

## 16. Authority matrix

| Concern | Target authority |
|---|---|
| Canonical field definition | Field Registry |
| Canonical document type/schema/metadata | Document Type Registry |
| Requirement/evaluation capability semantics | Platform Requirements |
| Recruitment field/document requirement configuration | Recruitment Profile Version |
| Recruitment candidate declaration state | Candidate requirement instance state |
| Evidence/file/verification | Existing Evidence / Document capabilities |
| Recruitment waiver | Versioned authorized manager override |
| Vacancy requirement policy | None; Vacancy binds profile version |
| Recruitment readiness verdict | Requirement evaluator / Ready for handoff consumer |
| Handoff provenance | ready_for_employment / handoff contracts |
| HR field/document/process requirement configuration | HR Employment Profile Version |
| Employment requirement instance state | `hr_employment_requirements` |
| Legal eligibility verdict | `legal_eligibility.v1` consumer |
| Ready-to-start verdict | Employment Ready to Start consumer |

## 17. Superseded ownership statements

This ADR supersedes, only where they assign module requirement write ownership to RPM/R5 or vacancy/process/document-pack writers:

- `requirement-policy-authority.md`;
- RPM ownership statements in `operator-candidate-employment-facts.md`;
- RPM ownership statements in `ce-code95-issuing-country.md`;
- RPM ownership statements in `requirement-resolution-contract.md`;
- RPM ownership statements in `legal-eligibility-contract.md`;
- RPM dependency in `hiring-eligibility-composition.md`;
- document/presence requirement mutation in `entity-profile-vacancy-overlay-contract.md`;
- corresponding policy-ownership portions of ADR-018;
- the CL0 assignment of transition/handoff field/document requiredness to Process Profile / Transfer Policy;
- the Entity Profile contract where `document_pack_code` is the source of the required document set;
- the Requirement Rules Engine v1 source rule where Entity Profile + Document Pack independently determine module requiredness.

These supersessions are limited to module requirement configuration ownership. Process Engine still owns process/stage behavior. Document Hub still owns document/evidence capabilities. Platform Requirements still owns requirement/evaluation semantics.

ADR-018 requirement/evidence/document separation and evaluation principles remain in force unless explicitly superseded here.

## 18. Migration sequence

1. Accept this ADR and freeze creation of new competing requirement writers.
2. Inventory all current requirement producers and consumers.
3. Introduce immutable Entity Profile Version identity and prove that published versions cannot be mutated in place.
4. Add versioned profile field/document requirement bindings against that immutable identity.
5. Add Recruitment Profile policy contract and tests without switching production consumers.
6. Add HR Employment Profile policy contract and tests.
7. Migrate the existing profile editor to the new contract.
8. Add candidate document declaration state and upload-slot behavior.
9. Bind Vacancy to a pinned Recruitment Profile Version and prohibit vacancy document requirement mutation.
10. Cut Recruitment evaluation / Ready for handoff to the pinned Recruitment Profile.
11. Pin Recruitment Profile provenance in handoff.
12. Materialize HR requirements from the pinned HR Employment Profile.
13. Cut HR requirement consumers from R5.
14. Prove consumer parity and boundary behavior.
15. Remove R5/RPM, legacy package and Process Profile requirement authority paths that no longer have consumers.
16. Remove compatibility projections after their deletion gates pass.

## 19. Acceptance gates

The architecture is not considered cut over until all of the following are proven:

1. Exactly one Recruitment authority answers whether canonical field/document X is required.
2. Exactly one HR authority answers the equivalent HR question.
3. Vacancy cannot mutate document requiredness.
4. Process Profile cannot independently introduce Recruitment document requiredness.
5. Required Recruitment evidence blocks Ready for handoff when absent.
6. Preferred/optional Recruitment evidence does not block.
7. `has_document` alone never satisfies a required requirement.
8. Authorized manager override can waive a specific requirement with full audit provenance.
9. Handoff reuses canonical facts/evidence without copying.
10. HR reuses acceptable Recruitment evidence without duplicate upload.
11. HR may require evidence that Recruitment did not require.
12. Recruitment is not forced to collect HR-only information.
13. Pinned profile versions make historical decisions reproducible.
14. No production consumer depends on R5/RPM as an independent requirement writer before R5/RPM removal.
15. Legacy CandidateProfile JSON is not a second write authority.

## 20. Non-goals

This ADR does not:

- merge Recruitment and HR;
- replace Field Registry;
- replace Document Type Registry;
- replace Evidence/Document Hub;
- create a second evaluator;
- change canonical fact ownership;
- make the handoff manifest a live data store;
- require Recruitment to collect all future Employment data;
- redesign Legal Eligibility itself;
- redesign Ready to Start itself.

## 21. Status of current compatibility fix

Removal of obsolete June `ready_for_handoff` address, unconditional medical and recruiter-confirmation requirements is compatible with this ADR.

That change removes legacy blockers.

It does not implement Profile-owned requirements and must remain independently testable/releasable from this architecture migration.
