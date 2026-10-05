# HR Employee Record Projection

**Status:** **Opened** — information architecture only. No schema. No runtime. No new fact. No change to `requirement_resolution.v1`, Legal Eligibility, requirements, evidence, or Ready to Start.  
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

A group shows a canonical address, an Employment or process record, or an evidence row. It does not create an HR copy of that value. Edit writes the live owner. Verify records a confirmation on `workforce_hr_verified_fields` and does not replace the owner. View does not write.

Requirements `satisfied` and Legal Eligibility `pass` stay different readings. Approved evidence may satisfy `legal_stay_confirmation` and `labor_market_access` while the legal gate stays `blocked` on `operator_verification`, until the right to work is matched to this Employment.

---

## Dane osobowe

Person identity. Citizenship is shown here. It is not asked again as the first step of a stay wizard.

| Order | What is shown | Address | Act |
|---|---|---|---|
| 1 | Legal name | `candidates.first_name`, `candidates.last_name` | edit |
| 2 | Latin name | `candidates.first_name_latin`, `candidates.last_name_latin` | edit |
| 3 | Birth date | `candidates.personal_data.birth_date` | edit |
| 4 | Citizenship | `candidates.personal_data.citizenship` | edit |
| 5 | Phone and country code | `candidates.phone`, `candidates.phone_country_code` | edit |
| 6 | Email | `candidates.email` | edit |
| 7 | Address | `candidates.personal_data` `address`, `city`, `country_code`, `address_latin`, `city_latin` | edit |
| 8 | PESEL | `candidates.personal_data.pesel` | edit |
| 9 | Languages | `candidates.languages` | edit |

`WorkforceEmployee.display_name` is the HR label, view. Handoff and Employment snapshots are view. An identity document's number and dates stay on the `documents` row and are not copied here. A confirmation is verify. No Employment record lives in this group.

---

## Pobyt i prawo do pracy

The legal chain for this Employment, in chain order. The same stay and work facts Recruitment recorded. No question sequence.

| Order | What is shown | Address | Act |
|---|---|---|---|
| 1 | Stay basis | `candidates.personal_data.operator_facts.stay_basis` | edit |
| 2 | Stay parameters and validity | `operator_facts` `visa_type`, `visa_purpose`, `stay_valid_to` | edit |
| 3 | Work basis | `operator_facts.employments[<employment_id>]` `work_authorization_basis` | edit |
| 4 | Procedure | that same work object, `procedure_type` | edit |
| 5 | Valid for this Employment | the chain reading `valid_for_this_employment` | view |
| 6 | Legal Eligibility outcome | `hr_legal_eligibility_gate_decisions` for this Employment | view |
| 7 | Stay and work requirements | `hr_employment_requirements` `legal_stay_confirmation`, `labor_market_access` | view |

Evidence for those requirements is not edited here. It is shown under Dokumenty. Choosing `karta_pobytu` does not place documents in this group. `operator_verification` remains a blocked gate. It does not become `pass` because the requirement rows are `satisfied`.

---

## Zatrudnienie

This Employment and the agreements that represent it.

| Order | What is shown | Address | Act |
|---|---|---|---|
| 1 | State | `hr_employments.state` | view |
| 2 | Client | `hr_employments.client_company_id` | edit |
| 3 | Vacancy of this hire | `hr_employments.vacancy_id` | view |
| 4 | Start and end | `hr_employments.started_on`, `hr_employments.ended_on` | edit |
| 5 | Agreed terms | current `hr_employment_terms` snapshot | edit |
| 6 | Contract cards | `workforce_employments` of this Employment | view |
| 7 | Ready to Start | latest `hr_ready_to_start_decisions` | view |

The card is not the Employment. Ready to Start is the stored decision. This group does not recompute it.

---

## Kwalifikacje i uprawnienia

Professional facts already stored for the person. A fact does not create a requirement.

| Order | What is shown | Address | Act |
|---|---|---|---|
| 1 | Licence country, categories, validity | `operator_facts` `licence_issuing_country`, `licence_categories`, `licence_valid_to` | edit |
| 2 | Code 95 presence and validity | `operator_facts` `code95_presence`, `code95_valid_to` | edit |
| 3 | Tachograph | `operator_facts` `tachograph_presence`, `tachograph_issuing_country`, `tachograph_valid_to` | edit |
| 4 | ADR | `operator_facts` `adr_presence`, `adr_issuing_country`, `adr_valid_to` | edit |
| 5 | CE and Code 95 requirements | `hr_employment_requirements` `driver_entitlement`, `professional_qualification` | view |

The licence file and the qualification card are documents. They appear under Dokumenty when a requirement still needs them.

---

## Doświadczenie

Prior jobs captured at intake. They are not this Employment.

| Order | What is shown | Address | Act |
|---|---|---|---|
| 1 | Prior employment rows | `candidate_employments` | view |

This group does not copy a prior job onto `hr_employments`.

---

## Dokumenty

Files and the evidence that links them to a requirement. The group does not decide which file is required.

| Order | What is shown | Address | Act |
|---|---|---|---|
| 1 | Document rows | `documents` for this person | view |
| 2 | Candidate Evidence | `candidate_evidence` and its document links | verify |
| 3 | What this Employment still needs | the HR required set already materialized for the open requirements | view |

Verify is the existing evidence status. It is not a second satisfaction flag. A Belarus stay of `karta_pobytu` plus `employer_declaration` shows the card, the decision, and the declaration only because those requirements resolved to `needs_evidence` and `r5_required_set` materialized them.

---

## Badania

Medical and psychological facts, then their documents when a policy has named them.

| Order | What is shown | Address | Act |
|---|---|---|---|
| 1 | Medical presence | `operator_facts.medical_presence` | edit |
| 2 | Psychological presence | `operator_facts.psych_presence` | edit |
| 3 | Certificates | `documents` whose type is the medical or psychological certificate | view |

Presence does not add those certificates to the required set.

---

## Ubezpieczenia

The insurance process record. It is not a person fact and it is not re-homed.

| Order | What is shown | Address | Act |
|---|---|---|---|
| 1 | Insurance profile | `workforce_insurance_profiles` | view |

---

## ZUS

The ZUS process record. Registration stays a post-start obligation.

| Order | What is shown | Address | Act |
|---|---|---|---|
| 1 | ZUS profile | `workforce_zus_profiles` | view |

---

## Historia

Append-only readings. Nothing in this group is edited.

| Order | What is shown | Address | Act |
|---|---|---|---|
| 1 | Handoff | `hr_employments` handoff columns and `candidate_snapshot` | view |
| 2 | Legal Eligibility decisions | `hr_legal_eligibility_gate_decisions` | view |
| 3 | Ready to Start decisions | `hr_ready_to_start_decisions` | view |
| 4 | Requirement rows of this Employment | `hr_employment_requirements` | view |

---

## Out of this slice

- A screen, including a redesign of `#hr-verification`.  
- A new fact, column, requirement, evidence variant, or stay basis.  
- Ukraine, or any legal case beyond the Belarus vertical already shipped.  
- Moving Employment lifecycle, Legal Eligibility, requirements, evidence, or Ready to Start onto this projection. That planting is the next slice. Their authority stays where it is.

Feat stays locked. HostFlow v1 is not release-ready.
