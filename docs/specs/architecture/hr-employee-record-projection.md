# HR Employee Record Projection

**Status:** **Opened** — information architecture of the ten groups. This file names each canonical address and the storage that holds it today. It adds no group and no fact. No change to `requirement_resolution.v1`, Legal Eligibility, requirements, evidence, or Ready to Start.  
**Date:** 2026-10-05  
**Parents:** [Employee Record & Employment Lifecycle](employee-record-employment-lifecycle-contract.md) · [Employee Data ownership](employee-record-employment-lifecycle-contract.md#employee-data-ownership) · [Legal Eligibility](legal-eligibility-contract.md) (`legal_eligibility.v1`) · [Requirement Resolution](requirement-resolution-contract.md) (`requirement_resolution.v1`) · [Operator facts](operator-candidate-employment-facts.md)

**L0 checklist:** No new P-rule. No Passport or Manifest shape change. No Architecture RFC. This projection does not rewrite L0 and does not author a required set.

> The HR employee record is a projection of owners that already exist. It is not a second person, not a questionnaire store, and not a wizard. Recruitment may ask citizenship, then stay, then work. HR shows those same values in the groups below.

`#hr-verification` is not redesigned here. Ukraine and any stay basis outside the Belarus case already shipped are not added here.

Feat stays locked. HostFlow v1 is not release-ready.

---

## Hierarchy

The operator surface is these groups, in this order. A Polish label is the group name. It is not a domain and not a fact key.

1. Dane osobowe  
2. Pobyt i prawo do pracy  
3. Zatrudnienie  
4. Kwalifikacje i uprawnienia  
5. Doświadczenie  
6. Dokumenty  
7. Badania  
8. Ubezpieczenia  
9. ZUS  
10. Historia  

## Canonical address and current storage

A canonical address names the fact or the record. Current storage is the place that holds the value today. The projection reads and writes the address. It does not read a Candidate bag as the owner.

`candidates.personal_data.operator_facts` is the current storage of stay, of the work fact for one Employment, and of licence, Code 95, tachograph, ADR, and medical presence. It is not the address of those facts. A later move of that storage keeps the address. It does not copy the value into an HR store, and it does not synchronize Recruitment into HR.

Edit writes the live owner of the address. Verify records a confirmation on `workforce_hr_verified_fields` and does not replace the owner. View does not write.

Requirements `satisfied` and Legal Eligibility `pass` stay different readings. Approved evidence may satisfy `legal_stay_confirmation` and `labor_market_access` while the legal gate stays `blocked` on `operator_verification`, until the right to work is matched to this Employment.

---

## Dane osobowe

Person identity. Citizenship is shown here. It is not asked again as the first step of a stay wizard.

| Order | What is shown | Canonical address | Current storage | Act |
|---|---|---|---|---|
| 1 | Legal name | `person.legal_name` | `candidates.first_name`, `candidates.last_name` | edit |
| 2 | Latin name | `person.latin_name` | `candidates.first_name_latin`, `candidates.last_name_latin` | edit |
| 3 | Birth date | `person.birth_date` | `candidates.personal_data.birth_date` | edit |
| 4 | Citizenship | `person.citizenship` | `candidates.personal_data.citizenship` | edit |
| 5 | Phone and country code | `person.phone` | `candidates.phone`, `candidates.phone_country_code` | edit |
| 6 | Email | `person.email` | `candidates.email` | edit |
| 7 | Address | `person.address` | `candidates.personal_data` `address`, `city`, `country_code`, `address_latin`, `city_latin` | edit |
| 8 | PESEL | `person.pesel` | `candidates.personal_data.pesel` | edit |
| 9 | Languages | `person.languages` | `candidates.languages` | edit |

`WorkforceEmployee.display_name` is the HR label, view. Handoff and Employment snapshots are view. An identity document's number and dates stay on the `documents` row and are not copied here. A confirmation is verify. No Employment record lives in this group.

---

## Pobyt i prawo do pracy

The legal chain for this Employment, in chain order. The same stay and work facts Recruitment recorded. No question sequence.

| Order | What is shown | Canonical address | Current storage | Act |
|---|---|---|---|---|
| 1 | Stay basis | `stay.basis` | `candidates.personal_data.operator_facts.stay_basis` | edit |
| 2 | Stay parameters and validity | `stay.visa_type`, `stay.visa_purpose`, `stay.valid_to` | the same bag, keys `visa_type`, `visa_purpose`, `stay_valid_to` | edit |
| 3 | Work basis | `work.authorization_basis` | `operator_facts.employments[<employment_id>].work_authorization_basis` | edit |
| 4 | Procedure | `work.procedure_type` | that same work object, `procedure_type` | edit |
| 5 | Valid for this Employment | `legal.valid_for_this_employment` | the chain reading of those facts | view |
| 6 | Legal Eligibility outcome | `legal.outcome` | `hr_legal_eligibility_gate_decisions` for this Employment | view |
| 7 | Stay and work requirements | `requirement.legal_stay_confirmation`, `requirement.labor_market_access` | `hr_employment_requirements` | view |

Evidence for those requirements is not edited here. It is shown under Dokumenty. Choosing `karta_pobytu` does not place documents in this group. `operator_verification` remains a blocked gate. It does not become `pass` because the requirement rows are `satisfied`.

---

## Zatrudnienie

This Employment and the agreements that represent it.

| Order | What is shown | Canonical address | Current storage | Act |
|---|---|---|---|---|
| 1 | State | `employment.state` | `hr_employments.state` | view |
| 2 | Client | `employment.client` | `hr_employments.client_company_id` | edit |
| 3 | Vacancy of this hire | `employment.vacancy` | `hr_employments.vacancy_id` | view |
| 4 | Start and end | `employment.started_on`, `employment.ended_on` | `hr_employments.started_on`, `hr_employments.ended_on` | edit |
| 5 | Agreed terms | `employment.terms` | current `hr_employment_terms` snapshot | edit |
| 6 | Contract cards | `employment.contract_cards` | `workforce_employments` of this Employment | view |
| 7 | Ready to Start | `employment.ready_to_start` | latest `hr_ready_to_start_decisions` | view |

The card is not the Employment. Ready to Start is the stored decision. This group does not recompute it.

---

## Kwalifikacje i uprawnienia

Professional facts already stored for the person. A fact does not create a requirement.

| Order | What is shown | Canonical address | Current storage | Act |
|---|---|---|---|---|
| 1 | Licence country, categories, validity | `qualification.licence_country`, `qualification.licence_categories`, `qualification.licence_valid_to` | `operator_facts` `licence_issuing_country`, `licence_categories`, `licence_valid_to` | edit |
| 2 | Code 95 presence and validity | `qualification.code95_presence`, `qualification.code95_valid_to` | `operator_facts` `code95_presence`, `code95_valid_to` | edit |
| 3 | Tachograph | `qualification.tachograph` | `operator_facts` `tachograph_presence`, `tachograph_issuing_country`, `tachograph_valid_to` | edit |
| 4 | ADR | `qualification.adr` | `operator_facts` `adr_presence`, `adr_issuing_country`, `adr_valid_to` | edit |
| 5 | CE and Code 95 requirements | `requirement.driver_entitlement`, `requirement.professional_qualification` | `hr_employment_requirements` | view |

The licence file and the qualification card are documents. They appear under Dokumenty when a requirement still needs them.

---

## Doświadczenie

Prior jobs captured at intake. They are not this Employment.

| Order | What is shown | Canonical address | Current storage | Act |
|---|---|---|---|---|
| 1 | Prior employment rows | `experience.prior_jobs` | `candidate_employments` | view |

This group does not copy a prior job onto `hr_employments`.

---

## Dokumenty

Files and the evidence that links them to a requirement. The group does not decide which file is required.

| Order | What is shown | Canonical address | Current storage | Act |
|---|---|---|---|---|
| 1 | Document rows | `document.rows` | `documents` for this person | view |
| 2 | Candidate Evidence | `evidence.rows` | `candidate_evidence` and its document links | verify |
| 3 | What this Employment still needs | `requirement.required_set` | the HR required set already materialized for the open requirements | view |

Verify is the existing evidence status. It is not a second satisfaction flag. A Belarus stay of `karta_pobytu` plus `employer_declaration` shows the card, the decision, and the declaration only because those requirements resolved to `needs_evidence` and `r5_required_set` materialized them.

---

## Badania

Medical and psychological facts, then their documents when a policy has named them.

| Order | What is shown | Canonical address | Current storage | Act |
|---|---|---|---|---|
| 1 | Medical presence | `medical.presence` | `operator_facts.medical_presence` | edit |
| 2 | Psychological presence | `psych.presence` | `operator_facts.psych_presence` | edit |
| 3 | Certificates | `medical.certificates` | `documents` whose type is `medical_certificate` or `psychological_certificate` | view |

Presence does not add those certificates to the required set.

---

## Ubezpieczenia

The insurance process record. It is not a person fact and it is not re-homed.

| Order | What is shown | Canonical address | Current storage | Act |
|---|---|---|---|---|
| 1 | Insurance profile | `insurance.profile` | `workforce_insurance_profiles` | view |

---

## ZUS

The ZUS process record. Registration stays a post-start obligation.

| Order | What is shown | Canonical address | Current storage | Act |
|---|---|---|---|---|
| 1 | ZUS profile | `zus.profile` | `workforce_zus_profiles` | view |

---

## Historia

Append-only readings. Nothing in this group is edited.

| Order | What is shown | Canonical address | Current storage | Act |
|---|---|---|---|---|
| 1 | Handoff | `history.handoff` | `hr_employments` handoff columns and `candidate_snapshot` | view |
| 2 | Legal Eligibility decisions | `history.legal_decisions` | `hr_legal_eligibility_gate_decisions` | view |
| 3 | Ready to Start decisions | `history.ready_to_start` | `hr_ready_to_start_decisions` | view |
| 4 | Requirement rows of this Employment | `history.requirements` | `hr_employment_requirements` | view |

---

## Out of this slice

- A redesign of `#hr-verification`.  
- A new fact, column, requirement, evidence variant, or stay basis.  
- Ukraine, or any legal case beyond the Belarus vertical already shipped.  
- A change to the authority of Employment lifecycle, Legal Eligibility, requirements, evidence, or Ready to Start. This projection reads them. It does not decide them.

Feat stays locked. HostFlow v1 is not release-ready.
