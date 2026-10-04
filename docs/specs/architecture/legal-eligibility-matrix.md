# Legal Eligibility Matrix

**Status:** **Decision model** — six-tuple lookup stopped. Legal Eligibility Matrix Gate **not PASS**.  
**Date:** 2026-10-02  
**Trusted base:** `integration/release-product-a-b` @ `5b68286f` ([#399](https://github.com/igortatarynovich/HostFlow/pull/399))  
**Contract:** [legal-eligibility-contract.md](legal-eligibility-contract.md) (`legal_eligibility.v1`, Legal Eligibility Contract Gate **PASS**, [decision chain](legal-eligibility-contract.md#decision-chain)).  
**Machine id:** none. No runtime module.

> Legal Eligibility answers two questions for employment in Poland: whether the person has a lawful basis to be in Poland, and whether the person has a lawful basis to perform this employment.  
> The live geometry is `citizenship_class` → `stay_basis` → `work_authorization_basis` → `valid_for_this_employment`. It does not take `kod zawodu`.  
> A level is filled only when the previous level makes it unambiguous. This file assigns no evidence list.  
> `r5_required_set` stays the sole writer of the required set. Feat stays locked. Runtime is not authorized. Minimal Recruitment → HR stays not scheduled. HostFlow v1 is not release-ready.

---

## Chain

The vocabulary is the contract decision chain. This file does not add a value.

| Step | Closed values | This amendment |
|---|---|---|
| `citizenship_class` | `pl`, `eu_eea_ch`, `third_country` | derived from recorded citizenship; absent citizenship is not `third_country` |
| `stay_basis` | `not_required`, `visa_d`, `visa_c`, `karta_pobytu`, `visa_free`, `waiting_for_trc`, `special_protection`, `other`, `none` | `''` is an empty card field, not one of these values |
| `work_authorization_basis` | `not_required`, `included_in_stay`, `separate_required` | an operator hold is not a fourth value |
| `valid_for_this_employment` | `yes`, `no`, `operator_verification` | not a country axis |

`employment_country`, `residence_permit_country`, `licence_issuing_country`, and `qualification_jurisdiction` are not steps. Driving licence, Code 95, ADR, profession, and `kod zawodu` are not steps. A procedure preset is country + procedure type + `kod zawodu`, and that preset is not this matrix. Work Authorization Procedure is opened in its own contract and is not defined here.

There is no six-tuple cell and no default cell. A combination that this chain does not determine matches nothing.

---

## Determined levels

| From | Stay | Work authorization | Valid for this employment |
|---|---|---|---|
| `pl` | `not_required` | `not_required` | `yes` |
| `eu_eea_ch` | `not_required` | `not_required` | `yes` |
| `third_country` | not skipped | not chosen by citizenship | not chosen by citizenship |

`not_required` on stay is not the card token `eu_citizen` and not `''`.

These stays do not choose a work authorization. The step is an operator hold, and it names no document:

| Stay | Why the next step stays open |
|---|---|
| `visa_d` | visa type and purpose are still required; `visa_d` is not the pack token `visa` |
| `visa_c` | same, and it is not `visa_d` |
| `karta_pobytu` | the card is not sufficient; the decision determines the permit and may set work conditions |
| `waiting_for_trc` | a pending procedure does not create the right to work |
| `visa_free` | no work rule is recorded here |
| `special_protection` | no single work rule is recorded here |
| `other` | the operator selects it, or a later rule does |
| `none` | no stay basis yet; the candidate is not ineligible |
| `''` | the card field is empty; the stay is not determined |

A `separate_required` or `included_in_stay` result does not satisfy stay. Lawful stay does not by itself choose the work authorization, except the `pl` and `eu_eea_ch` rows above. When work authorization is `included_in_stay` or `separate_required`, `valid_for_this_employment` is `operator_verification` until a later rule matches that authorization to this employment.

An operator hold is not an outcome id. It is not `candidate_default`.

---

## Evidence

RPM receives the evidence outcome of a fully determined chain, not a required document set. `r5_required_set` consumes that outcome and stays the sole writer of the required set. This amendment assigns no outcome, so it hands RPM nothing.

`required_set_override` remains a require list and a remove list. `candidate_default` remains future outcome schema and is assigned to no chain result. An unassigned chain result has no require list and no remove list.

A later encoding must be able to express these as separate chains. This file does not assign their documents:

- `third_country` → `karta_pobytu` → a decision that includes work → `yes` for this employment → the card and the decision.
- `third_country` → `visa_d` → `separate_required` → `yes` for this employment → the visa and the separate authorization.
- `third_country` → `none` → not yet able to work, and not ineligible as a candidate.

`visa_d` is not given the pack row for `visa`. `karta_pobytu` is not given the pack row for `card`. `''` is not given the pack row for `none` or `no_residence_card`.

---

## Default policy

The chain is default policy, not a ban. An authorized operator may `waive_requirement` for one document on this candidate and this process, or `override_readiness` while other system blockers stay listed. An administrator `update_preset` changes the default for later cases. The system does not. Five `rule_changed` waives of the same requirement are a review signal, not an edit.

The reason is one of `not_required`, `rule_changed`, `different_procedure`, `authority_confirmed`, `other`, with the actor and the timestamp. The audit keeps the system requirement.

`r5_required_set` is what policy requires. Evidence is what was obtained. A waiver is the requirement an operator lifted for this process and this candidate. Effective readiness is required − satisfied − waived. `r5_required_set` does not mutate, and a waive does not rewrite it. `override_readiness` does not mark a requirement satisfied or waived: the blockers stay, and the audit records the exception. A requirement is not an upload slot. One evidence object may satisfy more than one requirement and more than one source. An EU driving licence with a valid Code 95 may satisfy both the licence requirement and Code 95. A licence without Code 95 leaves Code 95 unsatisfied when policy requires it. This matrix writes no driver preset and no extraction.

`operator_verification` is not this override. `kod zawodu` is not this section. Work Authorization Procedure is opened in its own contract and is not defined here.

---

## Legal Eligibility Matrix Gate

**Outcome:** **not PASS**. The decision model is recorded. The evidence rules are not encoded.

PASS when, and only when, all of the following hold:

1. The chain order and the closed values above are unchanged.  
2. `visa_d`, `visa_c`, `karta_pobytu`, `waiting_for_trc`, `none`, and `''` remain distinct.  
3. Every unambiguous Polish rule has exactly one outcome id. An operator hold still has no require list and no remove list.  
4. A `required_set_override` names its require list and its remove list. This amendment has none.  
5. Licence, Code 95, ADR, profession, and qualification jurisdiction stay outside Legal Eligibility. `r5_required_set` is still the only required-document authority.  
6. No pack change, no engine change, no new column, and no runtime module. That PASS does not authorize a runtime module. Feat stays locked. Minimal Recruitment → HR is not scheduled. HostFlow v1 is not declared release-ready.

---

## History

- 2026-10-02: **Decision model.** The six-tuple lookup is stopped. Its population is not accepted.  
- 2026-10-02: **Opened** at [#399](https://github.com/igortatarynovich/HostFlow/pull/399). The cell key was exactly these six facts, in this order, and no other key: `stay_basis`, `citizenship`, `employment_country`, `residence_permit_country`, `licence_issuing_country`, `qualification_jurisdiction`. That geometry is not live.
