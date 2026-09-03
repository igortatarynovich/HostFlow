# Requirement Policy Authority

**Status:** **Accepted** (L2 contract — RPM-1 Authority Gate)  
**Date:** 2026-09-02  
**Trusted base:** `integration/release-product-a-b`  
**Related:** [`ADR-018`](ADR-018-requirement-policy-evaluation-model.md) · [`../tasks/requirement-policy-management.md`](../tasks/requirement-policy-management.md) · [`../tasks/platform-reference-identity-sot.md`](../tasks/platform-reference-identity-sot.md) · [`../tasks/entity-profile-vacancy-overlay-contract.md`](../tasks/entity-profile-vacancy-overlay-contract.md) · [`../tasks/documents-platform-e8-eval.md`](../tasks/documents-platform-e8-eval.md) · [`../gates/v1-release-dag-dependency-position.md`](../gates/v1-release-dag-dependency-position.md)

**L0 checklist:** No new P-rule; no Passport/Manifest **shape** change; no Architecture RFC. Applies **P-02** (one owner of this write), **INV-01** (one SoT for the operator question), **INV-16** (contract before a second admin). Does not rewrite L0. Does not mint a Documents Admin vs Rules Admin split.

> This file is the **SoT** for the operator question and the single write of document-requirement authority.  
> ADR-018 remains the evaluation model. Reference R5 remains `merge(pack, tenant_delta)`.  
> Vacancy Overlay remains a **different** write-set (vacancy delta over Profile / Screening Pack).  
> Machine copy: `requirement_policy_authority.v1` in `backend/app/reference/requirement_policy_authority.py`.

---

## Operator question (one)

For this tenant / client / vacancy / profile / country, **must this candidate provide document type X?**

Answer shape: **base rule**, **override**, **reason**, **result**.

No second question is this contract. Mapping, intake publish, hiring stage identity, HR handoff, and **intake qualification** (`lead_criteria_v1` / Meta screening) are other programs. Qualification is not a tenth write of this question.

---

## Write authority (one)

**R5** `merge(pack, tenant_delta)` and scoped overlays that **feed that merge**.

| May write | Must not write |
|-----------|----------------|
| Platform pack (`document-policy-platform-pack-v1.json`) as the base | A parallel pack catalog treated as SoT |
| Tenant overlay delta that `validate_tenant_overlay_delta` accepts | A tenant fork of pack defaults (`requiredTypes` / `optionalTypes` at delta root) |
| RPM-2 operator overlay that persists **that** delta (`tenant_document_policy_deltas`) | Vacancy Overlay / screening pack (already Overlay Gate) |
| | Leftover `sample_ruleset.json` / seeded `document_ruleset_versions` as a second write |
| | A Hub packages table |
| | `document_policies` flags as a parallel authority (fold in RPM-3) |

Producer of the merge function: `backend/app/reference/document_policy_merge.py` (`merge_resolved_policy`).  
D4 already **reads** this merge via E8-eval. RPM-2 persists `tenant_delta` in `tenant_document_policy_deltas`. This contract forbids a second **write** of the same question. It does not cut over leftover consumers (RPM-3A/3B).

---

## Answerer classification (frozen — nine rows)

A later RPM slice may **retire** a leftover. It may not add a tenth write of this question.

| # | Live answerer | RPM role | Evidence (paths) |
|---|---------------|----------|------------------|
| 1 | R5 pack + `tenant_delta` | **Write authority** | `backend/app/reference/document_policy_merge.py` · `docs/specs/platform/document-policy-platform-pack-v1.json` |
| 2 | Vacancy Overlay + screening pack | **Not this write** | `backend/app/entity_profile/vacancy_overlay_runtime.py` |
| 3 | leftover `sample_ruleset.json` / seeded `document_ruleset_versions` | **Leftover** | `backend/app/modules/documents/data/sample_ruleset.json` |
| 4 | Hub `DOCUMENT_PACK_DEFINITIONS` | **Consume or retire** | `backend/app/modules/documents/pack_definitions.py` |
| 5 | DB `ref_packs` (transfer policy) | **Consume** | `backend/app/services/transfer_policy_resolver.py` · `backend/app/models/ref_document_type.py` |
| 6 | ADR-018 requirement graph / Engine packs | **Consume or explicit contract** | `backend/app/requirement_rules/requirement_rule_graph.py` · `backend/app/requirement_rules/data/` |
| 7 | `document_applicability_policy.py` | **Consume** | `backend/app/services/document_applicability_policy.py` |
| 8 | hiring pipeline gates / `candidateStageDocPolicy.ts` | **Consume** | `hostflow-frontend/src/utils/candidateStageDocPolicy.ts` · `backend/app/services/candidate_doc_pipeline_guard.py` |
| 9 | `document_policies` table (TENANT/CLIENT/VACANCY flags) | **Consume or fold** into `tenant_delta` | `backend/app/models/document_policy.py` · `backend/app/api/v1/document_policies.py` |

Roles are closed: `write_authority` · `not_this_write` · `leftover` · `consume` · `consume_or_retire` · `consume_or_explicit_contract` · `consume_or_fold`. Exactly one row is `write_authority`.

---

## Architecture review (L0 — ten questions)

| # | Answer |
|---|--------|
| 1 | **Owner:** Platform Reference owns the merge write. Documents Hub **consumes** evaluation (E8-eval). Recruitment / Hiring **consume** the result; they do not write this authority. |
| 2 | Not a new capability. Applies ADR-018 evaluation + R5 merge. The unnamed gap was **who may write**. |
| 3 | No new adapter. Evaluation stays `documents.hub_adapter_v1`. Merge stays `document_policy_merge`. RPM-2 persists `tenant_delta` in `tenant_document_policy_deltas`; it does not mint a second adapter. |
| 4 | Overlay remains Overlay. No Hub packages table. No Documents Admin vs Rules Admin. No CL8. E8-eval / R5 not reopened. |
| 5 | Settings that edit non-authority JSON are not this write. RPM-2 is the one operator overlay. RPM-3A retires parallel writers; it does not mint a second overlay. |
| 6 | SoT for the operator question = this file + `requirement_policy_authority.v1`. Parallel leftover writers are classified, not blessed. |
| 7 | No new event family. RPM-2/3 emit existing security/eval events if they persist or cut over. |
| 8 | **Requires:** R5 merge, E8-eval D4 bind. **Optional:** Overlay as CL7 vacancy delta (different write-set). |
| 9 | No new licence. |
| 10 | Public contract **additive**: authority classification. No breaking Hub/Passport change. |

**INV-01:** one SoT for “must provide type X?”. **INV-16:** this contract before a second admin UI.

---

## False close

Reject: Documents Admin separate from Rules Admin; Hub packages table; Overlay rewrite as RPM; CL8; reopening E8-eval / R5; walking Hiring E2E without the overlay; starting Mapping / Intake / min HR “while we are here”; Foundation ✅; a tenth write of this question; folding intake qualification / `lead_criteria_v1` into this write.

---

## Consequences

- RPM-2 persists only this write authority (operator overlay with reason as sibling metadata).  
- RPM-3A **PASS** retired parallel writers of the operator question: A `document_policies`, C leftover ruleset writes, J P3B `document_required` only.  
- RPM-3B must make remaining classified consumers read the same merge or retire them as answerers.  
- ADR-018 “Admin UI for policy editing” is this program, not a second product.

---

## History

- 2026-09-03: RPM-3A Parallel Authority Retirement Gate **PASS**. Writes of A / C / J `document_required` retired. Active Product → RPM-3B.
- 2026-09-03: RPM-2 Operator Gate PASS [#342](https://github.com/igortatarynovich/HostFlow/pull/342). RPM-3A docs lock activates parallel-writer retirement (A / C / J `document_required`).
- 2026-09-03: Screening / `lead_criteria_v1` named as a different question, not a tenth write.
- 2026-09-02: Accepted as RPM-1 Authority contract. Nine-row classification frozen. Feat locked until RPM-2.
