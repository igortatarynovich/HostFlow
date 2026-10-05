# Requirement Resolution Contract

**Status:** **Accepted** — Requirement Resolution Contract Gate **PASS**. No legal rule. No document type. No authoring of the required set. No runtime module.  
**Date:** 2026-10-05  
**Line:** `dec5dac8` (ancestor `integration/release-product-a-b` @ `020cb4e5`)  
**Machine id:** `requirement_resolution.v1` — named here. No runtime module.  
**Parents:** [ADR-016](ADR-016-requirement-evidence-document-separation.md) · [Requirement and Evidence model](../platform/requirement-evidence-model-p0.md) · [Legal Eligibility](legal-eligibility-contract.md) (`legal_eligibility.v1`) · [Pre-employment requirements](employee-record-employment-lifecycle-contract.md) (`pre_employment_requirements.v1`) · [Work Authorization Procedure](work-authorization-procedure-contract.md) (`work_authorization_procedure.v1`)

**L0 checklist:** No new P-rule. No Passport or Manifest shape change. No Architecture RFC. Applies **P-02** and **INV-01**: one authority still answers whether this candidate must provide canonical type X, and that authority stays RPM `r5_required_set`. This contract does not rewrite L0.

> Requirement Resolution Contract determines which Employment requirement applies, which fact is missing when applicability cannot yet be resolved, and which accepted evidence variant may satisfy the requirement once the necessary facts are known. It does not define legal policy, create document types, or author the final required document set.

The sequential queue is unchanged. Employee Record & Employment Lifecycle stays the active product. Feat stays locked. HostFlow v1 is not release-ready.

---

## Question

For one requirement definition on one Employment: does it apply, which fact is still missing if applicability cannot yet be resolved, and which accepted evidence variant may satisfy it once the necessary facts are known?

What the work, the law, the client, or a submission requires is decided by those sources. Canonical document types, and the final required set, stay on their existing authorities. Ready to Start reads the stored result.

---

## Place

```text
Vacancy / Legal Eligibility / Company / Work-authorization submission
        ↓  what is required
Requirement Resolution
        ↓  which fact is still missing, and which accepted evidence variant may prove a known fact
Accepted Evidence
        ↓  the allowable proof
r5_required_set
        ↓  the only author of the final required set
Ready to Start
        reads the result
```

This contract is not a fifth source. A definition that none of the four sources named does not appear because this contract exists.

| Source | Provenance already used | What it decides | This contract |
|---|---|---|---|
| Vacancy / profession preset | vacancy, profession preset | What this work requires | consumes the definition |
| Legal Eligibility | Legal Eligibility | Lawful stay, and a lawful basis for this employment | consumes the chain result |
| Company | client or tenant policy | What this client adds | consumes the definition |
| Work Authorization Procedure | `work_authorization_submission` | What the selected submission preset adds | consumes the definition |

The instance stays one row of `pre_employment_requirements.v1`: one Employment, one `definition_key`. This contract adds no column and does not change that uniqueness. It adds no provenance column. The labels above are the sources that already name a definition.

---

## Progress and resolution

Progress is how proof is obtained. Resolution is the stored outcome of an applicable row.

The stored resolution stays `unresolved`, `satisfied`, `waived`, or `blocking`. This contract does not add a value and does not adopt `RequirementEvaluationStatus` or `CandidateEvidenceStatus` as that column.

| Progress | When | Stored resolution |
|---|---|---|
| `needs_input` | Applicability cannot yet be resolved because a fact is missing. The system asks for that fact | `unresolved`. No document is requested |
| `needs_evidence` | The necessary facts are known. An accepted evidence variant may satisfy the requirement. The proof is not linked | `unresolved` |
| `under_review` | The proof is linked and verification is not finished | `unresolved` |
| `satisfied` | The proof is accepted for this Employment row | `satisfied` |

`waived` is an explicit decision for this row, with actor, time, and reason. It is not a step of obtaining proof. It does not rewrite the definition.

### blocking

`blocking` is a resolved negative outcome, not missing evidence.

The fact is established, and it is incompatible with this Employment. A driving entitlement that is known and is not the entitlement this Employment requires, a Code 95 that is known and has expired, and a work authorization that is known and is not valid for this Employment are that outcome.

Missing proof stays `unresolved`. `needs_input`, `needs_evidence`, and `under_review` are readings of an unresolved row. They are not `blocking`.

Definition severity is a different axis. A REQUIRED definition may stay `unresolved` while proof is still missing. That row is not resolution `blocking`. This contract does not rename the stored word `blocking`.

---

## Cardinality

One requirement is not one document. All three shapes are normative.

| Shape | Rule |
|---|---|
| 1 requirement → 1 evidence | One accepted evidence variant, one document instance |
| 1 requirement → `all_of`(A, B) | The requirement is satisfied only when every component of the variant is linked |
| 2 requirements → 1 shared evidence | One document instance may satisfy two requirement rows, through two evidence links |

Accepted Evidence already names `any_of` and `all_of`. Shared evidence is normative beside them. A Polish driving licence that carries Code 95 is why the third shape has to exist. Which issuing country uses one file, and which uses a licence plus a qualification card, is the separate case [CE, Code 95, and the Issuing Country](ce-code95-issuing-country.md). This contract does not encode that selection.

A second upload is not created because a second source names the same proof.

---

## Reuse

The file is global. Candidate Evidence may be reused. Satisfaction of a requirement belongs to one Employment.

A new Employment does not inherit `satisfied`. The resolver checks existing evidence against the new row. That check may read `satisfied` when the same proof meets the new row, as with a driving entitlement already held. The same check may read `blocking` when the established fact does not cover this Employment, as with `valid_for_this_employment`.

The reading is not a write. Linking a row stays the act of `pre_employment_requirements.v1`, using an evidence id a later caller names. This contract does not search the store and does not copy the file. Employee history does not by itself mark the new row `satisfied`.

`valid_for_this_employment` is a fact of this Employment. It is not a global fact of the candidate.

---

## Levels

Levels travel with the definition from its source. This contract does not store them as resolution and does not create a second vocabulary.

| Definition | Effect on this Employment |
|---|---|
| REQUIRED | The applicable row must be `satisfied` or `waived` before the Ready to Start entrance is open |
| PREFERRED | The row may be recorded and shown. It does not hold that entrance |
| NOT_REQUIRED | The row is not applicable |

REQUIRED on a definition is not resolution `blocking`.

---

## Authority

| Question | Authority |
|---|---|
| Which definitions does the work, the law, the client, or the submission name? | Those four sources |
| Which Employment requirement applies, which fact is missing, which accepted evidence variant may satisfy it? | this contract |
| Which document shapes may prove a requirement? | Accepted Evidence |
| Must this candidate provide canonical type X? | RPM `r5_required_set` |
| Is this Employment row satisfied, waived, or blocking? | `pre_employment_requirements.v1` stores the result. This contract does not write the row |
| May this Employment start? | Ready to Start reads its four canonical results and does not recompute this contract |

Legal Eligibility keeps `citizenship_class` → `stay_basis` → `work_authorization_basis` → `valid_for_this_employment`. This contract adds no chain value, fills no matrix cell, and assigns no require list and no remove list. `visa_d` is not mapped onto `visa`. Driving licence, Code 95, ADR, and profession stay outside that chain.

---

## Requirement Resolution Contract Gate

**Outcome:** **PASS**. Evidence is this file.

PASS holds because all of the following are true:

1. The job is applicability, the missing fact, and the accepted evidence variant.  
2. This contract is not a source of requirements and is not an author of the required set. `r5_required_set` stays the sole writer.  
3. `blocking` is a resolved negative outcome, not missing evidence. The stored resolution set is unchanged.  
4. One requirement is not one document. The three cardinality shapes are normative.  
5. The file is global, Candidate Evidence may be reused, and satisfaction belongs to the Employment row. A new Employment does not inherit `satisfied`. The resolver re-checks existing evidence against the new row.  
6. No legal rule is encoded. The Legal Eligibility Matrix Gate is not passed by this file. No document type is created. No pack change. No column. No runtime module.  
7. The sequential queue is unchanged. HostFlow v1 is not declared release-ready.

This PASS does not materialize a requirement, does not choose an evidence variant for a person, and does not move an Employment.

---

## Out of this slice

The first vertical case is CE + Code 95 + issuing country. It exercises `needs_input`, shared evidence, separate evidence, and REQUIRED / PREFERRED. It is opened separately in [CE, Code 95, and the Issuing Country](ce-code95-issuing-country.md). It does not enter Legal Eligibility. This contract does not encode it. The [operator facts surface](operator-candidate-employment-facts.md) records the facts. It is not a source of requirements.

Also out of this slice:

- A population of the Legal Eligibility matrix.  
- Normalization of card tokens into pack inputs.  
- A Python or JSON machine copy. The id `requirement_resolution.v1` is reserved. It is not shipped.  
- A change to `hr_employment_requirements`, Ready to Start, or the legal chain.  
- Runtime.

Feat stays locked. HostFlow v1 is not release-ready.
