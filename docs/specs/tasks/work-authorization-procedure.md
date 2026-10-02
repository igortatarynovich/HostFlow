# Work Authorization Procedure

**Status:** **OPENED** — Work Authorization Procedure Contract Gate **PASS** 2026-10-02. No preset row. No Polish document list. Feat locked. Runtime not authorized.  
**Date:** 2026-10-02  
**Trusted base:** `integration/release-product-a-b` @ `86284870` ([#401](https://github.com/igortatarynovich/HostFlow/pull/401))  
**Parents:** [contract](../architecture/work-authorization-procedure-contract.md) (`work_authorization_procedure.v1`) · [Legal Eligibility](legal-eligibility-requirement-policy.md) · [Sequential queue](sales-to-comms-sequential-queue.md)

> Legal Eligibility stays the decision chain. This slice does not extend it.  
> The [contract](../architecture/work-authorization-procedure-contract.md) names `country` + `procedure_type` + `kod_zawodu`, the union into `r5_required_set`, and the two package states `submission_ready` and `submission_proceeded_by_override`. It writes no preset.  
> `r5_required_set` stays the only required-document writer. Minimal Recruitment → HR stays **not** scheduled. HostFlow v1 is not release-ready.

---

## Problem

A work-authorization submission needs its own requirements. Those requirements are not a second copy of the vacancy file, and they are not a Legal Eligibility question.

## Original Goal → Completion Proof

**Problem this phase must permanently remove:**
An operator cannot tell, from one policy, what must be in hand before a work-authorization procedure is submitted, without uploading again a document the product already holds.

**Completion proof (named consumer):**
For one named procedure key, the submission requirements and the effective readiness are readable, evidence already held satisfies them, and a waive is distinct from a readiness override. This opening does not supply that key's document list.

**False close (reject):** a global `kod_zawodu` → documents list, or a Polish preset written in this opening.

## Order

1. Boundary and procedure semantics. Recorded.
2. [Contract](../architecture/work-authorization-procedure-contract.md) accepted. Work Authorization Procedure Contract Gate **PASS**. No preset row.
3. Procedure presets for the keys this product will run. Not this acceptance.
4. Runtime. Not authorized.

## What stays closed

| Slice | State |
|---|---|
| Legal Eligibility decision chain | closed for this scope; Matrix Gate **not PASS** |
| Procedure presets and Polish document lists | not written |
| Runtime, pack, engine | not authorized; feat locked |
| Minimal Recruitment → HR | queued, not scheduled |

## History

- 2026-10-02: **Work Authorization Procedure Contract Gate PASS.** Evidence is the contract. Selector is `country` + `procedure_type` + `kod_zawodu` → one preset. No preset row. No document list. No procedure type. No `kod_zawodu` mapping. `r5_required_set` stays the only writer. Feat locked. Runtime not authorized. Legal Eligibility is unchanged. The Legal Eligibility Matrix Gate is not passed.
- 2026-10-02: **Procedure semantics named.** `procedure_type` is a stable procedure, not a document name. `kod_zawodu` selects a preset and is not a source of requirements. Requirements are added with provenance `work_authorization_submission` and unioned by `r5_required_set`. `submission_ready` and `submission_proceeded_by_override` stay distinct. Ready to submit is not a finding that an authority will accept the package. No preset row. Work Authorization Procedure Contract Gate **not PASS**. Feat locked. Runtime not authorized.
- 2026-10-02: **Contract opened.** Boundary only. Key is `country` + `procedure_type` + `kod_zawodu`. No preset row. Work Authorization Procedure Contract Gate **not PASS**. Evidence reuse and effective readiness are the Legal Eligibility default-policy rules. Feat locked. Runtime not authorized.
