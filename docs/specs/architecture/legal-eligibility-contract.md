# Legal Eligibility Contract

**Status:** **Accepted** (L2 contract — Legal Eligibility Contract Gate **PASS**).  
**Date:** 2026-10-02  
**Trusted base:** `integration/release-product-a-b` @ `71f46e46`  
**Evidence:** the corrected contract-open on `docs/legal-eligibility-contract-open`. No new legal fact, vocabulary token, policy outcome, or document rule.  
**Machine id:** `legal_eligibility.v1` — named here. No runtime module in this slice.  
**Related:** [Legal Eligibility brief](../tasks/legal-eligibility-requirement-policy.md) · [Requirement Policy Authority](requirement-policy-authority.md) (`requirement_policy_authority.v1`) · [Hiring eligibility composition](hiring-eligibility-composition.md) · [document policy platform pack](../platform/document-policy-platform-pack-v1.json) · [Sequential queue](../tasks/sales-to-comms-sequential-queue.md)

**L0 checklist:** No new P-rule. No Passport or Manifest shape change. No Architecture RFC. Applies **P-02** (the requirement write stays on RPM) and **INV-01** (one authority for “must this candidate provide type X?”). Does not rewrite L0. Does not mint a second policy writer, a legal-eligibility engine, or a document matrix.

> This file is the SoT for which legal facts exist, which vocabulary they use, which authority may turn them into a required set, and what shape that policy outcome has.  
> Legal Eligibility interprets those facts into normalized inputs and an outcome shape. It is not a second authority for required documents. The final required set stays exclusively `r5_required_set`.  
> It does not assign a document type to a fact. That assignment is the matrix, and the matrix is not written.  
> It does not change the pack or the engine. Feat stays locked. Runtime is not authorized.  
> `visa_d` is not mapped onto `visa`. Minimal Recruitment → HR stays not scheduled. HostFlow v1 is not release-ready.  
> **Live model:** the [decision chain](#decision-chain). It replaces the six-tuple lookup. The Contract Gate **PASS** record below keeps the vocabulary, the authority, and the outcome shape. This amendment assigns no evidence list.

---

## Operator question (one)

For one candidate on one vacancy, **which normalized legal facts may change the required document set, in which vocabulary, under whose authority, and what kind of policy outcome is that change?**

No second question is this contract. Which document each fact value requires is the matrix. Satisfaction, eligibility, and transfer stay on the authorities already sealed for Hiring.

---

## Facts

A fact is an input the later matrix may branch on. A fact is not a document requirement. The list is closed. Storage below is what the [brief](../tasks/legal-eligibility-requirement-policy.md) measured on `9269fa19`. This contract does not add a column.

| Fact key | Recorded today | What it is not |
|---|---|---|
| `stay_basis` | `extra.poland_stay_basis`, copied unchanged into owner-context `residency_status` | a pack token; a document type |
| `citizenship` | `extra.citizenship` or `personal.citizenship`, copied into the owner context; not a `when` key of the candidate overrides | a stay-basis token |
| `employment_country` | not a `when` key of the candidate overrides; this contract names no column | a stay-basis token |
| `residence_permit_country` | not a `when` key of the candidate overrides; this contract names no column | a stay-basis token |
| `licence_issuing_country` | not a `when` key of the candidate overrides; this contract names no column | a stay-basis token |
| `qualification_jurisdiction` | Code 95 / qualification-card jurisdiction; not a `when` key; this contract names no column | a stay-basis token |

The list above is closed. `residence_permit_type` is not a fact key. The card does not store a permit type apart from `stay_basis`, and this contract does not add that column.

`eu_member` on the country registry and `oswiadczenie_eligible_alpha2` on the pack (`UA`, `BY`, `MD`, `GE`) are reference lists. They are not fact keys and they are not a second writer. A later matrix may read them. This contract does not.

Empty `stay_basis` (`''` in `POLAND_BASIS_VALUES`) is a recorded state. It is not a silent synonym of `visa_d` or `karta_pobytu`.

---

## Vocabulary

Three vocabularies. They are not aliases of each other.

**Card vocabulary** — the closed fact vocabulary of `stay_basis`, from `POLAND_BASIS_VALUES`:

`''`, `visa_d`, `visa_c`, `karta_pobytu`, `eu_citizen`, `waiting_for_trc`, `other`.

**Legal-policy vocabulary** — the vocabulary of normalized inputs Legal Eligibility may supply to RPM. This contract does not list its tokens and does not map a card token onto a pack token.

**Pack tokens** — the closed vocabulary `r5_required_set` already matches on `residency_status`:

`eu_citizen`, `visa`, `none`, `no_residence_card`, `card`.

Normative:

1. `visa_d` is not the pack token `visa`. `visa_c` is not `visa`. `karta_pobytu` is not `card`. `waiting_for_trc` and `other` are not pack tokens. Empty `stay_basis` is not a pack token.
2. The only spelling shared by the card vocabulary and the pack tokens is `eu_citizen`. That shared spelling is not an alias rule for any other token, and it does not make the legal-policy vocabulary either of those two lists.
3. The intake map that stores pack-like tokens as card values (`visa` / `visa_d` → `visa_d`, `card` / `residence_card` / `residence_permit` / `karta_pobytu` → `karta_pobytu`) is a one-way write. It is not the inverse normalization and it is not the legal-policy vocabulary.
4. Document-type aliases (`visa_d` and `visa_c` onto document type `visa`; `karta_pobytu` onto `residence_card`) are document identity. They are not card vocabulary, not legal-policy vocabulary, and not a policy rule.
5. This contract does not add a vocabulary of document types. Canonical document types stay the RPM outcome vocabulary.

---

## Authority

Recorded legal facts go to Legal Eligibility. Legal Eligibility interprets them into normalized inputs and an outcome shape for RPM. It is not a second authority for required documents. The final required set is exclusively `r5_required_set`.

One policy question remains the RPM question: must this candidate provide document type X?

| Question | Authority | Role |
|---|---|---|
| Which stay basis, citizenship, and jurisdiction are recorded? | Candidate card fields, copied into the document owner context without translation | **fact source** |
| Must this candidate provide canonical type X? | RPM `r5_required_set` ([requirement-policy-authority.md](requirement-policy-authority.md)) | **sole policy write** |
| Is requirement R satisfied? | Candidate Evidence bound to Document Link | **not this contract** |
| May this candidate transfer, and why not? | HE-3 composer consuming RPM | **consumer** |
| Does a document-type alias change `stay_basis`? | nobody | **not an authority** |
| Does the intake map define `visa_d` → `visa`? | nobody | **not an authority** |

Roles are closed: `fact source` · `sole policy write` · `consumer` · `reference input` · `not an authority` · `not this contract`.

A later slice may normalize a fact into an input `r5_required_set` already evaluates. It may not add a second answer to “must provide type X?”, and it may not make eligibility or transfer compute a legal matrix of their own.

---

## Expected policy outcomes

A policy outcome is one required document-type set for one candidate on one vacancy, produced by `r5_required_set`. The required-request flow already consumes that set. This contract does not add an outcome channel, a request state, or a transfer decision.

| Outcome id | Shape | Assigned by this contract |
|---|---|---|
| `required_set_override` | a require list and a remove list, the shape of the existing pack `when.residency_status` rows | to no fact value |
| `candidate_default` | no legal-fact override; the required set is whatever `r5_required_set` already returns when no legal override matches. The pack's current unmatched default (`driver_license`, `driver_qualification_card`, `tachograph_card`, `passport`) describes that existing path. It is not assigned to empty `stay_basis` or to any other fact | to no fact value |

No row of this contract pairs `visa_d`, `visa_c`, `karta_pobytu`, `waiting_for_trc`, `other`, a citizenship, or a country with a document type. That pairing is the matrix.

What a later matrix must be able to express, because the brief measured these as collapsed or as the only split:

| Distinction | Observed on `9269fa19` | Expected expressibility |
|---|---|---|
| `eu_citizen` vs `visa_d` | different required sets | must remain two fact values; aliasing `visa_d` onto `eu_citizen` or onto `visa` is not the rule |
| `visa_d` vs `karta_pobytu` | the same required set (candidate default) | must be expressible as two outcomes; this contract does not say which documents |
| `visa_d` vs empty `stay_basis` | the same required set | must be expressible as two outcomes; this contract does not say which documents |
| `visa_c` vs `visa_d` | the same required set | two fact values; whether the outcomes differ is a matrix cell |
| citizenship, employment country, permit country, licence country, qualification jurisdiction | not matched | fact keys exist; whether any of them changes the set is a matrix cell |

“Expressible as two outcomes” means the matrix has a cell for each value. It does not mean this contract fills the cell, and it does not mean the two cells must differ. The [brief](../tasks/legal-eligibility-requirement-policy.md) completion proof is that they differ when the business rules say they must, and that they match when the rules say they must not. Those rules are the matrix.

---

## Legal Eligibility Contract Gate

**Outcome:** **PASS**. Evidence is this Accepted file. The matrix stays empty and is the next separate stage. It is not opened. Feat stays locked. Runtime is not authorized.

PASS holds because all of the following are true:

1. This file is **Accepted** and is the SoT for facts, vocabulary, authority, and outcome shape.  
2. The fact table, the three vocabularies, the authority table, and the two outcome ids are unchanged except by a later slice that the queue names.  
3. The matrix is still not in this file: no fact value is paired with a require list or a remove list. `required_set_override` and `candidate_default` stay shapes assigned to no fact value.  
4. `visa_d` is not defined as pack token `visa`. Empty `stay_basis` stays its own card state. Document-type aliases are not adopted as the stay-basis match.  
5. `r5_required_set` remains the exclusive authority for the final required set. Eligibility, transfer, and `ready_for_employment.v1` are unchanged.  
6. No pack change, no engine change, no new column, and no runtime module of `legal_eligibility.v1`. Feat stays locked.  
7. Minimal Recruitment → HR is not scheduled. HostFlow v1 is not declared release-ready.

This PASS does not assign `required_set_override` or `candidate_default` to a legal fact, does not fill the matrix, and does not change RPM, eligibility, transfer, `ready_for_employment.v1`, HR, or the database schema.

---

## Out of this slice

- The legal matrix (which documents each distinction requires).  
- Normalization of card tokens into pack inputs.  
- Pack or engine edits.  
- A Python or JSON machine copy. The id `legal_eligibility.v1` is reserved; it is not shipped.  
- Employee creation, auto-accept, `ready_for_employment.v1` changes.  
- Minimal Recruitment → HR.  
- Mapping `visa_d` onto `visa`.  
- Release Readiness Gate. HostFlow v1 stays not release-ready.

---

## Decision chain

This amendment is the live Legal Eligibility model. It is dated after `5b68286f` ([#399](https://github.com/igortatarynovich/HostFlow/pull/399)). The six-tuple lookup is not the live geometry. A population of that lookup is not accepted. No database column is added. No runtime module is added.

Legal Eligibility answers two questions, for employment in Poland:

1. Does this person have a lawful basis to be in Poland?
2. Does this person have a lawful basis to perform this employment?

A level is determined only when the previous level makes it unambiguous. Otherwise the chain stops for the operator and names no document.

```text
citizenship_class
  → stay_basis
  → work_authorization_basis
  → valid_for_this_employment
```

This chain is the whole Legal Eligibility model. It does not take `kod zawodu`.

`employment_country`, `residence_permit_country`, `licence_issuing_country`, and `qualification_jurisdiction` are not inputs of this chain. Driving licence, Code 95, ADR, and profession are not inputs of this chain.

### citizenship_class

Closed: `pl`, `eu_eea_ch`, `third_country`.

The class is derived from recorded citizenship. Absent citizenship does not become `third_country`. `eu_member` on the country registry is a reference the later encoding may read. This amendment does not publish the EU/EEA/Swiss country list. The card token `eu_citizen` is not this class.

### stay_basis

Closed: `not_required`, `visa_d`, `visa_c`, `karta_pobytu`, `visa_free`, `waiting_for_trc`, `special_protection`, `other`, `none`.

`not_required` is the determined stay for `pl` and for `eu_eea_ch` on ordinary employment in Poland. It is not a card token. Empty card `stay_basis` (`''`) is not `none`, not `not_required`, not `visa_d`, and not `karta_pobytu`. `none` means there is no stay basis yet. It is not ineligible: the employer may still be obtaining the stay and the work authorization. A work authorization does not replace a stay basis.

`visa_d` and `visa_c` stay distinct. Neither is the pack token `visa`. `visa_free` is named here and is not a card token today. `special_protection` is the group for special status or protection. This amendment does not enumerate those statuses and does not give them one work rule. `karta_pobytu` is not a sufficient stay fact for work: the card is the document issued after a permit, and the decision determines the kind of permit. `residence_permit_type` is still not a fact key, and this amendment adds no column for it.

### work_authorization_basis

Closed: `not_required`, `included_in_stay`, `separate_required`.

`not_required` means no separate permit. `included_in_stay` means the right to work follows from the residence status or its decision. `separate_required` means a separate permit or declaration. Lawful stay does not by itself select one of these, except for the two citizenship classes below. `waiting_for_trc` does not select one: a pending procedure may keep stay lawful and does not create the right to work. `karta_pobytu` does not select one until the decision is known. `visa_d` and `visa_c` do not select one until the visa type and purpose are known. `other`, `visa_free`, `special_protection`, and `none` do not select one in this amendment.

When the chain cannot choose one closed value, the step is an operator hold. An operator hold is not a fourth basis and it names no document.

For `pl` and for `eu_eea_ch`, stay is `not_required` and work authorization is `not_required`.

### valid_for_this_employment

Closed: `yes`, `no`, `operator_verification`.

This is the link to this employment. It is not another country axis. A decision or a separate authorization may name the employer and the conditions; work outside those conditions is not authorized. When work authorization is `not_required`, this step is `yes`. When it is `included_in_stay` or `separate_required`, this step is `operator_verification` until a later rule matches the decision or the authorization to this employment. This amendment does not match them.

### Evidence

The only handoff to RPM is still one outcome id, `required_set_override` or `candidate_default`. RPM `r5_required_set` stays the sole writer of the required set. This amendment assigns neither id and names no require list and no remove list.

A later encoding must be able to express, without collapsing the steps, a third-country `karta_pobytu` whose decision includes work and is valid for this employment, a third-country `visa_d` whose work authorization is separate, and a third-country `none` that is not yet eligible to work and is not ineligible as a candidate. That encoding is not this amendment. `visa_d` is not mapped onto `visa`.

### Other layers

Three layers meet only in RPM. This canon is the first layer. The other two are not opened here.

| Layer | Question | This canon |
|---|---|---|
| Legal Eligibility | lawful stay in Poland, and a lawful basis for this employment | the chain above |
| Profession / vacancy | professional documents for the vacancy | not Legal Eligibility |
| Work Authorization Procedure | what a submission requires | [opened](work-authorization-procedure-contract.md); this file does not define it |

Requirement Resolution is not one of these layers. It consumes their definitions. [requirement-resolution-contract.md](requirement-resolution-contract.md) (`requirement_resolution.v1`) names which Employment requirement applies, which fact is missing when applicability cannot yet be resolved, and which accepted evidence variant may satisfy it. It does not define this chain and it assigns no evidence list. The CE, Code 95, and issuing-country case is [opened beside it](ce-code95-issuing-country.md). That case does not enter this chain.

A profession preset belongs to the vacancy layer. A Driver CE preset may name a CE licence, Code 95, and a tachograph card, and a vacancy may add ADR. This canon does not write that preset.

A procedure preset is country + procedure type + `kod zawodu`. The occupation code does not by itself list documents: the same driver can use different work-authorization procedures. Submission readiness, milestones, and a reason on each required document belong to that slice. RPM `r5_required_set` stays the only writer. This canon adds no preset, no milestone, and no second writer.

Legal document lists that would prove this chain are not encoded here. They are not a `kod zawodu` list and they are not a procedure preset.

### Default policy

A preset is default policy. It is not an absolute prohibition. Legal Eligibility is not an insurmountable system ban: an authorized operator may continue only by an explicit audited override. The same principle is reserved for a later profession preset and for Work Authorization Procedure. This amendment does not open those slices and does not add a column.

`operator_verification` and an operator hold are chain states. They are not this override.

| Action | Who | Effect |
|---|---|---|
| `waive_requirement` | authorized operator | this requirement is lifted for this candidate and this process |
| `override_readiness` | authorized operator | the process may continue; no requirement becomes satisfied or waived |
| `update_preset` | administrator | the default rule changes for later cases |

A waive and a readiness override each record one reason from this closed set: `not_required`, `rule_changed`, `different_procedure`, `authority_confirmed`, `other`. Each record has the actor and the timestamp.

Four facts stay separate. `r5_required_set` does not mutate.

| Fact | Meaning |
|---|---|
| `r5_required_set` | what policy requires |
| evidence | what was actually obtained |
| waiver | which requirement the operator explicitly lifted for this process and this candidate |
| effective readiness | required − satisfied − waived |

`r5_required_set` stays the sole writer of the system required set. A waive does not delete that requirement and does not rewrite `r5_required_set`. Satisfaction is Candidate Evidence bound to Document Link. A requirement is missing only when policy requires it, evidence does not satisfy it, and no waiver lifts it. HostFlow does not treat “present in `r5_required_set` and no new upload” as the whole of missing.

`override_readiness` does not mark a requirement satisfied and does not mark it waived. The blockers stay. The operator allows the transition, and the audit records that exception. A later reader can tell a lifted requirement from a process that continued with the requirement still open.

The audit keeps the system requirement, then the operator action, then that the process continued.

Five `rule_changed` waives of the same requirement are a review signal for the administrator. The system does not edit the preset from that count. Only `update_preset` changes the default for later cases.

### Requirement and evidence

A requirement is not an upload slot. A document is evidence. One evidence object may satisfy more than one requirement, and more than one source of that requirement: vacancy, profession preset, Legal Eligibility, or a later Work Authorization Procedure. Provenance stays on the requirement. The same physical document is not uploaded again only because another source names it.

An EU driving licence that carries a valid Code 95 may satisfy both the applicable driving-licence requirement and the Code 95 requirement. A driving licence without Code 95 satisfies only the licence requirement. Code 95 stays unsatisfied on its own when policy requires it. Driving licence, Code 95, and work-authorization evidence are not separate upload slots when one document supplies that evidence. The same rule covers a residence card and its decision, a passport, and an ADR certificate. Which issuing country uses that one file, and which keeps the licence and the qualification card separate, is the [CE case](ce-code95-issuing-country.md). This amendment writes no driver preset, no Code 95 legal rule, and no extraction.

Code 95 is not a Legal Eligibility input. It shows the later layer: policy can still require it, evidence can satisfy it from a licence that already carries it, and an authorized operator can waive that requirement with `rule_changed`. The system row stays in the audit. The submission is ready when effective readiness has no remaining blocker. `override_readiness` is not that ready state.

Feat stays locked. Runtime is not authorized. Minimal Recruitment → HR stays not scheduled. HostFlow v1 is not release-ready. The Matrix Gate is not passed by this amendment. Work Authorization Procedure is opened in its own contract and is not defined here.
