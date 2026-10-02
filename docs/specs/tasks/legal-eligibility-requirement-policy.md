# Legal Eligibility / Requirement Policy Normalization

**Status:** **OPENED** — brief opened 2026-10-02. Legal Eligibility Contract Gate **PASS**. Decision model amendment. Legal Eligibility Matrix Gate **not PASS**. Evidence rules are not encoded. Feat locked. Implementation not authorized. Runtime not authorized. Business rules are not written here.  
**Date:** 2026-09-29 (named 2026-09-30 by [#394](https://github.com/igortatarynovich/HostFlow/pull/394) / `9269fa19`; brief opened 2026-10-02; contract opened 2026-10-02 from `71f46e46`)  
**Parents:** [Hiring workflow E2E](hiring-workflow-e2e.md) · [Legal Eligibility contract](../architecture/legal-eligibility-contract.md) (`legal_eligibility.v1`, Legal Eligibility Contract Gate **PASS**) · [Legal Eligibility matrix](../architecture/legal-eligibility-matrix.md) (Opened; Matrix Gate **not PASS**) · [document policy platform pack](../platform/document-policy-platform-pack-v1.json) · [Requirement Policy Management](requirement-policy-management.md) · [Sequential queue](sales-to-comms-sequential-queue.md)

> Hiring E2E Acceptance Gate **PASS** does **not** prove a legal employability matrix.  
> This brief records the legal facts the product already stores and the distinctions `r5_required_set` does not express.  
> The [contract](../architecture/legal-eligibility-contract.md) is Accepted. Legal Eligibility Contract Gate **PASS**. The live model is the [decision chain](../architecture/legal-eligibility-contract.md#decision-chain). Legal Eligibility Matrix Gate **not PASS**. Evidence rules are not encoded.  
> `visa_d` is not mapped onto `visa`. The next product slice is [Work Authorization Procedure](work-authorization-procedure.md). This brief does not define it. Minimal Recruitment → HR stays **not** scheduled. HostFlow v1 is not release-ready.

---

## Problem

`r5_required_set` is the requirement authority the hiring walk consumes. It branches on `residency_status` values `eu_citizen`, `visa`, `none`, `no_residence_card`, and `card`.

The candidate card stores `poland_stay_basis` as `eu_citizen`, `visa_d`, `visa_c`, `karta_pobytu`, `waiting_for_trc`, and `other`. Only `eu_citizen` matches the pack. Two candidates on one vacancy, one with a Polish visa D and one with a residence card, therefore receive the same required set as a candidate with no stay basis.

Citizenship alone, employment country, residence-permit country and type, driving-licence issuing country, and Code 95 / qualification-card jurisdiction do not change the set. `eu_member` and `oswiadczenie_eligible` country lists are not read by the required-set path.

## Original Goal → Completion Proof

**Problem this phase must permanently remove:**
A recruiter cannot rely on the required set to tell an EU citizen from a non-EU candidate, or a visa-D stay from a residence card, because product legal facts and the policy vocabulary are not the same model.

**Completion proof (named consumer):**
Two candidates on one vacancy, with different recorded legal facts, receive different outstanding requirements when the business rules say they must, and the same set when the rules say they must not. The required-request flow already consumes `r5_required_set`; this slice changes that set, not the request state machine.

**False close (reject):** mapping `visa_d` onto the pack token `visa` without a written rule for which document that stay basis actually requires. A document-type alias that already folds `visa_d` into document type `visa` is not that rule.

## Recorded facts

Measured on `9269fa19`. These are storage and match facts. They are not a statement of which document a fact should require.

### Candidate stay basis

The candidate card offers `POLAND_BASIS_VALUES`: `visa_d`, `visa_c`, `karta_pobytu`, `eu_citizen`, `waiting_for_trc`, `other` (`hostflow-frontend/src/modules/candidate-card/constants.ts`). The value is stored as `extra.poland_stay_basis`.

The document owner context copies that stored value into `residency_status` (`_candidate_owner_context_defaults` in `backend/app/modules/documents/router.py`). The copy does not translate a card value into a pack token.

### Policy vocabulary the required set matches

The platform pack candidate overrides match only `residency_status`, and only these tokens (`docs/specs/platform/document-policy-platform-pack-v1.json`):

| `when.residency_status` | require | remove |
|---|---|---|
| `eu_citizen` | `national_identity_card` | `passport`, `visa`, `residence_card`, `work_permit` |
| `visa`, `none`, `no_residence_card` | `passport`, `visa` | `national_identity_card` |
| `card` | `passport`, `residence_card` | `national_identity_card` |

When no override matches, the candidate default required types are `driver_license`, `driver_qualification_card`, `tachograph_card`, and `passport`. The vacancy addition matches `requires_driver_attestation` only. It does not match a legal fact.

### Intake map is one way

`_map_residency_status_to_poland_basis` (`backend/app/api/public/intake.py`) writes pack-like tokens onto the card vocabulary: `visa` and `visa_d` become stored `visa_d`; `card`, `residence_card`, `residence_permit`, and `karta_pobytu` become stored `karta_pobytu`. The required-set path does not apply the inverse. Stored `visa_d` is not turned back into pack token `visa`. Stored `karta_pobytu` is not turned back into pack token `card`.

### Document-type aliases are not this rule

`hostflow-frontend/src/data/documentTypeAliases.ts` maps document types `visa_d` and `visa_c` onto `visa`, and `karta_pobytu` onto `residence_card`. That is document identity. This brief does not adopt it as the stay-basis match.

### Facts copied or listed, and not matched

Citizenship is copied into the same owner context and is not a `when` key of the candidate overrides.

`eu_member` lives on the country registry. `oswiadczenie_eligible_alpha2` lives on the pack country set (`UA`, `BY`, `MD`, `GE`). Neither list is a `when` key of the candidate overrides. The required-set path does not read them.

The candidate overrides do not match employment country, licence issuing country, or qualification-card jurisdiction.

## Distinctions the required set does not express

Comparing the card vocabulary with the override tokens:

| Recorded `poland_stay_basis` | Equals a pack override token | Required set |
|---|---|---|
| `eu_citizen` | `eu_citizen` | the `eu_citizen` override |
| `visa_d` | no | candidate default |
| `visa_c` | no | candidate default |
| `karta_pobytu` | no (`card` is a different token) | candidate default |
| `waiting_for_trc` | no | candidate default |
| `other` | no | candidate default |
| empty | no | candidate default |

A visa-D candidate and a residence-card candidate therefore receive the same required set as a candidate whose stay basis matches nothing. An EU-citizen candidate receives a different set. Citizenship and the country lists do not move a candidate between those sets.

This table is the observed collapse. It is not the matrix of documents each distinction must require.

## What stays closed

| Slice | State |
|---|---|
| Contract — facts, vocabulary, authority, outcome shape | [Legal Eligibility Contract Gate **PASS**](../architecture/legal-eligibility-contract.md) |
| Matrix — decision chain; evidence rules | [decision model](../architecture/legal-eligibility-matrix.md); Legal Eligibility Matrix Gate **not PASS**; evidence rules are not encoded |
| Pack change, engine change, runtime, and any other implementation | not authorized; feat locked |
| Mapping `visa_d` onto pack token `visa` | forbidden as a false close |
| Minimal Recruitment → HR | queued, not scheduled |
| `ready_for_employment.v1`, employee creation, auto-accept | unchanged |
| HostFlow v1 | not release-ready |

## Order

1. This brief: recorded facts, and the distinctions the required set does not express.
2. Contract: facts, vocabulary, authority, and the shape of a policy outcome. [legal-eligibility-contract.md](../architecture/legal-eligibility-contract.md). Legal Eligibility Contract Gate **PASS**.
3. Matrix: the [decision chain](../architecture/legal-eligibility-matrix.md). Decision model amendment. Legal Eligibility Matrix Gate **not PASS**. Evidence rules are not encoded. The six-tuple lookup is not the live geometry.
4. Only then normalize the facts into the inputs `r5_required_set` already evaluates, and only then change the pack or the engine.

Step 4 stays locked. Runtime is not authorized. Minimal Recruitment → HR is not this slice.

## History

- 2026-10-02: **Decision model amendment.** Citizenship class → stay basis → work authorization basis → valid for this employment → evidence for RPM. Six-tuple population is not accepted. Evidence rules are not encoded. Legal Eligibility Matrix Gate **not PASS**. `r5_required_set` stays the only required-document authority. Feat stays locked. Runtime not authorized. min HR stays not scheduled. HostFlow v1 is not release-ready.
- 2026-10-02: **Matrix opened.** SoT [legal-eligibility-matrix.md](../architecture/legal-eligibility-matrix.md). Cell key is the contract's closed fact set. `visa_d`, `karta_pobytu`, and `''` are distinct cells with the outcome slot unassigned. No document and no outcome id is assigned. Legal Eligibility Matrix Gate **not PASS**. `r5_required_set` stays the only required-document authority. Feat stays locked. Runtime not authorized. min HR stays not scheduled. HostFlow v1 is not release-ready.
- 2026-10-02: **Legal Eligibility Contract Gate PASS.** Evidence is the corrected contract-open. Closed fact set accepted. Card vocabulary, legal-policy vocabulary, and pack tokens stay separate. `visa_d` is not `visa`. Empty `stay_basis` stays its own state. `r5_required_set` stays the only required-document authority. `required_set_override` and `candidate_default` stay outcome shapes with no fact assigned. Matrix stays empty and is the next separate stage. Feat stays locked. Runtime not authorized. min HR stays not scheduled. HostFlow v1 is not release-ready.
- 2026-10-02: **Contract opened.** SoT [legal-eligibility-contract.md](../architecture/legal-eligibility-contract.md) (`legal_eligibility.v1`). Facts, vocabulary, authority, and outcome shape are named. Not accepted. Legal Eligibility Contract Gate **not PASS**. Matrix not written. Runtime not authorized. Feat locked. `visa_d` is not mapped onto `visa`. min HR stays not scheduled. HostFlow v1 is not release-ready.
- 2026-10-02: **Brief opened.** Facts and collapsed distinctions recorded from `9269fa19`. Feat locked. Contract not opened. Matrix not written. `visa_d` is not mapped onto `visa`. Implementation not authorized. min HR stays not scheduled.
- 2026-09-30: **NAMED** by queue amendment [#394](https://github.com/igortatarynovich/HostFlow/pull/394). The amendment scheduled this brief and did not write the business rules.
