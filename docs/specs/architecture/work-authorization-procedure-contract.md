# Work Authorization Procedure

**Status:** **Accepted** — Work Authorization Procedure Contract Gate **PASS**. No preset row. No runtime module.  
**Date:** 2026-10-02  
**Trusted base:** `integration/release-product-a-b` @ `86284870` ([#401](https://github.com/igortatarynovich/HostFlow/pull/401))  
**Machine id:** `work_authorization_procedure.v1` — named here. No runtime module.  
**Parents:** [brief](../tasks/work-authorization-procedure.md) · [Legal Eligibility contract](legal-eligibility-contract.md) · [Legal Eligibility matrix](legal-eligibility-matrix.md)

> This slice asks whether a work-authorization package is ready to submit. It does not assert that the package is legally sufficient or that an authority will accept it.  
> The key is `country` + `procedure_type` + `kod_zawodu`. `procedure_type` is a stable procedure, not a document name. `kod_zawodu` selects a preset and is not itself a source of requirements.  
> The procedure adds requirements with provenance `work_authorization_submission`. `r5_required_set` unions them with the requirements already held. Existing evidence satisfies the new requirement. There is no second upload slot.  
> `submission_ready` and `submission_proceeded_by_override` are different states. This file writes no preset row. Feat stays locked. Runtime is not authorized. Legal Eligibility is not extended here. The Legal Eligibility Matrix Gate is not passed. HostFlow v1 is not release-ready.

---

## Question

For one candidate and one employment, when a work-authorization package is being prepared: which submission requirements does that procedure add, and is the package ready to submit?

This slice answers only those two things: the submission requirements, and the effective submission readiness, for that one candidate and that one employment.

Legal Eligibility has already answered whether the person may be in Poland and whether they may do this employment. This contract does not answer those questions again.

Ready to submit is a HostFlow package state. It is not a finding that the package is legally sufficient, and it is not a prediction that an authority will accept it. A preset is HostFlow default policy. The operator keeps the last decision by an audited override.

---

## Key

```text
country + procedure_type + kod_zawodu
  → preset
  → submission requirements
  → submission_ready | submission_proceeded_by_override
```

The selector is exactly `country` + `procedure_type` + `kod_zawodu` → one preset. It has no other meaning. This acceptance does not enumerate countries, procedure types, occupation codes, or documents. A procedure preset is that selected key plus its submission-requirement list. This file contains no preset row and no Polish document list.

### procedure_type

`procedure_type` is a stable type of procedure. It is not the name of a document in the package. It is not a document type and it is not an evidence type.

Two ways of obtaining the right to work are different procedure types when their submission requirements differ. A document name is evidence. It does not identify the procedure.

### kod_zawodu

`kod_zawodu` is an attribute of this employment and of the vacancy. The preset is selected with that attribute together with `country` and `procedure_type`.

`kod_zawodu` is not a source of requirements. It only takes part in selecting the preset. It does not by itself list documents, and it creates no requirement by itself. The same occupation can use different procedure types. If no preset matches this selector, this slice adds no submission requirement. It does not guess a list from `country`, `procedure_type`, or `kod_zawodu`.

---

## Submission requirements

The source of submission requirements is the selected preset. The procedure adds requirement instances with provenance `work_authorization_submission`. A submission requirement is a requirement, not an upload slot.

`r5_required_set` then unions those instances with the requirements already in the set. `r5_required_set` stays the sole writer of the system required set. The procedure does not write the set. Union keeps provenance on each requirement. Union does not create a second evidence object and does not create a second upload slot.

Satisfaction is Candidate Evidence bound to Document Link. Existing evidence may satisfy a submission requirement whatever provenance named it. A passport or a driving licence already held as evidence satisfies the new requirement at once. Vacancy, a profession preset, Legal Eligibility, and this procedure may all name that same evidence. There is no duplicate upload. This contract does not add a column. No preset is contributed here.

---

## Readiness

Four facts stay separate. `r5_required_set` does not mutate.

| Fact | Meaning |
|---|---|
| `r5_required_set` | what policy requires, after the union |
| evidence | what was actually obtained |
| waiver | which requirement the operator lifted for this process and this candidate |
| effective readiness | required − satisfied − waived |

Effective submission readiness is required − satisfied − waived. A requirement is missing only when policy requires it, evidence does not satisfy it, and no waiver lifts it.

`waive_requirement` lifts one requirement for this candidate and this process. It changes effective readiness. It does not mutate the policy requirement. `override_readiness` does not mark a requirement satisfied and does not mark it waived: the blockers stay, and the audit records the exception. Reasons, actor, and timestamp stay the closed set in the [Legal Eligibility default policy](legal-eligibility-contract.md#default-policy). This contract adds no reason and no action.

`update_preset` remains the administrator change for later cases. Repeated `rule_changed` waives are a review signal. The system does not edit a preset from that count.

Two package states stay distinct. An operator may go on from either of them. They are not the same state.

| State | Meaning |
|---|---|
| `submission_ready` | every submission requirement is satisfied or waived. Effective readiness has no remaining blocker. |
| `submission_proceeded_by_override` | at least one submission requirement is still a blocker, and an authorized operator applied `override_readiness`. The blockers stay listed. None of them becomes satisfied or waived. |

---

## Work Authorization Procedure Contract Gate

**Outcome:** **PASS**. Evidence is this contract. No preset row is written. `r5_required_set` stays the sole writer of the final required set.

The accepted contract is exactly this:

- The slice answers only submission requirements and effective submission readiness, for one candidate and one employment.
- The selector is exactly `country` + `procedure_type` + `kod_zawodu` → one preset.
- `procedure_type` is a stable procedure type. It is not a document type and it is not an evidence type.
- `kod_zawodu` only takes part in selecting that preset. It creates no requirement by itself.
- The source of submission requirements is the selected preset, with provenance `work_authorization_submission`.
- If no preset matches, this slice adds no submission requirement and does not guess one.
- `r5_required_set` stays the sole writer of the final required set.
- Existing evidence may satisfy a requirement whatever provenance named it. There is no duplicate upload.
- `waive_requirement` changes effective readiness and does not mutate the policy requirement.
- `override_readiness` does not satisfy a requirement and does not waive it.
- `submission_ready` and `submission_proceeded_by_override` stay different states.
- Readiness means only that the package is ready to submit. It is not legal sufficiency and it is not a prediction of an authority's decision.
- A preset is default policy. The operator keeps an audited override.

This PASS writes no Polish preset row, no document list, no procedure type, and no `kod_zawodu` mapping. It does not change Legal Eligibility, RPM, eligibility, transfer, `ready_for_employment.v1`, HR, or the database schema. It does not authorize a runtime module. Feat stays locked. Runtime is not authorized. Minimal Recruitment → HR stays not scheduled. The Legal Eligibility chain is unchanged. The Legal Eligibility Matrix Gate is not passed. Polish `country` + `procedure_type` + `kod_zawodu` → requirements is the next slice. This PASS does not produce it.

---

## Out of this opening

- Any Polish document list.  
- Any `kod_zawodu` preset row.  
- A change to the Legal Eligibility decision chain.  
- Pack, engine, eligibility, transfer, `ready_for_employment.v1`, HR, or a database column.  
- A runtime module of `work_authorization_procedure.v1`.  
- Unlocking feat. Scheduling Minimal Recruitment → HR.
